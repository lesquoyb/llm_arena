/* Fight length distributions and strategy lineages for the competition summary. */
const LENGTH_CLASSES=[['decisive','Decisive','#3568c0'],['draw','Draw before the turn limit','#c89211'],['capped','Draw at the turn limit','#b3482c']];
const LENGTH_FILTERS=[['all','All outcomes',['decisive','draw','capped']],['draws','All draws',['draw','capped']],['capped','Turn limit reached only',['capped']],['decisive','Decisive only',['decisive']]];

function stageRound(stage) {
  const match=String(stage).match(/g(\d+)-(?:tournament|panel|previous)$/);
  return match?Number(match[1]):0;
}
function stageInSource(stage,source) {
  if(source==='evaluation')return /-panel$/.test(stage);
  if(source==='progression')return /-previous$/.test(stage);
  return stage==='tournament'||stage==='.'||/^g\d+-tournament$/.test(stage);
}
async function loadFightLengths() {
  if(S.fightLengthsPending===S.run)return;
  const run=S.run;S.fightLengthsPending=run;
  try {
    const value=await runResource('/api/fight-lengths',{run});
    S.fightLengths={run,value};
    const node=$('#fight-lengths');
    if(node&&run===S.run&&S.tab==='summary')LiveDOM.replace(node,fightLengthCard(S.detail,overviewData(S.detail)));
  } catch(error) {if(error.name!=='AbortError')toast(error.message,true);}
  finally {if(S.fightLengthsPending===run)S.fightLengthsPending=null;}
}
function fightLengthCard(d,data) {
  const head='<div class="overview-section-head"><h2>Fight length</h2>'+chartFullScreenButton()+'</div>';
  if(S.fightLengths?.run!==S.run) {loadFightLengths();return `<section class="overview-card" id="fight-lengths">${head}<p class="muted">Loading fight lengths…</p></section>`;}
  const value=S.fightLengths.value,settings=overviewSettings();
  const view=settings.lengthView||'global',filter=settings.lengthFilter||'all';
  const classes=LENGTH_FILTERS.find(row=>row[0]===filter)[2];
  const stage=data.scope.round?.startsWith('stage:')?data.scope.round.slice(6):null;
  const scope=runScope(),focus=scope.model||settings.model||'';
  const series=value.series.filter(row=>(stage?row.stage===stage:stageInSource(row.stage,data.scope.source))&&classes.includes(row.outcome)
    &&(!scope.round||stageRound(row.stage)+1===Number(scope.round)));
  const empty=()=>Array(value.bins).fill(0);
  const sum=(rows)=>{const out={counts:Object.fromEntries(LENGTH_CLASSES.map(([key])=>[key,empty()])),fights:0,turns:0,seconds:0,byClass:{}};
    for(const row of rows) {
      row.counts.forEach((count,index)=>{out.counts[row.outcome][index]+=count;});
      out.fights+=row.fights;out.turns+=row.turns;out.seconds+=row.seconds;
      const own=out.byClass[row.outcome]||={fights:0,seconds:0};own.fights+=row.fights;own.seconds+=row.seconds;
    }
    return out;};
  const overall=sum(series.filter(row=>row.model===(focus||'*')));
  const capped=overall.byClass.capped||{fights:0,seconds:0};
  const filters=`<div class="chart-controls"><label class="field">View<select data-length-setting="lengthView" aria-label="Fight length view">${[['global','All selected fights'],['rounds','Per round'],['models','Per model']].map(([id,label])=>`<option value="${id}" ${view===id?'selected':''}>${label}</option>`).join('')}</select></label><label class="field">Outcomes<select data-length-setting="lengthFilter" aria-label="Fight outcomes">${LENGTH_FILTERS.map(([id,label])=>`<option value="${id}" ${filter===id?'selected':''}>${label}</option>`).join('')}</select></label></div>`;
  const kpis=`<div class="length-kpis"><div><span>Fights</span><strong>${fmt(overall.fights)}</strong></div><div><span>Mean length</span><strong>${overall.fights?fmt(overall.turns/overall.fights,1):'N/A'}</strong><small>turns</small></div><div><span>Reached the turn limit</span><strong>${overall.fights?pct(capped.fights/overall.fights):'N/A'}</strong><small>${value.max_turns?`limit ${fmt(value.max_turns)} turns`:'no limit recorded'}</small></div><div><span>Engine time in those fights</span><strong>${overall.seconds?pct(capped.seconds/overall.seconds):'N/A'}</strong><small>of ${fmt(overall.seconds/3600,1)} h measured</small></div></div>`;
  let body;
  if(!overall.fights&&view!=='models')body='<div class="overview-empty">No completed fights in this selection.</div>';
  else if(view==='rounds') {
    const rounds=[...new Set(series.map(row=>stageRound(row.stage)))].sort((a,b)=>a-b);
    body=`<div class="length-rows">${rounds.map(round=>{const total=sum(series.filter(row=>stageRound(row.stage)===round&&row.model===(focus||'*')));
      return lengthRow(`Round ${round+1}`,total,value,classes,`round-${round}`);}).join('')}</div>`;
  } else if(view==='models') {
    const models=[...new Set(series.map(row=>row.model).filter(model=>model!=='*'))]
      .map(model=>({model,total:sum(series.filter(row=>row.model===model))})).filter(row=>row.total.fights)
      .sort((a,b)=>shareOf(b.total,'capped')-shareOf(a.total,'capped')||a.model.localeCompare(b.model));
    body=models.length?`<p class="muted">Each fight counts once for each model on its sides. Sorted by the share of fights reaching the turn limit.</p><div class="length-rows">${models.map(row=>lengthRow(row.model,row.total,value,classes,row.model,overviewColor(row.model))).join('')}</div>`:'<div class="overview-empty">No completed fights in this selection.</div>';
  } else body=lengthHistogram(overall,value,classes);
  const legend=`<div class="overview-legend">${LENGTH_CLASSES.filter(([key])=>classes.includes(key)).map(([key,label,color])=>`<span><i style="background:${color}"></i>${label}</span>`).join('')}</div>`;
  return `<section class="overview-card" id="fight-lengths">${head}<p class="muted">Turns per completed fight in the selected category${focus?` for ${e(focus)}`:''}. Draws at the turn limit often mean neither strategy ever attacked; they dominate engine time.</p>${filters}${kpis}${body}${legend}</section>`;
}
function shareOf(total,key) {return total.fights?(total.byClass[key]?.fights||0)/total.fights:0;}
function lengthHistogram(total,value,classes) {
  const W=900,H=230,L=52,R=12,T=14,B=190,bins=value.bins,width=(W-L-R)/bins;
  const stacks=Array.from({length:bins},(_,index)=>classes.reduce((n,key)=>n+total.counts[key][index],0));
  const max=Math.max(1,...stacks),y=v=>B-(B-T)*v/max;
  const ticks=[0,.25,.5,.75,1].map(v=>Math.round(v*max));
  let bars='';
  for(let index=0;index<bins;index++) {
    let base=0;
    for(const [key,label,color] of LENGTH_CLASSES) {
      if(!classes.includes(key))continue;
      const count=total.counts[key][index];if(!count)continue;
      const from=index*value.bin_width,to=from+value.bin_width-1;
      const tip=`${label} · ${fmt(from)}–${fmt(to)} turns · ${fmt(count)} fights`;
      bars+=`<rect x="${L+index*width+1}" y="${y(base+count)}" width="${Math.max(1,width-2)}" height="${Math.max(1,y(base)-y(base+count))}" fill="${color}" tabindex="0" data-chart-model="${key}" data-chart-label="${e(tip)}"/>`;
      base+=count;
    }
  }
  const xTicks=[0,.25,.5,.75,1].map(v=>Math.round(v*(bins-1)));
  return `<div class="evolution-scroll"><svg class="length-histogram" viewBox="0 0 ${W} ${H}" role="img" aria-label="Distribution of fight lengths in turns">${ticks.map(v=>`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="#e0e7e4"/><text x="${L-6}" y="${y(v)+4}" text-anchor="end">${fmt(v)}</text>`).join('')}${bars}${xTicks.map(index=>`<text x="${L+(index+.5)*width}" y="${B+18}" text-anchor="middle">${fmt(index*value.bin_width)}</text>`).join('')}<text x="${(L+W-R)/2}" y="${H-4}" text-anchor="middle">Turns</text></svg></div>`;
}
function lengthRow(label,total,value,classes,model,color) {
  const bins=value.bins,stacks=Array.from({length:bins},(_,index)=>classes.reduce((n,key)=>n+total.counts[key][index],0));
  const max=Math.max(1,...stacks),W=360,H=34,width=W/bins;
  let spark='';
  for(let index=0;index<bins;index++){let base=0;for(const [key,,fill] of LENGTH_CLASSES){if(!classes.includes(key))continue;const count=total.counts[key][index];if(!count)continue;spark+=`<rect x="${index*width}" y="${H-H*(base+count)/max}" width="${Math.max(.6,width-.6)}" height="${Math.max(.6,H*count/max)}" fill="${fill}"/>`;base+=count;}}
  const shares=LENGTH_CLASSES.filter(([key])=>classes.includes(key)).map(([key,name,fill])=>`<span style="width:${100*shareOf(total,key)}%;background:${fill}" title="${e(name)}: ${pct(shareOf(total,key))}"></span>`).join('');
  const tip=`${label} · ${fmt(total.fights)} fights · mean ${total.fights?fmt(total.turns/total.fights,1):'N/A'} turns · ${pct(shareOf(total,'capped'))} at the turn limit`;
  return `<div class="length-row" tabindex="0" data-chart-model="${e(model)}" data-chart-label="${e(tip)}"><strong>${color?`<i class="dot" style="background:${color}"></i>`:''}${e(label)}</strong><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true">${spark}</svg><div class="length-share" aria-hidden="true">${shares}</div><span>${fmt(total.fights)} fights · ${total.fights?fmt(total.turns/total.fights,0):'—'} turns avg · ${pct(shareOf(total,'capped'))} capped</span></div>`;
}

