/* Render the same compact overview data; no extra fight/replay requests. */
function repetitionVariance(d,data) {
  const metric=S.repetitionMetric||'score';
  const specs=new Map((d.metadata.config?.models||[]).map(model=>[model.id,model]));
  const number=value=>value===null||value===undefined||value===''?null:Number.isFinite(Number(value))?Number(value):null;
  const sessions=data.sessions.filter(session=>specs.get(session.model)?.provider!=='mock').map(session=>{
    const usage=measuredUsage(session);
    return {...session,metrics:{cost:session.reconciliation_required||Number(session.money_reserved||0)>0?null:number(session.cost_spent),
      tools:number(session.steps),time:number(session.wall_seconds)===null?null:Number(session.wall_seconds)/60,
      tokens:usage.complete&&Number.isFinite(usage.input_tokens)&&Number.isFinite(usage.output_tokens)?usage.input_tokens+usage.output_tokens:null}};
  });
  const observations=[];
  for(const {match,entries} of data.selected)for(const entry of entries) {
    const opponent=match.sides[1-entry.side];
    if(data.scope.source!=='progression'&&overviewIdentity(opponent).model===entry.model)continue;
    observations.push({session:entry.id,opponent,seed:match.seed,side:entry.side,status:match.result.status,winner:match.result.winner_side});
  }
  const rows=RepetitionStats.summarize(sessions,observations,metric);
  for(const row of rows)row.expected=Math.max(row.points.length,runScope().replicate?1:Number(d.metadata.config?.replicates||0));
  const names={score:'Combat score',cost:'Preparation cost',tools:'Tool calls',time:'Preparation time (min)',tokens:'Preparation tokens'};
  const format=value=>value===null||!Number.isFinite(value)?'—':metric==='score'?pct(value):metric==='cost'?money(value):fmt(value,1);
  const spread=value=>value===null||!Number.isFinite(value)?'—':metric==='score'?fmt(100*value,1)+' pp':format(value);
  const values=rows.flatMap(row=>row.points.map(point=>point.value)).filter(Number.isFinite);
  const W=1100,L=265,R=195;
  const maximum=metric==='score'?1:values.reduce((maximum,value)=>Math.max(maximum,value),1)*1.05;
  const x=value=>L+(W-L-R)*value/maximum;
  let nextY=58;
  const positions=rows.map(row=>{
    const placed=[],offsets=new Map();
    for(const point of row.points.filter(point=>point.value!==null)) {
      let offset=0;
      while(placed.some(previous=>Math.abs(previous.x-x(point.value))<12&&previous.offset===offset))offset+=12;
      placed.push({x:x(point.value),offset});offsets.set(point.session,offset);
    }
    const y=nextY;nextY+=Math.max(70,55+Math.max(0,...placed.map(point=>point.offset)));
    return {y,offsets};
  });
  const H=nextY+2;
  const label=row=>`${row.model} · ${overviewRound(row.condition,row.generation)}`;
  const marks=rows.map((row,index)=>{
    const {y,offsets}=positions[index],stats=row.stats,color=overviewColor(row.model);
    const box=stats.n?`<line x1="${x(stats.min)}" x2="${x(stats.max)}" y1="${y}" y2="${y}" stroke="${color}" stroke-width="2"/><rect x="${x(stats.q1)}" y="${y-9}" width="${Math.max(1,x(stats.q3)-x(stats.q1))}" height="18" fill="${color}" fill-opacity=".17" stroke="${color}"/><line x1="${x(stats.median)}" x2="${x(stats.median)}" y1="${y-9}" y2="${y+9}" stroke="${color}" stroke-width="2"/><path d="M${x(stats.mean)},${y-5}l5,5 -5,5 -5,-5Z" fill="${color}"/>`:'';
    const dots=row.points.filter(point=>point.value!==null).map(point=>{
      const description=`${label(row)} · Repetition ${point.replicate+1} · ${names[metric]} ${format(point.value)}${metric==='score'?' · '+row.commonFixtures+' shared fixtures':''}`;
      return `<a href="#${e(query({view:'run',run:S.run,tab:'conversation',session:point.session}))}" data-action="session-conversation" data-session="${e(point.session)}" data-chart-model="${e(row.model)}" data-chart-label="${e(description)}" aria-label="${e(description)}"><circle class="repetition-point" cx="${x(point.value)}" cy="${y+17+offsets.get(point.session)}" r="5" fill="${color}" stroke="white" stroke-width="1.5"/></a>`;
    }).join('');
    const coverage=metric==='score'?`${stats.n}/${row.expected} scored · ${row.commonFixtures} shared fixtures`:`${stats.n}/${row.expected} measured`;
    return `<g data-chart-model="${e(row.model)}" data-chart-label="${e(label(row))}"><text class="repetition-label" x="8" y="${y-3}">${e(row.model.length>30?row.model.slice(0,28)+'…':row.model)}</text><text x="8" y="${y+14}">${e(overviewRound(row.condition,row.generation))}</text>${box}${dots}<text x="${W-R+15}" y="${y-3}">${stats.n?'Mean '+e(format(stats.mean)):'No comparable data'}</text><text x="${W-R+15}" y="${y+14}">${stats.n>=2?'SD '+e(spread(stats.sd)):'SD needs ≥2 repetitions'}</text><text x="${W-R+15}" y="${y+31}">${e(coverage)}</text></g>`;
  }).join('');
  const chart=rows.length?`<div class="repetition-scroll" role="region" aria-label="Variation across model repetitions" tabindex="0"><svg class="repetition-plot" style="min-width:${W}px" viewBox="0 0 ${W} ${H}" role="group" aria-label="${e(names[metric])} distribution across repetitions, grouped by model, round and track">${Array.from({length:5},(_,index)=>{const value=index*maximum/4;return `<line x1="${x(value)}" x2="${x(value)}" y1="32" y2="${H-12}" stroke="#e0e7e4"/><text x="${x(value)}" y="20" text-anchor="middle">${e(format(value))}</text>`;}).join('')}${marks}</svg></div>`:'<div class="overview-empty">No model repetitions in this selection. Fixed reference strategies are excluded.</div>';
  const details=rows.length?`<details class="overview-details"><summary>Dispersion and evaluation coverage</summary>${table(['Model / round / track','Measured / repetitions','Common fixtures','Mean','Sample SD','Sample variance','IQR','Outcome disagreement','Submitted','Invalid / checked','Engine failures'],rows.map(row=>`<tr><td>${e(label(row))}</td><td>${row.stats.n} / ${row.expected}</td><td>${metric==='score'?row.commonFixtures:'—'}</td><td>${format(row.stats.mean)}</td><td>${spread(row.stats.sd)}</td><td>${row.stats.variance===null?'—':fmt(row.stats.variance*(metric==='score'?10000:1),3)+(metric==='score'?' pp²':'')}</td><td>${row.stats.n<2?'—':spread(row.stats.q3-row.stats.q1)}</td><td>${metric==='score'?pct(row.disagreement):'—'}</td><td>${row.submitted} / ${row.expected}</td><td>${row.validated?row.invalid+' / '+row.validated:'—'}</td><td>${row.engineFailures}</td></tr>`))}</details>`:'';
  const conflicts=rows.reduce((sum,row)=>sum+row.conflicts,0);
  return `<section class="overview-card" id="repetition-variance" data-chart-key="repetitions:${e(S.run)}:${metric}"><div class="overview-section-head"><h2>Variation between repetitions</h2><div class="chart-controls">${chartFullScreenButton()}<label class="field">Measure<select data-repetition-metric aria-label="Repetition dispersion measure">${Object.entries(names).map(([key,name])=>`<option value="${key}" ${metric===key?'selected':''}>${e(name)}</option>`).join('')}</select></label></div></div><p class="muted">One point per repetition; click to open its conversation. Rounds and feedback tracks stay separate. ${metric==='score'?'Scores use only identical opponent versions, fight seeds and starting sides completed by every observed repetition in each row. Missing repetitions and engine failures are excluded, not scored as zero.':'Resource dispersion includes frozen submissions with known measurements; incomplete preparations and unknown values are excluded.'}</p>${chart}<p class="repetition-key">Dots: repetitions · Box: middle 50% · Line: full range · Vertical bar: median · Diamond: mean. SD is descriptive spread, not a confidence interval.</p>${metric==='score'?'<p class="muted">Outcome disagreement compares win/draw/loss on shared fixtures: identical means can hide different matchups. Few repetitions or few common fixtures make the estimate fragile. This measures variation between preparations, not between dependent messages in one conversation.</p>':''}${conflicts?`<p class="muted">${conflicts} conflicting duplicate fixtures excluded.</p>`:''}${details}</section>`;
}
