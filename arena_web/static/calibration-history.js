'use strict';
const $=id=>document.getElementById(id),study=new URLSearchParams(location.search).get('study');let versions=[],epoch=0;
const query=(route,extra={})=>route+'?'+new URLSearchParams({study,...extra});
async function api(route){const response=await fetch(route),body=await response.json();if(!response.ok)throw Error(body.error);return body;}
const guard=fn=>async(...args)=>{try{await fn(...args);}catch(error){$('error').hidden=false;$('error').textContent=error.message;}};
function option(select,value,label){const item=document.createElement('option');item.value=value;item.textContent=label;select.append(item);}
const preferenceKey='arena-preferred-prompt:'+study;
function preferred(){const choice=localStorage.getItem(preferenceKey);$('preference').textContent=choice?'Your preferred version in this browser: candidate '+(versions.find(v=>v.directory===choice)?.candidate??'?')+'. This is independent of the algorithm.':'';}
async function show(){
 const request=++epoch,version=versions.find(v=>v.directory===$('version').value);if(!version)return;
 const data=await api(query('/api/prompt-diff',{trial:version.directory,base:$('base').value,file:$('file').value}));if(request!==epoch)return;
 const file=$('file').value;$('file').replaceChildren();for(const name of data.files)option($('file'),name,name);if(data.files.includes(file))$('file').value=file;
 $('status').textContent=`Candidate ${version.candidate} · ${version.status} · Score ${version.score==null?'Not evaluated':(version.score*100).toFixed(1)+'%'} · Target tokens ${version.tokens??'Unknown'} · Target cost $${version.cost_usd??'Unknown'}`;
 $('rationale').textContent=data.rationale;$('before').value=data.before;$('after').value=data.after;$('diff').replaceChildren();
 if(!data.diff)$('diff').textContent='No changes against the selected comparison version.';
 for(const line of data.diff.split('\n')){if(!data.diff)break;const span=document.createElement('span');span.className='diff-line '+(line.startsWith('+')&&!line.startsWith('+++')?'diff-add':line.startsWith('-')&&!line.startsWith('---')?'diff-remove':'');span.textContent=line+'\n';$('diff').append(span)}preferred();
}
$('version').onchange=guard(async()=>{const selected=versions.find(v=>v.directory===$('version').value),previous=versions.filter(v=>v.candidate<selected.candidate).at(-1);const source=versions.find(v=>v.candidate===selected.source_candidate);$('base').value=(source||previous||selected).directory;await show();});
$('base').onchange=guard(show);$('file').onchange=guard(show);
$('prefer').onclick=()=>{localStorage.setItem(preferenceKey,$('version').value);preferred();};
$('reuse').onclick=()=>location.href='/?'+new URLSearchParams({study,candidate:$('version').value,reuse:'1'});
$('download').onclick=guard(async()=>{const version=versions.find(v=>v.directory===$('version').value),response=await fetch(query('/api/export-material',{trial:version.directory}));if(!response.ok)throw Error((await response.json()).error);const link=document.createElement('a');link.href=URL.createObjectURL(await response.blob());link.download=`${study}-candidate-${version.candidate}-learning-material.zip`;link.click();URL.revokeObjectURL(link.href);});
guard(async()=>{if(!study)throw Error('Choose a study from the calibration page first.');const data=await api(query('/api/prompt-history'));versions=data.versions;$('title').textContent=data.name+' · Prompt history';$('back').href='/?'+new URLSearchParams({study});if(!versions.length){$('status').textContent='No versions saved yet.';return;}
 for(const version of versions)for(const id of ['version','base'])option($(id),version.directory,`Candidate ${version.candidate} · ${version.status}`);
 const table=document.createElement('table'),head=document.createElement('tr');for(const label of ['Version','Status','Starting version','Inspect']){const cell=document.createElement('th');cell.textContent=label;head.append(cell)}table.append(head);
 for(const version of versions){const row=document.createElement('tr');for(const value of [version.candidate,version.status,version.source_candidate??'Initial']){const cell=document.createElement('td');cell.textContent=value;row.append(cell)}const cell=document.createElement('td'),button=document.createElement('button');button.textContent='Compare';button.onclick=guard(async()=>{$('version').value=version.directory;await $('version').onchange();});cell.append(button);row.append(cell);table.append(row)}const wrap=document.createElement('div');wrap.className='scroll';wrap.append(table);$('versions').append(wrap);
 const selected=localStorage.getItem(preferenceKey);$('version').value=versions.some(v=>v.directory===selected)?selected:versions.at(-1).directory;await $('version').onchange();
})();