/* Strategy lineages: every submitted version placed at its round and tournament score, linked to its parent. */
function lineageScores(data) {
  const scores=new Map();
  for(const match of S.overviewMatches||[]) {
    if(match.kind!=='competition'||match.mirror)continue;
    const weight=match.count||1;
    match.sides.forEach((id,side)=>{
      const row=scores.get(id)||{points:0,completed:0};
      if(match.result.status==='completed') {row.completed+=weight;row.points+=weight*(match.result.winner_side===-1?.5:match.result.winner_side===side?1:0);}
      scores.set(id,row);
    });
  }
  return scores;
}
function lineageChart(d,data) {
  const sessions=d.sessions.filter(session=>session.submission&&scopeAccept(overviewIdentity(session.id))&&(!data.scope.model||session.model===data.scope.model));
  const scores=lineageScores(data);
  const nodes=sessions.map(session=>{const score=scores.get(session.id);return {...session,generation:session.generation||0,score:score?.completed?score.points/score.completed:null,completed:score?.completed||0};}).filter(node=>node.score!=null);
  const head='<div class="overview-section-head"><h2>Strategy lineages</h2>'+chartFullScreenButton()+'</div>';
  if(!nodes.length)return `<section class="overview-card" id="strategy-lineages">${head}<div class="overview-empty">Lineages appear once submitted strategies have tournament results.</div></section>`;
  const byId=new Map(nodes.map(node=>[node.id,node]));
  const rounds=[...new Set(nodes.map(node=>node.generation))].sort((a,b)=>a-b);
  const W=Math.max(640,Math.min(1400,rounds.length*170)),H=330,L=52,R=24,T=16,B=290;
  const x=round=>L+(W-L-R)*(rounds.length>1?rounds.indexOf(round)/(rounds.length-1):.5),y=score=>B-(B-T)*score;
  const jitter=node=>((node.replicate||0)-1.5)*4;
  let edges='',dots='';
  for(const node of nodes) {
    const parent=byId.get(node.parent),color=overviewColor(node.model);
    const label=`${node.model} · ${overviewRound(node.condition||'initial',node.generation)} · repetition ${(node.replicate||0)+1} · ${pct(node.score)} of points · ${fmt(node.completed)} fights`;
    if(parent)edges+=`<path d="M${x(parent.generation)+jitter(parent)},${y(parent.score)} L${x(node.generation)+jitter(node)},${y(node.score)}" fill="none" stroke="${color}" stroke-width="1.6" stroke-opacity=".75" ${node.condition==='control'?'stroke-dasharray="4 4"':''} data-chart-model="${e(node.model)}" data-chart-label="${e(label)}"/>`;
    dots+=`<circle cx="${x(node.generation)+jitter(node)}" cy="${y(node.score)}" r="4.5" fill="${node.condition==='control'?'#fff':color}" stroke="${color}" stroke-width="1.8" tabindex="0" data-chart-model="${e(node.model)}" data-chart-label="${e(label)}"/>`;
  }
  const models=[...new Set(nodes.map(node=>node.model))].sort();
  return `<section class="overview-card" id="strategy-lineages">${head}<p class="muted">Each point is a submitted strategy version, placed at its round and its share of tournament points (wins + ½ draws). Lines join a version to the one it was derived from. Solid lines and filled points: with feedback; dashed lines and hollow points: without feedback. Hover a model to follow its descendants.</p><div class="chart-filterable" data-chart-key="lineage:${e(S.run)}"><div class="evolution-scroll"><svg class="lineage-chart" style="min-width:${W}px" viewBox="0 0 ${W} ${H}" role="img" aria-label="Strategy lineages across rounds">${[0,.25,.5,.75,1].map(v=>`<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="#e0e7e4"/><text x="${L-7}" y="${y(v)+4}" text-anchor="end">${pct(v)}</text>`).join('')}${rounds.map(round=>`<text x="${x(round)}" y="${B+24}" text-anchor="middle">Round ${round+1}</text>`).join('')}${edges}${dots}</svg></div><div class="overview-legend">${models.map(model=>`<span tabindex="0" data-chart-model="${e(model)}"><i style="background:${overviewColor(model)}"></i>${e(model)}</span>`).join('')}</div></div></section>`;
}
