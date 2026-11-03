const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const RepetitionStats=require('../arena_web/static/repetition-stats.js');
const script=fs.readFileSync(require.resolve('../arena_web/static/repetition-chart.js'),'utf8');
function fixture(count=6) {
  const sessions=Array.from({length:count},(_,replicate)=>({id:'model-r'+replicate,model:'model',replicate,condition:'initial',generation:0,submission:{},steps:10,cost_spent:'1',wall_seconds:60}));
  const data={sessions,scope:{source:'competition'},selected:sessions.map(session=>({entries:[{id:session.id,model:'model',side:0}],match:{sides:[session.id,'opponent'],seed:101,result:{status:'completed',winner_side:-1}}}))};
  const context={RepetitionStats,S:{run:'fixture'},runScope:()=>({}),measuredUsage:()=>({complete:false}),
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
  const {context,data,detail}=fixture(2);data.selected=[];
  assert(context.repetitionVariance(detail,data).includes('No comparable data'));
  context.S.repetitionMetric='cost';const html=context.repetitionVariance(detail,data);
  assert(html.includes('2/20 measured'));assert.equal((html.match(/class="repetition-point"/g)||[]).length,2);
});
