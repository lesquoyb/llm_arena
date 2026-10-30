const test=require('node:test');
const assert=require('node:assert/strict');
const {describe,summarize}=require('../arena_web/static/repetition-stats.js');
const session=(id,replicate,other={})=>({id,model:'model',replicate,generation:0,condition:'initial',submission:{},...other});
const fight=(session,opponent,seed,winner,other={})=>({session,opponent,seed,side:0,status:'completed',winner,...other});

test('sample variance uses independent repetitions, not the number of fights',()=>{
  const stats=describe([0,1]);assert.equal(stats.variance,.5);assert.equal(stats.sd,Math.sqrt(.5));
  assert.equal(stats.median,.5);assert.equal(stats.q1,.25);assert.equal(stats.q3,.75);
  assert.equal(describe([.5]).sd,null);assert.equal(describe([]).variance,null);
});
test('scores use identical opponent versions, seeds and starting sides',()=>{
  const [row]=summarize([session('a',0),session('b',1)],[fight('a','x',1,0),fight('a','y',1,1),fight('b','x',1,1)]);
  assert.equal(row.commonFixtures,1);assert.deepEqual(row.points.map(point=>point.value),[1,0]);
  assert.equal(row.stats.variance,.5);
});
test('identical means can hide complete matchup disagreement',()=>{
  const [row]=summarize([session('a',0),session('b',1)],[fight('a','x',1,0),fight('a','x',2,1),fight('b','x',1,1),fight('b','x',2,0)]);
  assert.equal(row.stats.sd,0);assert.equal(row.disagreement,1);assert.equal(row.commonFixtures,2);
});
test('no shared seed or side means unknown variance, not zero',()=>{
  const [row]=summarize([session('a',0),session('b',1)],[fight('a','x',1,0),fight('b','x',2,0),fight('b','x',1,0,{side:1})]);
  assert.equal(row.commonFixtures,0);assert.equal(row.stats.sd,null);assert.equal(row.stats.n,0);
});
test('missing submissions and failed fights remain separate from quality scores',()=>{
  const [row]=summarize([session('a',0),session('b',1),session('c',2,{submission:null,status:'no_submission'})],
    [fight('a','x',1,-1),fight('b','x',1,-1),fight('b','y',2,undefined,{status:'timeout'})]);
  assert.equal(row.stats.n,2);assert.equal(row.submitted,2);assert.equal(row.points[2].value,null);
  assert.equal(row.stats.mean,.5);assert.equal(row.engineFailures,1);assert.equal(row.stats.sd,0);
});
test('rounds and feedback tracks are never pooled',()=>{
  const rows=summarize([session('a',0),session('b',0,{generation:1,condition:'control'}),session('c',0,{generation:1,condition:'feedback'})],
    [fight('a','x',1,0),fight('b','x',1,1),fight('c','x',1,-1)]);
  assert.equal(rows.length,3);assert(rows.every(row=>row.stats.n===1&&row.stats.sd===null));
});
test('duplicate fixtures do not increase sample size and conflicting results are excluded',()=>{
  const [row]=summarize([session('a',0),session('b',1)],
    [fight('a','x',1,0),fight('a','x',1,0),fight('b','x',1,1),fight('a','y',1,0),fight('a','y',1,1)]);
  assert.equal(row.commonFixtures,1);assert.equal(row.conflicts,1);assert.equal(row.stats.n,2);
});
test('resource metrics exclude unavailable values and non-submitted attempts',()=>{
  const [row]=summarize([session('a',0,{metrics:{cost:1}}),session('b',1,{metrics:{cost:3}}),session('c',2,{metrics:{cost:null}}),session('d',3,{submission:null,metrics:{cost:99}})],[],'cost');
  assert.equal(row.stats.n,2);assert.equal(row.stats.mean,2);assert.equal(row.stats.variance,2);
});
test('all-round view averages each repetition before estimating spread',()=>{
  const rows=summarize([session('a0',0),session('b0',1),session('a1',0,{generation:1}),session('b1',1,{generation:1})],
    [fight('a0','x',1,0),fight('b0','x',1,1),fight('a1','x',1,1),fight('b1','x',1,0)]);
  const [pooled]=require('../arena_web/static/repetition-stats.js').poolRounds(rows);
  assert.equal(pooled.stats.n,2);assert.equal(pooled.stats.mean,.5);assert.equal(pooled.stats.sd,0);
  assert.deepEqual(pooled.rounds,[0,1]);
});
