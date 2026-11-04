const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const RepetitionStats=require('../arena_web/static/repetition-stats.js');
const script=fs.readFileSync(require.resolve('../arena_web/static/repetition-chart.js'),'utf8');
function fixture(count=6) {
  const sessions=Array.from({length:count},(_,replicate)=>({id:'model-r'+replicate,model:'model',replicate,condition:'initial',generation:0,submission:{},steps:10,cost_spent:'1',wall_seconds:60}));
  const data={sessions,scope:{source:'competition'},selected:sessions.map(session=>({entries:[{id:session.id,model:'model',side:0}],match:{sides:[session.id,'opponent'],seed:101,result:{status:'completed',winner_side:-1}}}))};
  const context={RepetitionStats,S:{run:'fixture',repetitionFixtures:{key:JSON.stringify(['fixture','competition',null]),
    observations:sessions.map(session=>({session:session.id,opponent:'opponent',seed:101,side:0,status:'completed',winner:-1}))}},runScope:()=>({}),measuredUsage:()=>({complete:false}),
    overviewIdentity:()=>({model:'other'}),overviewColor:()=> '#167568',overviewRound:()=> 'R1 · Initial',
    query:value=>new URLSearchParams(value).toString(),chartFullScreenButton:()=>'',
    e:value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),
    fmt:value=>String(value),pct:value=>value==null?'N/A':100*value+'%',money:value=>'$'+value,
    table:(headers,rows)=>'<table>'+rows.join('')+'</table>'};
  vm.createContext(context);vm.runInContext(script,context);
  return {context,data,detail:{metadata:{config:{replicates:20,models:[{id:'model',provider:'openai'}]}}}};
}
test('identical values keep all repetitions individually selectable and show expected coverage',()=>{
  const {context,data,detail}=fixture(20);const html=context.repetitionVariance(detail,data);
  const positions=[...html.matchAll(/class="repetition-point" cx="([^"]+)" cy="([^"]+)"/g)].map(match=>match[1]+':'+match[2]);
  assert.equal(positions.length,20);assert.equal(new Set(positions).size,20);
  assert(html.includes('20/20 scored'));assert(!html.includes('NaN'));
});
test('missing scheduled repetitions stay visible in coverage and single-repetition SD is unknown',()=>{
  const {context,data,detail}=fixture(1);const html=context.repetitionVariance(detail,data);
  assert(html.includes('1/20 scored'));assert(html.includes('SD needs ≥2 repetitions'));
});
test('resources and absent panels render without inventing quality scores',()=>{
  const {context,data,detail}=fixture(2);data.selected=[];context.S.repetitionFixtures.observations=[];
  assert(context.repetitionVariance(detail,data).includes('No comparable data'));
  context.S.repetitionMetric='cost';const html=context.repetitionVariance(detail,data);
  assert(html.includes('2/20 measured'));assert.equal((html.match(/class="repetition-point"/g)||[]).length,2);
});
test('pooled-model selector renders one row and one point per independent repetition',()=>{
  const {context,data,detail}=fixture(2);
  data.sessions.push(...data.sessions.map(row=>({...row,id:row.id+'-c',generation:1,condition:'control'})),
    ...data.sessions.slice(0,2).map(row=>({...row,id:row.id+'-f',generation:1,condition:'feedback'})));
  context.S.repetitionMetric='cost';context.S.repetitionRounds='model';
  const html=context.repetitionVariance(detail,data);
  assert(html.includes('By model · feedback pooled'));
  assert(html.includes('Feedback tracks pooled · 2 shared rounds'));
  assert.equal((html.match(/class="repetition-point"/g)||[]).length,2);
  assert(html.includes('Average of 3 conversations'));
  assert(html.includes('2/20 measured'));assert(!html.includes('NaN'));
});
