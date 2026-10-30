/* Descriptive repetition statistics; no replay bodies or new fights are needed. */
(function(root,factory) {
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.RepetitionStats=api;
})(globalThis,function() {
  'use strict';
  const finite=value=>typeof value==='number'&&Number.isFinite(value);
  function describe(values) {
    values=values.filter(finite).sort((a,b)=>a-b);
    const n=values.length;
    if(!n)return {n:0,mean:null,variance:null,sd:null,median:null,q1:null,q3:null,min:null,max:null};
    const mean=values.reduce((sum,value)=>sum+value,0)/n;
    const quantile=p=>{const index=(n-1)*p,low=Math.floor(index);return values[low]+(values[Math.ceil(index)]-values[low])*(index-low);};
    const variance=n>1?values.reduce((sum,value)=>sum+(value-mean)**2,0)/(n-1):null;
    return {n,mean,variance,sd:variance===null?null:Math.sqrt(variance),median:quantile(.5),q1:quantile(.25),q3:quantile(.75),min:values[0],max:values[n-1]};
  }
  function summarize(sessions,observations,metric='score') {
    const groups=new Map(),members=new Map();
    for(const session of sessions) {
      const key=JSON.stringify([session.model,session.generation||0,session.condition||'initial']);
      if(!groups.has(key))groups.set(key,{model:session.model,generation:session.generation||0,condition:session.condition||'initial',points:[]});
      const point={session:session.id,replicate:session.replicate||0,submitted:!!session.submission||session.status==='submitted',
        validity:session.validation_status||session.validity||'unknown',metrics:session.metrics||{},fixtures:new Map(),conflicts:new Set(),failures:new Set(),value:null};
      groups.get(key).points.push(point);members.set(session.id,point);
    }
    for(const observation of observations) {
      const point=members.get(observation.session);
      if(!point||observation.opponent===observation.session||!finite(observation.seed)||![0,1].includes(observation.side))continue;
      const key=JSON.stringify([observation.opponent,observation.seed,observation.side]);
      if(observation.status!=='completed'||![-1,0,1].includes(observation.winner)) {point.failures.add(key);continue;}
      const value=observation.winner===-1?.5:observation.winner===observation.side?1:0;
      if(point.fixtures.has(key)&&point.fixtures.get(key)!==value)point.conflicts.add(key);
      point.fixtures.set(key,value);
    }
    const result=[];
    for(const group of groups.values()) {
      const measured=[];const union=new Set();
      for(const point of group.points) {
        for(const key of point.conflicts)point.fixtures.delete(key);
        for(const key of point.fixtures.keys())union.add(key);
        if(point.fixtures.size)measured.push(point);
      }
      const common=measured.length?[...measured[0].fixtures.keys()].filter(key=>measured.every(point=>point.fixtures.has(key))):[];
      for(const point of group.points) {
        point.value=metric==='score'?(common.length&&point.fixtures.size?common.reduce((sum,key)=>sum+point.fixtures.get(key),0)/common.length:null):
          point.submitted&&finite(point.metrics[metric])?point.metrics[metric]:null;
      }
      let disagreement=null;
      if(measured.length>=2&&common.length) {
        const pairs=measured.length*(measured.length-1)/2;
        disagreement=common.reduce((sum,key)=>{
          const counts=new Map();
          for(const point of measured) {const value=point.fixtures.get(key);counts.set(value,(counts.get(value)||0)+1);}
          return sum+1-[...counts.values()].reduce((n,count)=>n+count*(count-1)/2,0)/pairs;
        },0)/common.length;
      }
      result.push({...group,metric,stats:describe(group.points.map(point=>point.value)),commonFixtures:common.length,
        unionFixtures:union.size,observedRepetitions:measured.length,disagreement,
        submitted:group.points.filter(point=>point.submitted).length,
        invalid:group.points.filter(point=>point.validity==='invalid').length,
        validated:group.points.filter(point=>['valid','invalid'].includes(point.validity)).length,
        engineFailures:group.points.reduce((sum,point)=>sum+point.failures.size,0),
        conflicts:group.points.reduce((sum,point)=>sum+point.conflicts.size,0),
        points:group.points.map(point=>({session:point.session,replicate:point.replicate,value:point.value,fixtures:point.fixtures.size}))});
    }
    return result.sort((a,b)=>a.model.localeCompare(b.model)||a.generation-b.generation||a.condition.localeCompare(b.condition));
  }
  function poolRounds(rows) {
    const groups=new Map();
    for(const row of rows) {
      const key=JSON.stringify([row.model,row.condition]);
      if(!groups.has(key))groups.set(key,[]);
      groups.get(key).push(row);
    }
    return [...groups.values()].map(group=>{
      const repetitions=new Map();
      for(const row of group)for(const point of row.points) {
        if(!repetitions.has(point.replicate))repetitions.set(point.replicate,new Map());
        if(point.value!==null)repetitions.get(point.replicate).set(row.generation,point);
      }
      const measured=[...repetitions.values()].filter(values=>values.size);
      const rounds=measured.length?[...measured[0].keys()].filter(round=>measured.every(values=>values.has(round))).sort((a,b)=>a-b):[];
      const points=[...repetitions].map(([replicate,values])=>{
        const last=[...values.values()].at(-1)||group.flatMap(row=>row.points).find(point=>point.replicate===replicate);
        return {...last,replicate,value:rounds.length&&values.size?rounds.reduce((sum,round)=>sum+values.get(round).value,0)/rounds.length:null};
      });
      return {...group[0],pooled:true,rounds,points,stats:describe(points.map(point=>point.value)),disagreement:null,
        commonFixtures:group.filter(row=>rounds.includes(row.generation)).reduce((sum,row)=>sum+row.commonFixtures,0),
        submitted:Math.min(...group.map(row=>row.submitted)),invalid:group.reduce((sum,row)=>sum+row.invalid,0),
        validated:group.reduce((sum,row)=>sum+row.validated,0),engineFailures:group.reduce((sum,row)=>sum+row.engineFailures,0),conflicts:group.reduce((sum,row)=>sum+row.conflicts,0)};
    });
  }
  return {describe,summarize,poolRounds};
});
