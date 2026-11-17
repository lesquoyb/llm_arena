/* Repetition dispersion; score fixtures come from /api/fight-fixtures. */
async function loadRepetitionFixtures(key,args) {
  if(S.repetitionFixturesPending===key)return;
  S.repetitionFixturesPending=key;
  try {
    const value=await runResource('/api/fight-fixtures',args);
    const observations=[],rows=value.rows,ids=value.ids;
    for(let index=0;index<rows.length;index+=5) {
      const side=rows[index+3],outcome=rows[index+4];
      observations.push({session:ids[rows[index]],opponent:ids[rows[index+1]],seed:rows[index+2],side,
        status:outcome===3?'failed':'completed',winner:outcome===1?-1:outcome===2?side:outcome===0?1-side:null});
    }
    S.repetitionFixtures={key,observations};
    const node=$('#repetition-variance');
    if(node&&S.tab==='summary'&&S.detail)LiveDOM.replace(node,repetitionVariance(S.detail,overviewData(S.detail)));
  } catch(error) {
    if(error.name!=='AbortError')toast(error.message,true);
  } finally {if(S.repetitionFixturesPending===key)S.repetitionFixturesPending=null;}
}
function repetitionVariance(d,data) {
  if(d.metadata.config?.evolutionary)
    return '<section class="overview-card" id="repetition-variance"><div class="overview-section-head"><h2>Variation between repetitions</h2></div><p class="muted">Later slots in this competition share parents. Use Strategy lineages and Evolutionary selection to compare their results; the independent-repetition chart does not apply.</p></section>';
  const metric=S.repetitionMetric||'score';
  const specs=new Map((d.metadata.config?.models||[]).map(model=>[model.id,model]));
  const number=value=>value===null||value===undefined||value===''?null:Number.isFinite(Number(value))?Number(value):null;
  const sessions=data.sessions.filter(session=>specs.get(session.model)?.provider!=='mock').map(session=>{
    const usage=measuredUsage(session);
    return {...session,metrics:{cost:session.reconciliation_required||Number(session.money_reserved||0)>0?null:number(session.cost_spent),
      tools:number(session.steps),time:number(session.wall_seconds)===null?null:Number(session.wall_seconds)/60,
      tokens:usage.complete&&Number.isFinite(usage.input_tokens)&&Number.isFinite(usage.output_tokens)?usage.input_tokens+usage.output_tokens:null}};
  });
  // Score dispersion needs exact fixtures (opponent, seed, side). The server
  // sends them as a compact integer array for the selected category only.
  let observations=[];
  if(metric==='score') {
    const stage=data.scope.round?.startsWith('stage:')?data.scope.round.slice(6):undefined;
    const key=JSON.stringify([S.run,data.scope.source,stage||null]);
    if(S.repetitionFixtures?.key!==key) {
      loadRepetitionFixtures(key,{run:S.run,source:data.scope.source,stage});
      return `<section class="overview-card" id="repetition-variance"><div class="overview-section-head"><h2>Variation between repetitions</h2></div><p class="muted">Loading repetition fixtures…</p></section>`;
    }
    observations=S.repetitionFixtures.observations;
  }
  const byRound=RepetitionStats.summarize(sessions,observations,metric);
  const all=S.repetitionRounds==='all';
  const grouped=all?RepetitionStats.allObservations(byRound):S.repetitionRounds==='model'?RepetitionStats.poolModels(byRound):S.repetitionRounds==='pooled'?RepetitionStats.poolRounds(byRound):byRound;
  const rows=orderCandidates(grouped,row=>row.model);
  for(const row of rows)row.expected=Math.max(row.points.length,(row.groups||1)*(runScope().replicate?1:Number(d.metadata.config?.replicates||0)));
  const names={score:'Combat score',cost:'Preparation cost',tools:'Tool calls',time:'Preparation time (min)',tokens:'Preparation tokens'};
  const format=value=>value===null||!Number.isFinite(value)?'—':metric==='score'?pct(value):metric==='cost'?money(value):fmt(value,1);
  const spread=value=>value===null||!Number.isFinite(value)?'—':metric==='score'?fmt(100*value,1)+' pp':format(value);
  const values=rows.flatMap(row=>row.points.map(point=>point.value)).filter(Number.isFinite);
  const W=1000,L=190,R=180,STEP=9;
  const maximum=metric==='score'?1:values.reduce((maximum,value)=>Math.max(maximum,value),1)*1.05;
  const x=value=>L+(W-L-R)*value/maximum;
  const key=point=>point.session+':'+point.generation+':'+point.condition;
  let nextY=44;
  const positions=rows.map(row=>{
    const placed=[],offsets=new Map();
    for(const point of row.points.filter(point=>point.value!==null)) {
      let offset=0;
      while(placed.some(previous=>Math.abs(previous.x-x(point.value))<STEP&&previous.offset===offset))offset+=STEP;
      placed.push({x:x(point.value),offset});offsets.set(key(point),offset);
    }
    const y=nextY;nextY+=Math.max(42,32+Math.max(0,...placed.map(point=>point.offset)));
    return {y,offsets};
  });
  const H=nextY-8;
  const roundLabel=row=>row.allObservations?`All rounds & tracks · ${row.rounds.length} round${row.rounds.length>1?'s':''}`:row.tracksPooled?`Feedback tracks pooled · ${row.rounds.length} shared rounds`:row.pooled?`All selected rounds · ${row.condition} (${row.rounds.length} shared)` : overviewRound(row.condition,row.generation);
  const label=row=>`${participantName(row.model)} · ${roundLabel(row)}`;
  const marks=rows.map((row,index)=>{
    const {y,offsets}=positions[index],stats=row.stats,color=overviewColor(row.model);
    const name=participantName(row.model);
    const box=stats.n?`<line x1="${x(stats.min)}" x2="${x(stats.max)}" y1="${y}" y2="${y}" stroke="${color}" stroke-width="2"/><rect x="${x(stats.q1)}" y="${y-6}" width="${Math.max(1,x(stats.q3)-x(stats.q1))}" height="12" fill="${color}" fill-opacity=".17" stroke="${color}"/><line x1="${x(stats.median)}" x2="${x(stats.median)}" y1="${y-6}" y2="${y+6}" stroke="${color}" stroke-width="2"/><path d="M${x(stats.mean)},${y-4}l4,4 -4,4 -4,-4Z" fill="${color}"/>`:'';
    const lastRound=Math.max(1,row.rounds?.length-1||0);
    const dots=row.points.filter(point=>point.value!==null).map(point=>{
      const where=row.allObservations?' · '+overviewRound(point.condition,point.generation):'';
      const description=`${label(row)}${where} · Repetition ${point.replicate+1} · ${names[metric]} ${format(point.value)}${metric==='score'&&!row.allObservations?' · '+row.commonFixtures+' shared fixtures':''}${row.tracksPooled?' · Average of '+point.sessions.length+' conversations; opens the latest included conversation':''}`;
      // In the all-observation view, later rounds are more opaque and no-feedback tracks are hollow.
      const opacity=row.allObservations?.35+.65*Math.max(0,row.rounds.indexOf(point.generation))/lastRound:1;
      const hollow=row.allObservations&&point.condition==='control';
      return `<a href="#${e(query({view:'run',run:S.run,tab:'conversation',session:point.session}))}" data-action="session-conversation" data-session="${e(point.session)}" data-chart-model="${e(row.model)}" data-chart-label="${e(description)}" aria-label="${e(description)}"><circle class="repetition-point" cx="${x(point.value)}" cy="${y+12+offsets.get(key(point))}" r="4" fill="${hollow?'white':color}" fill-opacity="${hollow?1:opacity.toFixed(2)}" stroke="${hollow?color:'white'}" stroke-opacity="${hollow?opacity.toFixed(2):1}" stroke-width="1.5"/></a>`;
    }).join('');
    const coverage=metric==='score'?`${stats.n}/${row.expected} scored${row.allObservations?'':' · '+row.commonFixtures+' fixtures'}`:`${stats.n}/${row.expected} measured`;
    const summary=stats.n?`Mean ${format(stats.mean)} · ${stats.n>=2?'SD '+spread(stats.sd):'SD needs ≥2 reps'}`:'No comparable data';
    return `<g data-chart-model="${e(row.model)}" data-chart-label="${e(label(row))}"><rect x="2" y="${y-9}" width="3" height="22" rx="1.5" fill="${color}"/><text class="repetition-label" x="10" y="${y-1}">${e(name.length>26?name.slice(0,24)+'…':name)}</text><text x="10" y="${y+11}">${e(roundLabel(row))}</text>${box}${dots}<text x="${W-R+12}" y="${y-1}">${e(summary)}</text><text x="${W-R+12}" y="${y+11}">${e(coverage)}${stats.n>=2&&stats.q1===stats.q3?' · IQR = 0':''}</text></g>`;
  }).join('');
  const groupingName={model:'grouped by model with feedback tracks pooled',all:'one row per model with every round, track and repetition'}[S.repetitionRounds]||'grouped by model, round and track';
  const chart=rows.length?`<div class="repetition-scroll" role="region" aria-label="Variation across model repetitions" tabindex="0"><svg class="repetition-plot" style="min-width:${W}px" viewBox="0 0 ${W} ${H}" role="group" aria-label="${e(names[metric])} distribution across repetitions, ${groupingName}">${Array.from({length:5},(_,index)=>{const value=index*maximum/4;return `<line x1="${x(value)}" x2="${x(value)}" y1="22" y2="${H-4}" stroke="#e0e7e4"/><text x="${x(value)}" y="14" text-anchor="middle">${e(format(value))}</text>`;}).join('')}${marks}</svg></div>`:'<div class="overview-empty">No model repetitions in this selection. Fixed reference strategies are excluded.</div>';
  const details=rows.length?`<details class="overview-details"><summary>Dispersion and evaluation coverage</summary>${table(['Model / round / track','Measured / repetitions','Common fixtures','Mean','Sample SD','Sample variance','IQR','Outcome disagreement','Submitted','Invalid / checked','Engine failures'],rows.map(row=>`<tr><td>${e(label(row))}</td><td>${row.stats.n} / ${row.expected}</td><td>${metric==='score'?row.commonFixtures:'—'}</td><td>${format(row.stats.mean)}</td><td>${spread(row.stats.sd)}</td><td>${row.stats.variance===null?'—':fmt(row.stats.variance*(metric==='score'?10000:1),3)+(metric==='score'?' pp²':'')}</td><td>${row.stats.n<2?'—':spread(row.stats.q3-row.stats.q1)}</td><td>${metric==='score'&&!row.pooled?pct(row.disagreement):'—'}</td><td>${row.submitted} / ${row.expected}</td><td>${row.validated?row.invalid+' / '+row.validated:'—'}</td><td>${row.engineFailures}</td></tr>`))}</details>`:'';
  const conflicts=rows.reduce((sum,row)=>sum+row.conflicts,0);
  return `<section class="overview-card" id="repetition-variance" data-chart-key="repetitions:${e(S.run)}:${metric}"><div class="overview-section-head"><h2>Variation between repetitions</h2><div class="chart-controls">${chartActions()}<label class="field">Grouping<select data-repetition-rounds aria-label="Repetition grouping"><option value="separate" ${!['pooled','model'].includes(S.repetitionRounds)?'selected':''}>Separate rounds</option><option value="pooled" ${S.repetitionRounds==='pooled'?'selected':''}>All selected rounds · tracks separate</option><option value="model" ${S.repetitionRounds==='model'?'selected':''}>By model · feedback pooled</option><option value="all" ${all?'selected':''}>By model · every round &amp; repetition</option></select></label><label class="field">Measure<select data-repetition-metric aria-label="Repetition dispersion measure">${Object.entries(names).map(([key,name])=>`<option value="${key}" ${metric===key?'selected':''}>${e(name)}</option>`).join('')}</select></label></div></div><p class="muted">${all?'One row per model with one point per conversation: every repetition of every selected round and track. Later rounds are darker; hollow points are no-feedback tracks. Each score is computed within its own round and track. The box and SD describe all these observations together; they are not independent samples, so use the other groupings to estimate spread between repetitions.':'One point per repetition; click to open its conversation. '+(S.repetitionRounds==='model'?'Feedback and no-feedback tracks are combined: each repetition averages its selected tracks within a round, then averages the same shared rounds with equal round weights. The initial round is counted once. Missing branches are excluded from the shared rounds, not treated as zero. Clicking a pooled point opens its latest included conversation.':'Feedback tracks stay separate.')+' In the all-round view, each point averages one repetition over the same shared rounds, with equal round weights; rounds are not extra independent samples.'} ${metric==='score'?'Scores use only identical opponent versions, fight seeds and starting sides completed by every observed repetition in each row. Missing repetitions and engine failures are excluded, not scored as zero.':'Resource dispersion includes frozen submissions with known measurements; incomplete preparations and unknown values are excluded.'}</p>${chart}<p class="repetition-key">Dots: repetitions · Box: middle 50% · Line: full range · Vertical bar: median · Diamond: mean. The box spans Q1–Q3, not mean ± SD: it can be off-center or exclude the mean when outcomes are skewed. If Q1 = Q3 it collapses to a line. SD is descriptive spread, not a confidence interval.</p>${metric==='score'?'<p class="muted">Outcome disagreement compares win/draw/loss on shared fixtures: identical means can hide different matchups. Few repetitions or few common fixtures make the estimate fragile. This measures variation between preparations, not between dependent messages in one conversation.</p>':''}${conflicts?`<p class="muted">${conflicts} conflicting duplicate fixtures excluded.</p>`:''}${details}</section>`;
}
