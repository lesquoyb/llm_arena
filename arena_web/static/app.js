"use strict";
const $ = (q, root = document) => root.querySelector(q);
const $$ = (q, root = document) => [...root.querySelectorAll(q)];
const e = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const pretty = (value) => JSON.stringify(value, null, 2);
const fmt = (v, digits = 0) =>
  v == null
    ? "N/A"
    : Number(v).toLocaleString("en-US", { maximumFractionDigits: digits });
const pct = (v) => (v == null ? "N/A" : fmt(v * 100, 1) + "%");
const money = (v) => (v == null ? "Unknown" : "$" + fmt(v, 6));
const date = (v) =>
  v
    ? new Date(v * 1000).toLocaleString("en-US", {
        dateStyle: "short",
        timeStyle: "short",
      })
    : "N/A";
const COLORS = [
  "#5278e5",
  "#c18a4f",
  "#8f75c8",
  "#3e9b87",
  "#cb718b",
  "#7e91ad",
];
// More series than the original six-color palette, with no cyclic reuse.
const SERIES_COLORS=['#3568c0','#b3482c','#16826a','#9255ac','#b27b0a','#c13e79','#397d94','#647824','#783f93','#99613d','#277947','#7759d4','#bd5915','#a43240','#477aaf','#736b36','#3d6973','#ad6889','#6b52a0','#43855b'];
function seriesColor(index) {return SERIES_COLORS[index]||`hsl(${(index*137.508)%360} 58% ${index%2?38:48}%)`;}
let chartHover=null,chartTooltip=null;
function clearChartHover() {
  if(chartHover)for(const item of chartHover.querySelectorAll('[data-chart-model]'))item.classList.remove('chart-dimmed','chart-selected');
  chartHover=null;if(chartTooltip)chartTooltip.hidden=true;
}
function showChartHover(target,event) {
  target.removeAttribute('title');for(const title of target.querySelectorAll('title,[title]')){if(title.tagName.toLowerCase()==='title')title.remove();else title.removeAttribute('title');}
  const scope=target.closest('.resource-chart,.overview-card,.comparison-chart,.panel');
  if(!scope)return;
  if(chartHover!==scope)clearChartHover();chartHover=scope;
  for(const item of scope.querySelectorAll('[data-chart-model]')) {
    const selected=item.dataset.chartModel===target.dataset.chartModel;
    item.classList.toggle('chart-dimmed',!selected);item.classList.toggle('chart-selected',selected);
  }
  if(!chartTooltip) {chartTooltip=document.createElement('div');chartTooltip.id='chart-tooltip';chartTooltip.setAttribute('role','tooltip');document.body.append(chartTooltip);}
  chartTooltip.textContent=target.dataset.chartLabel||target.dataset.chartModel;chartTooltip.hidden=false;
  const rect=target.getBoundingClientRect(),left=event?.clientX??rect.left,top=event?.clientY??rect.bottom;
  chartTooltip.style.left=`${Math.max(8,Math.min(left+12,innerWidth-chartTooltip.offsetWidth-8))}px`;
  chartTooltip.style.top=`${Math.max(8,Math.min(top+16,innerHeight-chartTooltip.offsetHeight-8))}px`;
}
for(const name of ['pointerover','focusin'])document.addEventListener(name,event=>{
  const target=event.target.closest?.('[data-chart-model]');if(target)showChartHover(target,event.type==='focusin'?null:event);
});
for(const name of ['pointerout','focusout'])document.addEventListener(name,event=>{
  const target=event.target.closest?.('[data-chart-model]');if(target&&!target.contains(event.relatedTarget))clearChartHover();
});
const hiddenChartModels=new Map();
function applyChartVisibility() {
  for(const scope of document.querySelectorAll('[data-chart-key]')) {
    const hidden=hiddenChartModels.get(scope.dataset.chartKey)||new Set();
    for(const item of scope.querySelectorAll('[data-chart-model]')) {
      item.removeAttribute('title');
      for(const title of item.querySelectorAll('title,[title]')){if(title.tagName.toLowerCase()==='title')title.remove();else title.removeAttribute('title');}
      const legend=!!item.closest('.chart-legend,.overview-legend');
      const off=hidden.has(item.dataset.chartModel);
      item.classList.toggle('chart-hidden',off&&!legend);
      item.classList.toggle('chart-legend-hidden',off&&legend);
      if(legend) {item.setAttribute('role','button');item.setAttribute('tabindex','0');item.setAttribute('aria-pressed',String(!off));item.setAttribute('aria-label',`${off?'Show':'Hide'} ${item.dataset.chartModel}`);}
    }
  }
}
function toggleChartModel(event) {
  const item=event.target.closest?.('.chart-legend [data-chart-model],.overview-legend [data-chart-model]');
  const scope=item?.closest('[data-chart-key]');if(!scope)return;
  event.preventDefault();
  const key=scope.dataset.chartKey,hidden=hiddenChartModels.get(key)||new Set();
  if(hidden.has(item.dataset.chartModel))hidden.delete(item.dataset.chartModel);else hidden.add(item.dataset.chartModel);
  hiddenChartModels.set(key,hidden);clearChartHover();applyChartVisibility();
}
document.addEventListener('click',toggleChartModel);
document.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' ')toggleChartModel(event);});
let chartVisibilityFrame=null;
new MutationObserver(()=>{if(chartVisibilityFrame===null)chartVisibilityFrame=requestAnimationFrame(()=>{chartVisibilityFrame=null;applyChartVisibility();});}).observe(document.documentElement,{childList:true,subtree:true});
const LABELS = {
  submitted: "Submitted",
  running: "Running",
  stopping: "Stopping",
  stopped: "Stopped",
  completed: "Completed",
  failed: "Failed",
  incomplete: "Incomplete",
  interrupted: "Interrupted",
  needs_reconciliation: "Billing reconciliation needed",
  blocked: "Waiting for recovery",
  budget_exhausted: "Budget exhausted",
  no_submission: "No submission",
  generation_failed: "Generation failed",
  provider_unavailable: "API unavailable",
  valid: "Valid",
  invalid: "Invalid",
  script_errors: "Script error events",
  initial: "Initial version",
  control: "Without feedback",
  feedback: "With feedback",
  all: "All reference opponents",
  g0: "Round 1 submissions as opponents",
  controls: "Built-in scripts as opponents",
  timeout: "Timeout",
  engine_error: "Engine error",
};
const generationLabel = (value) =>
  Number(value || 0) === 0
    ? "Round 1: initial strategy"
    : `Round ${Number(value) + 1}: strategy version`;
const text = (v) => LABELS[v] || v || "N/A";
const badge = (label, color = "") =>
  `<span class="badge ${color}">${e(label)}</span>`;
const status = (v) =>
  badge(
    text(v),
    ["submitted", "completed", "valid"].includes(v)
      ? "green"
      : ["running", "stopping"].includes(v)
        ? "blue"
        : [
              "failed",
              "invalid",
              "needs_reconciliation",
              "engine_error",
            ].includes(v)
          ? "red"
          : "orange",
  );
const raw = (value, title = "Full data") =>
  `<details><summary>${e(title)}</summary><pre>${e(pretty(value))}</pre></details>`;
const btn = (label, action, extra = "", primary = false) =>
  `<button class="button ${primary ? "primary" : ""}" data-action="${action}" ${extra}>${label}</button>`;
const head = (title, description, actions = "") =>
  `<div class="page-head"><div><h1>${e(title)}</h1><p>${e(description)}</p></div><div class="actions">${actions}</div></div>`;
const metric = (label, value, hint = "", icon = "◈") =>
  `<div class="metric"><span class="metric-icon">${icon}</span><span class="label">${e(label)}</span><strong class="value">${e(value)}</strong><span class="hint">${e(hint)}</span></div>`;
const notice = (content, kind = "") =>
  `<div class="notice ${kind}">${content}</div>`;
const empty = (title, description, action = "") =>
  `<div class="empty"><h2>${e(title)}</h2><p>${e(description)}</p>${action}</div>`;
const table = (headers, rows) =>
  `<div class="table-scroll"><table><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
const FIELD_HELP = {
  name: "Name shown in competition lists and exported reports.",
  id: "Local participant identifier. Previous competitions keep their saved participant configuration.",
  provider:
    "Protocol used to call the model. Mock runs a recorded scripted fixture without API calls.",
  replicates:
    "Independent conversations per participant. Each starts with a fresh history; this measures variation between attempts.",
  generations:
    "Total strategy rounds, including the initial round. Later rounds continue separate feedback and no-feedback tracks after all scheduled fights finish.",
  team_mode:
    "Shared mode fixes every member and item. Participant mode lets each AI choose its members, scripts and equipment under the same rules.",
  max_turns:
    "Maximum match rounds. This limits the game, not how long the model can prepare its strategy.",
  input_price:
    "USD per one million input tokens. Used to calculate cost from returned usage; this is a price, not a spending limit.",
  output_price:
    "USD per one million output tokens, including billable reasoning tokens where reported. This is a price, not a spending limit.",
  pricing_date:
    "Date of the prices you entered. The arena does not fetch prices automatically.",
  entity_level:
    "Level shared by all members. Participant-selected equipment cannot require a higher level.",
  entity_life: "Starting health points per member.",
  entity_strength:
    "Strength stat, which affects strength-based effects such as ordinary weapon damage.",
  entity_agility:
    "Critical-hit probability: agility / 1000 (100 agility gives 10%).",
  entity_frequency: "Determines play order: higher frequency acts earlier.",
  entity_wisdom: "Wisdom stat used by healing-related effects.",
  entity_resistance: "Resistance stat used by shield-related effects.",
  entity_science:
    "Increases characteristic buffs such as Protein. A science value of 100 doubles the base strength bonus.",
  entity_magic:
    "Increases poison damage and magic-based debuffs. A magic value of 100 doubles base poison damage.",
  entity_tp:
    "Action points available per member per turn. Weapon and chip costs consume AP.",
  entity_mp:
    "How many movement points this leek receives each turn. Ordinary movement spends one point per traversed cell.",
  entity_cores:
    "Per-turn operation limit is cores × 1,000,000, capped at 2,147,483,647.",
  entity_ram:
    "Also sets the maximum number of equipped chips (one chip per RAM point) in realistic mode. Memory available to each leek script for arrays and objects during a fight, not LLM context. Each RAM stat point permits 8,000,000 tracked 64-bit units (about 64 MB); the generator caps this at 50 points. The Java process has a separate heap limit.",
  team_max_weapons:
    "Additional competition cap. Realistic mode also permits 2 weapons below level 100, 3 below 200, then 4. Zero forbids weapons.",
  team_max_chips:
    "Additional competition cap. In realistic mode each member is also limited to one chip per RAM point. Zero forbids chips.",
};
let helpSequence = 0,
  activeHelp = null,
  helpHideTimer;
const fieldHeading = (label, help) => {
  const id = `field-help-${++helpSequence}`;
  return `<span class="field-heading">${e(label)}${help ? `<span class="help-tip" tabindex="0" role="button" aria-label="Field information" aria-describedby="${id}">?<span id="${id}" class="help-bubble" popover="manual" role="tooltip">${e(help)}</span></span>` : ""}</span>`;
};
function hideHelp() {
  clearTimeout(helpHideTimer);
  if (activeHelp) activeHelp.bubble.hidePopover();
  activeHelp = null;
}
function positionHelp() {
  if (!activeHelp) return;
  const { anchor, bubble } = activeHelp;
  if (!anchor.isConnected) return hideHelp();
  const rect = anchor.getBoundingClientRect();
  const container = anchor.closest("dialog")?.getBoundingClientRect();
  if (
    rect.bottom < 0 ||
    rect.top > innerHeight ||
    (container && (rect.bottom < container.top || rect.top > container.bottom))
  )
    return hideHelp();
  const gap = 8,
    margin = 8,
    size = bubble.getBoundingClientRect();
  const above = rect.top - gap - size.height;
  const top =
    above >= margin
      ? above
      : Math.min(rect.bottom + gap, innerHeight - size.height - margin);
  bubble.style.left = `${Math.max(margin, Math.min(rect.left, innerWidth - size.width - margin))}px`;
  bubble.style.top = `${Math.max(margin, top)}px`;
}
function showHelp(anchor) {
  clearTimeout(helpHideTimer);
  if (activeHelp?.anchor === anchor) return positionHelp();
  hideHelp();
  const bubble = $(".help-bubble", anchor);
  activeHelp = { anchor, bubble };
  bubble.showPopover();
  positionHelp();
}
function scheduleHideHelp() {
  clearTimeout(helpHideTimer);
  helpHideTimer = setTimeout(hideHelp, 180);
}
document.addEventListener("pointerover", (event) => {
  const anchor = event.target.closest(".help-tip");
  if (anchor) showHelp(anchor);
});
document.addEventListener("pointerout", (event) => {
  const anchor = event.target.closest(".help-tip");
  if (anchor && !anchor.contains(event.relatedTarget)) scheduleHideHelp();
});
document.addEventListener("focusin", (event) => {
  const anchor = event.target.closest(".help-tip");
  if (anchor) showHelp(anchor);
});
document.addEventListener("focusout", (event) => {
  if (event.target.closest(".help-tip")) scheduleHideHelp();
});
document.addEventListener("click", (event) => {
  const anchor = event.target.closest(".help-tip");
  if (anchor) {
    event.preventDefault();
    showHelp(anchor);
  }
});
document.addEventListener(
  "keydown",
  (event) => {
    if (event.key === "Escape" && activeHelp) {
      event.preventDefault();
      event.stopImmediatePropagation();
      hideHelp();
    } else if (
      (event.key === "Enter" || event.key === " ") &&
      event.target.matches(".help-tip")
    ) {
      event.preventDefault();
      showHelp(event.target);
    }
  },
  true,
);
window.addEventListener("resize", positionHelp);
document.addEventListener("scroll", positionHelp, true);
const field = (
  label,
  name,
  value = "",
  type = "text",
  help = "",
  attrs = "",
) => {
  help ||= FIELD_HELP[name] || "";
  return `<label class="field">${fieldHeading(label, help)}<input type="${type}" name="${name}" value="${e(value)}" ${attrs}></label>`;
};
const selectField = (label, name, values, current, help = "") => {
  help ||= FIELD_HELP[name] || "";
  return `<label class="field">${fieldHeading(label, help)}<select name="${name}" aria-label="${e(label)}">${values.map(([v, l]) => `<option value="${e(v)}" ${v === current ? "selected" : ""}>${e(l)}</option>`).join("")}</select></label>`;
};
const query = (args) =>
  new URLSearchParams(
    Object.entries(args).filter(([, v]) => v !== undefined && v !== null),
  ).toString();
let S = {
  boot: null,
  workspace: localStorage.getItem('arena-workspace') || '',
  view: "dashboard",
  run: null,
  tab: "summary",
  session: null,
  offset: 0,
  version: null,
  file: null,
  previous: null,
  matchPath: null,
  comparison: null,
  epoch: 0,
};
let toastTimer, replayTimer, R;
let pageRequests = new AbortController();
const runReadCache=new Map();
async function runResource(path,args) {
  const key=JSON.stringify([path,args,path==='/api/match'?'immutable':S.detail?.revision]);
  if(runReadCache.has(key))return runReadCache.get(key).value;
  const value=await api(path,args);
  runReadCache.set(key,{path,value});
  const replays=[...runReadCache].filter(([,entry])=>entry.path==='/api/match');
  for(const [old] of replays.slice(0,Math.max(0,replays.length-2)))runReadCache.delete(old);
  while(runReadCache.size>16)runReadCache.delete(runReadCache.keys().next().value);
  return value;
}
let sessionTokenRefresh=null;
async function refreshSessionToken() {
  if(!sessionTokenRefresh)sessionTokenRefresh=(async()=>{
    const response=await fetch('/api/bootstrap');
    const value=await response.json();
    if(!response.ok||typeof value.token!=='string'||!value.token)throw new Error(value.error||'Unable to refresh the application session');
    // Keep draft inputs and the current page intact across a backend restart.
    S.boot.token=value.token;
  })().finally(()=>{sessionTokenRefresh=null;});
  return sessionTokenRefresh;
}
async function api(path, args = {}, post = false) {
  const url=path+(post?'':Object.keys(args).length?'?'+query(args):'');
  const body=post?JSON.stringify(args):null;
  const initialToken=S.boot?.token;
  const send=(token=S.boot?.token)=>fetch(url,post?{method:'POST',headers:{'Content-Type':'application/json','X-Arena-Token':token},body}:{signal:pageRequests.signal});
  let response=await send(initialToken),value=await response.json();
  if(post&&response.status===403&&(value.code==='stale_arena_token'||value.error==='Reload the page before continuing')) {
    // The server rejected the token before dispatching the action. Retry exactly once.
    if(S.boot.token===initialToken)await refreshSessionToken();
    response=await send();value=await response.json();
  }
  if(!response.ok)throw new Error(value.error||`HTTP error ${response.status}`);
  if(post) {runReadCache.clear();S.detailFetchedAt=0;}
  if(path==='/api/run') {S.detailFetchedAt=Date.now();S.detailFetchedRun=args.run;}
  return value;
}

function toast(message, error = false) {
  const node = $("#toast");
  const dialog = $("#dialog");
  if (error && dialog.open) {
    const alert = $("#dialog-error");
    alert.textContent = message;
    alert.hidden = false;
    alert.scrollIntoView({ block: "nearest" });
    alert.focus({ preventScroll: true });
    return;
  }
  (dialog.open ? dialog : document.body).appendChild(node);
  node.textContent = message;
  node.className = error ? "error" : "";
  node.style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (node.style.display = "none"), 8000);
}
function navigate(view, values = {}) {
  location.hash = query({ view, ...values });
}
function route() {
  pageRequests.abort();
  pageRequests = new AbortController();
  S.liveConversation = null;
  const previousPage = `${S.view}/${S.run}/${S.tab}`;
  const q = new URLSearchParams(location.hash.slice(1));
  S.view = q.get("view") || "dashboard";
  S.run = q.get("run");
  S.tab = q.get("tab") || "summary";
  S.session = q.get("session");
  S.modelFilter = q.get("model");
  S.offset = Number(q.get("offset") || 0);
  S.explicitOffset = q.has("offset");
  S.matchFilters = Object.fromEntries(
    [
      "kind",
      "stage",
      "entrant",
      "opponent",
      "outcome",
      "search",
      "track",
      "entrant_model",
      "opponent_model",
      "round",
      "scored",
      "exclude_same_model",
    ].map((k) => [k, q.get(k) || ""]),
  );
  S.version = null;
  S.versions = null;
  S.previous = null;
  S.file = null;
  S.matchPath = null;
  const nextPage = `${S.view}/${S.run}/${S.tab}`;
  if (S.view==='run' && S.detail?.id===S.run)
    $('#main').innerHTML='<div id="run-chrome">'+runHeader(S.detail)+'</div><section id="run-content" class="panel" aria-busy="true">Loading…</section>';
  renderRoute().then(() => {
    if (nextPage !== previousPage && nextPage === `${S.view}/${S.run}/${S.tab}`)
      window.scrollTo({top:0, behavior:"instant"});
  }).catch(showError);
}
function showError(error) {
  if (error.name === "AbortError") return;
  toast(error.message, true);
  $("#main").classList.remove("busy");
}
async function refreshBoot() {
  S.boot = await api("/api/bootstrap");
  if(S.participantGroup && S.participantGroup!=='ungrouped' && !S.boot.participant_groups.some(g=>g.id===S.participantGroup))S.participantGroup='';
  if (S.workspace && S.workspace !== 'unassigned' && !S.boot.workspaces.some(w=>w.id===S.workspace)) setWorkspace('');
  S.equipment ||= await api("/api/equipment");
  syncLiveMode();
  updateChrome();
}
function syncLiveMode() {
  S.livePreferences ||= {};
  if (activeJobs().some((job) => job.run === S.run)) S.autoLiveRun = S.run;
  S.follow = S.livePreferences[S.run] ?? S.autoLiveRun === S.run;
}
function activityDuration(started) {
  if(!started)return '';
  const seconds=Math.max(0,Math.floor(Date.now()/1000-started));
  return seconds<60?`${seconds}s`:`${Math.floor(seconds/60)}m ${seconds%60}s`;
}
const activityClock=start=>`<span data-activity-clock="${start||''}">${activityDuration(start)}</span>`;
function competitionActivity(activity=S.activity) {
  if(!activity || S.activityRun!==S.run)return '<section id="competition-activity" class="competition-activity"><strong>Loading competition activity…</strong></section>';
  const labels={retry_backoff:'Waiting for automatic provider retry',starting:'Starting / resuming',checkpoint_verification:'Checking saved history and source integrity',scheduling_preparations:'Scheduling / resuming model conversations',checking_fights:'Checking completed fights and scheduling missing fights',request_preparation:'Preparing provider request',tournament_fight:'Tournament fight',reference_fight:'Reference evaluation',previous_round_fight:'Previous-round comparison (unscored)',validation:'Validating a submitted strategy',preparation_analysis:'Compiling a preparation script',preparation_fight:'Preparation test (unscored)'};
  const op=activity.operation||{},busy=op.kind&&op.kind!=='idle';
  const title=!activity.running ? text(activity.job_status || 'Paused') : labels[op.kind] || (activity.active.length?'Model preparation in progress':'Scheduling next work');
  const actor=sid=>{const info=activity.labels?.[sid];const label=info?`${info.model} · R${info.round}${info.condition!=='initial'?' · '+text(info.condition):''}${info.replicate?' · Repetition '+(info.replicate+1):''}`:sid;return info?btn(e(label),'session-conversation',`data-session="${e(sid)}"`):`<span>${e(label)}</span>`;};
  const phases=[['active','Preparing now'],['ready','Preparation finished'],['attention','Needs attention'],['waiting','Waiting']];
  const fightPhases={starting_jvm:'Starting reusable JVM',preparing:'Preparing scenario and source files',staging_data:'Preparing engine data',engine:'Java process',computing:'Engine',reading_result:'Reading and hashing output',cleanup_data:'Cleaning engine data',archiving_result:'Saving engine result',waiting_reference_cache:'Waiting for identical reference cache entry',reference_cache:'Checking reference cache',materializing_cache:'Copying cached replay',publishing_cache:'Saving reference cache',verifying_result:'Verifying result',ready_to_save:'Finished; waiting for publication'};
  const computingFights=(op.fights||[]).filter(fight=>!fight.phase||fight.phase==='computing'||fight.phase==='engine').length;
  const verifyingFights=(op.fights||[]).filter(fight=>fight.phase==='verifying_result').length;
  const finishedFights=(op.fights||[]).filter(fight=>fight.phase==='ready_to_save').length;
  const fightList=activity.running&&op.fights?.length?`<div class="activity-fights"><strong>${op.fights.length} occupied slots · limit ${op.parallel_fights}</strong>${op.fights.map(fight=>`<div class="activity-actors">${fight.participants.map(actor).join('<span>vs</span>')}<small>${e(fightPhases[fight.phase]||fightPhases.computing)} · ${activityClock(fight.phase_started_at||fight.started_at)} in stage · ${activityClock(fight.started_at)} since fight dispatch · Seed ${fight.seed}${fight.retry?' · Retry '+fight.retry+' / 2':''}</small></div>`).join('')}</div>`:'';
  const preparationList=phases.map(([phase,label])=>{
    const items=(activity.preparations||[]).filter(item=>item.phase===phase);
    const pending=phase==='waiting'?(activity.waiting_preparations||[]):[];
    if(!items.length&&!pending.length)return '';
    return `<div class="activity-roster-group"><strong>${label} · ${items.length+pending.reduce((sum,item)=>sum+item.count,0)}</strong><div>${items.map(item=>actor(item.session)).join('')}${pending.map(item=>`<span class="badge">${e(item.model)}${item.count>1?' × '+item.count:''}</span>`).join('')}</div></div>`;
  }).join('');
  const breakdown=activity.submission_breakdown||[];
  const generated=breakdown.filter(row=>!row.fixed).reduce((sum,row)=>sum+row.expected,0);
  const fixed=breakdown.filter(row=>row.fixed).reduce((sum,row)=>sum+row.expected,0);
  const submissionDetails=breakdown.length?`<details class="quiet-details"><summary>Expected submissions: ${generated} generated + ${fixed} fixed</summary>${table(['Participant','Repetitions','Tracks','Submitted / expected'],breakdown.map(row=>`<tr><td>${e(row.model)}${row.fixed?'<small>Fixed reference</small>':''}</td><td>${row.repetitions}</td><td>${row.tracks}</td><td>${row.submitted} / ${row.expected}</td></tr>`))}</details>`:'';
  const activeSessions=[...(activity.active||[]),...(activity.preparations||[]).filter(item=>item.phase==='active')];
  const activeModels=[...activeSessions.reduce((models,item)=>{const name=item.model||activity.labels?.[item.session]?.model||item.session;if(!models.has(name))models.set(name,item);return models;},new Map()).entries()];
  const preview=activeModels.slice(0,3).map(([model,item])=>btn(e(model),'session-conversation',`data-session="${e(item.session)}" title="Open active conversation"`)).join('');
  return `<section id="competition-activity" class="competition-activity activity-compact" aria-label="Competition activity"><div class="activity-heading"><strong>${activity.running?'<i class="activity-dot" aria-hidden="true"></i>':''}${e(title)}${activity.running&&busy&&op.started_at?` <small>· ${op.batch_started_at?'Batch ':''}${activityClock(op.started_at)}</small>`:''}</strong><span>Round ${activity.round}${activity.rounds==null?'':` / ${activity.rounds}`} · ${activity.participants} participants</span></div><div class="activity-at-a-glance">${op.kind!=='idle'&&op.parallel_fights&&activity.requested_parallel_fights&&op.parallel_fights!==activity.requested_parallel_fights?`<span>Worker change pending · current ${op.parallel_fights}, requested ${activity.requested_parallel_fights}</span>`:''}${!S.detail?.archived&&S.detail?.metadata.config?btn('Workers: '+(activity.requested_parallel_fights||S.detail?.execution_control?.parallel_fights||activity.operation?.parallel_fights||1),'live-fight-workers')+btn('Provider limits','provider-limits')+btn('Retry failed fights','retry-failed-fights'):''}${activity.running&&activity.parallel_requests?`<span><strong>${activity.active.filter(item=>item.kind==='model_request').length} / ${activity.parallel_requests}</strong> requests in flight</span>`:''}<span><strong>${activity.strategies_ready} / ${activity.strategies_expected}</strong> prepared</span><span><strong>${activity.tournament_completed} / ${activity.tournament_total}</strong> fights</span>${computingFights?`<span><strong>${computingFights}</strong> fights running</span>`:''}${verifyingFights?`<span><strong>${verifyingFights}</strong> verifying</span>`:''}${finishedFights?`<span><strong>${finishedFights}</strong> finished; saving</span>`:''}${activity.throughput?`<span><strong>${fmt(activity.throughput.engine_per_minute)}</strong> engine fights/min <small>${fmt(activity.throughput.turns_per_minute||0)} turns/min · ${fmt(activity.throughput.operations_per_minute||0)} operations/min · ${fmt(activity.throughput.cache_per_minute)} cache hits · last 60 s</small></span>`:''}${op.next_retry_at?`<span>Next retry: <strong>${new Date(op.next_retry_at*1000).toLocaleTimeString()}</strong></span>`:''}${op.total_records?`<span><strong>${op.checked_records} / ${op.total_records}</strong> ${op.kind==='checkpoint_verification'?'journal checks complete':'scheduled records checked'}</span>`:''}${activity.failed_preparations?`<span class="badge orange">${activity.failed_preparations} need attention</span>`:''}</div>${activity.running&&activeModels.length?`<div class="activity-preview"><span>Preparing · ${activeModels.length}</span>${preview}${activeModels.length>3?btn('+'+(activeModels.length-3)+' more','expand-activity'):''}</div>`:''}<details id="competition-activity-details" class="activity-details" ${S.activityExpanded?.[S.run]?'open':''}><summary>Activity details</summary><div class="activity-detail-body"><div class="activity-progress"><span><strong>${activity.ready_participants} / ${activity.participants}</strong> participants ready</span><span><strong>${activity.strategies_ready} / ${activity.strategies_expected}</strong> strategies submitted</span><span><strong>${activity.strategies_checked??activity.strategies_validated} / ${activity.strategies_ready}</strong> final compilation checks</span><span><strong>${activity.tournament_completed} / ${activity.tournament_total}</strong> tournament fights${activity.tournament_failed?` · ${btn(activity.tournament_failed+' engine failures','show-engine-failures',`data-stage="${activity.round===1?'tournament':'g'+(activity.round-1)+'-tournament'}"`)}`:''}</span><span><strong>${activity.tournament_pending_available??0}</strong> unfinished fights between submitted strategies</span>${activity.tournament_unscheduled_available?`<span><strong>${activity.tournament_unscheduled_available}</strong> available fights not yet added to the plan</span>`:''}<span><strong>${activity.tournament_waiting_submissions??0}</strong> fights await submissions</span></div>${op.publication?.started_at?`<small>Publishing a finished result · ${activityDuration(op.publication.started_at)}</small>`:''}${op.jvm_starts||op.jvm_reuses?`<small>JVM starts: ${op.jvm_starts||0} · Reused: ${op.jvm_reuses||0}</small>`:''}${op.publishing_seconds!=null?`<small>Result publication this batch: ${fmt(op.publishing_seconds,2)} s · ${op.finished_workers??0} workers finished</small>`:''}<small>${activity.strategies_valid??0} valid · ${activity.strategies_invalid??0} invalid · ${activity.strategies_awaiting_check??Math.max(0,activity.strategies_ready-activity.strategies_validated)} awaiting final check. Final checks run after preparation; earlier agent compilation checks are recorded under Errors.</small>${submissionDetails}${fightList}${activity.running&&busy&&!op.fights&&op.participants?.length?`<div class="activity-actors"><span>${op.kind==='preparation_fight'?'Testing':'Engine'}:</span>${op.participants.map(actor).join('<span>vs</span>')}${op.opponent?`<span>vs ${e(op.opponent)}</span>`:''}</div>`:''}${activity.running&&activity.active.length?`<div class="activity-requests">${activity.active.map(item=>`<span>${actor(item.session)}<small>${item.kind==='model_request'?'Awaiting model response':item.kind==='provider_receipt_waiting'?(item.transport_phase==='failed'?'Provider stopped; recovery pending':'Response received; waiting for coordinator'):e(item.name||'Using tool')} · ${activityClock(item.started_at)}${item.kind==='model_request'?` · No output for ${activityClock(item.no_output_since||item.started_at)} · pauses after ${item.inactivity_timeout_seconds??300}s`:''}</small></span>`).join('')}</div>`:''}${preparationList?`<div class="activity-roster">${preparationList}</div>`:''}${activity.failed_preparations?`<p>${activity.failed_preparations} preparations need recovery.</p>`:''}<div class="activity-footer"><span>${activity.last_event?.at?'Last recorded progress: '+date(activity.last_event.at):'No checkpoint event recorded yet.'}</span><small>Updated ${new Date(activity.observed_at*1000).toLocaleTimeString()}</small></div>${activity.running&&!busy&&!activity.active.length?'<small>No model request or engine operation is currently recorded.</small>':''}${!activity.running&&activity.job_note?`<p>${e(activity.job_note)}</p>`:''}</div></details></section>`;
}
let activityRequest=null;
async function refreshCompetitionActivity(epoch=S.epoch) {
  const run=S.run;
  if(!run||S.view!=='run')return;
  if(activityRequest?.run===run)return activityRequest.promise;
  const promise=(async()=>{
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),8000);
    try {
      const response=await fetch('/api/activity?'+query({run}),{signal:controller.signal});
      const data=await response.json();if(!response.ok)throw Error(data.error||'Activity unavailable');
      if(run!==S.run||S.view!=='run')return;
      S.activity=data;S.activityRun=run;S.activityReceived=Date.now();
      if(data.jobs)S.boot.jobs=[...S.boot.jobs.filter(job=>job.run!==run),...data.jobs];
      const panel=$('#competition-activity');if(panel)LiveDOM.replace(panel,competitionActivity(data));
      const chrome=$('#run-chrome');if(chrome&&S.detail)LiveDOM.update(chrome,runHeader(S.detail));
    } finally {clearTimeout(timeout);if(activityRequest?.promise===promise)activityRequest=null;}
  })();
  activityRequest={run,promise};return promise;
}
setInterval(()=>{
  if(!S.boot||document.hidden||S.view!=='run')return;
  refreshCompetitionActivity().catch(()=>{const panel=$('#competition-activity');if(panel)panel.dataset.stale='true';});
},2000);
setInterval(()=>{
  for(const node of $$('[data-activity-clock]'))node.textContent=activityDuration(Number(node.dataset.activityClock));
},1000);

function activeJobs() {
  return S.boot.jobs.filter((j) => ["running", "stopping"].includes(j.status));
}
function updateChrome() {
  const picker=$('#workspace-picker');
  const options=workspaceOptions(true);
  if (picker.dataset.options!==pretty(options)) {
    if(LiveDOM.update(picker,options.map(([id,name])=>`<option value="${e(id)}">${e(name)}</option>`).join('')))
      picker.dataset.options=pretty(options);
  }
  if(picker.value!==S.workspace)picker.value=S.workspace;
  const ready = S.boot.engine.ready;
  $("#engine-status").className = "badge " + (ready ? "green" : "orange");
  $("#engine-status").textContent = ready
    ? "● Engine ready"
    : "Engine check failed";
  $("#engine-status").title = ready
    ? "Engine validated for new matches."
    : (S.boot.engine.error || "Engine validation failed.") +
      " Existing match results remain readable. Refresh to recheck.";
  $("#active-count").textContent = activeJobs().length || "";
  $$("[data-nav]").forEach((n) => {
    const current = n.dataset.nav === (S.view === "run" || S.view === "editor" ? "competitions" : S.view);
    if (current) n.setAttribute("aria-current", "page"); else n.removeAttribute("aria-current");
    n.classList.toggle(
      "active",
      n.dataset.nav ===
        (S.view === "run" || S.view === "editor" ? "competitions" : S.view),
    );
  });
  $("#breadcrumb").textContent =
    "" +
    ({
      dashboard: "Overview",
      workspaces: "Workspaces",
      participants: "Participants",
      competitions: "Competitions",
      run: "Exploration",
      editor: "Configuration",
      compare: "Comparison",
      help: "Guide",
    }[S.view] || "Overview");
}
async function renderRoute() {
  hideHelp();clearChartHover();
  document.body.dataset.view = S.view;
  const epoch = ++S.epoch;
  clearInterval(replayTimer);
  replayTimer = null;
  R = null;
  updateChrome();
  if (S.view === 'workspaces' && S.workspace) {
    const workspace=S.workspace;
    S.workspaceSummary=null;S.workspaceLoadError=null;
    $('#main').innerHTML=workspacesPage();
    try {
      const resources=await api('/api/workspace',{workspace,section:'resources'});
      if(epoch!==S.epoch||workspace!==S.workspace)return;
      S.workspaceSummary=resources;
      LiveDOM.update($('#main'),workspacesPage());
      if(S.workspaceSummary.performance_pending) {
        const summary=await api('/api/workspace',{workspace});
        if(epoch!==S.epoch||workspace!==S.workspace)return;
        S.workspaceSummary=summary;
        LiveDOM.update($('#main'),workspacesPage());
      }
    } catch(error) {
      if(error.name==='AbortError'||epoch!==S.epoch)return;
      S.workspaceLoadError=error.message;
      LiveDOM.update($('#main'),workspacesPage());
    }
    return;
  }
  if (S.view === "run") {
    syncLiveMode();
    const reuse=S.detail?.id===S.run && S.detailFetchedRun===S.run && S.detailFetchedAt>0;
    const stale=reuse && Date.now()-S.detailFetchedAt>(activeJobs().some(job=>job.run===S.run)?2500:30000);
    const d = await (reuse?Promise.resolve(S.detail):api("/api/run", { run: S.run })).catch(async (error) => {
      if (error.name === "AbortError") throw error;
      if (activeJobs().some((j) => j.run === S.run)) {
        setTimeout(() => renderRoute().catch(showError), 800);
        return null;
      }
      throw error;
    });
    if (epoch !== S.epoch) return;
    if (!d) {
      $("#main").innerHTML = empty(
        "Preparing competition",
        "Creating initial checkpoints...",
      );
      return;
    }
    S.detail = d;
    await renderRun(epoch);
    if(stale && epoch===S.epoch) {
      const fresh=await api('/api/run',{run:S.run});
      if(epoch!==S.epoch)return;
      if(fresh.revision!==S.detail.revision) {S.detail=fresh;await renderRun(epoch,true);}
    }
    return;
  }
  if (S.view === "editor" && !S.equipment) {
    S.equipment = await api("/api/equipment");
    if (epoch !== S.epoch) return;
  }
  const renderers = {
    dashboard: dashboard,
    workspaces: workspacesPage,
    participants: participants,
    competitions: competitions,
    compare: comparePage,
    help: helpPage,
    editor: competitionEditor,
  };
  $("#main").innerHTML = (renderers[S.view] || dashboard)();
  if (S.view === "editor") updateStatPreviews();
}
function completed(report) {
  if (!report) return 0;
  return (
    (report.completed || 0) +
    (report.tournament?.completed || 0) +
    (report.evolution?.contemporaries?.completed || 0) +
    (report.evolution?.rows || [])
      .filter((r) => r.panel === "all")
      .reduce((n, r) => n + r.completed, 0)
  );
}
function runRows(runs) {
  return runs.map((r) => {
    const job = S.boot.jobs.find((j) => j.run === r.id);
    return `<tr><td><button class="table-button" data-action="open-run" data-run="${e(r.id)}">${e(r.name)}</button><small>${e(r.id)}</small><button class="workspace-tag" data-action="move-workspace" data-run="${e(r.id)}">${e(workspaceName(r.workspace_id))} ▾</button></td><td>${job && ["running", "stopping"].includes(job.status) ? status(job.status === "failed" && r.report?.incomplete ? "incomplete" : job.status) : r.error ? status("failed") : r.complete ? status("completed") : badge("Review needed", "orange")}</td><td>${r.simulated === true ? badge("Simulation", "blue") : r.simulated === false ? badge("Real API calls", "orange") : badge("Strategies")}</td><td class="numeric">${fmt(r.report?.sessions ?? r.models)}</td><td class="numeric">${fmt(completed(r.report))}</td><td class="numeric">${r.report?.cost_usd === undefined ? "N/A" : money(r.report.cost_usd)}</td><td>${date(r.created_at)}</td></tr>`;
  });
}
function runTable(runs) {
  return runs.length
    ? table(
        [
          "Competition",
          "Status",
          "Mode",
          "Sessions",
          "Completed matches",
          "API cost",
          "Created",
        ],
        runRows(runs),
      )
    : empty(
        "No competitions yet",
        "Configure participants or run the offline demo.",
        btn("＋ Create competition", "new-competition", "", true),
      );
}
function recentRuns(runs) {
  return runs.length ? `<div class="recent-runs">${runs.map(r=>{
    const job=S.boot.jobs.find(j=>j.run===r.id);
    const state=job?.status || (r.error ? "failed" : r.complete ? "completed" : "incomplete");
    return `<article class="recent-run"><div class="run-mark ${["running","stopping"].includes(state) ? "is-active" : ""}" aria-hidden="true">${["running","stopping"].includes(state) ? "◉" : "⚑"}</div><div class="recent-run-name"><button class="card-title" data-action="open-run" data-run="${e(r.id)}">${e(r.name)}</button><small>${e(r.id)} · ${date(r.created_at)}</small></div>${status(state)}<div class="recent-run-stat"><strong>${fmt(completed(r.report))}</strong><small>fights</small></div><button class="icon-button" data-action="open-run" data-run="${e(r.id)}" aria-label="Open ${e(r.name)}">→</button></article>`;
  }).join("")}</div>` : empty("Your first competition", "Add participants, choose a scenario, then launch a run.", btn("Create competition","new-competition","",true));
}
function dashboard() {
  const runs = scoped(S.boot.runs).filter((r) => !r.archived),
    known = runs.filter((r) => r.report?.cost_usd != null),
    unknown = runs.filter((r) => r.report && r.report.cost_usd === null).length;
  return (
    head(
      "Overview",
      "Your experiments at a glance.",
      btn("＋ New competition", "new-competition", "", true),
    ) +
    `<div class="metrics">${metric("Competitions", fmt(runs.length), `${activeJobs().length} running`, "⚑")}${metric("Configured participants", fmt(S.boot.participants.length), "Reusable profiles", "♧")}${metric("Completed matches", fmt(runs.reduce((n, r) => n + completed(r.report), 0)), "All evaluation stages", "⚔")}${metric("Estimated API cost", money(known.reduce((n, r) => n + Number(r.report.cost_usd), 0)), unknown ? `${unknown} costs still unknown` : "Configured token prices", "↗")}</div>` +
    (!S.boot.engine.ready
      ? notice(
          `The engine is not ready. Existing results are still readable. Run <code>python scripts/bootstrap.py</code> after installing JDK 25. ${e(S.boot.engine.error)}`,
          "warn",
        )
      : "") +
    `<section class="panel flush"><div class="panel-head"><div><h2>Recent competitions</h2><p>Latest activity across your workspace.</p></div>${btn("View all", "go", 'data-view="competitions"')}</div>${recentRuns([...runs].sort((a,b)=>Number(activeJobs().some(j=>j.run===b.id))-Number(activeJobs().some(j=>j.run===a.id))).slice(0,6))}</section>` +
    `<div class="workspace-shortcuts"><div><strong>Try a local run</strong><span>Built-in scripts, real engine, no API calls.</span></div>${btn("Configure demo", "new-demo")}<a href="#view=help">Scoring & setup guide →</a></div>`
  );
}
const PROVIDER_NAMES = {mock: "Built-in strategy", openai: "OpenAI", anthropic: "Anthropic", gemini: "Google Gemini", "openai-compatible": "Compatible API / local"};
function participantGroups(id) {
  return S.boot.participant_groups.filter(group=>group.members.includes(id));
}
function participantProfiles(term='') {
  const selected=S.participantGroup||'';
  return S.boot.participants.filter(({spec:m})=>{
    const groups=participantGroups(m.id);
    return (!selected || (selected==='ungrouped' ? !groups.length : groups.some(g=>g.id===selected))) &&
      `${m.id} ${m.provider} ${m.model||m.profile} ${groups.map(g=>g.name).join(' ')}`.toLowerCase().includes(term.toLowerCase());
  });
}
function refreshParticipantCards() {
  const term=$('#participant-search')?.value||'';
  $('#participant-cards').innerHTML=participantCards(term);
  $('#participant-count').textContent=`${participantProfiles(term).length} of ${S.boot.participants.length} profiles`;
}
function participantGroupDialog(id=null) {
  const current=S.boot.participant_groups.find(g=>g.id===id);
  openDialog('Participant groups','Profiles can belong to several groups.',`
    <div class="participant-group-list">${S.boot.participant_groups.map(group=>`<button class="button ${group.id===id?'primary':''}" data-action="edit-participant-group" data-id="${e(group.id)}">${e(group.name)} (${group.members.length})</button>`).join('')}${btn('New group','new-participant-group')}</div>
    <form data-form="participant-group" data-id="${e(id||'')}"><label class="field">Group name<input name="name" value="${e(current?.name||'')}" required maxlength="100" placeholder="Local, Free APIs, Reasoning models..."></label>
    <label class="field">Find profiles<input type="search" id="group-member-search"></label>
    <div class="actions">${btn('Select visible','group-select-visible')}${btn('Clear visible','group-clear-visible')}</div>
    <div class="group-members">${S.boot.participants.map(({spec:m})=>`<label class="group-member choice"><input type="checkbox" name="member" value="${e(m.id)}" ${current?.members.includes(m.id)?'checked':''}><span><strong>${e(m.id)}</strong><small>${e(m.model||m.profile)} · ${e(m.provider)}</small></span></label>`).join('')}</div>
    <div class="form-footer">${current?btn('Delete group','delete-participant-group',`data-id="${e(id)}"`):''}<button type="submit" class="button primary">Save group</button></div></form>`);
}
function profileGroupsDialog(id) {
  openDialog('Groups',id, S.boot.participant_groups.length ?
    `<form data-form="profile-groups" data-id="${e(id)}"><div class="group-members">${S.boot.participant_groups.map(group=>`<label class="choice"><input type="checkbox" name="group" value="${e(group.id)}" ${group.members.includes(id)?'checked':''}><span>${e(group.name)}</span></label>`).join('')}</div><button class="button primary" type="submit">Save memberships</button></form>`:
    `<p>No groups yet.</p>${btn('Create a group','new-participant-group')}`);
}
function competitionGroupPicker() {
  const groups=S.boot.participant_groups;
  return `<div class="competition-group-picker">${selectField('Add participants from group','participant_group',[['','Choose a group'],...groups.map(g=>[g.id,`${g.name} (${g.members.length})`])],'')}${btn('Add group','add-competition-group',groups.length?'':'disabled')}${btn('Clear selection','clear-competition-participants')}</div><p id="group-selection-status" class="muted" aria-live="polite"></p>`;
}

function participantCards(term = "") {
  const profiles = participantProfiles(term);
  return profiles.length ? profiles.map(({spec:m,key_configured,key_optional}) => `<article class="profile-card">
    <div class="profile-card-top"><span class="provider-mark provider-${e(m.provider)}" aria-hidden="true">${e((PROVIDER_NAMES[m.provider] || m.provider)[0])}</span>${badge(m.profile === "saved-strategy" ? "Saved strategy" : PROVIDER_NAMES[m.provider] || m.provider)}<span class="spacer"></span><button class="icon-button" data-action="delete-participant" data-id="${e(m.id)}" title="Remove profile" aria-label="Remove ${e(m.id)}">×</button></div>
    <h2><button class="card-title" data-action="edit-participant" data-id="${e(m.id)}">${e(m.id)}</button></h2><p class="profile-model mono">${e(m.model || m.profile)}</p><div class="participant-group-tags">${participantGroups(m.id).map(g=>badge(g.name)).join("")}</div>
    <dl class="profile-facts">${m.model_size_billion ? `<div><dt>Model size</dt><dd>${fmt(m.model_size_billion,3)}B parameters</dd></div>` : ""}<div><dt>Reasoning</dt><dd>${m.provider === "mock" ? "Scripted" : e(reasoningLabel(m.parameters))}</dd></div><div><dt>Input / output · $ / 1M</dt><dd>${m.pricing ? `${e(m.pricing.input_per_million)} / ${e(m.pricing.output_per_million)}` : "No API cost"}</dd></div></dl>
    <div class="profile-card-footer">${m.provider === "mock" ? badge("Ready", "green") : badge(key_optional && !key_configured ? "Local · no key required" : key_configured ? "Key configured" : "API key missing", key_configured || key_optional ? "green" : "orange")}${m.provider!=="mock"?btn("Test API","test-model",`data-id="${e(m.id)}"`):""}${btn("Groups", "profile-groups", `data-id="${e(m.id)}"`)}${btn("Configure", "edit-participant", `data-id="${e(m.id)}"`)}</div></article>`).join("") : empty("No participants found", term ? "Try a different name, model or provider." : "Add a model provider or a built-in strategy.", term ? "" : btn("Add participant","new-participant","",true));
}
function providersDialog(identifier=null) {
  const saved=(S.boot.providers||[]),spec=saved.find(row=>row.spec.id===identifier)?.spec||{};
  openDialog('Saved providers','Reuse a connection across model participants.',`
    <div class="actions">${saved.map(row=>`<button type="button" class="button" data-action="edit-provider" data-id="${e(row.spec.id)}">${e(row.spec.id)} · ${row.key_configured?'Key configured':row.key_optional?'Local':'Key needed'}</button>`).join('')}${btn('New provider','new-provider')}</div>
    <form data-form="provider"><div class="form-grid">
    ${field('Provider name','id',spec.id||'','text','',`required pattern="[a-zA-Z0-9][a-zA-Z0-9_-]{0,39}" ${identifier?'readonly':''}`)}
    ${selectField('Protocol','provider',[['openai-compatible','OpenAI-compatible (Groq, Ollama, etc.)'],['openai','OpenAI'],['anthropic','Anthropic'],['gemini','Google Gemini']],spec.provider||'openai-compatible')}
    ${field('Full API endpoint','endpoint',spec.endpoint||'','url','For compatible APIs, include /v1/chat/completions. Leave blank for the default OpenAI, Anthropic or Gemini endpoint.')}
    ${field('API key environment variable','api_key_env',spec.api_key_env||'','text','Example: ARENA_GROQ_KEY. Define it in the repository-root .env file; loaded on startup. Reused by every participant from this provider.','required pattern="ARENA_[A-Z0-9_]+"')}
    <label class="field full">API key<input name="secret" type="password" autocomplete="new-password"><small>Kept in server memory until shutdown. Put the key in the repository-root .env file under the variable name above to keep it available after restarting.</small></label>
    </div><div class="form-footer">${identifier?`<button type="button" class="button" data-action="delete-provider" data-id="${e(identifier)}">Delete provider</button>`:''}<button type="submit" class="button primary">Save connection</button></div></form>
    ${identifier?`<section class="form-section"><h3>Create model participants</h3><p>Load the catalog, select models and enter each model’s prices. No generation requests are made.</p><button type="button" class="button" data-action="provider-models" data-id="${e(identifier)}">Load models</button><div id="provider-models"></div></section>`:''}`);
}
async function providerModels(identifier) {
  const spec=S.boot.providers.find(row=>row.spec.id===identifier).spec;
  const data=await api('/api/models',spec,true);
  const occupied=new Set(S.boot.participants.map(row=>row.spec.id));
  const rows=data.models.map((row,index)=>{
    const stem=(identifier+'-'+row.id).replace(/[^a-zA-Z0-9_-]/g,'-').slice(0,35);let id=stem,n=2;
    while(occupied.has(id))id=stem+'-'+n++;
    occupied.add(id);
    return `<section class="form-section" data-provider-model="${index}"><label class="check"><input type="checkbox" name="selected" value="${index}"><strong>${e(row.id)}</strong></label><div class="form-grid">${field('Participant ID','id-'+index,id,'text','')}${field('Input / million tokens ($)','input-'+index,'','number','','min="0" step="any"')}${field('Output / million tokens ($)','output-'+index,'','number','','min="0" step="any"')}${field('Size (B parameters), optional','size-'+index,'','number','Total parameters in billions. Blank means unknown.','min="0.000001" max="1000000" step="any"')}${spec.provider==='anthropic'?field('Maximum output tokens','max-'+index,4096,'number','Required by Anthropic.','min="1"'):''}</div></section>`;
  }).join('');
  S.providerModelCatalog=data.models;
  $('#provider-models').innerHTML=`<form data-form="provider-participants" data-provider="${e(identifier)}"><label class="field">Filter models<input type="search" id="provider-model-search"></label><p>${data.models.length} listed; ${(data.excluded||[]).length} incompatible models excluded${data.truncated?' (partial catalog)':''}. Chat/tool compatibility is not guaranteed.</p>${rows}<button type="submit" class="button primary">Create selected participants</button></form>`;
}

function participants() {
  return head("Participants", "Reusable model profiles for your competitions.", btn("Groups","participant-groups") + btn("Providers & bulk add","providers") + btn("Add reference strategy","add-reference") + btn("＋ Add participant", "new-participant", "", true)) +
    `<div class="collection-toolbar"><span id="participant-count" aria-live="polite">${participantProfiles().length} of ${S.boot.participants.length} profiles</span>${selectField("Filter by group","participant_group_filter",[["","All profiles"],["ungrouped","Ungrouped"],...S.boot.participant_groups.map(g=>[g.id,g.name])],S.participantGroup||"")}<input type="search" id="participant-search" placeholder="Search name, model or provider" aria-label="Search participants"></div><div class="profile-grid" id="participant-cards">${participantCards()}</div><details class="quiet-details"><summary>API keys and pricing</summary><p>Keys entered in the interface stay in server memory. Prices are entered in USD per million tokens. Existing competitions retain the settings saved at launch.</p></details>`;
}
function freshConfig() {
  const config = structuredClone(S.boot.default_config),
    catalog = S.boot.participants.map((p) => p.spec),
    ids = config.models.map((m) => m.id);
  config.budget_per_session = {};
  delete config.spending.max_total_usd;
  config.models = structuredClone(catalog.filter((m) => ids.includes(m.id)));
  if (!config.models.length)
    config.models = structuredClone(catalog.slice(0, 2));
  return config;
}
function workspaceName(id) {
  return S.boot.workspaces.find(w=>w.id===id)?.name || 'Unassigned';
}
function workspaceOptions(scope=false) {
  return [...(scope ? [['','All competitions'],['unassigned','Unassigned']] : [['','Unassigned']]),
    ...S.boot.workspaces.map(w=>[w.id,w.name])];
}
function setWorkspace(id) {
  S.workspace=id;
  localStorage.setItem('arena-workspace',id);
  S.comparison=null;S.compareSelection=[];S.workspaceSummary=null;S.workspaceGroup=0;
}
function scoped(rows) {
  return rows.filter(row=>!S.workspace || (S.workspace==='unassigned' ? !row.workspace_id : row.workspace_id===S.workspace));
}
async function chooseWorkspace(id) {
  setWorkspace(id);
  const next='#'+query({view:'workspaces'});
  if(location.hash===next)await renderRoute();else navigate('workspaces');
}
function workspaceDialog(id=null) {
  const current=S.boot.workspaces.find(w=>w.id===id);
  openDialog(current?'Edit workspace':'New workspace','Organize competitions without changing their saved settings.',
    `<form data-form="workspace" data-id="${e(id||'')}"><label class="field">Name<input name="name" value="${e(current?.name||'')}" required maxlength="100"></label>
    <label class="field">Description<textarea name="description" rows="3" maxlength="2000">${e(current?.description||'')}</textarea></label>
    <div class="form-footer">${current?btn('Delete workspace','delete-workspace',`data-id="${e(id)}"`):''}<button type="submit" class="button primary">Save workspace</button></div></form>`);
}
function workspaceMembers(id) {
  const title=(row,kind)=>kind==='drafts'?row.config.name:row.name;
  openDialog('Choose competitions',workspaceName(id),`<form data-form="workspace-members" data-id="${e(id)}">
    <label class="field">Search<input type="search" id="workspace-member-search" placeholder="Name or competition ID"></label>
    <div class="actions">${btn('Select visible','workspace-select-visible')}${btn('Clear visible','workspace-clear-visible')}</div>
    <div class="workspace-members">${[['runs','Competitions',S.boot.runs],['drafts','Saved configurations',S.boot.drafts]].map(([kind,label,rows])=>
      `<h3>${label}</h3>${rows.length?rows.map(row=>`<label class="workspace-member"><input type="checkbox" name="${kind}" value="${e(row.id)}" ${row.workspace_id===id?'checked':''}><span><strong>${e(title(row,kind))}</strong><small>${e(workspaceName(row.workspace_id))} · ${e(row.id)}${row.archived?' · Exported copy (excluded from statistics)':''}</small></span></label>`).join(''):'<p class="muted">None yet.</p>'}`).join('')}</div>
    <p class="muted">Selected items move here. Unchecked items currently in this workspace become unassigned.</p>
    <button type="submit" class="button primary">Save selection</button></form>`);
}
function workspaceSkeleton(label) {
  if(S.workspaceLoadError)return `<section class="panel"><h2>${e(label)}</h2>${notice(e(S.workspaceLoadError),'error')}${btn('Retry statistics','reload-workspace')}</section>`;
  return `<section class="panel workspace-skeleton" aria-busy="true" aria-label="Loading ${e(label.toLowerCase())}"><h2>${e(label)}</h2><span class="muted" role="status">Loading ${e(label.toLowerCase())}…</span><div class="skeleton-metrics">${Array.from({length:4},()=>'<div class="skeleton-block"></div>').join('')}</div><div class="skeleton-block skeleton-chart"></div></section>`;
}
function workspacesPage() {
  const id=S.workspace,current=S.boot.workspaces.find(w=>w.id===id);
  if(!id)return head('Workspaces','Keep tests and benchmark campaigns separate.',btn('New workspace','new-workspace','',true))+
    `<div class="workspace-grid">${S.boot.workspaces.map(w=>{
      const runs=S.boot.runs.filter(r=>r.workspace_id===w.id&&!r.archived);
      const drafts=S.boot.drafts.filter(d=>d.workspace_id===w.id);
      return `<article class="panel workspace-card"><button class="card-title" data-action="open-workspace" data-id="${e(w.id)}">${e(w.name)}</button><p>${e(w.description||'')}</p><div class="workspace-card-meta">${runs.length} competitions · ${drafts.length} configurations</div><div class="actions">${btn('Open','open-workspace',`data-id="${e(w.id)}"`,true)}${btn('New competition','new-competition',`data-workspace="${e(w.id)}"`)}${btn('Edit','edit-workspace',`data-id="${e(w.id)}"`)}</div></article>`;
    }).join('')}</div>`+
    `<section class="panel"><h2>Unassigned</h2><p>${S.boot.runs.filter(r=>!r.workspace_id).length} competitions have no workspace.</p>${btn('Organize existing competitions','open-workspace','data-id="unassigned"')}</section>`;
  const data=S.workspaceSummary,t=data?.totals;
  const actions=btn('New competition','new-competition','',true)+(current?btn('Add existing competitions','workspace-members',`data-id="${e(id)}"`)+btn('Edit workspace','edit-workspace',`data-id="${e(id)}"`):'')+btn('New workspace','new-workspace');
  const title=head(current?.name||'Unassigned',current?.description||'Competition results in this workspace.',actions);
  const drafts=scoped(S.boot.drafts);
  const draftPanel=drafts.length?`<section class="panel"><h2>Ready to launch</h2>${drafts.map(d=>`<div class="workspace-draft"><div><strong>${e(d.config.name)}</strong><small>${d.config.models.length} participants</small></div><div class="actions">${btn('Edit','edit-draft',`data-id="${e(d.id)}"`)}${btn('Launch','launch',`data-id="${e(d.id)}"`,true)}</div></div>`).join('')}</section>`:'';
  if(!scoped(S.boot.runs).length)return title+draftPanel+empty(drafts.length?'No runs yet':'No competitions yet',drafts.length?'Launch a saved configuration above, or create another competition.':'Create a competition here, or add an existing one.');
  if(!data)return title+draftPanel+workspaceSkeleton('Statistics')+`<section class="panel flush"><div class="panel-head"><h2>Competitions</h2></div>${runTable(scoped(S.boot.runs))}</section>`;
  return title+draftPanel+
    `<div class="metrics">${metric('Competitions',fmt(t.competitions),'Exported copies excluded')}${metric('Strategies',`${t.submitted+t.frozen_strategies} / ${t.sessions+t.frozen_strategies}`,`${t.frozen_strategies} frozen · ${t.invalid} invalid · ${t.attention} need attention`)}${metric('Completed fights',data.performance_pending?'Loading…':fmt(t.completed_matches),data.performance_pending?'Reading fight results':`${t.preparation_matches} preparation · ${t.failed_matches} engine failures`)}${metric('Recorded API cost',money(t.known_cost_usd),`${money(t.reserved_usd)} reserved${t.unresolved_sessions?` · ${t.unresolved_sessions} unresolved`:''}`)}</div>
    <section class="panel workspace-resources"><div class="panel-title"><h2>Model resources</h2><details class="action-menu"><summary class="button">Download CSV</summary><div>${['summary','fights','sessions','results'].map(table=>`<a class="button" href="/api/results.csv?${query({workspace:id,table})}">${table==='summary'?'Workspace scores':table==='fights'?'Match results':table==='sessions'?'Usage & conversations':'Raw strategy results'}</a>`).join('')}</div></details></div>
    ${data.models.length?table(['Participant','Size (B)','Submitted','Input / output tokens','Recorded cost','Tool calls','Preparation time'],data.models.map(m=>`<tr><td><strong>${e(m.name)}</strong><small>${e(m.model||'Built-in strategy')}</small>${raw(m.configuration,'Configuration')}</td><td>${fmt(m.model_size_billion,3)}</td><td>${m.submitted} / ${m.sessions}<small>${m.invalid} invalid</small></td><td>${fmt(m.input_tokens)} / ${fmt(m.output_tokens)}${m.unmeasured_sessions?`<small>${m.unmeasured_sessions} conversations with missing measurements</small>`:''}</td><td>${money(m.known_cost_usd)}${Number(m.reserved_usd)?`<small>${money(m.reserved_usd)} reserved</small>`:''}</td><td>${fmt(m.tool_calls)}</td><td>${fmt(m.wall_seconds/60,1)} min</td></tr>`)):'<p class="muted">No model conversations yet.</p>'}</section>
    ${data.performance_pending?workspaceSkeleton('Performance'):`<section class="panel"><div class="panel-title"><h2>Performance</h2><label class="field">Comparison group<select id="workspace-group">${data.groups.map((g,i)=>`<option value="${i}" ${i===(S.workspaceGroup||0)?'selected':''}>${g.kind==='evaluation'?'Fixed-baseline evaluation':g.kind==='progression'?'Previous-round comparison':'Tournament'} · ${workspaceStage(g.stage)} · ${e(workspaceScenario(g.scenario))} · ${g.runs.length} competition${g.runs.length===1?'':'s'} · Group ${i+1}</option>`).join('')}</select></label></div><p class="muted">Groups keep different scenarios, preparation settings and opponent pools separate. Same-model fights are excluded from tournament scores.</p><div id="workspace-performance">${workspacePerformance(data.groups[S.workspaceGroup||0]||data.groups[0])}</div></section>`}

    <section class="panel flush"><div class="panel-head"><h2>Competitions</h2>${btn('New competition','new-competition')}</div>${runTable(scoped(S.boot.runs))}</section>
    ${data.excluded.length?`<details class="panel"><summary>${data.excluded.length} competitions excluded from statistics</summary>${data.excluded.map(r=>`<p>${e(r.run)}: ${e(r.reason)}</p>`).join('')}</details>`:''}`;
}
function workspaceScenario(scenario) {
  if(scenario.team_selection?.mode==='participant')return 'AI-built teams';
  if(scenario.preset==='dream-team')return 'Dream team';
  return Number(scenario.team_size||1)===1?'Simple duel':`Fixed team (${scenario.team_size} members)`;
}
function workspaceStage(stage) {
  if(stage==='tournament'||stage==='.')return 'Round 1';
  const match=stage.match(/g(\d+)-(tournament|panel)/);
  return match?`Round ${Number(match[1])+1}`:stage;
}
function resourceScatter(points, metric='size') {
  const labels={size:'Model size (B parameters)',cost:'Mean preparation cost ($ / strategy)',time:'Mean preparation time (minutes / strategy)',tools:'Mean tool calls / strategy',tests:'Mean preparation fights / strategy',replays:'Mean replay read calls / strategy'};
  const eligible=points.filter(p=>!['cost','time','tools','tests','replays'].includes(metric)||!p.reference);
  const valid=eligible.filter(p=>p.score!=null && Number.isFinite(p[metric]) && p[metric]>=0 && (metric!=='size'||p[metric]>0));
  if(!valid.length)return `<p class="muted">${metric==='size'?'No model sizes recorded for this selection. Set the optional size in Participants.':'No complete measurements for this selection.'}</p>`;
  const W=760,H=260,L=56,R=728,T=20,B=208,max=Math.max(...valid.map(p=>p[metric]))*1.1||1;
  const x=v=>L+(R-L)*v/max,y=v=>B-(B-T)*v;
  return `<svg class="resource-scatter" viewBox="0 0 ${W} ${H}" role="img" aria-label="Score versus ${e(labels[metric])}">
    ${[0,.5,1].map(v=>`<line x1="${L}" x2="${R}" y1="${y(v)}" y2="${y(v)}" stroke="#e0e7e4"/><text x="${L-8}" y="${y(v)+4}" text-anchor="end">${v*100}%</text>`).join('')}
    ${[0,.25,.5,.75,1].map(v=>`<text x="${x(v*max)}" y="${B+20}" text-anchor="middle">${fmt(v*max,metric==='cost'?4:2)}</text>`).join('')}
    <text x="${(L+R)/2}" y="${H-5}" text-anchor="middle">${e(labels[metric])}</text>
    ${valid.map((p,i)=>`<circle cx="${x(p[metric])}" cy="${y(p.score)}" r="6" fill="${p.color||seriesColor(i)}" stroke="white" stroke-width="1.5" tabindex="0" data-chart-model="${e(p.model||p.label)}" data-chart-label="${e(p.label)} · ${pct(p.score)} · ${fmt(p[metric],metric==='cost'?6:2)} ${e(labels[metric])}"><title>${e(p.label)}: ${pct(p.score)} · ${fmt(p[metric],metric==='cost'?6:3)}${metric==='size'?'B':metric==='time'?' min':metric==='tools'?' tool calls':metric==='tests'?' preparation fights':metric==='replays'?' replay reads':' USD'}</title></circle>`).join('')}</svg>
    <div class="chart-legend">${valid.map((p,i)=>`<span tabindex="0" data-chart-model="${e(p.model||p.label)}" data-chart-label="${e(p.label)} · ${pct(p.score)}"><i class="dot" style="background:${p.color||seriesColor(i)}"></i>${e(p.label)} · ${pct(p.score)} · ${metric==='cost'?money(p.cost):fmt(p[metric],3)+(metric==='size'?'B':metric==='tools'?' tool calls':metric==='tests'?' preparation fights':metric==='replays'?' replay reads':' min')}</span>`).join('')}</div>
    ${valid.length<eligible.length?`<p class="muted">${eligible.length-valid.length} entries with missing measurements excluded from this chart.</p>`:''}`;
}
const RESOURCE_LABELS={size:'Size (B)',cost:'Mean cost ($)',time:'Mean time (min)',tools:'Mean tool calls',tests:'Mean preparation fights',replays:'Mean replay reads'};
function resourceBars(points,metric) {
  const eligible=points.filter(p=>metric==='size'||!p.reference);
  const rows=eligible.filter(p=>p.score!=null&&Number.isFinite(p[metric])&&p[metric]>0)
    .map(p=>({...p,efficiency:100*p.score/p[metric]}))
    .sort((a,b)=>b.efficiency-a.efficiency||a.label.localeCompare(b.label));
  if(!rows.length)return '<p class="muted">No positive resource measurements for this selection. Efficiency is undefined for zero consumption.</p>';
  const units={size:'B parameters',cost:'$',time:'minute',tools:'tool call',tests:'preparation fight',replays:'replay read'},unit=units[metric];
  const maximum=Math.max(...rows.map(p=>p.efficiency))||1;
  return `<p class="muted">Score points per ${e(unit)} = score (0–100) ÷ ${e(RESOURCE_LABELS[metric].toLowerCase())}. Higher is better.</p><div class="resource-bar-head"><span>Model</span><span>Resource / strategy</span><span>Points / ${e(unit)} ↓</span></div><div class="resource-bar-list" role="region" aria-label="Performance per ${e(unit)}" tabindex="0">${rows.map(row=>{
    const value=fmt(row.efficiency,metric==='cost'?2:3);
    const label=`${row.label} · ${value} score points / ${unit} · score ${pct(row.score)} · ${RESOURCE_LABELS[metric]}: ${fmt(row[metric],metric==='cost'?6:2)}`;
    return `<div class="resource-score-row" data-chart-model="${e(row.model||row.label)}" data-chart-label="${e(label)}" tabindex="0"><strong>${e(row.label)}</strong><span>${metric==='cost'?money(row[metric]):fmt(row[metric],2)}</span><div class="resource-score"><div class="workspace-bar-track"><span style="width:${100*row.efficiency/maximum}%;background:${row.color}"></span></div><b>${value}</b></div></div>`;
  }).join('')}</div><div class="chart-legend">${[...new Map(rows.map(row=>[row.model||row.label,row])).values()].map(row=>`<span tabindex="0" data-chart-model="${e(row.model||row.label)}"><i class="dot" style="background:${row.color}"></i>${e(row.model||row.label)}</span>`).join('')}</div>${rows.length<eligible.length?`<small>${eligible.length-rows.length} entries with missing or zero resource measurements excluded; division by zero is undefined.</small>`:''}`;
}
function renderResourceChart(context) {
  const points=S.resourcePoints?.[context]||[],metric=S.resourceMetric||'tools';
  return S.resourceView==='points'?resourceScatter(points,metric):resourceBars(points,metric);
}
function resourcePanel(points, context) {
  const names=[...new Set(points.map(p=>p.model||p.label))].sort();
  points=points.map(p=>({...p,color:p.color||seriesColor(names.indexOf(p.model||p.label))}));
  S.resourcePoints ||= {};S.resourcePoints[context]=points;
  const metric=S.resourceMetric||'tools';
  return `<div class="resource-chart" data-chart-key="resource:${e(context)}:${e(context==='workspace'?S.workspace:S.run)}"><div class="overview-section-head"><h3>Performance vs resources</h3><div class="chart-controls"><label class="field">Display<select data-resource-view="${context}" aria-label="Resource chart display"><option value="bars" ${S.resourceView!=='points'?'selected':''}>Bars</option><option value="points" ${S.resourceView==='points'?'selected':''}>Points</option></select></label><label class="field">Compare by<select data-resource-axis="${context}">${[['size','Model size'],['cost','Preparation cost'],['time','Preparation time'],['tools','Tool calls'],['tests','Preparation fights'],['replays','Replay reads']].map(([id,name])=>`<option value="${id}" ${id===metric?'selected':''}>${name}</option>`).join('')}</select></label></div></div><div class="resource-pair"><section><h4>Total tool calls</h4>${toolCallTotals(points)}<p class="muted">Each tool invocation counts, including failures. Preparation fights count both starting sides. Replay reads count read_replay and read_past_fight calls, including pagination; they are not distinct replays.</p></section><section><h4>Performance by resource</h4><div id="${context}-resource-chart">${renderResourceChart(context)}</div></section></div></div>`;
}
function overviewModelSize(d, id) {
  const pinned=d.model_metadata?.[id]?.model_size_billion;
  if(pinned!=null)return pinned;
  const specs=(d.metadata.manifest?.strategies||[]).filter(s=>s.origin?.variant===id);
  const sizes=[...new Set(specs.map(s=>s.origin.model_size_billion))];
  return sizes.length===1 && sizes[0]>0?sizes[0]:null;
}
function overviewResourcePoints(d,data) {
  const scores=new Map(data.models.map(row=>[row.model,row.score]));
  const ids=[...new Set([...scores.keys(),...data.sessions.map(session=>session.model)])];
  return ids.map(id=>{
    const sessions=data.sessions.filter(session=>session.model===id),costKnown=sessions.length && sessions.every(session=>session.status!=='needs_reconciliation'&&!Number(session.money_reserved||0));
    const total=sessions.reduce((sum,session)=>sum+(session.steps||0),0);
    return {reference:d.metadata.config?.models.find(model=>model.id===id)?.provider==='mock' || (!sessions.length && !!d.metadata.manifest),
      model:id,label:id,color:overviewColor(id),score:scores.get(id)??null,size:overviewModelSize(d,id),
      toolTotal:total,tools:sessions.length?total/sessions.length:null,
      tests:sessions.length?sessions.reduce((sum,s)=>sum+(s.test_matches||0),0)/sessions.length:null,
      replays:sessions.length&&sessions.every(s=>s.replay_reads!=null)?sessions.reduce((sum,s)=>sum+s.replay_reads,0)/sessions.length:null,
      cost:costKnown?sessions.reduce((sum,session)=>sum+Number(session.cost_spent||0),0)/sessions.length:null,
      time:sessions.length&&sessions.every(session=>session.wall_seconds!=null)?sessions.reduce((sum,session)=>sum+session.wall_seconds,0)/sessions.length/60:null};
  });
}
function toolCallTotals(points) {
  const rows=points.filter(point=>!point.reference&&Number.isFinite(point.toolTotal)).sort((a,b)=>b.toolTotal-a.toolTotal);
  const max=Math.max(1,...rows.map(row=>row.toolTotal));
  return rows.length?`<div class="tool-call-bars">${rows.map(row=>`<div tabindex="0" data-chart-model="${e(row.model||row.label)}" data-chart-label="${e(row.label)} · ${fmt(row.toolTotal)} tool calls"><span title="${e(row.label)}">${e(row.label)}</span><div class="workspace-bar-track"><span style="width:${100*row.toolTotal/max}%;background:${row.color||COLORS[0]}"></span></div><strong>${fmt(row.toolTotal)}</strong></div>`).join('')}</div>`:'<p class="muted">No model tool calls recorded for this selection.</p>';
}

function workspacePerformance(group) {
  if(!group)return '<p class="muted">No evaluation results yet.</p>';
  return resourcePanel(group.models.map(m=>({model:m.name,reference:m.is_reference,toolTotal:m.total_tool_calls,tools:m.mean_tool_calls,tests:m.mean_test_matches,replays:m.mean_replay_reads,label:`${m.name} · ${m.round ? "R"+m.round : "Frozen"} · ${text(m.condition)}`,score:m.score,size:m.model_size_billion,cost:m.mean_cost_usd,time:m.mean_wall_seconds==null?null:m.mean_wall_seconds/60})),"workspace")+`<div class="workspace-bars">${group.models.map(m=>`<div class="workspace-bar"><div><strong>${e(m.name)}</strong><small>${m.round ? `Round ${m.round}` : 'Frozen strategy'} · ${e(text(m.condition))}</small></div><div class="workspace-bar-track"><span style="width:${Math.max(0,Math.min(100,(m.score||0)*100))}%"></span></div><strong>${pct(m.score)}</strong></div>`).join('')}</div>`+
    table(['Participant','Size (B)','Score / B','Round / track','Win / draw / loss','Failed fights','Strategies'],group.models.map(m=>`<tr><td>${e(m.name)}</td><td>${fmt(m.model_size_billion,3)}</td><td>${fmt(m.score_per_billion,4)}</td><td>${m.round??'Frozen'} · ${e(text(m.condition))}</td><td>${m.wins} / ${m.draws} / ${m.losses}</td><td>${m.failed}</td><td>${m.conversations}</td></tr>`))+
    `<p class="muted">Mean score per conversation: win 1, draw 0.5, loss 0. ${group.internal_matches} same-model fights excluded. ${group.runs.length} competitions in this group.</p><details class="quiet-details"><summary>Included competitions & scenario</summary><div class="actions">${group.runs.map(id=>btn(e(S.boot.runs.find(r=>r.id===id)?.name||id),'open-run',`data-run="${e(id)}"`)).join('')}</div>${raw(group.scenario,'Scenario settings')}</details>`;
}

function competitions() {
  const drafts=scoped(S.boot.drafts), runs=scoped(S.boot.runs);
  const jobs=S.boot.jobs.filter(j=>runs.some(r=>r.id===j.run));
  return (
    head(
      "Competitions",
      "Saved settings and run history.",
      btn("＋ New competition", "new-competition", "", true),
    ) +
    `<section class="panel flush"><div class="panel-head"><div><h2>Saved configurations</h2><p>Editable until launch. Each run keeps its own copy.</p></div></div>${
      drafts.length
        ? `<div class="draft-grid">${drafts.map(d=>`<article class="draft-card"><span class="eyebrow">Saved configuration</span><h3>${e(d.config.name)}</h3><p>${d.config.models.length} participants · ${d.config.replicates} repetitions · ${d.config.generations === null ? "Manual stop" : `${d.config.generations || 1} rounds`}</p><div class="draft-models">${d.config.models.map(m=>badge(m.id)).join("")}</div><div class="draft-card-actions">${btn("Edit", "edit-draft", `data-id="${e(d.id)}"`)}${btn("Launch", "launch", `data-id="${e(d.id)}"`, true)}<button class="icon-button" data-action="delete-draft" data-id="${e(d.id)}" aria-label="Remove ${e(d.config.name)}" title="Remove configuration">×</button></div></article>`).join("")}</div>`
        : empty(
            "No saved configurations",
            "Use the demo settings or create a configuration.",
            btn("Create configuration", "new-competition"),
          )
    }</section>` +
    `<section class="panel flush"><div class="panel-head"><div><h2>Run history</h2><p>Exported copies are excluded from aggregates.</p></div><input type="search" id="run-search" placeholder="Search competitions..." aria-label="Search competitions"></div><div id="run-table">${runTable(runs)}</div></section>` +
    (jobs.length
      ? `<details class="panel history-details"><summary>Process history <span>${jobs.length}</span></summary>${table(
          ["Name", "Status", "Started", ""],
          jobs
            .slice(0, 12)
            .map(
              (j) =>
                `<tr><td>${e(j.name)}<small>${e(j.run)}</small></td><td>${status(j.status)}</td><td>${date(j.started_at)}</td><td>${btn("Journal", "job-log", `data-id="${e(j.id)}"`)}</td></tr>`,
            ),
        )}</details>`
      : "")
  );
}
function openDialog(title, subtitle, body) {
  hideHelp();
  $("#dialog-content").innerHTML =
    `<div class="dialog-head"><div><h2 id="dialog-title">${e(title)}</h2><p>${e(subtitle)}</p></div><button class="icon-button" data-action="close-dialog" aria-label="Close">×</button></div><div id="dialog-error" class="notice error dialog-error" role="alert" tabindex="-1" hidden></div>${body}`;
  if (!$("#dialog").open) $("#dialog").showModal();
}
function renderModelCatalog() {
  const term = $("#model-search").value.toLowerCase();
  const models = (S.catalogModels || []).filter((m) =>
    `${m.id} ${m.name}`.toLowerCase().includes(term),
  );
  $("#available-models").innerHTML = models.length
    ? models
        .map(
          (m) =>
            `<button type="button" class="model-option" data-action="select-model" data-model="${e(m.id)}"><strong>${e(m.name || m.id)}</strong><code>${e(m.id)}</code><small>${e(m.availability || "Listed by API; chat and tool support unverified")}</small></button>`,
        )
        .join("")
    : `<p>No matching models.</p>`;
}
function reasoningLabel(parameters = {}) {
  if (parameters.reasoning_effort != null) return String(parameters.reasoning_effort);
  if (parameters.output_config?.effort != null) return String(parameters.output_config.effort);
  const thinking = parameters.thinking_config || parameters.thinkingConfig || parameters.thinking;
  return thinking ? JSON.stringify(thinking) : "Provider default (not specified)";
}
function reasoningField(provider, parameters = {}, model = "") {
  if (!["openai", "openai-compatible"].includes(provider))
    return `<div class="field full"><small>Reasoning requested: ${e(reasoningLabel(parameters))}. Configure provider-specific thinking settings in the JSON parameters below.</small></div>`;
  const selected = parameters.reasoning_effort ?? "";
  const restricted = model.toLowerCase() === "gpt-6.1-sol";
  const levels = ["", "none", "minimal", "low", "medium", "high", "xhigh"];
  if (!levels.includes(selected)) levels.push(selected);
  return `<label class="field full">${fieldHeading("Reasoning effort", "Supported levels depend on the model and endpoint. For gpt-6.1-sol use low, medium, high or xhigh. Default omits the parameter; it does not mean medium. The journal records the requested value. GPT-6 reasoning uses Responses with function tools; Responses does not support seed. This does not expose hidden reasoning.")}<select name="reasoning_effort" data-initial="${e(selected)}">${levels.map(value => `<option value="${e(value)}" ${restricted && ["none", "minimal"].includes(value) ? "disabled" : ""} ${value === selected ? "selected" : ""}>${e(value || "Provider default (do not send)")}</option>`).join("")}</select></label>`;
}
function participantDialog(identifier = null, provider = null, connection = null) {
  const m = identifier
    ? S.boot.participants.find((p) => p.spec.id === identifier).spec
    : connection || {};
  if (m.profile === 'saved-strategy') {
    const origin=m.strategy.origin;
    openDialog(m.id,'Saved strategy',`<p>${origin.reference && !origin.run ? "Fixed reference code. Adapts to the selected scenario and roster when added; unchanged during the competition. No model calls." : "Frozen code and team. No model calls; unchanged in every round. Use its original scenario."}</p><p>Source: ${e(origin.reference || origin.run)}${origin.session ? ' · '+e(origin.session) : ''}</p><p>${Object.keys(m.strategy.files).length} files</p>${origin.run ? `<a class="button" href="#${query({view:'run',run:origin.run,tab:'code',session:origin.session})}" data-action="saved-source" data-run="${e(origin.run)}" data-session="${e(origin.session)}">Inspect source</a>` : `<pre>${e(m.strategy.files['main.leek'])}</pre>`}`);
    return;
  }
  S.editParticipant = identifier;
  const p = provider || m.provider || "mock",
    pricing = m.pricing || {};
  openDialog(
    identifier ? "Edit participant" : "New participant",
    "",
    `<form data-form="participant">${!identifier && (S.boot.providers||[]).length ? selectField('Saved provider','saved_provider',[['','Custom connection'],...S.boot.providers.map(row=>[row.spec.id,row.spec.id])],connection?.id||'') : ''}<section class="form-section"><h3>Profile</h3><div class="form-grid">${field("Participant ID", "id", (connection ? "" : m.id) || "", "text", "Letters, digits and hyphens; up to 40 characters.", `required pattern="[a-zA-Z0-9][a-zA-Z0-9_-]{0,39}" ${identifier ? "readonly" : ""}`)}${selectField(
      "Provider",
      "provider",
      [
        ["mock", "Mock (no API calls)"],
        ["openai", "OpenAI"],
        ["anthropic", "Anthropic"],
        ["gemini", "Google Gemini"],
        ["openai-compatible", "OpenAI-compatible API"],
      ],
      p,
    )}
 ${
   p === "mock"
     ? selectField(
         "Mock behavior",
         "profile",
         S.boot.profiles.map((v) => [v, v]),
         m.profile || "single-shot",
         "single-shot submits a simple strategy; repair-and-submit fixes a script and submits rush.",
       )
     : `</div></section><section class="form-section"><h3>Connection</h3><div class="form-grid">${field("API key environment variable", "api_key_env", m.api_key_env || (p === "anthropic" ? "ARENA_ANTHROPIC_KEY" : p === "gemini" ? "ARENA_GEMINI_KEY" : "ARENA_OPENAI_KEY"), "text", "Name of the server environment variable containing the key, or the name under which to store a session key entered below.", "required")}<label class="field full">API key (this server session only)<input name="secret" type="password" autocomplete="new-password" placeholder="Optional for local compatible servers; otherwise leave blank to keep the key"><small>Not returned to the browser or written to configuration files.</small></label>${p === "openai-compatible" ? field("Full API endpoint", "endpoint", m.endpoint || "", "url", "Ollama: http://localhost:11434/v1/chat/completions. HTTP is allowed on loopback; remote servers require HTTPS. API keys are optional for local compatible servers.", "required") : m.endpoint ? field("HTTPS endpoint", "endpoint", m.endpoint, "url") : ""}</div></section><section class="form-section"><h3>Model</h3><div class="form-grid"><div class="field full">${btn("Load models", "list-models")}<label class="field" hidden id="model-search-field">Search models<input type="search" id="model-search" placeholder="Filter by model name or ID"></label><div id="available-models" class="model-catalog" role="group" aria-label="Available models" hidden></div><small id="model-list-status">Load models available to the configured API key. You can also enter an ID manually.</small><details id="excluded-models" hidden><summary>Excluded models</summary><div id="excluded-model-list"></div></details></div>${field("Exact model ID", "model", m.model || "", "text", "The exact ID accepted by the API.", "required")}${reasoningField(p, m.parameters || {}, m.model || "")}${field("Model size (B parameters), optional", "model_size_billion", m.model_size_billion ?? "", "number", "Total parameters in billions: 7 for 7B, 0.5 for 500M. For MoE use total parameters, not active parameters. This is not disk size or VRAM usage. Leave blank when unknown.", 'min="0.000001" max="1000000" step="any"')}</div></section><details class="form-section form-disclosure" ${!identifier ? "open" : ""}><summary>Token pricing <span>USD per million</span></summary><div class="form-grid">${field("Input price / million tokens ($)", "input_price", pricing.input_per_million ?? "", "number", "", 'required min="0" step="any"')}${field("Output price / million tokens ($)", "output_price", pricing.output_per_million ?? "", "number", "", 'required min="0" step="any"')}${field("Price date", "pricing_date", pricing.date || new Date().toISOString().slice(0, 10), "date", "", "required")}${field("Cache read price / million ($), optional", "cached_price", pricing.cached_input_per_million ?? "", "number", "Blank uses the standard input price.", 'min="0" step="any"')}${field("Cache write price / million ($), optional", "creation_price", pricing.cache_creation_per_million ?? "", "number", "", 'min="0" step="any"')}</div></details><details class="form-section form-disclosure"><summary>Advanced settings <span>Limits, retries & parameters</span></summary><div class="form-grid">${field("Maximum input per call (tokens)", "max_input_tokens_per_call", m.max_input_tokens_per_call ?? "", "number", "Optional. Blank disables local input admission limits.", 'min="1"')}${field("Maximum output per call (tokens)", "max_output_tokens", m.max_output_tokens ?? "", "number", p === "anthropic" ? "Required by Anthropic (max_tokens)." : "Optional. Blank uses the API default; one call may exceed the remaining financial budget.", p === "anthropic" ? 'required min="1"' : 'min="1"')}${field("Call timeout (seconds)", "timeout_seconds", m.timeout_seconds || 60, "number", "Socket connection/read timeout. Streaming activity can keep a call open longer.", 'required min="1" max="3600"')}${field("Pause after no provider output (seconds)","inactivity_timeout_seconds",m.inactivity_timeout_seconds??300,"number","Pauses this conversation and frees its request slot when no text, reasoning or tool output arrives. Keepalive signals do not count. Increase for long silent reasoning or local prompt processing.",'required min="1" max="3600"')}${field("Retries on HTTP 429", "max_retries", m.max_retries ?? 1, "number", "Calls with unknown outcomes are not retried automatically.", 'required min="0" max="3"')}${p === "anthropic" ? `<p class="muted">Seed: not available in the Anthropic API.</p>` : field("Model seed", "model_seed", m.parameters?.seed ?? (identifier ? "" : 0), "number", p === "openai-compatible" ? "Server support varies. Identical output is not guaranteed." : "Sent with every call when supported by the model. Identical output is not guaranteed.", 'min="0" max="2147483647"')}<label class="field full">Model parameters (JSON)<textarea name="parameters" class="mono">${e(pretty(m.parameters || {}))}</textarea><small>API-specific options such as temperature and top_p. Use the seed and reasoning controls above. The reasoning selector is authoritative; it overrides reasoning_effort in this JSON.</small></label>`
 }</div>${p === "mock" ? "</section>" : "</details>"}<div class="form-footer">${btn("Cancel", "close-dialog")}<button type="submit" class="button primary">Save participant</button></div></form>`,
  );
}
const ENTITY_FIELDS = [
  ["level", "Level", 100],
  ["life", "HP", 600],
  ["strength", "Strength", 100],
  ["agility", "Agility", 0],
  ["frequency", "Frequency", 100],
  ["wisdom", "Wisdom", 0],
  ["resistance", "Resistance", 0],
  ["science", "Science", 0],
  ["magic", "Magic", 0],
  ["tp", "AP per turn", 12],
  ["mp", "MP per turn", 5],
  ["cores", "Cores", 10],
  ["ram", "RAM / chip slots", 6],
];
function componentIds(pieces) {
  return pieces.map((piece) =>
    typeof piece === "object" ? piece.template : piece,
  );
}
function componentBonuses(pieces) {
  const result = {};
  for (const piece of pieces || []) {
    const item =
      S.equipment.components[
        typeof piece === "object" ? piece.template : piece
      ];
    for (const [key, value] of item?.stats || [])
      result[key] = (result[key] || 0) + value;
    if (typeof piece === "object")
      for (const [key, value] of Object.entries(piece.stats || {}))
        result[key] = (result[key] || 0) + value;
  }
  return result;
}
function withComponents(stats, pieces) {
  const bonus = componentBonuses(pieces);
  return Object.fromEntries(
    Object.entries(stats).map(([key, value]) => [
      key,
      value + (bonus[key] || 0),
    ]),
  );
}
function selectedComponents(section) {
  const original = JSON.parse(section.dataset.componentInstances || "[]");
  return String(
    section.querySelector(
      'input[name="' +
        memberGearName(Number(section.dataset.memberBuild), "components") +
        '"]',
    ).value,
  )
    .split(",")
    .filter((v) => v.trim())
    .map(Number)
    .map(
      (id) =>
        original.find(
          (piece) => typeof piece === "object" && piece.template === id,
        ) || id,
    );
}
function syncComponentStats(section) {
  if (!section) return;
  const old = JSON.parse(section.dataset.componentBonus || "{}"),
    next = componentBonuses(selectedComponents(section));
  for (const input of $$("input[data-stat]", section))
    input.value =
      Number(input.value) +
      (next[input.dataset.stat] || 0) -
      (old[input.dataset.stat] || 0);
  section.dataset.componentBonus = JSON.stringify(next);
}
function equipmentPicker(label, name, kind, ids, allowlist = false) {
  const catalog = S.equipment?.[kind] || {};
  const names = ids.map((id) => catalog[id]?.name || `Unknown ID ${id}`);
  const emptyLabel = allowlist ? "All eligible items" : "None";
  const help = allowlist
    ? "Select the equipment participants may choose. An empty selection allows all catalog items; realistic mode also enforces the member level."
    : "Equipment for this leek, used by both sides and fixed reference opponents. An empty selection equips none.";
  return `<div class="field full">${fieldHeading(label, help)}<input type="hidden" name="${name}" value="${e(ids.join(", "))}"><details class="equipment-picker" data-kind="${kind}" data-name="${name}" data-empty="${emptyLabel}"><summary><span class="equipment-selection">${e(names.join(", ") || emptyLabel)}</span></summary><div class="equipment-picker-body"><label class="field">Search ${kind}<input type="search" class="equipment-search" placeholder="Name or ID"></label><div class="equipment-options">${Object.entries(
    catalog,
  )
    .sort(
      (a, b) => a[1].level - b[1].level || a[1].name.localeCompare(b[1].name),
    )
    .map(
      ([id, item]) =>
        `<article class="equipment-option" data-search="${e(`${id} ${item.name}`.toLowerCase())}"><label class="check"><input type="checkbox" class="equipment-check" value="${e(id)}" ${ids.includes(Number(id)) ? "checked" : ""}><strong>${e(item.name)}</strong><span>ID ${e(id)} · level ${e(item.level)}</span></label><small>${item.restricted_reason ? `<strong>${e(item.restricted_reason)}</strong><br>` : ""}${kind === "components" ? `${item.slots} / 8 slots · ${(item.stats || []).map(([key, value]) => `${value > 0 ? "+" : ""}${value} ${key}`).join(" · ")}</small><details><summary>Item details</summary><p>Bonuses are added after capital allocation. Each template can be equipped once. Recovery components consume three slots. Realistic mode validates component levels, slots and alteration charge against the frozen public catalog. Alteration deltas are included in the final stats.</p>${raw(item, "Component definition")}</details></article>` : `${e(item.cost)} AP · range ${e(item.min_range)}–${e(item.max_range)} · ${item.los ? "line of sight required" : "no line of sight required"}</small><details><summary>Item details</summary><p>These values come from the pinned engine catalog. Effects depend on the member stats and target rules.</p><dl><dt>Cooldown</dt><dd>${e(item.cooldown ?? "Not applicable")} turns</dd><dt>Uses per turn</dt><dd>${e(item.max_uses ?? "Not specified")}</dd><dt>Effects</dt><dd>${(item.effects || []).map((effect) => `${e(S.equipment.effects[String(effect.type)] || `Effect ${effect.type}`)}: base ${e(effect.value1)} + random component ${e(effect.value2)}; duration ${e(effect.turns)} turns`).join("<br>") || "None"}</dd></dl>${raw(item, "Full pinned item definition")}</details></article>`}`,
    )
    .join(
      "",
    )}</div><small class="equipment-level-status" role="status"></small><small>${kind === "components" ? `Public component catalog · game data ${e(S.equipment?.component_snapshot?.master_version)}` : `Player equipment catalog · pinned engine ${e(S.equipment?.snapshot?.slice(0, 12))}`}. <a href="#view=help" target="_blank" rel="noopener">Equipment and API guide</a></small></div></details></div>`;
}
function updateEquipmentLevels() {
  const form = $("#competition-form");
  if (!form || form.elements.team_mode.value === "participant") return;
  const limited = form.elements.realistic_stats.checked,
    level = Number(form.elements.entity_level.value);
  if (!Number.isInteger(level) || level < 1 || (limited && level > 301)) return;
  const allRemoved = [];
  for (const picker of $$(".equipment-picker", form)) {
    const removed = [];
    const memberLevel = Number(
      picker
        .closest("[data-member-build]")
        ?.querySelector("[data-member-level]")?.value || level,
    );
    for (const input of $$(".equipment-check", picker)) {
      const item = S.equipment[picker.dataset.kind][input.value],
        locked =
          limited &&
          (item.level > memberLevel ||
            !!item.restricted_reason ||
            (picker.dataset.kind === "components" && item.level == null));
      input.disabled = locked;
      input
        .closest(".equipment-option")
        .classList.toggle("equipment-locked", locked);
      input.title = locked
        ? item.restricted_reason ||
          `Requires level ${item.level}; leek level is ${level}`
        : "";
      if (locked && input.checked) {
        input.checked = false;
        removed.push(item.name);
      }
    }
    const checked = $$(".equipment-check:checked", picker).map((input) =>
      Number(input.value),
    );
    const previous = String(form.elements[picker.dataset.name].value)
      .split(",")
      .filter((id) => id.trim())
      .map(Number);
    const selected = [
      ...previous.filter((id) => checked.includes(id)),
      ...checked.filter((id) => !previous.includes(id)),
    ];
    form.elements[picker.dataset.name].value = selected.join(", ");
    if (picker.dataset.kind === "components")
      syncComponentStats(picker.closest("[data-member-build]"));
    $(".equipment-selection", picker).textContent =
      selected
        .map((id) => S.equipment[picker.dataset.kind][id]?.name || id)
        .join(", ") || picker.dataset.empty;
    const status = $(".equipment-level-status", picker);
    allRemoved.push(...removed);
    if (removed.length)
      status.textContent = `Removed ineligible items at level ${level}: ${removed.join(", ")}.`;
    else if (!status.textContent.startsWith("Removed"))
      status.textContent = limited
        ? `Items above level ${level} are locked in realistic mode. Boss and summon-only chips are excluded in every mode.`
        : "Free mode: all player-equipment levels are selectable. Boss and summon-only chips remain excluded.";
  }
  if (allRemoved.length) {
    const warning = $("#equipment-removals", form);
    warning.textContent = `Removed ineligible equipment at level ${level}: ${[...new Set(allRemoved)].join(", ")}.`;
    warning.hidden = false;
  }
}
function capitalTotal(level) {
  return (
    50 +
    (level - 1) * 5 +
    Math.floor(level / 100) * 45 +
    (level === 301 ? 95 : 0)
  );
}
function defaultCapital(level) {
  let remaining = capitalTotal(level);
  const capital = {};
  for (const [key, target] of [
    ["cores", 140],
    ["tp", 65],
    ["mp", 60],
    ["life", 50],
    ["strength", 50],
  ]) {
    capital[key] = Math.min(remaining, target);
    remaining -= capital[key];
  }
  return capital;
}
function statsForCapital(level, capital) {
  const rules = S.equipment.stat_rules,
    result = {};
  for (const [key, steps] of Object.entries(rules.costs)) {
    let remaining = Math.max(0, Math.min(100000, Number(capital[key]) || 0)),
      bonus = 0;
    while (remaining > 0) {
      const step = [...steps].reverse().find((s) => bonus >= s.step);
      if (remaining < step.capital) break;
      remaining -= step.capital;
      bonus += step.sup;
    }
    result[key] =
      (rules.base[key] || 0) + bonus + (key === "life" ? (level - 1) * 3 : 0);
  }
  return result;
}
function baseStat(key, level) {
  return (
    (S.equipment.stat_rules.base[key] || 0) +
    (key === "life" ? (level - 1) * 3 : 0)
  );
}
function statChoices(key, level) {
  level = Math.max(1, Math.min(301, Number(level) || 1));
  const choices = [{ value: baseStat(key, level), cost: 0 }];
  let bonus = 0,
    cost = 0;
  const steps = S.equipment.stat_rules.costs[key];
  while (cost <= capitalTotal(level)) {
    const step = [...steps].reverse().find((s) => bonus >= s.step);
    cost += step.capital;
    bonus += step.sup;
    if (cost <= capitalTotal(level))
      choices.push({ value: baseStat(key, level) + bonus, cost });
  }
  return choices;
}
function customSliderMax(key, level, value) {
  if (key === "ram") return 50;
  if (key === "cores") return 100;
  return Math.min(
    100000,
    Math.max(statChoices(key, level).at(-1).value, Number(value) * 2, 1),
  );
}
function capitalForStat(key, value, level) {
  const choices = statChoices(key, level);
  return (
    choices.find((c) => c.value >= value) || { cost: capitalTotal(level) + 1 }
  ).cost;
}
function memberGearName(index, kind) {
  return index ? `member_${index}_${kind}` : kind;
}
function readStatBuilds(form) {
  const mode = $("#member-stat-builds", form).dataset.mode;
  return $$("[data-member-build]", form).map((section, index) => {
    const level = Number($("[data-member-level]", section).value);
    const components = selectedComponents(section),
      bonus = componentBonuses(components);
    const values = Object.fromEntries(
      $$("input[data-stat]", section).map((input) => [
        input.dataset.stat,
        mode === "realistic-v1"
          ? capitalForStat(
              input.dataset.stat,
              Number(input.value) - (bonus[input.dataset.stat] || 0),
              level,
            )
          : Number(input.value),
      ]),
    );
    return {
      level,
      name: $("[data-member-name]", section).value,
      components,
      [mode === "realistic-v1" ? "capital" : "stats"]: values,
      ...Object.fromEntries(
        ["weapons", "chips"].map((kind) => [
          kind,
          String(form.elements[memberGearName(index, kind)]?.value || "")
            .split(",")
            .filter((s) => s.trim())
            .map(Number),
        ]),
      ),
    };
  });
}
function memberBuildsMarkup(scenario) {
  const realistic = scenario.stats_mode === "realistic-v1";
  const groups = [
    ["Offense", ["strength", "science", "magic"]],
    ["Survival", ["life", "resistance", "wisdom", "agility"]],
    ["Turn resources", ["tp", "mp", "frequency", "cores", "ram"]],
  ];
  return `<div id="member-stat-builds" class="character-roster" data-mode="${realistic ? "realistic-v1" : "free"}"><nav class="character-tabs" aria-label="Team members">${Array.from({ length: scenario.team_size }, (_, i) => `<button type="button" class="button ${i === 0 ? "primary" : ""}" aria-pressed="${i === 0}" data-action="character-tab" data-index="${i}">${i + 1} · ${e(scenario.member_stats?.[i]?.name || `Leek ${i + 1}`)}</button>`).join("")}</nav>${Array.from(
    { length: scenario.team_size },
    (_, index) => {
      const spec = scenario.member_stats?.[index] || {},
        level = spec.level ?? scenario.entity.level;
      const bonus = componentBonuses(spec.components || []);
      const values = realistic
        ? withComponents(
            statsForCapital(level, spec.capital || defaultCapital(level)),
            spec.components || [],
          )
        : { ...scenario.entity, ...spec.stats };
      return `<article class="character-card" data-member-build="${index}" data-component-instances="${e(JSON.stringify(spec.components || []))}" data-component-bonus="${e(JSON.stringify(bonus))}" ${index ? "hidden" : ""}><header class="character-header"><div class="character-avatar" aria-hidden="true">${index + 1}</div><div><label>Leek name<input data-member-name name="member_${index}_name" value="${e(spec.name || `Leek ${index + 1}`)}" maxlength="80"></label><label class="character-level">Level <input data-member-level name="member_${index}_level" type="number" min="1" max="${realistic ? 301 : 100000}" value="${level}" required></label></div></header><div class="character-highlights"></div><div class="member-stat-summary" role="status" aria-live="polite"></div><progress class="capital-meter" max="${capitalTotal(level)}" value="0" aria-label="Leek ${index + 1} capital spent" ${realistic ? "" : "hidden"}></progress><div class="character-stats">${groups
        .map(
          ([group, keys]) =>
            `<section class="stat-group"><h4>${group}</h4>${keys
              .map((key) => {
                const label = ENTITY_FIELDS.find(([k]) => k === key)[1],
                  value = values[key] ?? 0;
                const choices = realistic ? statChoices(key, level) : null;
                const min = realistic
                  ? choices[0].value + (bonus[key] || 0)
                  : ["life", "ram", "cores"].includes(key)
                    ? 1
                    : ["tp", "mp"].includes(key)
                      ? 0
                      : -100000;
                const max = realistic
                  ? choices.at(-1).value + (bonus[key] || 0)
                  : customSliderMax(key, level, value);
                const numberMax = realistic
                  ? max
                  : key === "ram"
                    ? 50
                    : key === "cores"
                      ? 100
                      : 100000;
                return `<div class="stat-row" data-stat-row="${key}">${fieldHeading(label, FIELD_HELP["entity_" + key] || "", false)}<div class="stat-controls"><input type="range" data-stat-slider="${key}" aria-label="Leek ${index + 1} ${label} slider" min="${min}" max="${max}" value="${value}"><input type="number" name="member_${index}_${key}" data-stat="${key}" aria-label="Leek ${index + 1} ${label}" min="${min}" max="${numberMax}" value="${value}" required></div><small class="stat-cost"></small></div>`;
              })
              .join("")}</section>`,
        )
        .join(
          "",
        )}</div><section class="character-equipment"><h4>Equipment</h4><div class="equipment-capacity"></div>${["weapons", "chips", "components"].map((kind) => equipmentPicker(kind === "weapons" ? "Weapons" : kind === "chips" ? "Chips" : "Components", memberGearName(index, kind), kind, kind === "components" ? componentIds(spec.components || []) : (spec[kind] ?? scenario.entity[kind] ?? []))).join("")}</section></article>`;
    },
  ).join("")}</div>`;
}
function statsEditor(scenario) {
  return `<section id="stats-editor"><h3>Team roster</h3><label class="check"><input type="checkbox" name="realistic_stats" ${scenario.stats_mode === "realistic-v1" ? "checked" : ""}>Realistic stats (capital, components and alterations)</label><p class="muted">Adjust final stats. Capital costs and remaining points update below. ${btn("Official rules and scope", "reference", 'data-document="stats"')}</p>${field("Level (all members)", "entity_level", scenario.entity.level, "number", "Changing this sets every member's level. Individual levels can then be adjusted on each card.", 'required min="1" max="100000"')}<p id="stats-validation" class="notice" role="status" hidden></p><p id="equipment-removals" class="notice warn" role="status" hidden></p>${memberBuildsMarkup(scenario)}</section>`;
}
function updateTeamMode() {
  const form = $("#competition-form");
  if (!form) return;
  const participant = form.elements.team_mode.value === "participant";
  $("#team-selection-rules", form).hidden = !participant;
  const roster = $("#fixed-roster", form);
  roster.hidden = participant;
  roster.disabled = participant;
  const size = form.elements.team_size;
  size.closest(".field").hidden = participant;
  size.disabled = participant;
}
function updateStatPreviews(refreshEquipment = true) {
  const form = $("#competition-form");
  if (!form) return;
  updateTeamMode();
  if (refreshEquipment) updateEquipmentLevels();
  const realistic = $("#member-stat-builds").dataset.mode === "realistic-v1",
    builds = readStatBuilds(form);
  $$("[data-member-build]", form).forEach((section, index) => {
    const build = builds[index],
      level = build.level,
      total = capitalTotal(level);
    const used = realistic
      ? Object.values(build.capital).reduce((a, b) => a + b, 0)
      : null;
    const values = realistic
      ? withComponents(statsForCapital(level, build.capital), build.components)
      : build.stats;
    $(".character-highlights", section).innerHTML = [
      "life",
      "strength",
      "tp",
      "mp",
    ]
      .map(
        (key) =>
          `<span><strong>${fmt(values[key])}</strong>${e(ENTITY_FIELDS.find(([k]) => k === key)[1])}</span>`,
      )
      .join("");
    const node = $(".member-stat-summary", section);
    node.className =
      "member-stat-summary" +
      (realistic && (used > total || level > 301 || level < 1) ? " error" : "");
    node.textContent = realistic
      ? `${fmt(total - used)} capital remaining · ${fmt(used)} / ${fmt(total)} spent`
      : "Published / custom final stats · no capital allocation";
    $(".capital-meter", section).value = used || 0;
    $(".capital-meter", section).max = total;
    const componentSlots = componentIds(build.components).reduce(
      (sum, id) => sum + (S.equipment.components[id]?.slots || 0),
      0,
    );
    $(".equipment-capacity", section).classList.toggle(
      "error",
      componentSlots > 8,
    );
    $(".equipment-capacity", section).textContent =
      `${componentSlots} / 8 component slots · ` +
      (realistic
        ? `${level < 100 ? 2 : level < 200 ? 3 : 4} weapon slots · ${values.ram} chip slots`
        : "Custom loadout · boss and summon-only chips excluded");
    $$("[data-stat-row]", section).forEach((row) => {
      const key = row.dataset.statRow,
        number = $("[data-stat]", row),
        slider = $("[data-stat-slider]", row);
      slider.value = number.value;
      if (!realistic) {
        slider.max = customSliderMax(key, level, number.value);
        slider.value = number.value;
        $(".stat-cost", row).textContent = "Final stat";
        return;
      }
      const choices = statChoices(key, level),
        selected = choices.find((c) => c.cost === build.capital[key]),
        next = choices.find((c) => c.cost > build.capital[key]);
      slider.min =
        choices[0].value + (componentBonuses(build.components)[key] || 0);
      slider.max =
        choices.at(-1).value + (componentBonuses(build.components)[key] || 0);
      number.min = slider.min;
      number.max = slider.max;
      slider.value = number.value;
      const cost =
        next && selected
          ? `Next +${next.value - selected.value}: ${next.cost - selected.cost} capital`
          : "Level maximum";
      $(".stat-cost", row).textContent =
        `${build.capital[key]} capital spent${componentBonuses(build.components)[key] ? ` · components ${componentBonuses(build.components)[key] > 0 ? "+" : ""}${componentBonuses(build.components)[key]}` : ""}`;
      const bubble = $(".help-bubble", row);
      if (bubble)
        bubble.textContent = `${FIELD_HELP["entity_" + key] || ""} ${cost}.`;
    });
  });
}
async function rebuildStatFields() {
  const form = $("#competition-form"),
    oldMode = $("#member-stat-builds").dataset.mode;
  const mode = form.elements.realistic_stats.checked ? "realistic-v1" : "free",
    level = Number(form.elements.entity_level.value);
  const builds = readStatBuilds(form),
    count = Number(form.elements.team_size.value);
  let scenario = {
    team_size: count,
    max_turns: Number(form.elements.max_turns.value),
    stats_mode: mode,
    entity: {
      level,
      weapons: builds[0]?.weapons || [],
      chips: builds[0]?.chips || [],
    },
    member_stats: Array.from({ length: count }, (_, i) => {
      const build = builds[i] || { ...builds[0], name: `Leek ${i + 1}` };
      return {
        ...build,
        ...(mode === oldMode
          ? {}
          : mode === "realistic-v1"
            ? {}
            : {
                stats: withComponents(
                  statsForCapital(build.level || level, build.capital),
                  build.components,
                ),
              }),
      };
    }),
  };
  const message = $("#stats-validation", form);
  if (mode === "realistic-v1" && oldMode === "free") {
    form.inert = true;
    try {
      // Validate the current final values, without substituting a default build.
      scenario.stats_mode = "free";
      const first = scenario.member_stats[0];
      Object.assign(scenario.entity, first.stats, {
        level: first.level,
        weapons: first.weapons,
        chips: first.chips,
      });
      ({ scenario } = await api("/api/stats/realistic", { scenario }, true));
      message.textContent =
        "Validated: capital, component alterations and equipment. All final stats preserved.";
      message.className = "notice";
      message.hidden = false;
    } catch (error) {
      form.elements.realistic_stats.checked = false;
      message.textContent = `Realistic validation failed: ${error.message}. Your final stats and equipment have been kept.`;
      message.className = "notice warn";
      message.hidden = false;
      return;
    } finally {
      form.inert = false;
    }
  } else {
    message.hidden = true;
  }
  if (mode === "free") scenario.member_stats.forEach((m) => delete m.capital);
  else scenario.member_stats.forEach((m) => delete m.stats);
  $("#member-stat-builds").outerHTML = memberBuildsMarkup(scenario);
  updateStatPreviews();
}
function updateCompetitionSelection() {
  const rows=$$('.competition-model'), search=($('#competition-participant-search')?.value||'').toLowerCase();
  const selectedOnly=$('#competition-selected-only')?.checked;
  for(const row of rows)row.hidden=!row.dataset.search.includes(search)||(selectedOnly&&!$('input',row).checked);
  const count=$$('#competition-form input[name=participant]:checked').length;
  $('#competition-selection-count').textContent=`${count} of ${rows.length} participants selected`;
}
function competitionEditor() {
  const c = S.editConfig || structuredClone(S.boot.default_config),
    b = c.budget_per_session;
  const choices = new Map(c.models.map((m) => [m.id, m]));
  S.boot.participants.forEach(({ spec: m }) => {
    choices.set(m.id, m);
  });
  S.choiceModels = [...choices.values()];
  return (
    head(
      S.editDraft ? "Edit competition" : "New competition",
      "Shared game rules; optional preparation limits. Saving settings does not call an API.",
      btn("Settings guide", "reference", 'data-document="ui"'),
    ) +
    `<form data-form="competition" id="competition-form"><div class="grid asymmetric"><div><section class="panel editor-section" id="editor-participants"><div class="section-heading"><span>01</span><h2>Participants & rounds</h2></div><p class="muted">Each repetition starts an independent conversation.</p><div class="form-grid">${field("Competition name", "name", c.name, "text", "", "required")}${selectField("Workspace","workspace_id",workspaceOptions(),S.editDraft ? (S.boot.drafts.find(d=>d.id===S.editDraft)?.workspace_id||"") : (S.workspace==="unassigned"?"":S.workspace))}${field("Repetitions per generated participant", "replicates", c.replicates, "number", "Fixed saved strategies participate once, regardless of repetitions.", 'required min="1" max="20"')}${field("Parallel model requests", "parallel_requests", c.parallel_requests ?? 1, "number", "Maximum concurrent requests, including repetitions of the same model. Local endpoints default to one request at a time. Use Provider limits in the competition to change this while running. Different local models are processed in turn.", 'required min="1" max="20" step="1"')}${requestOrderField(c.request_order)}${field("Simultaneous fights", "parallel_fights", c.parallel_fights ?? 2, "number", "Independent engine workers. Start with 2–4; each worker can use 512 MB of Java heap plus overhead. Preparation tests remain coordinated.", 'required min="1" step="1"')}${selectField(
      "Round stopping rule",
      "round_stop",
      [
        ["fixed", "Fixed number of rounds"],
        ["manual", "Continue until I press Stop"],
      ],
      c.generations === null ? "manual" : "fixed",
    )}${field("Number of rounds", "generations", c.generations ?? 2, "number", "Includes the initial round. Each later round continues both improvement tracks.", c.generations === null ? 'disabled min="1" step="1"' : 'min="1" step="1"')}</div>${learningMetricFields(c.compare_previous_round)}<h3 class="section-label">Selected participants</h3>${competitionGroupPicker()}<div class="competition-roster-toolbar"><input type="search" id="competition-participant-search" placeholder="Search profiles" aria-label="Search competition participants"><label class="check"><input type="checkbox" id="competition-selected-only">Selected only</label></div><div class="competition-model-list" role="group" aria-label="Competition participants">${S.choiceModels.map((m) => `<label class="choice competition-model" data-search="${e(`${m.id} ${m.provider} ${m.model||m.profile}`.toLowerCase())}"><input type="checkbox" name="participant" value="${e(m.id)}" ${c.models.some((v) => v.id === m.id) ? "checked" : ""}><span><strong>${e(m.id)}</strong><small>${e(m.provider)} · ${e(m.model || m.profile)}</small></span></label>`).join("")}</div>${btn("Manage profiles", "go", 'data-view="participants"')}</section>
 <section class="panel editor-section" id="editor-scenario"><div class="section-heading"><span>02</span><h2>Scenario</h2></div><div class="scenario-presets">${btn("<strong>Simple duel</strong><small>1 level-300 leek · weapons only</small>", "preset-simple", `aria-pressed="${!c.scenario.source && c.scenario.preset !== 'llm-team'}"`)}${btn("<strong>Dream team</strong><small>4 complex builds · saved roster</small>", "preset-dream", `aria-pressed="${!!c.scenario.source}"`)}${btn("<strong>AI-built team</strong><small>Each model builds its own roster</small>", "preset-llm", `aria-pressed="${c.scenario.preset === 'llm-team'}"`)}</div><p id="preset-status" role="status" class="muted">${c.scenario.source ? `Based on public team · original snapshot ${e(c.scenario.source.snapshot_sha256.slice(0, 12))}. The roster below can be edited. Published final stats include component bonuses; component selections and alteration deltas are preserved without adding bonuses twice.` : c.scenario.preset === "llm-team" ? "Each LLM freely chooses 1–4 leeks, their levels (1–301), stats, scripts, equipment and component alterations. preview_build and validate_team check official game rules. No character stats or equipment lists are imposed." : "Starting preset: one level-300 gunner per team, direct-damage weapons, no chips. Edit each character independently below."}</p>${c.scenario.source ? raw(c.scenario.source, "Public source and frozen snapshot") : ""}<details><summary>Refresh or replace the saved Dream team</summary>${btn("Refetch current top farmer", "preset-dream-refresh")}<p class="muted">Only this button reads the current farmer ranking and fetches four leeks of its first player. The saved preset is reused until an explicit refresh; existing competitions keep their frozen roster.</p><p class="muted">Use scripts/import_dream_team.py on a machine with access to leekwars.com, then paste its snapshot JSON here.</p><textarea id="dream-snapshot" class="mono" aria-label="Public team snapshot JSON" rows="4"></textarea>${btn("Import snapshot", "preset-dream-json")}</details></section><section class="panel editor-section" id="editor-rules"><div class="section-heading"><span>03</span><h2>Match rules & roster</h2></div><p class="muted">Every distinct pair plays A vs B and B vs A on the same seed. Both sides count toward standings. Use a shared roster or let each LLM build its team.</p><div class="form-grid">${selectField(
   "Team setup",
   "team_mode",
   [
     ["fixed", "Same roster for every participant"],
     ["participant", "Participants choose teams and equipment"],
   ],
   c.scenario.team_selection ? "participant" : "fixed",
 )}${field("Team size", "team_size", c.scenario.team_size, "number", "Exact size in shared mode; maximum size when participants choose.", 'required min="1" max="8"')}${field("Maximum turns", "max_turns", c.scenario.max_turns, "number", "", 'required min="1" max="1000"')}${field("Round 1 combat seeds", "seeds", c.seeds.join(", "), "text", "Comma-separated seeds, for example 101, 202. Every pair plays each seed on both starting sides.", "required")}${field("Round 2+ combat seeds", "final_seeds", (c.final_seeds || []).join(", "), "text", "Reused for every later round. May match Round 1 seeds for the same maps; use different seeds for other maps. Seed 17 is reserved for preparation.")}</div><div id="team-selection-rules" ${c.scenario.team_selection ? "" : "hidden"}><p class="muted">Each LLM freely chooses 1–4 leeks: levels from 1 to 301, names, scripts, capital allocations, weapons, chips, components and alterations. Only official game rules apply. Character stats below are not imposed on its team. Preparation tests use a separate fixed reference team.</p></div><label class="check" style="margin-top:15px"><input type="checkbox" name="include_mirrors" ${c.include_mirrors ? "checked" : ""}>Add self-play diagnostics (A vs an identical A)</label><small class="self-play-help">Same strategy and team on both sides. Useful for inspecting side advantages and runtime behavior; excluded from standings and model feedback. Side-swapped A/B matches are already included above.</small><fieldset id="fixed-roster" style="border:0;padding:0;margin-top:15px" ${c.scenario.team_selection ? "hidden disabled" : ""}><details class="roster-disclosure"><summary><strong>Character builds & equipment</strong><small>${c.scenario.team_size} leek${c.scenario.team_size === 1 ? "" : "s"} · customize stats, weapons, chips & components</small></summary>${statsEditor(c.scenario)}</details></fieldset><details><summary>Custom map</summary><div class="form-grid" style="margin-top:15px"><label class="field full">Custom map (JSON, optional)<textarea name="map" class="mono">${c.scenario.map ? e(pretty(c.scenario.map)) : ""}</textarea><small>Without a custom map, the seed determines the map and starting positions.</small></label></div></details></section>
 <details class="panel editor-disclosure" id="editor-limits" ${Object.keys(b).length ? "open" : ""}><summary><span class="section-heading"><span>04</span><strong>Optional limits</strong></span><small>Tokens, time & spending</small></summary><p class="muted">Leave blank to let each model work until submission. Calls, tools, matches, tokens, elapsed time and costs are recorded regardless. Improvement branches use the same optional limits.</p><div class="form-grid">${field("Model calls", "max_calls", b.max_calls ?? "", "number", "Maximum API responses, including responses after tool results. Blank means unlimited.", 'min="1"')}${field("Tool calls", "max_agent_steps", b.max_agent_steps ?? "", "number", "Maximum tool invocations. Blank means unlimited.", 'min="1"')}${field("Preparation matches", "max_test_matches", b.max_test_matches ?? "", "number", "One test runs two matches, one per side. Blank means unlimited.", 'min="0"')}${field("Preparation time (seconds)", "max_wall_seconds", b.max_wall_seconds ?? "", "number", "Blank means no session time limit.", 'min="1"')}${field("Total input tokens", "max_input_tokens", b.max_input_tokens ?? "", "number", "Optional. Blank means no conversation token limit.", 'min="1"')}${field("Total output tokens", "max_output_tokens", b.max_output_tokens ?? "", "number", "Optional. Blank means no conversation token limit.", 'min="1"')}${field("API spending limit per conversation ($)", "max_cost_usd", b.max_cost_usd ?? "", "number", "Blank means no financial limit.", 'min="0" step="any"')}${field("API spending limit for the experiment ($)", "max_total_usd", c.models.every((m) => m.provider === "mock") ? "" : (c.spending.max_total_usd ?? ""), "number", "Includes all branches. Blank means no financial limit.", 'min="0" step="any"')}</div><small>Financial limits are checked between calls. Without an output cap, a call can exceed the configured limit.</small></details>
 <section class="panel"><details><summary>Import a JSON configuration</summary><textarea id="import-config" class="mono" style="width:100%;margin-top:12px" placeholder="Paste an experiment manifest"></textarea><div style="margin-top:10px">${btn("Apply configuration", "import-config")}</div></details></section></div>
 <aside class="panel sticky editor-review"><h2>Competition setup</h2><nav class="editor-section-nav" aria-label="Configuration sections"><button type="button" data-action="editor-section" data-section="editor-participants"><span>01</span> Participants & rounds</button><button type="button" data-action="editor-section" data-section="editor-scenario"><span>02</span> Scenario</button><button type="button" data-action="editor-section" data-section="editor-rules"><span>03</span> Match rules & roster</button><button type="button" data-action="editor-section" data-section="editor-limits"><span>04</span> Optional limits</button></nav><div class="divider"></div><h3>Schedule preview</h3><div id="plan-preview">${notice("Each round freezes submissions before scoring. Later rounds split into feedback and no-feedback tracks.")}</div>${btn("Calculate schedule", "preview-plan")}</aside></div></form><div class="competition-savebar"><div><strong id="competition-selection-count" aria-live="polite">${c.models.length} participants selected</strong><small>Saving does not start a run.</small></div><label class="check"><input form="competition-form" type="checkbox" name="allow_paid_calls" ${c.spending.allow_paid_calls ? "checked" : ""}>Allow API calls</label><button form="competition-form" type="submit" class="button primary">Save configuration</button></div>`
  );
}
function readCompetition(form) {
  const f = new FormData(form),
    n = (k) => Number(f.get(k)),
    ids = f.getAll("participant"),
    base = structuredClone(S.editConfig || S.boot.default_config),
    models = S.choiceModels.filter((m) => ids.includes(m.id));
  const array = (k) =>
      String(f.get(k) || "")
        .split(/[\s,;]+/)
        .filter(Boolean)
        .map(Number),
    real = models.some((m) => m.provider !== "mock");
  base.name = f.get("name");
  base.models = models;
  base.replicates = n("replicates");
  base.parallel_requests = n("parallel_requests");
  base.request_order = f.get("request_order");
  base.parallel_fights = n("parallel_fights");
  base.compare_previous_round = f.has('compare_previous_round');
  base.generations = f.get("round_stop") === "manual" ? null : n("generations");
  base.schema_version = 2;
  base.improvement_conditions = ["control", "feedback"];
  base.prompt_language = "en";
  base.seeds = array("seeds");
  base.final_seeds = base.generations !== 1 ? array("final_seeds") : [];
  base.include_mirrors = f.has("include_mirrors");
  base.scenario.team_size = n("team_size");
  base.scenario.max_turns = n("max_turns");
  const participantTeams = f.get("team_mode") === "participant";
  if (participantTeams) {
    // Reference opponents are separate from each LLM's independently chosen build.
    base.scenario = structuredClone(S.boot.participant_scenario);
    base.scenario.max_turns = n("max_turns");
    base.scenario.team_selection = {
      mode: "participant",
      require_capital: true,
      independent_builds: true,
      max_weapons: 4,
      max_chips: 50,
    };
  } else {
    delete base.scenario.team_selection;
    if (base.scenario.preset === "llm-team") base.scenario.preset = "custom";
  }
  if (!participantTeams) {
    base.scenario.stats_mode = f.has("realistic_stats")
      ? "realistic-v1"
      : "free";
    base.scenario.member_stats = readStatBuilds(form);
    base.scenario.entity.level = base.scenario.member_stats[0].level;
    Object.assign(
      base.scenario.entity,
      base.scenario.stats_mode === "realistic-v1"
        ? withComponents(
            statsForCapital(
              base.scenario.member_stats[0].level,
              base.scenario.member_stats[0].capital,
            ),
            base.scenario.member_stats[0].components,
          )
        : base.scenario.member_stats[0].stats,
    );
    base.scenario.entity.weapons = base.scenario.member_stats[0].weapons;
    base.scenario.entity.chips = base.scenario.member_stats[0].chips;
  }
  if (String(f.get("map")).trim()) base.scenario.map = JSON.parse(f.get("map"));
  else delete base.scenario.map;
  base.budget_per_session = {};
  for (const key of [
    "max_calls",
    "max_agent_steps",
    "max_test_matches",
    "max_wall_seconds",
    ...(real ? ["max_input_tokens", "max_output_tokens"] : []),
  ]) {
    if (String(f.get(key) || "").trim()) base.budget_per_session[key] = n(key);
  }
  if (real && String(f.get("max_cost_usd") || "").trim())
    base.budget_per_session.max_cost_usd = f.get("max_cost_usd");
  base.spending = real
    ? { allow_paid_calls: f.has("allow_paid_calls") }
    : { allow_paid_calls: false, max_total_usd: 0 };
  if (real && String(f.get("max_total_usd") || "").trim())
    base.spending.max_total_usd = f.get("max_total_usd");
  return base;
}
function planMarkup(p) {
  const total =
    p.ranked_matches_if_all_submit +
    p.mirrors_if_all_submit +
    (p.g1_contemporary_matches || 0) +
    (p.common_reference_matches || 0);
  return `<div class="info-row"><span>Parallel model requests</span><strong>${p.parallel_requests || 1}</strong></div><div class="info-row"><span>Simultaneous fights</span><strong>${p.parallel_fights || 1}</strong></div><div class="info-row"><span>Conversations</span><strong>${p.sessions == null ? "Until manual stop" : fmt(p.sessions)}</strong></div><div class="info-row"><span>Evaluation matches</span><strong>${p.sessions == null ? "Until manual stop" : fmt(total)}</strong></div><div class="info-row"><span>Extra fights for learning-progress metrics</span><strong>${p.previous_comparison_matches===null?"Until manual stop":fmt(p.previous_comparison_matches||0)}</strong></div><div class="info-row"><span>Maximum preparation matches</span><strong>${p.max_preparation_matches == null ? "Unlimited" : fmt(p.max_preparation_matches)}</strong></div><div class="info-row"><span>Total API spending limit</span><strong>${p.simulated ? "$0 (mock)" : p.max_cost_usd == null ? "No limit" : money(p.max_cost_usd)}</strong></div><p class="muted" style="font-size:10px;margin-top:12px">Schedule assuming every participant submits a strategy. ${p.simulated ? "Mock run with no API calls." : "Reservations estimate cost; they do not confirm provider billing."}</p>`;
}
function fightPurposeGuide() {
  return `<dl class="fight-purpose-guide"><div><dt>Ranked tournament</dt><dd><strong>Current vs current</strong><span>Example: R5 vs R5. Used for standings.</span></dd></div><div><dt>Fixed-baseline evaluation</dt><dd><strong>Current vs frozen Round 1</strong><span>Example: R5 vs R1, plus fixed scripts. Collected in multi-round runs to measure progress against unchanged opponents; unscored.</span></dd></div><div><dt>Previous-round comparison</dt><dd><strong>Current vs previous</strong><span>Example: R5 vs R4. Optional engine work for step-by-step progress metrics; unscored.</span></dd></div></dl>`;
}
function learningMetricFields(enabled) {
  return `<fieldset class="metric-collection"><legend>Progression data collection</legend>${fightPurposeGuide()}<label class="check"><input type="checkbox" name="compare_previous_round" ${enabled?'checked':''}>Also collect current-vs-previous comparisons at every round</label><small>Runs throughout unlimited competitions too. R2 vs R1 already exists in the fixed baseline, so it is reused; R3 vs R2, R4 vs R3 and every later comparison add engine fights. No extra model calls, standings points or model feedback.</small></fieldset>`;
}

function requestOrderField(value='models') {
  return selectField('Request scheduling preference','request_order',[
    ['models','Different models first'],['repetitions','Repetitions of one model first']],value,
    'Order preference only: free slots can run several conversations of the same model. On a local server, finish all conversations of the loaded model before switching models.');
}

function runMetricCollectionDialog() {
  const d=S.detail,config=d.metadata.config;
  if(!config)return;
  if(activeJobs().some(job=>job.run===S.run)) {
    openDialog('Execution & metrics',config.name,'<p>Fight workers can be adjusted while this competition runs. Other participant and metric settings require stopping it.</p>'+btn('Adjust fight workers','live-fight-workers')+btn('Close','close-dialog'));return;
  }
  const enabled=d.roster?.compare_previous_round??config.compare_previous_round??false;
  openDialog('Execution & metrics',config.name,`<form data-form="run-metrics">${field("Parallel model requests","parallel_requests",d.roster?.parallel_requests??config.parallel_requests??1,"number","Maximum requests in flight. Lower this when a provider is overloaded; saved work is retained.",'required min="1" max="20"')}${requestOrderField(d.roster?.request_order??config.request_order)}${field("Simultaneous fights","parallel_fights",d.execution_control?.parallel_fights??d.roster?.parallel_fights??config.parallel_fights??1,"number","Maximum concurrent engine workers. Each worker allows 512 MB of Java heap plus overhead.",'required min="1" step="1"')}${learningMetricFields(enabled)}<p>Save, then resume to generate missing comparisons from frozen submissions. Disabling collection keeps existing results.</p><div class="form-footer">${btn('Cancel','close-dialog')}<button type="submit" class="button primary">Save settings</button></div></form>`);
}
async function runParticipantsDialog() {
  await refreshBoot();
  S.detail = await api('/api/run', {run:S.run});
  const config=S.detail.metadata.config;
  if(!config || S.detail.archived) throw new Error('This competition is read-only');
  const active=activeJobs().some(job=>job.run===S.run);
  if(active) {
    openDialog('Edit participants',config.name, '<p>Stop this competition before changing participants. Saved conversations, files and fights are retained. Reopen this dialog after it stops.</p>'+btn('Close','close-dialog'));
    return;
  }
  const known=new Set(config.models.map(model=>model.id));
  const withdrawn=new Set(S.detail.roster?.withdrawn || []);
  const profiles=[...config.models,...S.boot.participants.map(row=>row.spec).filter(model=>!known.has(model.id))];
  const frozen=S.detail.roster?.frozen_tracks || {};
  const submitted=new Set(S.detail.sessions.filter(session=>session.submission).map(session=>session.model));
  const rows=profiles.map(model=>`<section data-run-profile="${e(model.id.toLowerCase())}"><label class="check"><input type="checkbox" name="participant" value="${e(model.id)}" ${known.has(model.id)&&!withdrawn.has(model.id)?'checked':''}><span><strong>${e(model.id)}</strong><small>${e(model.model||model.profile)} · ${known.has(model.id)?(withdrawn.has(model.id)?'Withdrawn':'In competition'):'New participant'}</small></span></label>${submitted.has(model.id) ? `<details class="quiet-details"><summary>Freeze preparation</summary><div class="actions">${[['control','No feedback'],['feedback','With feedback']].map(([track,label])=>`<label class="check"><input type="checkbox" name="freeze-${track}" value="${e(model.id)}" ${(frozen[model.id]||[]).includes(track)?'checked':''}>${label}</label>`).join('')}</div></details>` : ''}</section>`).join('');
  openDialog('Edit participants',config.name,
    `<form data-form="run-participants"><p>Uncheck a participant to withdraw it. Its history and completed fights stay; it no longer blocks later rounds. Check it again to reactivate it.</p><p>New participants prepare missing rounds with the saved scenario and budgets. Existing submissions stay frozen. New fights can extend earlier rounds; feedback already sent is kept unchanged.</p><details class="quiet-details"><summary>What freezing does</summary><p>A frozen track keeps fighting with its previous submitted strategy, without new model calls. Current unsubmitted edits are kept on disk but not used. Uncheck the freeze option to enable future preparation again. Every reused version is recorded.</p></details><label class="field">Find participant<input type="search" id="run-participant-search"></label><div class="run-participant-list">${rows}</div><div class="form-footer">${btn('Cancel','close-dialog')}<button type="submit" class="button primary">Save participants</button></div></form>`);
}
function resumeRecoveryMarkup(detail) {
  const failed=detail.sessions.filter(s=>!s.withdrawn && !s.planned_frozen && ["provider_unavailable","generation_failed","no_submission"].includes(s.status));
  return failed.length ? `<section class="form-section"><h3>Conversation recovery</h3>${failed.map(s=>`<div class="info-row"><span>${e(s.model)} · ${e(sessionLabel(s))}${s.failure?.message ? `<small>${e(s.failure.message)}</small>` : ""}</span><strong>${s.retry_allowed ? (s.context_recovery_required ? "Will retry with a fresh context" : "Will retry") : "Blocked"}${!s.retry_allowed ? `<small>${e(s.retry_reason)}</small>` : ""}</strong></div>`).join("")}<p>Resuming sends another request. A provider that is still unavailable may reject it again.</p></section>` : "";
}
async function launchDialog(draftId = null, runId = null) {
  if (runId) {
    S.detail = await api("/api/run", {run:runId});
    const blocked = S.detail.sessions.filter(s => !s.withdrawn && s.reconciliation_required);
    if (blocked.length) {
      openDialog("Resolve billing before resuming", S.detail.metadata.config.name,
        `<p>These conversations have unresolved provider requests. Record their costs, then resume. All saved submissions and matches are retained.</p>${blocked.map(s => `<div class="info-row"><span>${e(s.model)} · ${e(sessionLabel(s))}</span>${btn("Resolve billing", "reconcile-session", `data-session="${e(s.id)}"`)}</div>`).join("")}`);
      return;
    }
  }
  if (draftId) await refreshBoot();
  let config = draftId
    ? S.boot.drafts.find((d) => d.id === draftId).config
    : S.detail.metadata.config;
  const p = await api("/api/plan", { config, frozen: !!runId, run:runId }, true);
  config = p.config;
  S.launch = { draftId, runId, config, expectedHash: p.config_sha256 };
  openDialog(
    runId ? "Resume competition" : "Launch competition",
    config.name,
    `<form data-form="launch">${runId ? notice("Retryable conversations will continue from their checkpoints. Saved strategies and completed matches are retained.") : ""}${runId ? resumeRecoveryMarkup(S.detail) : ""}${planMarkup(p)}${p.simulated ? notice("Mock participants, real matches. No LLM calls or API charges.") : notice("Calls use the configured keys and prices. Calculated costs are not confirmed provider bills.", "warn")}<div>${config.models.filter(m=>!p.active_models||p.active_models.includes(m.id)).map((m) => `<div class="info-row"><span>${e(m.id)}${m.provider !== "mock" ? `<small>${e(m.endpoint || (m.provider === "anthropic" ? "https://api.anthropic.com/v1/messages" : m.provider === "gemini" ? "https://generativelanguage.googleapis.com/v1beta" : "https://api.openai.com/v1/chat/completions"))}<br>Key: ${e(m.api_key_env)}</small>` : ""}</span><strong>${e(m.model || m.profile)}${m.provider !== "mock" ? `<small>Reasoning: ${e(reasoningLabel(m.parameters))}<br>Seed: ${m.parameters?.seed ?? (m.provider === "anthropic" ? "not available" : "not set")}</small>` : ""}</strong></div>`).join("")}</div>${!p.simulated ? `<label class="check" style="margin-top:20px"><input type="checkbox" name="confirm_paid" required>I authorize API calls ${config.spending.max_total_usd == null ? "without an arena spending limit" : "with a configured total spending limit of " + money(config.spending.max_total_usd)}.</label>` : ""}<div class="form-footer">${btn("Cancel", "close-dialog")}<button type="submit" class="button primary">${runId ? "Resume" : "Start competition"}</button></div></form>`,
  );
}
function retryButton(session) {
  if (!session || S.detail.archived) return '';
  const retryControl=session.submission?'':btn(session.automatic_retries_paused?'Enable automatic retries':'Pause automatic retries','toggle-automatic-retries',`data-session="${e(session.id)}" data-paused="${session.automatic_retries_paused?'false':'true'}"`);
  if (session.reconciliation_required && !activeJobs().some(j=>j.run===S.run))
    return retryControl+btn('Resolve billing','reconcile-session',`data-session="${e(session.id)}"`);
  if(session.finalize_allowed)return retryControl+btn('Finalize saved files','recover-conversation',`data-session="${e(session.id)}"`);
  if (!session.retry_allowed) return retryControl;
  return `${retryControl}${session.automatic_retries_paused?'<small>Automatic retries paused; manual continuation remains available.</small>':''}${session.automatic_retry_at?`<small>Automatic retry at ${new Date(session.automatic_retry_at*1000).toLocaleTimeString()}</small>`:''}${btn('Continue now','recover-conversation',`data-session="${e(session.id)}"`)}${btn('Restart preparation','restart-conversation',`data-session="${e(session.id)}"`)}`;
}
function reconciliationDialog(sid) {
  const session = S.detail.sessions.find(s => s.id === sid);
  openDialog("Resolve request billing", strategyName(sid),
    `<form data-form="reconcile" data-session="${e(sid)}"><p>The provider request was interrupted or returned incomplete usage. Its response may have been charged. Check the provider's usage dashboard before repeating it.</p><p>If a response was saved, its pending tools will continue. Otherwise the request can be retried. Existing files and other participants' results are kept.</p><label>Additional cost for this unresolved request (USD)<input name="cost_usd" type="number" min="0" step="any" required placeholder="0 if confirmed uncharged or local"></label><small>Enter only the unresolved charge, not the conversation total. Already recorded cost: ${money(session.cost_spent || 0)}.</small><label>Verification note<textarea name="note" required placeholder="How you checked the charge; for a local model, state that it runs locally."></textarea></label><div class="form-footer">${btn("Cancel", "close-dialog")}<button class="button primary" type="submit">Record and unlock</button></div></form>`);
}
async function retryDialog(sid) {
  const session = S.detail.sessions.find((s) => s.id === sid),
    config = S.detail.metadata.config;
  if (!session?.retry_allowed)
    throw new Error(session?.retry_reason || "Conversation cannot be retried");
  const model = config.models.find((m) => m.id === session.model),
    paid = model.provider !== "mock";
  const reviewed = await api("/api/plan", { config, frozen: true, run:S.run }, true);
  S.launch = {
    draftId: null,
    runId: S.run,
    config,
    retrySession: sid,
    expectedHash: reviewed.config_sha256,
  };
  openDialog(
    "Retry conversation",
    strategyName(sid),
    `<form data-form="launch">${session.context_recovery_required ? notice("Context window exceeded. Retry starts a fresh request context with the original instructions and access to your saved files. Earlier exchanges remain visible here; usage and budgets are preserved.") : ""}<p>Continue this conversation from its saved files and history. Other models' submissions and completed matches are kept.</p><p>Usage counters and configured limits are preserved. If this recovers an initial strategy, its previously unavailable improvement branches can also run.</p><p>This competition keeps its saved settings. Editing a reusable participant does not change a retry. An effort change below is recorded for this conversation and inherited by its future improvement branches.</p>${reasoningField(model.provider, {...model.parameters, ...session.provider_parameter_overrides}, model.model || "")}<div class="info-row"><span>Model</span><strong>${e(model.id)} · ${e(model.model || model.profile)}</strong></div><div class="info-row"><span>Previous usage</span><strong>${session.completed_calls ?? session.calls} completed model calls · ${session.steps} tool calls</strong></div>${paid ? `<label class="check"><input type="checkbox" name="confirm_paid" required>I authorize API calls for this model${config.spending.max_total_usd == null ? " without an arena spending limit" : " within the existing competition limit of " + money(config.spending.max_total_usd)}.</label>` : ""}<div class="form-footer">${btn("Cancel", "close-dialog")}<button type="submit" class="button primary">Retry conversation</button></div></form>`,
  );
}
const TABS = [
  ["summary", "Summary"],
  ["conversation", "Conversations"],
  ["code", "Code & versions"],
  ["matches", "Matches"],
  ["faults", "Errors"],
  ["files", "Files"],
  ["events", "Journal"],
  ["config", "Configuration"],
];
function runHeader(d) {
  syncLiveMode();
  S.renderedJobState = S.boot.jobs.find((j) => j.run === S.run)?.status;
  const config = d.metadata.config || d.metadata.manifest,
    job = S.boot.jobs.find((j) => j.run === S.run),
    active = job && ["running", "stopping"].includes(job.status),
    experiment = !!d.metadata.config;
  const problems = d.sessions.filter(s=>conversationNeedsAttention(s,active));
  const recovery = problems.length ? `<details class="recovery-panel" data-recovery-run="${e(S.run)}" ${S.recoveryOpen?.[S.run] ? "open" : ""}><summary><span class="recovery-count">${problems.length}</span><strong>Conversations need attention</strong><span>Review & recover</span></summary><div>${problems.map(s=>`<div class="recovery-row"><div><strong>${e(s.model)}</strong><small>${e(sessionLabel(s))}</small>${s.failure?.message ? `<small class="provider-error">${e(s.failure.message)}</small>` : `<small>${e(text(s.status))}</small>`}${!s.retry_allowed && !s.reconciliation_required && !active ? `<small>${e(s.retry_reason || "Retry unavailable")}</small>` : ""}</div><div class="actions">${btn("Open conversation","session-conversation",`data-session="${e(s.id)}"`)}${retryButton(s)}</div></div>`).join("")}</div></details>` : "";
  return `<a class="back-link" href="#view=competitions">← Competitions</a>` + head(config.name, "", `${active ? btn("■ Stop", "stop-job", `data-id="${e(job.id)}"`) : experiment && !d.archived ? btn("Resume", "resume", "", true) : ""}<details class="action-menu"><summary class="button">More <span aria-hidden="true">⌄</span></summary><div>${experiment && !d.archived ? btn("Edit participants","edit-run-participants")+btn("Execution & metrics","run-metric-collection") : ""}${experiment?btn('Copy scheduling diagnostics','copy-scheduling-diagnostics'):''}${btn("Move to workspace","move-workspace",`data-run="${e(S.run)}"`)}<a class="button" href="/api/results.csv?${query({run:S.run})}" download>Download results CSV</a><a class="button" href="/api/results.csv?${query({run:S.run,table:"fights"})}" download>Download match results CSV</a><a class="button" href="/api/results.csv?${query({run:S.run,table:"sessions"})}" download>Download sessions CSV</a>${experiment ? btn("Clone configuration", "clone-run") + btn("Export competition", "export-run") : ""}</div></details>`) +
    `<div class="toolbar run-toolbar">${job ? status(job.status === "failed" && d.report?.incomplete ? "incomplete" : job.status) : ""}${job?.mode==='retry_fights'?badge('Engine recovery · no model calls'):''}${config.models ? badge(config.models.every(m=>m.provider==="mock") ? "Built-in strategies" : "Model competition") : badge("Provided strategies")}${d.archived ? badge("Exported copy", "orange") : ""}<span class="run-id mono" title="Competition ID">${e(S.run)}</span><span class="spacer"></span><label class="check live-toggle"><input id="follow-live" type="checkbox" ${S.follow ? "checked" : ""}>Live</label>${job ? btn("Run log", "job-log", `data-id="${e(job.id)}"`) : ""}</div>` + competitionActivity() + recovery +
    (d.roster ? `<details class="quiet-details"><summary>Recorded competition changes · revision ${d.roster.revision}</summary><p>${d.roster.active.length} active · ${d.roster.withdrawn.length} withdrawn · ${Object.values(d.roster.frozen_tracks||{}).reduce((sum,tracks)=>sum+tracks.length,0)} frozen tracks. Completed fights and earlier submissions are retained. Scores cover the opponents actually faced.</p><p>Withdrawn: ${e(d.roster.withdrawn.join(", ") || "None")}</p>${btn("Edit participants","edit-run-participants")}</details>` : "") +
    (d.sessions.some(s=>s.continuation_identity) ? `<details class="quiet-details"><summary>Continued after an application update</summary><p>Version changes are recorded in the journal.</p></details>` : "") +
    `<nav class="tabs" aria-label="Competition views">${TABS.map(([key,label])=>`<button class="tab ${S.tab===key ? "active" : ""}" ${S.tab===key ? 'aria-current="page"' : ""} data-action="tab" data-tab="${key}">${label}</button>`).join("")}</nav>`;
}
function configurationView(d) {
  const c = d.metadata.config;
  if (!c) return `<section class="panel"><h2>Competition configuration</h2>${raw(d.metadata,"Full configuration")}</section>`;
  const activeModels=c.models.filter(model=>!d.roster?.withdrawn.includes(model.id));
  return `<div class="grid two"><section class="panel"><h2>Format</h2><dl class="configuration-facts"><div><dt>Rounds</dt><dd>${c.generations === null ? "Until manual stop" : c.generations || 1}</dd></div><div><dt>Repetitions per generated model</dt><dd>${c.replicates}</dd></div><div><dt>Repetitions per fixed reference</dt><dd>${d.metadata.fixed_reference_repetitions??c.replicates}</dd></div><div><dt>Learning-progress data</dt><dd>${(d.roster?.compare_previous_round??c.compare_previous_round)?"Extra previous-round comparisons":"Standard comparisons only"}</dd></div><div><dt>Parallel model requests</dt><dd>${d.roster?.parallel_requests??c.parallel_requests??1}</dd></div><div><dt>Request scheduling preference</dt><dd>${(d.roster?.request_order??c.request_order??"models")==="models"?"Different models first":"Repetitions first"}</dd></div><div><dt>Simultaneous fights</dt><dd>${d.execution_control?.parallel_fights??d.roster?.parallel_fights??c.parallel_fights??1}</dd></div><div><dt>Team size</dt><dd>${c.scenario.team_size}</dd></div><div><dt>Maximum turns</dt><dd>${fmt(c.scenario.max_turns)}</dd></div><div><dt>Team selection</dt><dd>${c.scenario.team_selection ? "Chosen by each model" : "Shared roster"}</dd></div></dl></section><section class="panel"><h2>Participants (${activeModels.length} active)</h2><div class="configuration-models">${activeModels.map(m=>`<div><strong>${e(m.id)}</strong><small>${e(PROVIDER_NAMES[m.provider] || m.provider)} · ${e(m.model || m.profile)}</small></div>`).join("")}</div></section></div><section class="panel"><div class="panel-title"><div><h2>Saved settings</h2><p class="muted">Scenario and budgets remain fixed. Participant and metric-collection changes are audited; historical profiles remain in the full record.</p></div>${`<a class="button" href="/api/results.csv?${query({run:S.run})}" download>Download results CSV</a><a class="button" href="/api/results.csv?${query({run:S.run,table:"fights"})}" download>Download match results CSV</a><a class="button" href="/api/results.csv?${query({run:S.run,table:"sessions"})}" download>Download sessions CSV</a>`}${btn("Clone configuration", "clone-run")}</div>${raw(d.metadata,"Full JSON & provenance")}</section>`;
}
function runModels(d) {
  const configured = d.metadata?.config?.models || [];
  return [
    ...new Set([
      ...configured.map((m) => m.id),
      ...d.sessions.map((s) => s.model),
    ]),
  ]
    .filter(Boolean)
    .map((id) => {
      const spec = configured.find((m) => m.id === id);
      const exact = spec?.model || spec?.profile;
      return { id, label: exact && exact !== id ? `${id} · ${exact}` : id };
    });
}
function modelPicker(d, journal = false) {
  return `<label for="conversation-model">Model</label><select id="conversation-model">${journal ? '<option value="">All models</option>' : ""}${runModels(
    d,
  )
    .map(
      (m) =>
        `<option value="${e(m.id)}" ${m.id === S.modelFilter ? "selected" : ""}>${e(m.label)}</option>`,
    )
    .join("")}</select>`;
}
function strategyName(id) {
  const session=S.detail?.sessions.find(s=>s.id===id);
  const origin=S.detail?.metadata.manifest?.strategies?.find(s=>s.id===id)?.origin;
  if (!session && !origin && !/^(.*)-r\d+(?:-g\d+-(?:control|feedback))?$/.test(String(id || ""))) return id || "Competition";
  const item=overviewIdentity(id);
  const model=S.detail?.metadata.config?.models.find(model=>model.id===item.model);
  const fixed=model?.profile==='saved-strategy';
  const description=fixed?(model.strategy?.origin?.reference?'fixed reference · same code':'frozen strategy · same code'):model?.provider==='mock'?'scripted test fixture':item.generation?`revised ${item.condition==='feedback'?'with':'without'} feedback`:'initial strategy';
  return `Round ${item.generation+1} · ${item.model} · repetition ${item.replicate+1} · ${description}${fixed&&item.generation?' · '+text(item.condition):''}`;
}
function sessionLabel(session) {
  const fixed=S.detail?.metadata.config?.models.find(model=>model.id===session.model)?.profile==='saved-strategy';
  return `Repetition ${Number(session.replicate || 0) + 1} · ${generationLabel(session.generation)}${session.generation ? " · " + text(session.condition) : ""} · ${fixed?"Fixed code · ":""}${session.withdrawn ? "Withdrawn" : session.manual_frozen ? "Manually frozen" : session.status==='budget_exhausted'&&session.submission ? "Submitted · preparation limit" : text(session.status)}`;
}
function canProbeProvider(d, sid) {
  const session = d.sessions.find(s => s.id === sid);
  const model = d.metadata.config?.models.find(m => m.id === session?.model);
  if (!model || !["openai","openai-compatible"].includes(model.provider) || session.status !== "provider_unavailable") return false;
  const parameters = {...model.parameters, ...session.provider_parameter_overrides};
  return (model.endpoint || "").replace(/\/$/, "").endsWith("/responses") ||
    (model.model.toLowerCase().startsWith("gpt-6") && parameters.reasoning_effort !== "none");
}
function sessionChooser(d) {
  const selected = d.sessions.find((s) => s.id === S.session);
  const models = runModels(d);
  if (selected) S.modelFilter = selected.model;
  if (!models.some((m) => m.id === S.modelFilter))
    S.modelFilter = selected?.model || models[0]?.id || null;
  const sessions = d.sessions.filter((s) => s.model === S.modelFilter);
  if (!sessions.some((s) => s.id === S.session)) {
    S.session = sessions[0]?.id || null;
    S.offset = 0;
  }
  return `<div id="session-toolbar" class="toolbar">${modelPicker(d)}<label for="session-choice">Conversation</label><select id="session-choice" ${sessions.length ? "" : "disabled"}>${sessions.map((s) => `<option value="${e(s.id)}" ${s.id === S.session ? "selected" : ""}>${e(sessionLabel(s))}</option>`).join("") || "<option>No conversations yet</option>"}</select>${S.session ? btn("Conversation journal", "conversation-journal") + btn("Copy provider diagnostics", "copy-provider-diagnostics", `data-session="${e(S.session)}"`) + (canProbeProvider(d, S.session) ? btn("Test API", "test-provider", `data-session="${e(S.session)}"`) : "") : ""}${retryButton(d.sessions.find((s) => s.id === S.session))}${d.sessions.find(s=>s.id===S.session)?.submission ? btn("Save as participant","save-strategy",`data-session="${e(S.session)}"`) : ""}<span class="spacer"></span></div>`;
}
async function renderRun(epoch, liveUpdate=false) {
  const d = S.detail;
  if(!$("#run-chrome"))$("#main").innerHTML='<div id="run-chrome">'+runHeader(d)+'</div><section id="run-content" class="panel" aria-busy="true">Loading…</section>';
  if(S.activityRun!==S.run) {
    await refreshCompetitionActivity(epoch);
    if(epoch!==S.epoch)return;
  }
  let body = "", sourceChanged=false, deferredErrors=null;
  if (S.tab === "summary") {
    const refreshFaults=S.overviewFaultRun!==S.run || Date.now()-(S.overviewFaultTime||0)>10000 || !activeJobs().some(job=>job.run===S.run);
    const fights=await runResource('/api/matches',{run:S.run,compact:'1'});
    const statistics={training_matches:fights.matches.filter(m=>m.kind==='training').length};
    if (epoch !== S.epoch) return;
    S.overviewMatches = fights.matches;
    S.overviewProgression=fights.progression||[];
    if(refreshFaults) {
      const run=S.run;
      if(S.overviewFaultRun!==run)S.overviewFaults={sessions:[],loading:true};
      deferredErrors=async()=>{
        try {
          const faults=await api('/api/faults',{run});
          if(epoch!==S.epoch||run!==S.run)return;
          S.overviewFaults=faults;S.overviewFaultRun=run;S.overviewFaultTime=Date.now();
          const chart=$('#overview-errors');if(chart)LiveDOM.replace(chart,overviewErrors(S.detail,overviewData(S.detail)));
        } catch(error) {if(error.name!=='AbortError'&&epoch===S.epoch){const chart=$('#overview-errors');if(chart)chart.innerHTML='<h2>Errors</h2><p class="muted">Error statistics could not be loaded. Refresh to retry.</p>';}}
      };
    }
    S.statistics = statistics;
    body = summary(d, statistics);
  } else if (S.tab === "config")
    body = configurationView(d);
  else if (S.tab === "conversation" || S.tab === "code") {
    const selectedSession=d.sessions.find(session=>session.id===S.session);
    const frozenNotice=selectedSession?.manual_frozen ? notice(`Manually frozen from ${e(selectedSession.manual_frozen.from_session)}. Evaluation uses the reused submission; workspace edits remain for audit. <a href="/api/file?${query({run:S.run,path:`sessions/${selectedSession.id}/submission/${selectedSession.submission.entrypoint}`})}" target="_blank" rel="noopener">View executed entrypoint</a>`) : '';
    const chooser = sessionChooser(d) + frozenNotice;
    if (d.sessions.length && !S.session)
      body =
        chooser +
        empty(
          "No conversations for this model",
          "Conversations appear when this participant starts.",
        );
    else if (!d.sessions.length && S.tab === "code") {
      S.files = (await runResource("/api/files", { run: S.run })).files.filter((f) =>
        f.path.endsWith(".leek"),
      );
      body =
        notice(
          "Frozen tournament sources. No generation or intermediate edits were recorded.",
        ) + filesPage();
    } else if (!d.sessions.length)
      body = empty(
        "No recorded conversation",
        "This tournament received .leek files directly and made no generation requests. Mock participants in the demo do have recorded conversations.",
      );
    else if (S.tab === "conversation") {
      let data = await api("/api/conversation", {
        lightweight:1,
        run: S.run,
        session: S.session,
        model: S.modelFilter,
        offset: S.offset,
        tail:S.explicitOffset?undefined:1,
      });
      if (epoch !== S.epoch) return;
      S.offset=data.offset;
      // Opening a conversation follows its tail; explicit page links retain history.
      if (!S.explicitOffset && data.offset+data.messages.length < data.total) {
        S.offset = Math.max(0, data.total - 25);
        data = await api("/api/conversation", {
        lightweight:1,
          run: S.run, session: S.session, offset: S.offset,
        });
        if (epoch !== S.epoch) return;
      }
      // Keep the selected conversation stable across reloads.
      const conversationURL = new URL(location.href);
      conversationURL.hash = query({view: "run", run: S.run, tab: "conversation",
        session: S.session, model: S.modelFilter,
        ...(S.explicitOffset ? {offset: S.offset} : {})});
      history.replaceState(null, "", conversationURL);
      S.liveConversation = {
        run: S.run,
        session: S.session,
        next: data.offset + data.messages.length,
        total: data.total,
        armed: !S.explicitOffset || data.offset + data.messages.length >= data.total,
      };
      body =
        chooser +
        '<section class="conversation-panel"><nav class="conversation-navigation" aria-label="Conversation navigation">' +
        btn('↑ First message', 'conversation-top') + btn('↓ Latest message', 'conversation-bottom') +
        '</nav><div id="conversation-scroll" role="region" aria-label="Conversation messages" tabindex="0"><div id="conversation-transcript">' +
        conversation(data) +
        '</div></div><div id="conversation-live-status" aria-live="polite">' +
        conversationLiveStatus(S.liveConversation, false) + '</div></section>';
    } else {
      const previousVersion=S.version;
      const followLatest=liveUpdate && S.version===(S.versions?.versions?.length||0)-1 && S.previous==null &&
        !document.activeElement?.matches('#source-file,#source-previous');
      const previousCount=S.versions?.versions?.length||0;
      S.versions = await runResource("/api/versions", {
        run: S.run,
        session: S.session,
        model: S.modelFilter,
      });
      if(followLatest && S.versions.versions.length>previousCount)S.version=null;
      body = chooser + codePage(S.versions);
      sourceChanged=previousVersion!==S.version;
    }
  } else if (S.tab === "matches") {
    S.matches = (await runResource("/api/matches", { run: S.run })).matches;
    body = matchesPage();
  } else if (S.tab === 'faults') {
    const data=await api('/api/faults',{run:S.run});
    if(epoch!==S.epoch)return;
    S.faults=data;
    body=faultsPage();
  } else if (S.tab === "files") {
    S.files = (await runResource("/api/files", { run: S.run })).files;
    body = filesPage();
  } else if (S.tab === "events") {
    const chosen = d.sessions.find((s) => s.id === S.session);
    if (chosen && !S.modelFilter) S.modelFilter = chosen.model;
    if (chosen && S.modelFilter && chosen.model !== S.modelFilter) {
      S.session = null;
      S.offset = 0;
    }
    S.events = await api("/api/events", {
      run: S.run,
      session: S.session || undefined,
      model: S.modelFilter || undefined,
      offset: S.offset,
    });
    body = eventsPage(S.events);
  }
  if (epoch !== S.epoch) return;
  const html='<div id="run-chrome">' + runHeader(d) + '</div><div id="run-content">' + body + '</div>';
  if(liveUpdate) LiveDOM.update($('#main'),html);
  else $('#main').innerHTML=html;
  if(deferredErrors)deferredErrors();
  if(S.tab==='conversation')refreshConversationDiagnostics(epoch);
  if (S.tab === "conversation" && S.follow && !S.explicitOffset)
    animateConversationTail();
  if ((!liveUpdate || sourceChanged || !$("#source-content")?.liveLoaded) && S.tab === "code" && d.sessions.length && S.versions?.versions?.length)
    await loadSource(liveUpdate);
  if ((!liveUpdate || !$("#match-detail")?.liveLoaded) && S.tab === "matches" && S.matchPath) await loadMatch();
  if (
    (S.tab === "files" || (S.tab === "code" && !d.sessions.length)) &&
    S.files.length
  )
    await loadFile(
      S.files.find((f) => f.path === S.file)?.path ||
        S.files.find((f) => f.path === "report.md")?.path ||
        S.files[0].path, liveUpdate,
    );
}
function measuredUsage(session) {
  const receipt = session.usage_receipts;
  if (receipt?.responses) return {
    ...receipt,
    complete: !receipt.missing_usage && session.token_usage_known!==false && !session.in_flight && session.status !== "needs_reconciliation",
  };
  return {
    input_tokens: session.input_tokens || 0,
    output_tokens: session.output_tokens || 0,
    cached_input_tokens: null,
    reasoning_tokens: null,
    complete: !!session.token_usage_known && !session.in_flight,
  };
}
function faultRateBars(rows,metric='tools') {
  const numerator=metric==='tools'?'tool_errors':'failed_analyses',denominator=metric==='tools'?'tool_calls':'completed_analyses';
  const models=new Map();
  for(const row of rows) {const group=models.get(row.model)||{errors:0,attempts:0};group.errors+=row[numerator]||0;group.attempts+=row[denominator]||0;models.set(row.model,group);}
  return [...models].sort((a,b)=>(b[1].errors/(b[1].attempts||1))-(a[1].errors/(a[1].attempts||1))).map(([model,value])=>`<div class="error-rate-row"><strong>${e(model)}</strong><div class="workspace-bar-track"><span style="width:${100*value.errors/(value.attempts||1)}%;background:${metric==='tools'?'#bd5c52':'#b8863c'}"></span></div><span>${value.errors} / ${value.attempts} · ${value.attempts?pct(value.errors/value.attempts):'N/A'}</span></div>`).join('')||'<p class="muted">No observations for this selection.</p>';
}
function overviewErrors(d,data) {
  const sessions=new Set(data.sessions.map(session=>session.id));
  const rows=(S.overviewFaults?.sessions||[]).filter(row=>sessions.has(row.session)&&d.metadata.config?.models.find(model=>model.id===row.model)?.provider!=='mock');
  return `<section class="overview-card" id="overview-errors">${S.overviewFaults?.loading?'<p class="muted">Loading error statistics…</p>':''}<div class="overview-section-head"><h2>Errors</h2>${btn('Details & incidents','open-errors')}</div><div class="error-rate-grid"><section><h3>Tool call errors</h3>${faultRateBars(rows,'tools')}</section><section><h3>Compilation failure rate</h3>${faultRateBars(rows,'compilation')}</section></div><p class="muted">Uses the overview model and round filters. Failed attempts / executed calls or compilation checks. API failures are separate; these rates are not a direct hallucination score.</p></section>`;
}
function faultsPage() {
  const data=S.faults || {sessions:[],incidents:[]};
  const rows=data.sessions.filter(row=>(!S.faultModel||row.model===S.faultModel)&&(!S.faultRound||String(row.round)===S.faultRound)&&(!S.faultCondition||row.condition===S.faultCondition));
  const selected=new Set(rows.map(row=>row.session));
  const total=key=>rows.reduce((sum,row)=>sum+(row[key]||0),0);
  const rateMetric=S.faultMetric||'tools';
  const bars=faultRateBars(rows,rateMetric);
  const incidents=[...data.incidents].reverse().filter(row=>selected.has(row.session));
  return `<section id="faults-content"><div class="collection-toolbar">${selectField('Model','fault_model', [['','All models'],...[...new Set(data.sessions.map(row=>row.model))].map(model=>[model,model])],S.faultModel||'')}${selectField('Round','fault_round',[['','All rounds'],...[...new Set(data.sessions.map(row=>row.round))].sort((a,b)=>a-b).map(round=>[String(round),'Round '+round])],S.faultRound||'')}${selectField('Track','fault_condition',[['','All tracks'],['initial','Initial'],['control','No feedback'],['feedback','With feedback']],S.faultCondition||'')}<a class="button" href="/api/results.csv?${query({run:S.run,table:'errors'})}" download>Download errors CSV</a></div><div class="metrics">${metric('Tool errors',`${total('tool_errors')} / ${total('tool_calls')}`,total('tool_calls')?pct(total('tool_errors')/total('tool_calls')):'No executed tools')}${metric('Compilation failure rate',total('completed_analyses')?pct(total('failed_analyses')/total('completed_analyses')):'N/A',`${total('failed_analyses')} failed / ${total('completed_analyses')} completed checks · ${total('compiler_errors')} diagnostics · ${total('analysis_infrastructure_failures')} technical failures`)}${metric('Runtime errors',fmt(total('runtime_errors')),`${total('preparation_runtime_errors')} in preparation tests`)}${metric('Provider failures',fmt(total('provider_failures')),'Reported separately from authoring errors')}</div><section class="panel">${selectField('Failure rate','fault_metric',[['tools','Tool calls'],['compilation','Compilation checks']],rateMetric)}<div class="workspace-bars">${bars||'<p>No observations yet.</p>'}</div></section><section class="panel"><h2>By round and track</h2>${table(['Participant','Round / track','Tool errors','Unknown tools','Bad arguments','Failed compilation checks','Invalid teams','Runtime errors'],rows.map(row=>`<tr><td>${e(row.model)}${row.manual_frozen?'<small>Manually frozen</small>':''}</td><td>R${row.round} · ${e(text(row.condition))}</td><td>${row.tool_errors} / ${row.tool_calls}</td><td>${row.unknown_tools}</td><td>${row.invalid_arguments}</td><td>${row.completed_analyses?pct(row.failed_analyses/row.completed_analyses):'N/A'}<small>${row.failed_analyses} / ${row.completed_analyses??0} completed checks · ${row.compiler_errors} diagnostics</small></td><td>${row.invalid_teams}</td><td>${row.runtime_errors}</td></tr>`))}<p class="muted">Observed errors, not a hallucination score. Tool failures include unavailable files and other operational errors. Compiler warnings are excluded. Compilation failure rate divides failed checks by completed checks; engine timeouts are excluded from that denominator. Repeated attempts count separately. Runtime errors count recorded execution events across scored and reference fights; preparation is separate.</p></section><section class="panel"><h2>Recent incidents</h2><p>${data.incidents_total??data.incidents.length} recorded incidents; the most recent 200 are available here. Full receipts remain in the Journal.</p>${incidents.map(row=>`<details class="quiet-details" data-fault-event="${row.event}" data-fault-run="${e(S.run)}" ${S.faultOpen?.[S.run+'/'+row.event]?'open':''}><summary>${e(row.model)} · R${row.round} · ${e(text(row.category))}${row.tool?' · '+e(row.tool):''}</summary><p>${date(row.at)} · ${e(text(row.condition))} · Journal event ${row.event}</p><pre>${e(row.message)}</pre>${btn('Open conversation','session-conversation',`data-session="${e(row.session)}"`)}</details>`).join('')||'<p>No incidents in this selection.</p>'}</section></section>`;
}
function usageAccounting(d) {
  const models = d.metadata.config?.models || [];
  const rows = models.filter(m => m.provider !== "mock").map(model => {
    const sessions = d.sessions.filter(s => s.model === model.id);
    const usages = sessions.map(measuredUsage);
    const sum = key => usages.reduce((n, u) => n + (u[key] || 0), 0);
    const input = sum("input_tokens"), cached = sum("cached_input_tokens");
    const p = model.pricing || {};
    return `<tr><td>${e(model.id)}</td><td>${fmt(input)}</td><td>${fmt(sum("output_tokens"))}</td><td>${usages.some(u => u.cached_input_tokens == null || u.missing_cache_usage) ? "Unknown / partial" : `${fmt(cached)} (${input ? (100*cached/input).toFixed(1) : 0}%)`}</td><td>${usages.some(u=>u.cache_creation_input_tokens == null || u.missing_cache_creation_usage) ? "Not reported / partial" : fmt(sum("cache_creation_input_tokens"))}</td><td>${usages.some(u=>u.reasoning_tokens == null || u.missing_reasoning_usage) ? "Unknown / partial" : fmt(sum("reasoning_tokens"))}</td><td>${money(sessions.reduce((n,s) => n+Number(s.cost_spent || 0),0))}</td><td>${e([p.input_per_million, p.cached_input_per_million ?? p.input_per_million, p.output_per_million].join(" / "))}</td></tr>`;
  });
  const incomplete = d.sessions.some(s => s.calls && models.find(m=>m.id===s.model)?.provider !== "mock" && !measuredUsage(s).complete);
  const paid = d.sessions.filter(s=>models.find(m=>m.id===s.model)?.provider !== "mock");
  const totalTokens = paid.reduce((n,s)=>n+measuredUsage(s).input_tokens+measuredUsage(s).output_tokens,0);
  const totalCost = paid.reduce((n,s)=>n+Number(s.cost_spent || 0),0);
  return `<h3>Whole competition API usage</h3>${btn("Copy usage diagnostics", "copy-usage-diagnostics")}<p><strong>${fmt(totalTokens)} tokens · ${money(totalCost)} estimated${incomplete ? " (partial)" : ""}</strong></p><p>All rounds, both tracks, retries and API diagnostics. ${incomplete ? "Partial: requests are in progress or usage is missing." : ""}</p>${table(["Model", "Input", "Output", "Cached input", "Cache writes", "Reasoning", "Estimated USD", "USD / 1M input / cached / output"], rows)}<p class="muted">Cached input is included in input; reasoning is included in output. Configured prices are frozen. GPT-6.1 cache writes default to 1.25 times input price unless explicitly configured. Old receipts with recorded cache-write usage are repriced for this view; their original charges are preserved. These are calculated estimates, not the provider's invoice. Compare the same project, model and time range in the provider dashboard; other competitions are separate.</p>`;
}
function tokenDisplay(d) {
  const models = new Map(
    (d.metadata?.config?.models || []).map((m) => [m.id, m.provider]),
  );
  const real = d.sessions.filter(
    (s) => models.get(s.model) !== "mock" && (s.calls || s.token_usage_known),
  );
  if (d.report.simulated) return "N/A";
  if (!real.length)
    return d.report.input_tokens == null
      ? "Unavailable"
      : `${fmt(d.report.input_tokens)} / ${fmt(d.report.output_tokens)}`;
  const known = real.map(measuredUsage).filter((u) => u.input_tokens || u.output_tokens || u.complete);
  if (!known.length) return "Unavailable from provider";
  return `${fmt(known.reduce((n, s) => n + (s.input_tokens || 0), 0))} / ${fmt(known.reduce((n, s) => n + (s.output_tokens || 0), 0))}${known.length < real.length || known.some(u=>!u.complete) ? " (partial)" : ""}`;
}
// One scope drives every section of the competition overview.
function overviewSettings() {
  S.overviews ||= {};
  return (S.overviews[S.run] ||= {
    round: "all",
    model: "",
    source: "competition",
    matrix: "models",
  });
}
let overviewIdentities={};
function overviewIdentityCache() {
  if(overviewIdentities.detail!==S.detail)overviewIdentities={detail:S.detail,values:new Map()};
  return overviewIdentities.values;
}
function conversationNeedsAttention(s, active=false) {
  if(s.withdrawn || s.planned_frozen)return false;
  if(s.reconciliation_required && (!active || s.status==='needs_reconciliation'))return true;
  if(s.status==='budget_exhausted')return false;
  return !s.submission && ['provider_unavailable','needs_reconciliation','generation_failed','no_submission'].includes(s.status);
}
function overviewIdentity(id) {
  const cache=overviewIdentityCache();
  if(cache.has(id))return cache.get(id);
  const session = S.detail?.sessions.find((s) => s.id === id);
  const origin = S.detail?.metadata.manifest?.strategies?.find(s=>s.id===id)?.origin;
  const parts = String(id || "").match(
    /^(.*)-r(\d+)(?:-g(\d+)-(control|feedback))?$/,
  );
  const identity = {
    id,
    model: session?.model || origin?.variant || parts?.[1] || id,
    condition: session?.condition || origin?.condition || parts?.[4] || "initial",
    generation: Number(session?.generation ?? (origin ? origin.round-1 : undefined) ?? parts?.[3] ?? 0),
    replicate: Number(session?.replicate ?? origin?.replicate ?? parts?.[2] ?? 0),
  };
  cache.set(id,identity);return identity;
}
const overviewRound = (condition, generation = 1) => {
  if (condition === "initial") return "R1 · Initial";
  if (String(condition).includes(":"))
    [generation, condition] = condition.split(":");
  return `R${Number(generation) + 1} · ${condition === "control" ? "No feedback" : "Feedback"}`;
};
const overviewRoundKey = (item) =>
  item.condition === "initial"
    ? "initial"
    : item.generation === 1
      ? item.condition
      : `${item.generation}:${item.condition}`;
function overviewEntries(match) {
  const candidateSide =
    match.candidate_side ??
    (match.candidate ? match.sides.indexOf(match.candidate) : -1);
  return match.sides
    .map((id, side) => ({ ...overviewIdentity(id), side }))
    .filter(
      (item) =>
        !['evaluation','progression'].includes(match.kind) ||
        candidateSide < 0 ||
        item.side === candidateSide,
    );
}
function overviewAccept(item, scope) {
  return (
    (!scope.model || item.model === scope.model) &&
    (scope.round === "all" ||
      scope.round?.startsWith("stage:") ||
      overviewRoundKey(item) === scope.round)
  );
}
function overviewData(d, scope=overviewSettings()) {
  const all = (S.overviewMatches || []).filter(
      (m) =>
        !m.mirror &&
        matchCategory(m,scope.source) &&
        (!scope.round.startsWith("stage:") || m.stage === scope.round.slice(6)),
    );
  const selected = all
    .map((match) => ({
      match,
      entries: overviewEntries(match).filter((item) =>
        overviewAccept(item, scope),
      ),
    }))
    .filter((v) => v.entries.length);
  const models = new Map(),
    matrix = new Map(),
    history = new Map();
  const add = (row, match, side) => {
    const result = match.result;
    if (result.status !== "completed") row.failures++;
    else {
      const outcome =
        result.winner_side === -1
          ? "draws"
          : result.winner_side === side
            ? "wins"
            : "losses";
      row[outcome]++;
    }
  };
  const blank = () => ({ wins: 0, draws: 0, losses: 0, failures: 0 });
  for (const { match, entries } of selected)
    for (const item of entries) {
      const withinModel=overviewIdentity(match.sides[1-item.side]).model===item.model;
      if (!withinModel || scope.source==='progression') {
        if (!models.has(item.model))
          models.set(item.model, { model: item.model, ...blank() });
        add(models.get(item.model), match, item.side);
        const key = JSON.stringify([item.model, item.generation, item.condition]);
        if (!history.has(key))
          history.set(key, {
            model: item.model,
            condition: item.condition,
            generation: item.generation,
            ...blank(),
          });
        add(history.get(key), match, item.side);
      }
      const who = scope.matrix === "versions" ? item.id : item.model;
      const other = scope.matrix === "versions" ? match.sides[1-item.side] : overviewIdentity(match.sides[1 - item.side]).model;
      if (scope.matrix !== "versions" && other === item.model && scope.source!=='progression') continue;
      const pair = JSON.stringify([who, other]);
      if (!matrix.has(pair))
        matrix.set(pair, {
          who,
          other,
          entrants: new Set(),
          opponents: new Set(),
          stages: new Set(),
          ...blank(),
        });
      const cell = matrix.get(pair);
      cell.entrants.add(item.id);
      cell.opponents.add(match.sides[1 - item.side]);
      cell.stages.add(match.stage);
      add(cell, match, item.side);
    }
  const finish = (row) => {
    row.completed = row.wins + row.draws + row.losses;
    row.score = row.completed
      ? (row.wins + 0.5 * row.draws) / row.completed
      : null;
    return row;
  };
  const sessions = d.sessions.filter((v) =>
    (!v.withdrawn || v.submission) && overviewAccept(overviewIdentity(v.id), scope),
  );
  return {
    scope,
    selected,
    sessions,
    models: [...models.values()]
      .map(finish)
      .sort((a, b) => (b.score ?? -1) - (a.score ?? -1)),
    matrix: [...matrix.values()].map(finish),
    history: [...history.values()].map(finish),
  };
}
function overviewFilters(d, data) {
  const options = (values, value) =>
    values
      .map(
        ([id, label]) =>
          `<option value="${e(id)}" ${id === value ? "selected" : ""}>${e(label)}</option>`,
      )
      .join("");
  const models = d.sessions.length
    ? runModels(d).map((m) => m.id)
    : [
        ...new Set(
          (S.overviewMatches || []).flatMap((m) =>
            m.sides.map((id) => overviewIdentity(id).model),
          ),
        ),
      ];
  const sourceVersions = [...d.sessions.map(s=>overviewIdentity(s.id)), ...(d.metadata.manifest?.strategies || []).filter(s=>s.origin).map(s=>overviewIdentity(s.id))];
  const hasImprovement =
    sourceVersions.some((s) => s.generation > 0) ||
    (S.overviewMatches || []).some((m) => m.stage.includes("g1"));
  return `<div class="overview-filters" role="group" aria-label="Overview filters"><label>Round<select data-overview-filter="round" aria-label="Overview round">${options(
    [
      ["all", "All rounds"],
      ["initial", "Round 1 · Initial"],
      ...(!d.sessions.length
        ? [...new Set((S.overviewMatches || []).map((m) => m.stage))].map(
            (stage) => ["stage:" + stage, stageText(stage)],
          )
        : []),
      ...[
        ...new Set(
          sourceVersions
            .filter((v) => v.generation > 0)
            .map(overviewRoundKey),
        ),
      ]
        .sort(
          (a, b) =>
            (a.includes(":") ? Number(a.split(":")[0]) : 1) -
            (b.includes(":") ? Number(b.split(":")[0]) : 1),
        )
        .map((key) => [key, overviewRound(key).replace(/^R/, "Round ")]),
    ],
    data.scope.round,
  )}</select></label><label>Model<select data-overview-filter="model" aria-label="Overview model">${options([["", "All models"], ...models.map((m) => [m, m])], data.scope.model)}</select></label><label>Matches<select data-overview-filter="source" aria-label="Overview matches">${options(
    [
      ["competition", "Tournament"],
      ["evaluation", "Fixed baseline (unscored)"],
      ["progression", "Previous-round comparisons (unscored)"],
    ],
    data.scope.source,
  )}</select></label><label>Matrix grouping<select data-overview-filter="matrix" aria-label="Matrix grouping">${options([["models","By model"],["versions","By strategy version"]],data.scope.matrix || "models")}</select></label><span class="overview-scope">${data.selected.length} fights · ${data.models.length} models</span></div>`;
}
function overviewRanking(data) {
  if (!data.models.length)
    return '<div class="overview-empty">No scored matches in this selection.</div>';
  const resultLink=(row,outcome,value)=>`<a href="#${query({view:'run',run:S.run,tab:'matches',kind:data.scope.source,entrant_model:row.model,round:data.scope.round,outcome,scored:'1',exclude_same_model:data.scope.source==='progression'?undefined:'1'})}">${value}</a>`;
  return `<p class="muted">${data.scope.source==='progression'?'Against previous-round versions, including the same model.':'Against other models only.'} Click a result to inspect its fights. Counts are appearances across selected submitted versions: fixed references have fewer repetitions. Cache reuse counts as a completed scheduled fight.</p><ol class="overview-ranking">${data.models.map((r, i) => `<li><span class="overview-rank">${i + 1}</span><div class="overview-rank-body"><div><strong>${e(r.model)}</strong><span>${pct(r.score)}</span></div><div class="overview-bar"><span style="width:${100 * (r.score || 0)}%;background:${overviewColor(r.model)}"></span></div><small>${resultLink(r,"win",r.wins+"W")} · ${resultLink(r,"draw",r.draws+"D")} · ${resultLink(r,"loss",r.losses+"L")}${r.failures ? ` · ${r.failures} failed` : ""}</small> <small title="Tournament fights count for both sides. Same-model fights are excluded. Fixed references have one sample; generated participants include repetitions. Cache reuse still counts every scheduled fight.">${fmt(r.completed)} fights · ${data.sessions.filter(session=>session.model===r.model&&session.submission).length} submitted strategies${data.selected.some(v=>v.entries.some(item=>item.model===r.model)&&v.match.result.reference_cache?.hit)?" · includes cached fights":""}</small></div></li>`).join("")}</ol>`;
}
let overviewPalette={};
function overviewColor(model) {
  if(overviewPalette.matches!==S.overviewMatches || overviewPalette.detail!==S.detail) {
  const names=[...new Set([...(S.detail?.metadata.config?.models||[]).map(m=>m.id),...(S.overviewMatches||[]).flatMap(m=>m.sides.map(id=>overviewIdentity(id).model))])].sort();
  overviewPalette={matches:S.overviewMatches,detail:S.detail,colors:new Map(names.map((name,i)=>[name,seriesColor(i)]))};
  }
  return overviewPalette.colors.get(model)||seriesColor(0);
}
function overviewEvolution(data) {
  const mode=overviewSettings().evolution||'bars';
  return `<div class="evolution-view"><label class="chart-view-choice">Display<select data-evolution-view aria-label="Evolution display"><option value="bars" ${mode==='bars'?'selected':''}>Grouped bars</option><option value="lines" ${mode==='lines'?'selected':''}>Lines</option></select></label><div id="overview-evolution-chart">${mode==='lines'?overviewEvolutionLines(data):overviewEvolutionBars(data)}</div></div>`;
}
function overviewEvolutionBars(data) {
  if(!data.history.length)return '<div class="overview-empty">Evolution appears as rounds finish.</div>';
  const models=[...new Set(data.history.map(row=>row.model))].sort();
  const rounds=[...new Set(data.history.map(row=>row.generation))].sort((a,b)=>a-b);
  const gap=24,L=data.signed?70:42,R=12,T=20,B=210,H=255;
  const available=Math.max(320,Math.min(1200,$('#overview-evolution-chart')?.clientWidth||($('#main')?.clientWidth||innerWidth)-96));
  const band=Math.max(12,Math.min(22,Math.floor((available-L-R-rounds.length*gap)/(rounds.length*models.length))));
  const groupWidth=Math.max(60,models.length*band),W=Math.max(available,L+R+rounds.length*(groupWidth+gap));
  const step=(W-L-R)/rounds.length,min=data.signed?-1:0,max=1,y=score=>B-(B-T)*(score-min)/(max-min),origin=y(0);
  const ticks=data.signed?[-1,-.5,0,.5,1]:[0,.25,.5,.75,1];
  const rows=new Map(data.history.map(row=>[JSON.stringify([row.model,row.generation,row.condition]),row]));
  const marks=rounds.map((round,index)=>{
    const start=L+index*step+(step-models.length*band)/2;
    return `<text x="${L+(index+.5)*step}" y="${B+25}" text-anchor="middle">Round ${round+1}</text>`+models.map((model,mi)=>{
      const conditions=round===0?['initial']:['control','feedback'];
      return conditions.map((condition,ci)=>{
        const row=rows.get(JSON.stringify([model,round,condition]));if(row?.score==null)return '';
        const width=round===0?band-6:Math.floor((band-4)/2),x=start+mi*band+(round===0?3:ci*(width+2)+1),color=overviewColor(model);
        const label=row.tooltip||`${model} · ${overviewRound(condition,round)} · ${pct(row.score)} · ${row.wins}W / ${row.draws}D / ${row.losses}L · ${row.completed} appearances`;
        return `<rect x="${x}" y="${Math.min(y(row.score),origin)-(row.score===0?2:0)}" width="${width}" height="${Math.max(2,Math.abs(origin-y(row.score)))}" fill="${color}" fill-opacity="${condition==='control'?.35:1}" stroke="${color}" stroke-width=".6" tabindex="0" aria-label="${e(label)}" data-chart-model="${e(model)}" data-chart-label="${e(label)}"/>`;
      }).join('');
    }).join('');
  }).join('');
  return `<div class="chart-filterable" data-chart-key="${e(data.chartKey||'evolution:'+S.run)}"><div class="evolution-scroll" role="region" aria-label="Evolution by round" tabindex="0"><svg class="overview-evolution evolution-bars" style="min-width:${W}px" viewBox="0 0 ${W} ${H}" role="img" aria-label="Model scores grouped by round">${ticks.map(value=>`<line x1="${L}" x2="${W-R}" y1="${y(value)}" y2="${y(value)}" stroke="#e0e7e4"/><text x="${L-7}" y="${y(value)+4}" text-anchor="end">${data.signed?progressionPoints(value):pct(value)}</text>`).join('')}${data.parity?`<line x1="${L}" x2="${W-R}" y1="${y(.5)}" y2="${y(.5)}" stroke="#6f8294" stroke-dasharray="4 4"/>`:''}${marks}</svg></div><div class="evolution-track-key"><span><i class="track-swatch"></i>${data.parity||data.signed?'With feedback':'Initial / With feedback'}</span><span><i class="track-swatch pale"></i>Without feedback</span></div><div class="overview-legend">${models.map(model=>`<span tabindex="0" data-chart-model="${e(model)}"><i style="background:${overviewColor(model)}"></i>${e(model)}</span>`).join('')}</div></div>`;
}
function overviewEvolutionLines(data) {
  if (!data.history.length)
    return '<div class="overview-empty">Evolution appears as rounds finish.</div>';
  const models = [...new Set(data.history.map((r) => r.model))];
  const generations = [...new Set(data.history.map((r) => r.generation))].sort(
    (a, b) => a - b,
  );
  const width = innerWidth < 600 ? 420 : 560,
    height = 210;
  const x = (g) =>
    (data.signed?75:45) +
    (generations.indexOf(g) * (width - (data.signed?115:80))) /
      Math.max(1, generations.length - 1);
  const y = (v) => 165 - ((v-(data.signed?-1:0))/(data.signed?2:1))*140;
  const ticks = generations.filter(
    (g, i) =>
      i === 0 ||
      i === generations.length - 1 ||
      i % Math.max(1, Math.ceil(generations.length / 8)) === 0,
  );
  return `<div class="chart-filterable" data-chart-key="${e(data.chartKey||'evolution:'+S.run)}"><svg class="overview-evolution" viewBox="0 0 ${width} ${height}" role="img" aria-label="Model scores across strategy rounds">${(data.signed?[-1,-.5,0,.5,1]:[0,.5,1]).map((v) => `<line x1="${data.signed?68:38}" x2="${width - 25}" y1="${y(v)}" y2="${y(v)}" stroke="#e7ebf2"/><text x="0" y="${y(v) + 4}">${data.signed?progressionPoints(v):pct(v)}</text>`).join("")}${ticks.map((g) => `<text x="${x(g)}" y="195" text-anchor="middle">R${g + 1}</text>`).join("")}${models
    .map((model) => {
      const rows = data.history.filter((r) => r.model === model),
        color = overviewColor(model);
      return ["control", "feedback"]
        .map((condition) => {
          const track = rows
            .filter(
              (r) => r.condition === "initial" || r.condition === condition,
            )
            .sort((a, b) => a.generation - b.generation);
          return track
            .map((r, i) => {
              if (r.score == null) return "";
              const prev = track[i - 1];
              return `${prev?.score != null ? `<path d="M${x(prev.generation)},${y(prev.score)} L${x(r.generation)},${y(r.score)}" fill="none" stroke="${color}" stroke-width="2" data-chart-model="${e(model)}" data-chart-label="${e(model)} · ${condition==='control'?'No feedback':'With feedback'}" ${condition === "control" ? 'stroke-dasharray="4 4"' : ""}/>` : ""}<circle cx="${x(r.generation)}" cy="${y(r.score)}" r="4" fill="${color}" tabindex="0" data-chart-model="${e(model)}" data-chart-label="${e(r.tooltip||`${model} · ${overviewRound(r.condition,r.generation)} · ${pct(r.score)} (${r.completed} appearances)`)}"><title>${e(model)} · ${overviewRound(r.condition, r.generation)}: ${pct(r.score)} (${r.completed} appearances)</title></circle>`;
            })
            .join("");
        })
        .join("");
    })
    .join(
      "",
    )}</svg><div class="overview-legend">${models.map((model) => `<span tabindex="0" data-chart-model="${e(model)}"><i style="background:${overviewColor(model)}"></i>${e(model)}</span>`).join("")}<span>Solid: feedback · Dashed: no feedback</span></div></div>`;
}
const PROGRESSION_MODES=[['own_initial','Against own Round 1'],['own_previous','Against own previous round'],['previous_pool','Against previous-round LLM pool'],['score_change','Score change in selected category']];
const progressionPoints=value=>value==null?'N/A':`${value>0?'+':''}${fmt(value*100,1)} pp`;
function learningProgressionData(d,mode) {
  const scope=overviewSettings(),profiles=new Map((d.metadata.config?.models||[]).map(model=>[model.id,model]));
  let history;
  if(mode==='score_change') {
    const all=overviewData(d,{...scope,round:'all'}).history;
    const indexed=new Map(all.map(row=>[JSON.stringify([row.model,row.generation,row.condition]),row]));
    const expected=S.overviewProgression?.length?S.overviewProgression:all.filter(row=>row.generation>0&&profiles.get(row.model)?.provider!=='mock');
    history=expected.map(identity=>{
      const row=indexed.get(JSON.stringify([identity.model,identity.generation,identity.condition]))||{...identity,score:null,completed:0};
      const previous=indexed.get(JSON.stringify([row.model,row.generation-1,row.generation===1?'initial':row.condition]));
      const initial=indexed.get(JSON.stringify([row.model,0,'initial']));
      const delta=row.score!=null&&previous?.score!=null?row.score-previous.score:null;
      return {...row,score:delta,currentScore:row.score,previousScore:previous?.score??null,initialScore:initial?.score??null,
        totalDelta:row.score!=null&&initial?.score!=null?row.score-initial.score:null,
        relativeChange:row.score!=null&&initial?.score>0?(row.score-initial.score)/initial.score:null,
        tooltip:`${row.model} · ${overviewRound(row.condition,row.generation)} · ${progressionPoints(delta)} vs previous round · ${pct(previous?.score)} → ${pct(row.score)} · ${row.completed} current fights`};
    });
  } else {
    history=(S.overviewProgression||[]).map(row=>({...row,...row[mode],
      tooltip:`${row.model} · ${overviewRound(row.condition,row.generation)} · ${pct(row[mode].score)} · ${row[mode].wins}W / ${row[mode].draws}D / ${row[mode].losses}L · ${row[mode].completed} fights against ${row[mode].opponent_versions} versions`}));
  }
  const visible=new Set(d.sessions.filter(session=>!session.withdrawn||session.submission).map(session=>JSON.stringify([session.model,session.generation||0,session.condition||'initial'])));
  history=history.filter(row=>visible.has(JSON.stringify([row.model,row.generation,row.condition]))&&overviewAccept(row,scope));
  if(scope.round.startsWith('stage:')) {
    const selected=new Set(overviewData(d).history.map(row=>JSON.stringify([row.model,row.generation,row.condition])));
    history=history.filter(row=>selected.has(JSON.stringify([row.model,row.generation,row.condition])));
  }
  return {history,chartKey:'learning:'+S.run,signed:mode==='score_change',parity:mode!=='score_change'};
}
function learningProgression(d) {
  if(!(d.metadata.config?.models||[]).some(model=>model.provider!=='mock'))return '';
  const scope=overviewSettings(),mode=scope.progressionMode||'own_initial',view=scope.progressionView||'bars',data=learningProgressionData(d,mode);
  const descriptions={own_initial:'Direct comparison with your frozen Round 1 strategy, paired by repetition. 50% is parity; above 50% favors the newer version.',
    own_previous:'Direct comparison with the same repetition and track from the previous round. 50% is parity.',
    previous_pool:'Available fights against previous-round LLM versions, including your own. Fixed reference scripts are excluded. 50% is parity.',
    score_change:'Score at round t minus score at t-1 in the category selected above, in percentage points. Opponent pools and evaluation seeds can change between rounds.'};
  const latest=new Map();for(const row of data.history) {const key=JSON.stringify([row.model,row.condition]);if(!latest.has(key)||latest.get(key).generation<row.generation)latest.set(key,row);}
  const rows=[...latest.values()].sort((a,b)=>a.model.localeCompare(b.model)||a.condition.localeCompare(b.condition));
  const measured=data.history.filter(row=>row.score!=null),missing=data.history.length-measured.length;
  const chartData=mode==='score_change'?data:{...data,signed:true,parity:false,history:data.history.map(row=>({...row,score:row.score==null?null:2*row.score-1}))};
  const extra=mode==='own_previous'||mode==='previous_pool';
  const enabled=d.roster?.compare_previous_round??d.metadata.config?.compare_previous_round;
  const needsExtra=extra&&data.history.some(row=>row.generation>=2&&row.score==null);
  const details=mode==='score_change'
    ?table(['Model','Track','Latest round','Current score','Vs previous round','Since Round 1','Relative to Round 1'],rows.map(row=>`<tr><td>${e(row.model)}</td><td>${e(text(row.condition))}</td><td>R${row.generation+1}</td><td>${pct(row.currentScore)}</td><td>${progressionPoints(row.score)}</td><td>${progressionPoints(row.totalDelta)}<small>R1: ${pct(row.initialScore)}</small></td><td>${row.relativeChange==null?'N/A':(row.relativeChange>0?'+':'')+pct(row.relativeChange)}</td></tr>`))
    :table(['Model','Track','Latest round','Head-to-head score','Win / draw / loss','Opponent versions','Completed fights'],rows.map(row=>`<tr><td>${e(row.model)}</td><td>${e(text(row.condition))}</td><td>R${row.generation+1}</td><td>${pct(row.score)}</td><td>${row.wins} / ${row.draws} / ${row.losses}</td><td>${row.opponent_versions}</td><td>${row.completed}${row.failures?` · ${row.failures} failed`:''}</td></tr>`));
  return `<section class="overview-card" id="learning-progress"><div class="overview-section-head"><h2>Learning progress</h2><div class="chart-controls"><label class="field">Comparison<select data-learning-mode aria-label="Learning progress comparison">${PROGRESSION_MODES.map(([id,label])=>`<option value="${id}" ${mode===id?'selected':''}>${e(label)}</option>`).join('')}</select></label><label class="field">Display<select data-learning-view aria-label="Learning progress display">${[['bars','Grouped bars'],['lines','Lines'],['latest','Latest values']].map(([id,label])=>`<option value="${id}" ${view===id?'selected':''}>${label}</option>`).join('')}</select></label></div></div><p class="muted">${descriptions[mode]} ${mode!=='score_change'?'Bars show wins minus losses as a share of fights: zero is parity, positive is progress, negative is regression.':''}</p>${needsExtra&&enabled?'<p class="progression-availability">Previous-round metric collection is enabled. Missing engine fights run after preparation; resume a stopped run to fill gaps.</p>':''}${needsExtra&&!enabled?`<div class="progression-availability">Round 2 reuses existing Round 1 comparisons. To collect comparisons at every later round, including unlimited runs, enable <strong>Also collect current-vs-previous comparisons at every round</strong> in More → Execution & metrics, then resume. ${btn('Execution & metrics','run-metric-collection')}</div>`:''}${missing?`<p class="muted">${missing} round/track observations have no usable comparison yet. Missing values are not scored as zero.</p>`:''}${view==='latest'?details:measured.length?view==='lines'?overviewEvolutionLines(chartData):overviewEvolutionBars(chartData):'<div class="overview-empty">No completed comparison for the selected model and round yet.</div>'}${view!=='latest'&&rows.length?`<details class="overview-details"><summary>Latest values by model and track</summary>${details}</details>`:''}<small class="muted">Completed fights only; model and round filters apply. ${mode==='score_change'?'Changes describe the selected category; they do not establish improvement against fixed opponents.':'Historical comparisons are unscored diagnostics and are not sent as model feedback.'}</small></section>`;
}

function overviewMatchLink(data, who, other, outcome, value, description) {
  const cell = data.matrix.find(
    (row) => row.who === who && row.other === other,
  );
  const ids = [...cell.entrants],
    opponents = [...cell.opponents],
    stages = [...cell.stages];
  // Keep compact, exact legacy links for individual strategies; grouped links retain model and round scope.
  if (
    ids.length === 1 &&
    opponents.length === 1 &&
    stages.length === 1 &&
    (ids[0] !== opponents[0] || data.scope.matrix === "versions")
  )
    return matrixLink(
      stages[0],
      ids[0],
      opponents[0],
      outcome,
      value,
      description,
      data.scope.source,
    );
  const href =
    "#" +
    query({
      view: "run",
      run: S.run,
      tab: "matches",
      kind: data.scope.source,
      entrant_model: who,
      opponent_model: other,
      round: data.scope.round,
      outcome,
      scored: "1",
    });
  return `<a href="${e(href)}" aria-label="${e(`${who} vs ${other}: ${description}`)}">${e(value)}</a>`;
}
function overviewMatrix(data) {
  if (!data.matrix.length)
    return '<div class="overview-empty">Head-to-head results appear after opponents meet.</div>';
  const names = [...new Set(data.matrix.map((r) => r.other))].sort();
  const rows = [...new Set(data.matrix.map(r=>r.who))].sort();
  const short = (name) => (name.length > 18 ? name.slice(0, 16) + "…" : name);
  const label = (name) => {
    if (data.scope.matrix === "versions" && (S.detail.sessions.some(s=>s.id===name) || S.detail.metadata.manifest?.strategies?.some(s=>s.id===name && s.origin))) {
      const identity=overviewIdentity(name);
      return `<abbr title="${e(strategyName(name))}" tabindex="0">${e(short(identity.model))}<small>${e(overviewRound(identity.condition,identity.generation))} · #${identity.replicate+1}</small></abbr>`;
    }
    return `<abbr title="${e(name)}" tabindex="0">${e(short(name))}</abbr>`;
  };
  return `<div class="overview-matrix-wrap"><table class="overview-matrix" style="min-width:${names.length > 5 ? (names.length + 1) * 96 : 0}px" aria-label="Head-to-head results by selected grouping"><thead><tr><th scope="col">vs</th>${names.map((name) => `<th scope="col">${label(name)}</th>`).join("")}</tr></thead><tbody>${rows
    .map(
      (who) =>
        `<tr><th scope="row">${label(who)}</th>${names
          .map((other) => {
            const r = data.matrix.find(
              (row) => row.who === who && row.other === other,
            );
            if (!r) return '<td class="overview-no-match">·</td>';
            return `<td style="background:rgba(82,120,229,${r.score == null ? 0 : 0.04 + r.score * 0.16})"><div class="overview-cell-score">${overviewMatchLink(data, who, other, "completed", pct(r.score), countLabel(r.completed, "completed match", "completed matches"))}</div><div class="overview-cell-results">${overviewMatchLink(data, who, other, "win", r.wins, countLabel(r.wins, "win"))}<span> / </span>${overviewMatchLink(data, who, other, "draw", r.draws, countLabel(r.draws, "draw"))}<span> / </span>${overviewMatchLink(data, who, other, "loss", r.losses, countLabel(r.losses, "loss", "losses"))}</div>${r.failures ? `<small>${overviewMatchLink(data, who, other, "failure", r.failures + " failed", countLabel(r.failures, "failure"))}</small>` : ""}</td>`;
          })
          .join("")}</tr>`,
    )
    .join(
      "",
    )}</tbody></table></div><div class="overview-caption">Row vs column · score and wins / draws / losses${data.scope.matrix === "versions" ? " · Each entry is a frozen strategy, identified by round, track and repetition." : " · Switch to strategy versions to inspect fights between rounds or feedback tracks of the same model."}</div>`;
}
function overviewDetails(d, data, statistics) {
  const recorded = (S.overviewMatches || []).filter(
    (m) => m.result.status === "completed",
  );
  const count = (predicate) => recorded.filter(predicate).length;

  const totals = new Map();
  for (const { match, entries } of data.selected)
    for (const item of entries) {
      const row = statistics?.match_totals?.[match.path]?.[item.side];
      if (!row) continue;
      if (!totals.has(item.model)) totals.set(item.model, { id: item.model });
      const total = totals.get(item.model);
      for (const key of [
        "actions",
        "cells_moved",
        "damage_dealt",
        "damage_taken",
        "operations",
        "errors",
      ])
        total[key] =
          row[key] == null || total[key] === null
            ? null
            : (total[key] || 0) + row[key];
    }
  return `<details class="overview-details"><summary>Detailed metrics</summary><div class="overview-detail-body">${table(
    ["Model", "Size (B)", "Score", "Score / B", "Wins", "Draws", "Losses", "Appearances", "Failures"],
    data.models.map(
      (r) =>
        `<tr><td>${e(r.model)}</td><td>${fmt(overviewModelSize(d,r.model),3)}</td><td>${pct(r.score)}</td><td>${fmt(r.score!=null && overviewModelSize(d,r.model)?r.score/overviewModelSize(d,r.model):null,4)}</td><td>${r.wins}</td><td>${r.draws}</td><td>${r.losses}</td><td>${r.completed}</td><td>${r.failures}</td></tr>`,
    ),
  )}${
    totals.size
      ? `<h3>Combat totals</h3><p class="muted">Selected scored fights only. Per-turn details are available in Matches.</p>${table(
          [
            "Model",
            "Actions",
            "Movement",
            "Damage dealt",
            "Damage taken",
            "Operations",
            "Errors",
          ],
          [...totals.values()].map(
            (r) =>
              `<tr><td>${e(r.id)}</td>${["actions", "cells_moved", "damage_dealt", "damage_taken", "operations", "errors"].map((k) => `<td>${fmt(r[k])}</td>`).join("")}</tr>`,
          ),
        )}`
      : ""
  }</div></details>
  <details class="overview-details" id="overview-conversations"><summary>Conversations <span>${data.sessions.length}</span></summary><div class="overview-detail-body">${
    data.sessions.length
      ? table(
          ["Model", "Version", "Status", "Calls", "Cost", ""],
          data.sessions.map(
            (s) =>
              `<tr><td>${e(s.model)}</td><td>${overviewRound(overviewIdentity(s.id).condition, s.generation)}<small>Repetition ${s.replicate + 1}</small></td><td>${status(s.status)} ${s.validation_status && !["valid", "not_submitted"].includes(s.validation_status) ? badge(s.validation_status === "pending" ? "Validation pending" : "Validation: " + text(s.validation_status), s.validation_status === "pending" ? "blue" : "orange") : ""}</td><td>${fmt(s.calls)}</td><td>${money(s.cost_spent)}</td><td>${btn("Open", "session-conversation", `data-session="${e(s.id)}"`)}${btn("Diagnostics", "session-diagnostics", `data-session="${e(s.id)}"`)}${retryButton(s)}${s.submission ? btn("Save as participant","save-strategy",`data-session="${e(s.id)}"`) : ""}</td></tr>`,
          ),
        )
      : "<p>No conversations recorded.</p>"
  }</div></details>
  <details class="overview-details"><summary>Usage & match accounting</summary><div class="overview-detail-body">${usageAccounting(d)}<h3>Selected versions</h3><p>Tokens: ${e(tokenDisplay({ ...d, sessions: data.sessions }))} · ${fmt(data.sessions.reduce((n, s) => n + (s.calls || 0), 0))} model calls · ${fmt(data.sessions.reduce((n, s) => n + (s.steps || 0), 0))} tool calls</p><h3>Whole competition</h3><dl class="overview-accounting"><div><dt>Completed evaluations (ranked + diagnostics)</dt><dd>${fmt(count((m) => m.kind !== "training"))}</dd></div><div><dt>Ranked fights · Round 1</dt><dd>${fmt(count((m) => m.kind === "competition" && !m.mirror && !/^g\d+-tournament$/.test(m.stage)))}</dd></div><div><dt>Ranked fights · Later rounds</dt><dd>${fmt(count((m) => m.kind === "competition" && !m.mirror && /^g\d+-tournament$/.test(m.stage)))}</dd></div><div><dt>Fixed-baseline evaluations (unscored)</dt><dd>${fmt(count((m) => m.kind === "evaluation"))}</dd></div><div><dt>Extra previous-round comparisons (unscored)</dt><dd>${fmt(count((m) => m.kind === "progression"))}</dd></div><div><dt>Preparation tests (unscored)</dt><dd>${fmt(statistics?.training_matches || 0)}</dd></div><div><dt>Of these: cached fixed-reference fights</dt><dd>${fmt(count(m=>!!m.result.reference_cache?.hit))}</dd></div><div><dt>Self-play diagnostics (unscored)</dt><dd><a href="#${query({view:'run',run:S.run,tab:'matches',kind:'selfplay'})}">${fmt(count((m) => m.mirror))} · View fights</a></dd></div></dl>${btn("View preparation tests", "show-training")}</div></details>
  <details class="overview-details"><summary>How to read these results</summary><div class="overview-detail-body"><p>Score = (wins + 0.5 × draws) / completed appearances. 50% can mean all draws. Failures do not earn points and remain visible separately.</p>${fightPurposeGuide()}<p>A vs B and B vs A are both included in standings. Self-play (A vs identical A) is unscored: counting both copies would always contribute 50%, which dilutes scores without comparing distinct strategies.</p><p>Filters apply to all charts, the matrix and details. The model filter selects the candidate; opponents remain visible. Self-play diagnostics and preparation tests are excluded from scored results. Tournament rankings and progress exclude fights against versions of the same model. The separate previous-round comparison view includes them. The strategy-version matrix retains these comparisons; fight counts include them. Other appearances can exceed the number of unique fights. Tournament diagonals are omitted.</p><p>Cost and tokens measure preparation of selected versions, independently of the match category. Unknown provider usage stays unknown. Zero configured prices still allow token measurement.</p></div></details>`;
}
function summary(d, statistics = null) {
  const data = overviewData(d),
    sessions = data.sessions;
  const failures = sessions.filter(s=>conversationNeedsAttention(s,activeJobs().some(job=>job.run===S.run)));
  const known = sessions.map(measuredUsage).filter((u) => u.input_tokens || u.output_tokens || u.complete),
    tokens = known.reduce(
      (n, s) => n + (s.input_tokens || 0) + (s.output_tokens || 0),
      0,
    );
  const real = sessions.filter(
    (s) =>
      d.metadata.config?.models.find((m) => m.id === s.model)?.provider !==
        "mock" && s.calls,
  );
  const costUnknown = sessions.some(
      (s) =>
        s.status === "needs_reconciliation" ||
        Number(s.money_reserved || 0) > 0,
    ),
    cost = sessions.reduce((n, s) => n + Number(s.cost_spent || 0), 0);
  return `<div class="competition-overview">${overviewFilters(d, data)}${data.scope.source==='progression'?notice('Unscored progression diagnostic: current LLM versions face the preceding round. This includes same-model historical opponents; results do not change tournament standings or model feedback.'):''}${failures.length ? `<div class="overview-alert">${failures.length} conversation${failures.length === 1 ? "" : "s"} need attention. <button class="table-button" data-action="overview-failures">Review & retry</button></div>` : ""}<div class="overview-kpis"><div><span>Completed fights</span><strong>${fmt(data.selected.filter((v) => v.match.result.status === "completed").length)}</strong><small>${data.selected.filter((v) => v.match.result.status !== "completed").length} failed</small></div><div><span>Submitted strategies</span><strong>${sessions.length ? sessions.filter((s) => s.submission || s.status === "submitted").length : d.metadata.manifest?.strategies?.filter(s=>overviewAccept(overviewIdentity(s.id),data.scope)).length ?? data.models.length}${sessions.length ? `<small> / ${sessions.length}</small>` : ""}</strong><small>${d.metadata.config ? d.metadata.config.models.filter(model=>!d.roster?.withdrawn.includes(model.id)&&(!data.scope.model||data.scope.model===model.id)).length : data.models.length} active participants</small></div><div><span>Estimated API cost</span><strong>${sessions.length ? (costUnknown ? "Unknown" : money(cost)) : "N/A"}</strong><small>Selected versions</small></div><div><span>Tokens · selected versions</span><strong>${known.length ? fmt(tokens) : real.length ? "Unknown" : "N/A"}</strong><small>${known.length ? (known.length < real.length || known.some(u=>!u.complete) ? "Partial reported usage" : "Input + output") : real.length ? "Not reported by provider" : "No measured LLM usage"}</small></div></div>
  <div class="overview-charts"><section class="overview-card"><div class="overview-section-head"><h2>Model ranking</h2><span>Score</span></div>${overviewRanking(data)}</section><section class="overview-card"><div class="overview-section-head"><h2>Evolution</h2><span>Score by version</span></div>${overviewEvolution(data)}</section></div><section class="overview-card">${resourcePanel(overviewResourcePoints(d,data),"overview")}</section>
  ${learningProgression(d)}
  ${overviewErrors(d,data)}
  ${data.matrix.length ? `<section class="overview-card overview-head-to-head"><div class="overview-section-head"><h2>Match matrix</h2><span>Click a result to see fights</span></div>${overviewMatrix(data)}</section>` : `<div class="overview-empty">${data.selected.length ? "No head-to-head pairs in this selection." : `No ${data.scope.source === "competition" ? "tournament" : data.scope.source==='progression'?"previous-round comparison":"reference"} matches yet.`}${statistics?.training_matches ? ` ${statistics.training_matches} preparation tests recorded; excluded from standings. ${btn("View preparation tests", "show-training")}` : ""}</div>`}
  ${overviewDetails(d, data, statistics)}</div>`;
}
let conversationValues = [];
function conversationData(value, title) {
  const index = conversationValues.push(value) - 1;
  return `<details class="conversation-data" data-conversation-value="${index}"><summary>${e(title)}</summary><pre></pre></details>`;
}
function feedbackView(value) {
  if (!Array.isArray(value?.matches)) return "";
  return `<section class="game-brief"><strong>Tournament feedback supplied to the model</strong><p>Results are from this strategy's perspective. Opponents are anonymous. This historical run contains ${value.matches.length} match summaries${value.truncated ? " (truncated)" : ""}.</p>${table(
    ["Opponent", "Result", "Turns", "Operations", "Errors"],
    value.matches.map(
      (m) =>
        `<tr><td>${e(m.opponent)}</td><td>${e(m.status && m.status !== "completed" ? text(m.status) : m.winner === "self" ? "Win" : m.winner === "draw" ? "Draw" : "Loss")}</td><td>${fmt(m.turns)}</td><td>${fmt(m.operations)}</td><td>${fmt(m.errors)}</td></tr>`,
    ),
  )}</section>`;
}
function callPerformance(message) {
  if (message.role !== 'assistant' || message.elapsed_seconds == null) return '';
  const usage=message.usage || {}, metrics=message.request_metrics;
  return `<details class="quiet-details"><summary>Call performance · ${fmt(usage.input_tokens)} input tokens · ${fmt(message.elapsed_seconds,1)} s</summary><p>${fmt(usage.output_tokens)} output tokens${message.elapsed_seconds > 0 && usage.output_tokens != null ? ` · ${fmt(usage.output_tokens/message.elapsed_seconds,2)} output tokens/s across the full request` : ''}. This rate includes prompt processing and request time; it is not the provider's decode-only speed.</p>${metrics ? `<p>${fmt(metrics.history_messages)} context messages · ${fmt(metrics.request_characters)} request characters · ${fmt(metrics.request_setup_seconds,2)} s preparing the request.</p>` : ''}</details>`;
}
function providerOutput(message, index) {
  const blocks = (message.output_blocks || []).filter(
    (b) => !b.hidden && !(message.file_exchange && b.kind === "tool_result"),
  );
  let requestIndex = 0;
  const label = (block) => {
    if (block.kind !== "tool_call") return block.label;
    const call = message.call_summaries?.[requestIndex++];
    if (!call) return block.label;
    const args = call.arguments || {};
    return `Tool request: ${call.name}${args.path ? " · " + args.path : ""}${args.offset != null ? " · offset " + args.offset : ""}${args.limit != null ? " · limit " + args.limit : ""}`;
  };
  return (
    blocks
      .map(
        (block) =>
          `<details class="provider-output ${e(block.kind)}" data-output-block="${block.index}" data-output-message="${index}" data-record-run="${e(S.run)}" data-record-session="${e(S.session)}"><summary><span>${e(label(block))}</span><small>${block.kind === "reasoning" ? "Recorded reasoning" : block.kind === "tool_call" ? "Open request arguments" : fmt(block.characters) + " characters"}</small></summary><pre></pre></details>`,
      )
      .join("") +
    (Number(message.usage?.reasoning_tokens) > 0
      ? `<p class="output-coverage">${fmt(message.usage.reasoning_tokens)} reasoning tokens reported${blocks.some((b) => b.kind === "reasoning" && b.readable) ? "" : "; no readable reasoning text returned"}.</p>`
      : "")
  );
}
function sessionDiagnostics(data, full = false) {
  if (!data) return '<div data-session-diagnostics><small>Loading fight summary…</small></div>';
  const problems = data.problems || [],
    compilation = data.compilation || [];
  const validationProblems = problems.filter(
    (p) => p.phase !== "script execution",
  );
  const scriptProblems = problems.filter((p) => p.phase === "script execution");
  const validation =
    data.validation_status === "pending"
      ? "Validation pending"
      : data.validation_status === "not_submitted"
        ? "No submitted strategy"
        : data.validation_status === "valid"
          ? "Compilation passed"
          : "Validation: " + text(data.validation_status);
  const problem = (p) =>
    `<div><strong>${e(p.phase)} · ${e(text(p.status))}</strong><p>${e(p.message)}</p>${p.origin_session ? btn("Open original failure", "session-conversation", `data-session="${e(p.origin_session)}"`) : ""}${p.sides ? `<small>${e(p.sides.map(strategyName).join(" vs "))} · Seed ${e(p.seed)}</small>` : ""}${p.path ? `<small class="mono">${e(p.path)}</small>` : ""}</div>`;
  const errors = compilation.filter((row) => row.severity === "error").length;
  const warnings = compilation.filter(
    (row) => row.severity === "warning",
  ).length;
  return `<div class="notice ${problems.length ? "error" : ""}" data-session-diagnostics><strong>${data.has_submission ? "Strategy submitted" : e(text(data.generation_status))}</strong> · ${e(validation)}<p>${fmt(data.matches.completed)} completed fights across all categories · ${fmt(data.matches.failed)} engine failures</p><small>${fmt(data.matches.competition_completed)} scored tournament fights · ${fmt(data.matches.reference_completed)} fixed-baseline evaluations · ${fmt(data.matches.mirror_completed)} self-play diagnostics · ${fmt(data.matches.preparation_completed)} preparation fights</small>${validationProblems.map(problem).join("")}${
    compilation.length
      ? `<p><strong>${errors} compilation error${errors === 1 ? "" : "s"} · ${warnings} warning${warnings === 1 ? "" : "s"}</strong></p>${table(
          ["Severity", "Location", "Diagnostic"],
          compilation.map(
            (row) =>
              `<tr><td>${e(row.severity)}</td><td class="mono">${e(row.file)}:${e(row.line ?? "?")}:${e(row.column ?? "?")}</td><td>${e(row.message)}<small>Code ${e(row.code ?? "?")}${row.name ? " · " + e(row.name) : ""}</small></td></tr>`,
          ),
        )}`
      : ""
  }${scriptProblems.length ? `<details><summary>Script error events in ${scriptProblems.length} fights</summary><p>The same error can recur on many turns. These counts are error events, not distinct bugs. Completed fights can contain compilation or execution errors.</p>${scriptProblems.map(problem).join("")}</details>` : ""}${!problems.length ? "<p>No recorded validation or fight failure for this strategy.</p>" : ""}<small>${e(data.schedule_note)}</small>${data.assessment ? `<details><summary>Submission validation report</summary><pre>${e(pretty(data.assessment))}</pre></details>` : ""}${full ? `<details><summary>Diagnostic JSON</summary><pre id="session-diagnostic-json">${e(pretty(data))}</pre></details>` : ""}</div>`;
}

function fileExchange(message, index) {
  const info = message.file_exchange;
  if (!info) return "";
  const writing = info.name === "write_file";
  const label = writing
    ? `${info.saved ? "Saved" : "Attempted write"}: ${info.path} · ${fmt(info.characters)} characters`
    : `Read ${info.name === "read_docs" ? "documentation" : "source"}: ${info.path}`;
  return `<section class="file-exchange"><strong>${e(label)}</strong>${info.error ? `<p>Tool error: ${e(info.error)}</p>` : !writing ? `<p>Characters ${fmt(info.offset)}–${fmt(info.end_offset)}${info.total_characters != null ? " of " + fmt(info.total_characters) : " (total length not recorded)"} · ${info.truncated ? "Partial read; next offset " + fmt(info.next_offset) : "End of file reached"}</p>` : ""}<details data-file-exchange="${index}" data-record-run="${e(S.run)}" data-record-session="${e(S.session)}"><summary>${writing ? "Inspect written content and diff" : "Document excerpt actually sent to the model"}</summary><pre></pre></details></section>`;
}
let conversationAnimation;
function cancelConversationAnimation() {
  if (conversationAnimation != null)
    cancelAnimationFrame(conversationAnimation);
  conversationAnimation = null;
}
function animateConversationTail() {
  cancelConversationAnimation();
  const pane = $("#conversation-scroll");
  if (!pane) return;
  const target = Math.max(0, pane.scrollHeight - pane.clientHeight);
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
    pane.scrollTop = target;
    return;
  }
  const start = pane.scrollTop, started = performance.now();
  let expected = start;
  const tick = now => {
    if (pane !== $("#conversation-scroll") || Math.abs(pane.scrollTop - expected) > 2) {
      cancelConversationAnimation(); return;
    }
    const progress = Math.min(1, (now - started) / 320);
    pane.scrollTop = start + (target - start) * (1 - Math.pow(1 - progress, 3));
    expected = pane.scrollTop;
    conversationAnimation = progress < 1 ? requestAnimationFrame(tick) : null;
  };
  conversationAnimation = requestAnimationFrame(tick);
}
window.addEventListener(
  "wheel",
  (event) => {
    cancelConversationAnimation();
    if (event.deltaY < 0 && event.target.closest?.("#conversation-scroll") && S.tab === "conversation" && S.liveConversation)
      S.liveConversation.userPaused = true;
  },
  { passive: true },
);
window.addEventListener("touchstart", cancelConversationAnimation, {
  passive: true,
});
window.addEventListener("pointerdown", cancelConversationAnimation, {
  passive: true,
});
window.addEventListener("keydown", (event) => {
  if (
    ["ArrowUp", "PageUp", "Home"].includes(event.key) &&
    S.tab === "conversation" &&
    event.target.closest?.("#conversation-scroll") &&
    S.liveConversation
  )
    S.liveConversation.userPaused = true;
  if (
    [
      "ArrowUp",
      "ArrowDown",
      "PageUp",
      "PageDown",
      "Home",
      "End",
      "Escape",
    ].includes(event.key)
  )
    cancelConversationAnimation();
});
function nearConversationEnd() {
  const pane = $("#conversation-scroll");
  return !!pane && pane.scrollHeight - pane.scrollTop - pane.clientHeight < 100;
}
function conversationLiveStatus(live, following) {
  const remaining = Math.max(0, live.total - live.next);
  return remaining
    ? `${remaining} ${live.armed ? "new" : "later"} message${remaining === 1 ? "" : "s"} ${btn("Follow latest", "conversation-latest")}`
    : following
      ? "<small>Following new messages</small>"
      : "<small>Reading history. Return to the bottom to follow new messages.</small>";
}
document.addEventListener('click',event=>{if(event.target.closest('[data-action=retry-conversation-diagnostics]'))refreshConversationDiagnostics(S.epoch);});
function refreshConversationDiagnostics(epoch) {
  const run=S.run,session=S.session,key=run+'/'+session;
  S.conversationDiagnoses ||= {};
  const previous=S.conversationDiagnoses[key];
  if((previous?.pending && previous.epoch===epoch) || (previous?.data && Date.now()-previous.at<15000)) {
    const mount=$('[data-session-diagnostics]');
    if(previous?.data&&mount)LiveDOM.replace(mount,sessionDiagnostics(previous.data));
    return;
  }
  const entry={epoch,at:Date.now(),pending:true,data:previous?.data};S.conversationDiagnoses[key]=entry;
  if(Object.keys(S.conversationDiagnoses).length>8)for(const old of Object.keys(S.conversationDiagnoses).slice(0,-8))delete S.conversationDiagnoses[old];
  api('/api/session-diagnostics',{run,session}).then(data=>{
    entry.data=data;entry.at=Date.now();
    if(epoch!==S.epoch||run!==S.run||session!==S.session||S.tab!=='conversation')return;
    const mount=$('[data-session-diagnostics]');if(mount)LiveDOM.replace(mount,sessionDiagnostics(data));
  }).catch(error=>{
    if(epoch!==S.epoch||error.name==='AbortError')return;
    const mount=$('[data-session-diagnostics]');if(mount)mount.innerHTML='<small>Fight summary unavailable.</small>'+btn('Retry summary','retry-conversation-diagnostics');entry.at=0;
  }).finally(()=>{entry.pending=false;});
}
async function refreshLiveConversation(epoch, force = false) {
  const live = S.liveConversation,
    mount = $("#conversation-transcript");
  if (!live || !mount || live.run !== S.run || live.session !== S.session)
    return false;
  if (live.refreshing) return true;
  live.refreshing = true;
  try {
    if (force) {
      live.armed = true;
      live.userPaused = false;
      S.explicitOffset = false;
      const latestURL = new URL(location.href);
      const parameters = new URLSearchParams(latestURL.hash.slice(1));
      parameters.delete("offset");
      latestURL.hash = parameters.toString();
      history.replaceState(null, "", latestURL);
    }
    let following =
      force || (live.armed && !live.userPaused && nearConversationEnd() &&
        !$(".chat-message details[open], details[data-provider-event][open]"));
    let data = await api("/api/conversation", {
        lightweight:1,
      run: live.run,
      session: live.session,
      offset: live.next,
      limit: following ? 100 : 1,
    });
    if (
      (!S.follow && !force) ||
      epoch !== S.epoch ||
      live !== S.liveConversation ||
      S.tab !== "conversation" ||
      live.session !== S.session ||
      live.run !== S.run ||
      mount !== $("#conversation-transcript")
    )
      return true;
    if (!force && (live.userPaused || !nearConversationEnd() ||
        $(".chat-message details[open], details[data-provider-event][open]"))) following = false;
    // A resumed/replaced history can be shorter than the previously loaded one.
    // Rebuild that page instead of keeping messages that no longer exist.
    if (data.total < live.next) {
      S.offset = Math.max(0, data.total - 25);
      data = await api("/api/conversation", {
        lightweight:1,
        run: live.run, session: live.session, offset: S.offset,
      });
      if (epoch !== S.epoch || live !== S.liveConversation || mount !== $("#conversation-transcript")) return true;
      LiveDOM.update(mount,conversation(data));
      live.next = data.offset + data.messages.length;
      live.total = data.total;
      live.armed = true;
      const banner = $("#conversation-live-status");
      if (banner) LiveDOM.update(banner,conversationLiveStatus(live, following));
      return true;
    }
    const scrollWithMessages =
      following &&
      (force || nearConversationEnd()) &&
      (force || !$(".chat-message details[open]"));
    const pane = $("#conversation-scroll");
    const preservedScroll = pane.scrollTop;
    live.total = data.total;
    if (following && data.messages.length) {
      const template = document.createElement("template");
      template.innerHTML = conversation(data, true);
      const fragment = document.createDocumentFragment();
      template.content
        .querySelectorAll(".chat-message")
        .forEach((message, index) => {
          message.classList.add("message-arrival");
          message.style.animationDelay = Math.min(index, 4) * 50 + "ms";
          fragment.append(message);
        });
      mount.append(fragment);
      live.next = data.offset + data.messages.length;
      if (scrollWithMessages) {
        const messages = $$(".chat-message", mount);
        messages
          .slice(0, Math.max(0, messages.length - 200))
          .forEach((message) => message.remove());
        S.offset = Number(
          $(".chat-message", mount)?.id.replace("message-", "") || S.offset,
        );
      }
    }
    const diagnosis = $("[data-session-diagnostics]", mount);
    if (following && diagnosis && data.diagnostics && !diagnosis.querySelector("details[open]")) {
      const html = sessionDiagnostics(data.diagnostics);
      if (diagnosis.dataset.signature !== html) {
        const holder = document.createElement("template");
        holder.innerHTML = html;
        const replacement = holder.content.firstElementChild;
        replacement.dataset.signature = html;
        LiveDOM.replace(diagnosis,replacement.outerHTML);
      }
    }
    refreshConversationDiagnostics(epoch);
    const pager = $(".pager", mount),
      first = S.offset + 1;
    if (pager)
      LiveDOM.update(pager,`<span>${fmt(live.total)} messages · ${status(data.status)} · Showing ${first}–${live.next}</span><div class="actions">${btn("← Previous", "conversation-page", `data-offset="${Math.max(0, S.offset - 25)}" ${S.offset === 0 ? "disabled" : ""}`)}${btn("Next →", "conversation-page", `data-offset="${live.next}" ${live.next >= live.total ? "disabled" : ""}`)}</div>`);
    const banner = $("#conversation-live-status");
    if (banner) LiveDOM.update(banner,conversationLiveStatus(live, following));
    if (scrollWithMessages && data.messages.length) animateConversationTail();
    const chrome = $("#run-chrome");
    if (chrome) LiveDOM.update(chrome,runHeader(S.detail));
    if (!scrollWithMessages)
      pane.scrollTop = preservedScroll;
    return true;
  } finally {
    live.refreshing = false;
  }
}
let conversationScrollTimer;
document.addEventListener(
  "scroll",
  event => {
    if (event.target.id !== "conversation-scroll") return;
    const pane = event.target;
    const live = S.liveConversation;
    if (live) {
      if (conversationAnimation == null && pane.scrollTop < (live.lastScrollTop ?? pane.scrollTop) - 2)
        live.userPaused = true;
      live.lastScrollTop = pane.scrollTop;
    }
    clearTimeout(conversationScrollTimer);
    conversationScrollTimer = setTimeout(async () => {
      const live = S.liveConversation;
      if (
        live?.userPaused &&
        pane.scrollHeight - pane.scrollTop - pane.clientHeight < 4
      )
        live.userPaused = false;
      if (
        S.tab !== "conversation" ||
        !S.follow ||
        !live?.armed ||
        live.userPaused ||
        live.next >= live.total ||
        !nearConversationEnd() ||
        $(".chat-message details[open]")
      )
        return;
      try {
        await refreshLiveConversation(S.epoch);
      } catch (error) {
        /* Retry on the next live update. */
      }
    }, 150);
  },
  { passive: true, capture: true },
);

function conversation(data, append = false) {
  if (!append) conversationValues = [];
  const failure = data.failure;
  return (
    (failure
      ? notice(
          `<strong>${e(text(data.status))}</strong><p>${e(failure.message)}</p><small>${e(failure.phase)} · ${date(failure.at)}${failure.diagnostics?.endpoint ? " · " + e(failure.diagnostics.endpoint) : ""}${failure.diagnostics?.request_id ? " · Request ID: " + e(failure.diagnostics.request_id) : ""}${failure.retryable ? " · Retryable API error" : ""}${failure.uncertain ? " · Check billing before resuming" : ""}</small>`,
          "error",
        )
      : "") +
    (failure?.diagnostics ? `<details><summary>Provider error details</summary><pre>${e(pretty(failure.diagnostics))}</pre></details>` : "") +
    sessionDiagnostics(data.diagnostics) +
    (data.failure_event
      ? `<details class="provider-output" data-provider-event="${data.failure_event.id}" data-record-run="${e(S.run)}"><summary>Provider response or failure record</summary><pre></pre></details>`
      : "") +
    (data.generation > 0
      ? `<div class="toolbar">${badge(`Round ${data.generation + 1} · ` + text(data.condition), "blue")}${btn(`Round ${data.generation + 1} instruction`, "conversation-page", `data-offset="${data.instruction_index}"`)}${data.history_policy === "fresh-round" ? "" : btn("Initial history", "conversation-page", 'data-offset="0"')}</div>`
      : "") +
    `<div class="pager"><span>${fmt(data.total)} messages · ${status(data.status)}${data.offset + data.messages.length < data.total ? " · More messages on the next page" : ""}</span><div class="actions">${btn("← Previous", "conversation-page", `data-offset="${Math.max(0, S.offset - 25)}" ${S.offset === 0 ? "disabled" : ""}`)}<span>${data.total ? S.offset + 1 : 0}-${Math.min(data.total, S.offset + 25)}</span>${btn("Next →", "conversation-page", `data-offset="${S.offset + 25}" ${S.offset + 25 >= data.total ? "disabled" : ""}`)}</div></div>` +
    data.messages
      .map((m, index) => {
        const absolute = data.offset + index,
          native = m.native;
        const content =
          m.output_text ??
          (m.role === "user"
            ? m.model_text ?? m.content
            : m.role === "tool"
              ? pretty(m.result)
              : typeof native?.content === "string"
                ? native.content
                : Array.isArray(native?.content)
                  ? native.content
                      .filter((v) => v.type === "text")
                      .map((v) => v.text)
                      .join("\n")
                  : native?.parts
                    ? native.parts
                        .filter((v) => v.text && !v.thought)
                        .map((v) => v.text)
                        .join("\n")
                    : m.content || "");
        const direction =
          m.arena_finalization ? 'Arena · Preparation closed' : m.output_continuation ? 'Arena → Model · Continue output' :
          m.role === "user"
            ? `Arena → Model · ${generationLabel(m.generation ?? (absolute >= data.instruction_index ? data.generation : 0))}${m.condition ? " · " + text(m.condition) : ""}`
            : m.role === "tool"
              ? `Tool → Model · ${m.name}`
              : `${data.model || "Model"} → Arena`;
        const resultError =
          m.role === "tool" &&
          (m.tool_error || m.result?.error || m.result?.valid === false);
        const display = data.timeline?.[index] || {};
        const calls = (m.output_blocks ? [] : m.tool_calls || [])
          .map(
            (call, n) =>
              `<section class="tool-call" id="call-${absolute}-${n}"><strong>Model → Tool · ${e(call.name)}</strong><small>Call ${n + 1} in this response${call.id ? " · " + e(call.id) : ""}</small>${conversationData(call.arguments, "Tool arguments")}</section>`,
          )
          .join("");
        const snippet = String(content || "").slice(0, 1800);
        return `${data.generation > 0 && absolute === data.instruction_index ? `<div class="notice"><strong>Round ${data.generation + 1} starts here · ${e(text(data.condition))}</strong></div>` : ""}<article class="chat-message ${e(m.role)} ${resultError ? "tool-error" : ""}" id="message-${absolute}"><div class="message-head"><strong>${e(direction)}${m.simulated ? " · predefined strategy" : ""}</strong><span>Message ${absolute + 1} · ${data.times?.[index] ? date(data.times[index]) : "Time not recorded"}</span></div>${display.reply_to != null ? `<p class="message-reply">Result of tool request in message ${display.reply_to + 1}${display.reply_to >= S.offset && display.reply_to < S.offset + 25 ? ` · <a href="#message-${display.reply_to}" data-action="message-anchor" data-index="${display.reply_to}">Go to request</a>` : ""}${m.call_id ? " · " + e(m.call_id) : ""}</p>` : ""}${resultError ? badge("Tool error", "red") : ""}${callPerformance(m)}${snippet ? `<div class="message-content">${e(snippet)}${m.output_text_truncated || content.length > 1800 ? "\n[Preview truncated; open the full record below.]" : ""}</div>` : m.role === "assistant" && calls ? '<p class="muted">The model requested tools without a text response.</p>' : ""}${m.briefing && !m.model_text ? `<div class="game-brief"><strong>Game briefing sent to the model</strong><p>${e(m.briefing.game)}</p><p>${e(m.briefing.objective)}</p><p>${e(m.briefing.team_mode)}</p></div>` : ""}${m.role === "user" ? feedbackView(m.feedback) : ""}${calls}${fileExchange(m, absolute)}${providerOutput(m, absolute)}${m.model_text ? conversationData(m.model_text,m.briefing_readable_view ? "Complete readable briefing (historical raw request retained)" : "Complete gameplay briefing sent to the model") : m.role === "user" && !m.arena_finalization && !m.output_continuation ? conversationData(Object.fromEntries(Object.entries(m).filter(([key]) => !["role", "content", "request_recorded", "request_seed"].includes(key))), m.generation ? "Full improvement instruction and supplied feedback" : "Scenario, roster, ID guide and preparation rules sent to the model") : ""}${m.usage ? `<small>Input ${fmt(m.usage.input_tokens)} · Output ${fmt(m.usage.output_tokens)} · Cost ${money(m.cost_usd)} · Response took ${fmt(m.elapsed_seconds, 3)} s</small>` : ""}${m.request_metrics ? `<small>Context: ${fmt(m.request_metrics.history_messages)} messages · ${fmt(m.request_metrics.request_characters)} request characters · ${fmt(m.request_metrics.request_setup_seconds, 2)} s local request setup${m.usage?.output_tokens != null && m.elapsed_seconds > 0 ? ` · ${fmt(m.usage.output_tokens / m.elapsed_seconds, 2)} output tokens/s including input processing and API waits` : ""}</small>` : ""}${(m.adapter_notes || []).map(note => `<small>${e(note)}</small>`).join("")}${m.request_recorded ? `<p class="muted">Reasoning requested: ${e(reasoningLabel(m.request_reasoning))} · Sent seed: ${e(m.request_seed ?? "not set")}${m.stop_reason ? " · Stop reason: " + e(m.stop_reason) : ""}</p>` : ""}<details data-message-record="${absolute}" data-record-run="${e(S.run)}" data-record-session="${e(S.session)}"><summary>Full record: exact request, native response and metadata</summary><pre></pre></details></article>`;
      })
      .join("")
  );
}
document.addEventListener(
  "toggle",
  async (event) => {
    const node = event.target;
    if (
      !node.open ||
      node.dataset.loaded ||
      !node.matches(
        "details[data-conversation-value], details[data-message-record], details[data-output-block], details[data-provider-event], details[data-file-exchange]",
      )
    )
      return;
    node.dataset.loaded = "true";
    const output = $("pre", node);
    try {
      if (node.dataset.fileExchange != null) {
        const record = await api("/api/tool-exchange", {
          run: node.dataset.recordRun,
          session: node.dataset.recordSession,
          index: node.dataset.fileExchange,
        });
        if (record.name === "write_file") {
          const note = document.createElement("p");
          note.textContent = record.saved
            ? record.before_known
              ? "Changes compared with the previous saved version."
              : "No previous content was recorded. The diff below shows the captured write as added content."
            : "This write was rejected; the proposed content was not saved.";
          node.insertBefore(note, output);
          output.className = "code-diff";
          output.innerHTML = (record.diff || "No text changes.")
            .split("\n")
            .map(
              (line) =>
                `<span class="diff-line ${line.startsWith("+") && !line.startsWith("+++") ? "add" : line.startsWith("-") && !line.startsWith("---") ? "remove" : "meta"}">${e(line)}</span>`,
            )
            .join("\n");
          const complete = document.createElement("details"),
            title = document.createElement("summary"),
            pre = document.createElement("pre");
          title.textContent = "Complete written file";
          pre.textContent = record.after || "";
          complete.append(title, pre);
          node.append(complete);
        } else
          output.textContent =
            record.content ?? record.error ?? "No content was returned.";
      } else if (node.dataset.outputBlock != null) {
        output.textContent = "Loading recorded output...";
        const block = await api("/api/message-output", {
          run: node.dataset.recordRun,
          session: node.dataset.recordSession,
          index: node.dataset.outputMessage,
          block: node.dataset.outputBlock,
        });
        output.textContent =
          typeof block.value === "string" ? block.value : pretty(block.value);
      } else if (node.dataset.providerEvent != null) {
        const record = await api("/api/event", {
          run: node.dataset.recordRun,
          id: node.dataset.providerEvent,
        });
        output.textContent = pretty(record);
      } else if (node.dataset.messageRecord != null) {
        output.textContent = "Loading exact record...";
        const record = await api("/api/message", {
          run: node.dataset.recordRun,
          session: node.dataset.recordSession,
          index: node.dataset.messageRecord,
        });
        output.textContent = pretty(record.message);
      } else
        { const value=conversationValues[Number(node.dataset.conversationValue)];output.textContent=typeof value==='string'?value:pretty(value); }
    } catch (error) {
      output.textContent = error.message;
      delete node.dataset.loaded;
    }
  },
  true,
);
function codePage(data) {
  if (!data.versions.length)
    return empty(
      "No files written yet",
      "Versions appear after successful file writes. Frozen sources are also available under Files.",
    );
  S.version = Math.min(
    S.version ?? data.versions.length - 1,
    data.versions.length - 1,
  );
  const current = data.versions[S.version];
  S.file = current.files.includes(S.file) ? S.file : current.files[0];
  return (
    notice(
      "Each successful source write or team configuration creates a version in the journal. Improved versions include inherited initial history. Git is not required in participant folders.",
    ) +
    `<div class="code-grid"><section class="panel"><h3>File write history</h3><div class="version-list">${data.versions.map((v) => `<button class="version-button ${v.index === S.version ? "active" : ""}" data-action="version" data-version="${v.index}"><strong>Version ${v.index + 1} <span class="timeline-tag">${generationLabel(v.generation)}</span></strong>${e(v.path)}<small>${v.saved_strategy ? "Frozen saved strategy" : v.inherited_round ? `Inherited from Round ${v.inherited_round}` : `After message ${v.message + 1}`} · ${v.files.length} files</small></button>`).join("")}</div></section><section class="panel"><div class="toolbar"><select id="source-file" aria-label="File">${current.files.map((f) => `<option ${f === S.file ? "selected" : ""}>${e(f)}</option>`).join("")}</select><span class="spacer"></span>${current.message >= 0 ? btn("Open conversation", "version-message", `data-message="${current.message}"`) : badge(current.saved_strategy ? "Frozen saved strategy" : `Starting files · Round ${current.inherited_round}`)}</div><div class="toolbar"><label for="source-previous">Compare with</label><select id="source-previous"><option value="-1">Empty state</option>${data.versions
      .slice(0, S.version)
      .map(
        (v) =>
          `<option value="${v.index}" ${v.index === (S.previous ?? S.version - 1) ? "selected" : ""}>Version ${v.index + 1} · ${generationLabel(v.generation)}</option>`,
      )
      .join(
        "",
      )}</select></div><div id="source-content" data-live-preserve>Loading...</div></section></div>`
  );
}
async function loadSource(liveUpdate=false) {
  const epoch = S.epoch,
    v = S.version,
    filename = S.file,
    previous = S.previous;
  const d = await api("/api/source", {
    run: S.run,
    session: S.session,
    version: v,
    file: S.file,
    previous: S.previous ?? v - 1,
  });
  if (
    epoch !== S.epoch ||
    v !== S.version ||
    filename !== S.file ||
    previous !== S.previous ||
    !$("#source-content")
  )
    return;
  const sourceHTML =
    `<h3>Code at version ${v + 1}</h3><pre class="source">${e(d.after)}</pre><details open><summary>Changes from the selected version</summary><pre class="source">${
      d.diff
        ? d.diff
            .split("\n")
            .map(
              (l) =>
                `<span class="diff-line ${l.startsWith("+") && !l.startsWith("+++") ? "add" : l.startsWith("-") && !l.startsWith("---") ? "remove" : l.startsWith("@@") ? "meta" : ""}">${e(l)}</span>`,
            )
            .join("")
        : "No changes in this file."
    }</pre></details><small class="mono">SHA-256 : ${e(d.sha256)}</small>`;
  if(liveUpdate)LiveDOM.update($('#source-content'),sourceHTML);else $('#source-content').innerHTML=sourceHTML;
  $('#source-content').liveLoaded=true;
}
function filesPage() {
  const filter=$('#file-search')?.value?.toLowerCase()||'';
  return `<div class="files-grid"><section class="panel"><h3>Experiment files</h3><input id="file-search" type="search" placeholder="Filter paths..." aria-label="Filter files" style="width:100%;margin-bottom:12px"><label class="check"><input id="engine-files" type="checkbox">Include static engine data</label><small>${fmt(S.files.length)} available files</small><div id="file-list" class="file-list">${fileButtons(S.files.filter(file=>file.path.toLowerCase().includes(filter)))}</div></section><section class="panel"><div id="file-title" data-live-preserve class="panel-title"></div><div id="file-content" data-live-preserve>Select a file.</div></section></div>`;
}
function fileButtons(files) {
  if (!$("#engine-files")?.checked) files = files.filter((f) => !f.engine_data);
  return (
    files
      .slice(0, 1500)
      .map(
        (f) =>
          `<button class="file-button ${S.file === f.path ? "active" : ""}" data-action="file" data-path="${e(f.path)}">${e(f.path)} <small>· ${fmt(f.size / 1024, 1)} Ko</small></button>`,
      )
      .join("") +
    (files.length > 1500 ? "<small>Filter to find more files.</small>" : "")
  );
}
async function loadFile(path, liveUpdate=false) {
  S.file = path;
  const epoch = S.epoch;
  const titleHTML =
    `<h3 class="mono" style="overflow-wrap:anywhere">${e(path)}</h3>${/\.(md|json)$/i.test(path) ? `<div class="actions">${btn("Raw", "file-mode", 'data-mode="raw"')}${btn("Rendered", "file-mode", 'data-mode="rendered"')}</div>` : ""}<a class="button small" href="/api/file?${query({ run: S.run, path, download: 1 })}" download>Download</a>`;
  if(liveUpdate)LiveDOM.update($('#file-title'),titleHTML);else $('#file-title').innerHTML=titleHTML;
  const response = await fetch("/api/file?" + query({ run: S.run, path }));
  const content = await response.text();
  if (epoch !== S.epoch || S.file !== path) return;
  S.filePreview = {
    path,
    content: response.ok ? content : JSON.parse(content).error || content,
  };
  renderFileView(liveUpdate);
  $$(".file-button").forEach((n) =>
    n.classList.toggle("active", n.dataset.path === path),
  );
}
function eventsPage(data) {
  return `<section class="panel"><h2>Event log</h2><p class="muted">Calls, responses, reservations, tools and evaluations. Opening an event checks its artifact hash.</p><div class="toolbar">${modelPicker(S.detail, true)}<label for="event-session">Conversation</label><select id="event-session"><option value="">All conversations</option>${S.detail.sessions
    .filter((s) => !S.modelFilter || s.model === S.modelFilter)
    .map(
      (s) =>
        `<option value="${e(s.id)}" ${S.session === s.id ? "selected" : ""}>${e(s.model)} · ${e(sessionLabel(s))}</option>`,
    )
    .join(
      "",
    )}</select><span class="muted">${fmt(data.total)} events</span></div>${table(
    ["N°", "Timestamp", "Model / conversation", "Type", ""],
    data.events.map(
      (v) =>
        `<tr><td>${v.id}</td><td>${date(v.at)}</td><td>${e(S.detail.sessions.find((s) => s.id === v.session)?.model || "Competition")}<small>${e(strategyName(v.session))}</small></td><td><code>${e(v.kind)}</code></td><td>${btn("View artifact", "event", `data-id="${v.id}"`)}${S.detail.sessions.some((s) => s.id === v.session) ? btn("Open conversation", "session-conversation", `data-session="${e(v.session)}"`) : ""}</td></tr>`,
    ),
  )}<div class="pager"><span>Events ${data.total ? S.offset + 1 : 0}-${Math.min(data.total, S.offset + 100)}</span><div class="actions">${btn("← Previous", "event-page", `data-offset="${Math.max(0, S.offset - 100)}" ${S.offset === 0 ? "disabled" : ""}`)}${btn("Next →", "event-page", `data-offset="${S.offset + 100}" ${S.offset + 100 >= data.total ? "disabled" : ""}`)}</div></div></section>`;
}
function stageText(stage) {
  const previous=String(stage).match(/^evaluations\/g(\d+)-previous$/);
  if(previous)return `Round ${Number(previous[1])+1} vs Round ${Number(previous[1])} (unscored)`;
  const stageRound = String(stage).match(
    /^(?:g(\d+)-tournament|evaluations\/g(\d+)-panel)$/,
  );
  if (stageRound)
    return `Round ${Number(stageRound[1] ?? stageRound[2]) + 1}: ${stageRound[1] ? "tournament" : "reference evaluation"}`;
  return (
    {
      ".": "Tournament",
      tournament: "Round 1: tournament",
      "g1-tournament": "Round 2: tournament",
      "evaluations/g0-panel": "Round 1: reference evaluation",
      "evaluations/g1-panel": "Round 2: reference evaluation",
      préparation: "Preparation tests (unscored)",
      training: "Preparation tests (unscored)",
    }[stage] || stage
  );
}
function matchCategory(match,kind) {
  if(kind==='all')return true;
  if(kind==='selfplay')return !!match.mirror;
  if(!kind||kind==='competition')return match.kind==='competition'&&!match.mirror;
  if(kind==='progression')return match.kind==='progression'||match.previous_round_comparison;
  return match.kind===(kind||'competition');
}
function matchSubset() {
  const f = S.matchFilters || {};
  return S.matches.filter((m) => {
    const kind =
      m.kind ||
      (m.stage === "training" || m.stage === "préparation"
        ? "training"
        : m.stage.startsWith("evaluations/")
          ? "evaluation"
          : "competition");
    if (!matchCategory({...m,kind},f.kind)) return false;
    if (f.stage && m.stage !== f.stage) return false;
    if (f.scored && m.mirror) return false;
    if (f.exclude_same_model && overviewIdentity(m.sides[0]).model===overviewIdentity(m.sides[1]).model) return false;
    let scopedSide = null;
    if (f.entrant_model || f.opponent_model || f.round || f.track) {
      const candidates = overviewEntries(m).filter(
        (item) =>
          (!f.entrant_model || item.model===f.entrant_model) &&
          (!f.round || f.round==='all' || item.generation+1===Number(f.round)) &&
          (!f.track || item.condition===f.track) &&
          (kind!=='training' || S.detail.sessions.some(session=>session.id===item.id)) &&
          (!f.opponent_model ||
            overviewIdentity(m.sides[1 - item.side]).model ===
              f.opponent_model),
      );
      if (!candidates.length) return false;
      scopedSide = candidates[0].side;
    }
    if (f.entrant && !m.sides.includes(f.entrant)) return false;
    if (
      f.opponent &&
      (!m.sides.includes(f.opponent) ||
        (f.entrant && !m.sides.some((id, side)=>id===f.entrant && m.sides[1-side]===f.opponent)))
    )
      return false;
    if (
      f.search &&
      !`${m.sides.join(" ")} ${m.seed}`
        .toLowerCase()
        .includes(f.search.toLowerCase())
    )
      return false;
    const completed = m.result.status === "completed",
      side = scopedSide ?? (f.entrant ? (m.candidate === f.entrant && m.candidate_side != null ? m.candidate_side : m.sides.indexOf(f.entrant)) : 0);
    if (f.outcome === "failure") return !completed;
    if (f.outcome === "completed") return completed;
    if (f.outcome === "draw") return completed && m.result.winner_side === -1;
    if (f.outcome === "win") return completed && m.result.winner_side === side;
    if (f.outcome === "loss")
      return (
        completed &&
        m.result.winner_side !== -1 &&
        m.result.winner_side !== side
      );
    return true;
  });
}
function matchesPage() {
  const f = S.matchFilters ||= {};
  if(String(f.round||'').startsWith('stage:')) {f.stage=f.round.slice(6);f.round='all';}
  // Preserve precise old matrix links, while exposing independent model/round filters.
  const oldRound=String(f.round||'').match(/^g(\d+)-(control|feedback)$/);
  if(oldRound) {f.round=String(Number(oldRound[1])+1);f.track=oldRound[2];}
  if(f.round==='initial')f.round='1';
  if(['control','feedback'].includes(f.round)) {f.track=f.round;f.round='2';}
  const branchRound=String(f.round||'').match(/^(\d+):(control|feedback)$/);
  if(branchRound) {f.round=String(Number(branchRound[1])+1);f.track=branchRound[2];}
  if(f.stage) {const stage=String(f.stage).match(/g(\d+)-(?:tournament|panel)/);if(!f.round)f.round=stage?String(Number(stage[1])+1):'all';}
  if(f.entrant && !f.entrant_model) {const identity=overviewIdentity(f.entrant);f.entrant_model=identity.model;if(!f.round)f.round=String(identity.generation+1);}
  if(f.opponent && !f.opponent_model)f.opponent_model=overviewIdentity(f.opponent).model;
  const participants=[...new Set(S.matches.flatMap(match=>match.sides).map(id=>overviewIdentity(id).model))].sort();
  const rounds=[...new Set([...S.detail.sessions.map(session=>Number(session.generation||0)+1),...S.matches.flatMap(match=>match.sides.map(id=>overviewIdentity(id).generation+1))])].sort((a,b)=>a-b);
  const rows = matchSubset();
  const categoryTotal = S.matches.filter(
    (m) => matchCategory(m,f.kind),
  ).length;
  const trainingCount = S.matches.filter((m) => m.kind === "training").length;
  S.matchPath =
    rows.find((m) => m.path === S.matchPath)?.path || rows[0]?.path || null;
  return `<details class="fight-category-guide"><summary>Which fights count toward standings?</summary>${fightPurposeGuide()}<p>Self-play means the same strategy and team on both sides (A vs A); it is a diagnostic. Swapping two different strategies (A vs B, then B vs A) is standard tournament play and both fights count. Engine failures (process timeout, crash or unreadable output) are unscored and retried when the fight pool runs again, including Resume. Their logs are available in the fight details. Preparation tests are separate and unscored. Self-play outcome filters refer to the blue side.</p></details>${trainingCount ? `<p id="training-count">${trainingCount} preparation tests stored separately. ${btn("View preparation tests", "show-training")}</p>` : ""}${selectField(
    "Match category",
    "match-kind",
    [
      ["competition", "Ranked tournament fights"],
      ["selfplay", "Self-play diagnostics (A vs A, unscored)"],
      ["training", "Preparation tests (unscored)"],
      ["evaluation", "Fixed-baseline evaluations (unscored)"],
      ["progression", "Previous-round comparisons (unscored)"],
      ["all", "All fights"],
    ],
    f.kind || "competition",
  )}<div id="match-origin-scope">${f.stage ? notice('Stage selected from overview: '+e(stageText(f.stage))) : ''}${f.entrant || f.opponent ? notice(`Exact versions selected from the matrix: ${e(strategyName(f.entrant||'Any participant'))} vs ${e(strategyName(f.opponent||'Any opponent'))}. Changing the filters below selects models across versions.`) : ''}</div><div class="match-filters">${field("Search", "match-search", f.search || "", "search", "", 'id="match-search"')}${selectField('Model','match-model',[['','All models'],...participants.map(model=>[model,model])],f.entrant_model||'')}${selectField('Opponent model','match-opponent-model',[['','All opponents'],...participants.map(model=>[model,model])],f.opponent_model||'')}${selectField('Round','match-round',[['all','All rounds'],...(rounds.length?rounds:[1]).map(round=>[String(round),'Round '+round])],f.round||'all')}${selectField('Track','match-track',[['','All tracks'],['initial','Initial'],['control','No feedback'],['feedback','With feedback']],f.track||'')}${selectField(
    f.kind==='selfplay'?"Outcome for blue side":"Outcome for selected participant (otherwise blue side)",
    "match-outcome",
    [
      ["", "All outcomes"],
      ["win", "Wins"],
      ["draw", "Draws"],
      ["loss", "Losses"],
      ["failure", "Engine failures (unscored)"],
      ["completed", "Completed"],
    ],
    f.outcome || "",
  )}<div class="actions">${btn("Clear filters", "clear-match-filters")}<span id="match-filter-count" class="muted">${rows.length} / ${categoryTotal} matches in this category</span></div></div>${S.matches.length ? `<div class="match-layout"><div id="match-list" class="match-list">${matchButtons(rows)}</div><section class="panel" id="match-detail" data-live-preserve>${rows.length ? "Loading match..." : !categoryTotal && f.kind==='selfplay'?empty("No self-play diagnostics", "No optional A-vs-A diagnostics were recorded for this competition.") : !categoryTotal && (!f.kind || f.kind === "competition") ? empty("No competition matches yet", "Models may still be preparing their strategies.", btn("View preparation tests", "show-training")) : empty("No matches found", "Change or clear the filters.")}</section></div>` : empty("No competition matches yet", "Models may still be preparing their strategies.", btn("View preparation tests", "show-training"))}`;
}
function matchButtons(rows) {
  return (
    rows
      .slice(0, 800)
      .map(
        (m) =>
          `<button class="match-card ${m.path === S.matchPath ? "active" : ""}" data-action="match" data-path="${e(m.path)}"><span class="badge ${m.stage.includes("panel") ? "blue" : ""}">${e(stageText(m.stage))}</span>${m.result.reference_cache?.hit?badge("Cached reference","green"):""}${m.mirror?badge("Self-play · unscored","orange"):m.kind==='evaluation'?badge("Fixed baseline · unscored","blue"):m.kind==='progression'?badge("Previous round · unscored","blue"):m.kind === "training" ? badge("Preparation · unscored", "orange") : ""}<strong>${e(strategyName(m.sides[0]))}<br><span class="muted">vs</span> ${e(strategyName(m.sides[1]))}</strong><small>Seed ${e(m.seed)} · ${m.result.status === "completed" ? (m.result.winner_side === -1 ? "Draw" : "Winner: " + (m.mirror?(m.result.winner_side===0?"Blue side":"Orange side"):e(strategyName(m.sides[m.result.winner_side])))) : e(text(m.result.status))}</small></button>`,
      )
      .join("") +
    (rows.length > 800 ? "<small>Filter to find more matches.</small>" : "")
  );
}
async function matchSourceDialog(path,side) {
  const run=S.run,epoch=S.epoch;
  clearInterval(replayTimer);replayTimer=null;
  if($('#replay-play'))$('#replay-play').textContent='▷';
  const source=await api('/api/match/source',{run,path,side});
  if(epoch!==S.epoch||run!==S.run)return;
  const match=S.matches.find(match=>match.path===path);
  S.matchSource={path,side};
  openDialog('Executed code',`${side===0?'Blue':'Orange'} · ${strategyName(match?.sides[side]||'Unknown')}`,
    `<p>The archived files used in this fight, including preparation tests. Editing a current workspace does not change this snapshot.</p>${selectField('Source file','executed-source-file',source.files.map(file=>[file,file]),source.path)}<pre class="source" id="executed-source-content">${e(source.content)}</pre><small class="mono" id="executed-source-hash">SHA-256: ${e(source.sha256)}</small>`);
}
function fightTimingView(result, record={}) {
  const timing=result.timings||{};
  const rows=[['Scenario & source snapshots',timing.scenario_and_sources_seconds],['Engine data staging',timing.data_staging_seconds],['Java process',timing.java_process_seconds],['Reading & hashing result',timing.result_read_seconds],['Data cleanup',timing.data_cleanup_seconds],['Reference cache lookup & copy',timing.cache_reuse_seconds],['Worker pipeline',record.work_seconds??timing.fight_wall_seconds],['Artifact verification',record.verification_seconds],['Waiting for publication',record.publication_wait_seconds]].filter(([,value])=>Number.isFinite(value));
  if(!rows.length)return '';
  return `<details class="quiet-details"><summary>Execution timing</summary>${table(['Phase','Seconds'],rows.map(([name,value])=>`<tr><td>${e(name)}</td><td>${fmt(value,3)}</td></tr>`))}${timing.data_hardlinked_files!=null?`<small>${timing.data_hardlinked_files} engine data files linked · ${timing.data_copied_files||0} copied · ${fmt((timing.data_copied_bytes||0)/1048576,2)} MB copied</small>`:''}</details>`;
}
async function loadMatch() {
  clearInterval(replayTimer);
  replayTimer = null;
  const path = S.matchPath,
    epoch = S.epoch,
    data = await runResource("/api/match", { run: S.run, path });
  if (epoch !== S.epoch || S.matchPath !== path) return;
  const row = S.matches.find((m) => m.path === path),
    result = data.result;
  const sources=(await api('/api/match/sources',{run:S.run,path})).sources;
  if(epoch!==S.epoch||S.matchPath!==path)return;
  $("#match-detail").innerHTML =
    `<div class="panel-title"><div><h2>${result.status === "completed" ? (result.winner_side === -1 ? "Draw" : "Winner: " + (row.mirror?(result.winner_side===0?"Blue side":"Orange side"):e(strategyName(row.sides[result.winner_side])))) : e(text(result.status))}</h2><small>Seed ${e(row.seed)} · ${result.turns == null ? "N/A turns" : countLabel(result.turns, "turn")} · ${fmt(result.elapsed_seconds, 2)} s</small></div>${status(result.status)}</div>${row.kind === "progression" ? notice('Previous-round comparison. Diagnostic only: no tournament points and not sent as model feedback.') : row.kind === "training" ? notice("Preparation test requested by the model. Editable scripts; excluded from competition standings and matrices.", "warn") : row.kind==='evaluation'?notice("Fixed-baseline evaluation: a submitted strategy faces frozen Round 1 opponents or fixed scripts. Used to measure progress; excluded from standings and model feedback."):row.mirror?'':notice("Frozen strategies: these scripts cannot change during this round.")}${result.reference_cache?.hit?notice("Cached fixed-reference fight: exact scripts, teams, scenario, seed and engine settings were reused. This occurrence did not execute the engine."):""}${row.mirror ? notice("Self-play diagnostic: identical strategy and team on both sides. Excluded from standings and model feedback; inspect the replay for side advantages and runtime behavior.") : ""}<div class="replay-sources">${row.sides.map((id,side)=>`<div><strong>${side===0?'Blue':'Orange'} · ${e(strategyName(id))}</strong>${sources.find(source=>source.side===side)?.available?btn('View executed code','match-source',`data-side="${side}" data-path="${e(path)}"`):'<small>No archived source available</small>'}${S.detail.sessions.some(session=>session.id===id)?`<a class="button" href="#${query({view:'run',run:S.run,tab:'code',session:id})}">Code history</a>`:''}</div>`).join('')}</div>${
      data.replay
        ? `<div class="replay-legend">${Object.entries(row.sides)
            .map(
              ([side, id]) =>
                `<p style="border-left:6px solid ${Number(side) === 0 ? "#5278e5" : "#c77749"};padding-left:10px"><strong>Side ${Number(side) + 1} · ${Number(side) === 0 ? "Blue" : "Orange"}</strong>: ${e(strategyName(id))}</p>`,
            )
            .join(
              "",
            )}</div><svg id="replay-board" class="board" role="img" aria-label="Match map and entity positions"></svg><div class="replay-controls">${btn("▷", "replay-play", 'id="replay-play" aria-label="Play or pause"')}${btn("←", "replay-prev", 'aria-label="Previous action"')}<input id="replay-range" type="range" min="0" max="${data.replay.events.length}" value="0" aria-label="Replay position">${btn("→", "replay-next", 'aria-label="Next action"')}<select id="replay-speed" aria-label="Playback speed"><option value="400">× 1</option><option value="150">× 2</option><option value="50">× 4</option></select></div><div class="toolbar"><strong id="replay-label" style="font-size:11px"></strong><span class="spacer"></span><span id="replay-count" class="muted" style="font-size:10px"></span></div><div id="replay-entities" class="entity-list"></div><div id="replay-events" class="event-list"></div><p class="muted" style="font-size:10px;margin-top:13px">${e(data.replay.note)}${data.replay.unknown_codes.length ? " Actions not visualized: " + e(data.replay.unknown_codes.join(", ")) + "." : ""}</p>`
        : notice(
            e(result.error || "No replay is available for this match."),
            "warn",
          )
    }${data.statistics ? combatStatistics(data.statistics) : ""}${fightTimingView(result,S.matches.find(match=>match.path===path)?.timings||{})}${raw(result, "Full metrics: computation, errors and result")}${data.scenario ? raw(data.scenario, "Exact match scenario") : ""}${raw(data.provenance, "Strategies, hashes and provenance")}${data.outcome ? raw(data.outcome, "Full raw replay, actions and logs") : ""}`;
  $('#match-detail').liveLoaded=true;
  S.combatStatistics = data.statistics;
  $$(".match-card").forEach((n) =>
    n.classList.toggle("active", n.dataset.path === path),
  );
  if (data.replay) {
    R = {
      ...data.replay,
      fight: data.outcome.fight,
      index: 0,
      cache: new Map(),
    };
    R.cellsById = new Map(R.cells.map((c) => [c.id, c]));
    R.initial = {
      entities: Object.fromEntries(
        R.fight.leeks.map((l) => [
          l.id,
          { ...l, maxLife: l.life, born: !l.summon, alive: !l.summon },
        ]),
      ),
      actor: null,
      turn: 1,
      last: null,
    };
    R.cache.set(0, structuredClone(R.initial));
    renderReplay(0);
  }
}
function replayState(index) {
  const checkpoint = Math.floor(index / 100) * 100,
    start = R.cache.has(checkpoint) ? checkpoint : 0;
  const state = structuredClone(R.cache.get(start) || R.initial),
    entity = (id) => state.entities[id];
  for (let i = start; i < index; i++) {
    const ev = R.events[i],
      a = ev.raw,
      code = a[0];
    state.last = ev;
    state.turn = ev.turn;
    if (code === 7) state.actor = a[1];
    if (code === 10 && entity(a[1])) entity(a[1]).cellPos = a[2];
    if ([101, 108, 109, 110, 111].includes(code) && entity(a[1])) {
      entity(a[1]).life = Math.max(0, entity(a[1]).life - a[2]);
      if (a[3]) entity(a[1]).maxLife = Math.max(0, entity(a[1]).maxLife - a[3]);
    }
    if (code === 107 && entity(a[1]))
      entity(a[1]).maxLife = Math.max(1, entity(a[1]).maxLife - a[2]);
    if (code === 103 && entity(a[1]))
      entity(a[1]).life = Math.min(
        entity(a[1]).maxLife,
        entity(a[1]).life + a[2],
      );
    if (code === 104 && entity(a[1])) {
      entity(a[1]).life += a[2];
      entity(a[1]).maxLife += a[2];
    }
    if (code === 112 && entity(a[1])) entity(a[1]).maxLife += a[2];
    if (code === 5 && entity(a[1])) {
      entity(a[1]).alive = false;
      entity(a[1]).life = 0;
    }
    if (code === 9 && entity(a[2]) && a[4] === 1) {
      entity(a[2]).cellPos = a[3];
      entity(a[2]).alive = true;
      entity(a[2]).born = true;
      entity(a[2]).summoner = a[1];
    }
    if (code === 105 && entity(a[2]))
      Object.assign(entity(a[2]), {
        cellPos: a[3],
        life: a[4],
        maxLife: a[5],
        alive: true,
        born: true,
      });
    if ((i + 1) % 100 === 0) R.cache.set(i + 1, structuredClone(state));
  }
  return state;
}
function renderReplay(index) {
  if (!R || !$("#replay-board")) return;
  index = Math.max(0, Math.min(R.events.length, index));
  R.index = index;
  const state = replayState(index),
    entities = Object.values(state.entities),
    obstacles = R.fight.map.obstacles || {};
  const xmax = Math.max(...R.cells.map((c) => c.x)),
    ymax = Math.max(...R.cells.map((c) => c.y));
  $("#replay-board").setAttribute(
    "viewBox",
    `-20 -24 ${xmax + 40} ${ymax + 48}`,
  );
  const shot =
      state.last && [12, 16].includes(state.last.code)
        ? R.cellsById.get(state.last.raw[state.last.code === 12 ? 2 : 1])
        : null,
    actor = state.entities[state.actor],
    origin = actor ? R.cellsById.get(actor.cellPos) : null;
  $("#replay-board").innerHTML =
    R.cells
      .map(
        (c) =>
          `<polygon class="tile ${obstacles[c.id] ? "obstacle" : ""}" points="${c.x - 12},${c.y} ${c.x},${c.y - 6} ${c.x + 12},${c.y} ${c.x},${c.y + 6}"><title>Cell ${c.id}${obstacles[c.id] ? " · obstacle" : ""}</title></polygon>`,
      )
      .join("") +
    (shot && origin
      ? `<line x1="${origin.x}" y1="${origin.y}" x2="${shot.x}" y2="${shot.y}" stroke="#df8f45" stroke-width="2" stroke-dasharray="3 2"/>`
      : "") +
    entities
      .filter((v) => v.born)
      .map((v) => {
        const c = R.cellsById.get(v.cellPos);
        if (!c) return "";
        const color = v.team === 1 ? "#5278e5" : "#c77749";
        return `<g data-entity="${v.id}" data-summon="${!!v.summon}" class="${v.alive ? "" : "dead"}"><ellipse cx="${c.x}" cy="${c.y + 2}" rx="10" ry="5" fill="${color}" opacity=".18"/>${state.actor === v.id ? `<circle cx="${c.x}" cy="${c.y - 5}" r="10" fill="none" stroke="${color}" stroke-width="1"/>` : ""}${v.summon ? `<rect x="${c.x - 6}" y="${c.y - 11}" width="12" height="12" rx="2" fill="${color}"/>` : `<circle cx="${c.x}" cy="${c.y - 5}" r="7" fill="${color}"/>`}<text class="entity-label" x="${c.x}" y="${c.y - 5}">${v.id}</text><rect x="${c.x - 9}" y="${c.y - 16}" width="18" height="2" rx="1" fill="#cdd6e7"/><rect x="${c.x - 9}" y="${c.y - 16}" width="${18 * Math.max(0, Math.min(1, v.life / (v.maxLife || 1)))}" height="2" rx="1" fill="${color}"/><title>${e(v.name)} · ${v.life}/${v.maxLife} HP · cell ${v.cellPos}</title></g>`;
      })
      .join("");
  $("#replay-range").value = index;
  $("#replay-label").textContent = state.last
    ? `Turn ${state.turn} · ${state.last.text}`
    : "Initial positions";
  $("#replay-count").textContent = `Action ${index} / ${R.events.length}`;
  $("#replay-entities").innerHTML = entities
    .filter((v) => v.born)
    .map(
      (v) =>
        `<div class="entity-card"><strong style="color:${v.team === 1 ? "#5278e5" : "#c77749"}">${v.summon ? "◆ Summon · " : "● "}${e(v.name)} (#${v.id})</strong><span style="float:right">${v.life} / ${v.maxLife} HP</span><div class="hp-track"><div class="hp-fill" style="width:${Math.max(0, Math.min(100, (100 * v.life) / (v.maxLife || 1)))}%;background:${v.team === 1 ? "#5278e5" : "#c77749"}"></div></div></div>`,
    )
    .join("");
  $("#replay-events").innerHTML = R.events
    .slice(Math.max(0, index - 20), Math.min(R.events.length, index + 30))
    .map(
      (ev, i) =>
        `<button class="event-line ${ev.index === index - 1 ? "active" : ""}" data-action="replay-step" data-index="${Math.max(0, index - 20) + i + 1}"><span class="mono">${ev.index + 1}</span> · T${ev.turn} · ${e(ev.text)} <span class="muted mono">${e(pretty(ev.raw))}</span></button>`,
    )
    .join("");
  if (index === R.events.length) {
    clearInterval(replayTimer);
    replayTimer = null;
    $("#replay-play").textContent = "▷";
  }
}
function playReplay() {
  if (!R) return;
  if (replayTimer) {
    clearInterval(replayTimer);
    replayTimer = null;
    $("#replay-play").textContent = "▷";
    return;
  }
  if (R.index === R.events.length) renderReplay(0);
  $("#replay-play").textContent = "Ⅱ";
  replayTimer = setInterval(
    () => renderReplay(R.index + 1),
    Number($("#replay-speed").value),
  );
}
function comparePage() {
  const runs = scoped(S.boot.runs).filter((r) => !r.archived && !r.error),
    selected = S.compareSelection || [];
  return (
    head("Compare results", "Comparison by model and competition protocol.") +
    `<section class="panel"><h2>Select competitions</h2><p class="muted">Complete experiments are compared against fixed opponents.</p><div class="comparison-select">${runs.map((r) => `<label class="choice"><input type="checkbox" name="compare-run" value="${e(r.id)}" ${selected.includes(r.id) ? "checked" : ""}><span><strong>${e(r.name)}</strong><small>${date(r.created_at)} · ${r.simulated ? "simulation" : r.simulated === false ? "Real API calls" : "Tournament"}</small></span></label>`).join("")}</div><div class="form-footer">${btn("Compare selected runs", "compare-selection", "", true)}</div></section><div id="comparison-result">${S.comparison ? comparisonResult(S.comparison) : notice("Mock runs and API runs form separate groups. Exports are not counted twice.")}</div>`
  );
}
function lineChart(group) {
  const runs = [
    ...new Map(group.series.map((p) => [p.run, p.created_at])).entries(),
  ].sort((a, b) => a[1] - b[1]);
  if (!runs.length) return "";
  const series = new Map(),
    labels = new Map();
  for (const p of group.series) {
    if (p.score == null || p.failed) continue;
    const key = `${p.model_signature}/g${p.generation}/${p.condition}`;
    labels.set(
      key,
      `${p.model} · ${generationLabel(p.generation)} ${text(p.condition)} · ${p.model_id}`,
    );
    if (!series.has(key)) series.set(key, new Map());
    const data = series.get(key);
    if (!data.has(p.run)) data.set(p.run, []);
    data.get(p.run).push(p.score);
  }
  const W = 780,
    H = 260,
    L = 48,
    T = 20,
    B = 215,
    right = 745,
    X = (i) =>
      L +
      (runs.length === 1
        ? (right - L) / 2
        : (i * (right - L)) / (runs.length - 1)),
    Y = (v) => B - v * (B - T);
  const chart = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Score history across competitions">${[0, 0.25, 0.5, 0.75, 1].map((v) => `<line x1="${L}" x2="${right}" y1="${Y(v)}" y2="${Y(v)}" stroke="#e9edf5"/><text x="0" y="${Y(v) + 4}">${v * 100} %</text>`).join("")}${runs.map(([id, t], i) => `<text x="${X(i)}" y="240" text-anchor="middle">${e(new Date(t * 1000).toLocaleDateString("en-US"))}<title>${e(id)}</title></text>`).join("")}${[
    ...series,
  ]
    .map(([key, data], j) => {
      const label = labels.get(key),
        points = runs.map(([id], i) => {
          const values = data.get(id);
          return values
            ? {
                id,
                x: X(i),
                y: Y(values.reduce((a, b) => a + b, 0) / values.length),
                v: values.reduce((a, b) => a + b, 0) / values.length,
              }
            : null;
        });
      return `<polyline points="${points
        .filter(Boolean)
        .map((p) => `${p.x},${p.y}`)
        .join(
          " ",
        )}" fill="none" stroke="${seriesColor(j)}" stroke-width="2" data-chart-model="${e(label)}" data-chart-label="${e(label)}"/>${points
        .filter(Boolean)
        .map(
          (p) =>
            `<circle cx="${p.x}" cy="${p.y}" r="4" fill="${seriesColor(j)}" tabindex="0" data-chart-model="${e(label)}" data-chart-label="${e(label)} · ${e(p.id)} · ${pct(p.v)}"><title>${e(label)} · ${e(p.id)} : ${pct(p.v)}</title></circle>`,
        )
        .join("")}`;
    })
    .join("")}</svg>`;
  return (
    `<div class="chart-filterable" data-chart-key="history:${e(JSON.stringify(group.protocol))}">`+chart +
    `<div class="chart-legend">${[...series.keys()].map((key, j) => `<span tabindex="0" data-chart-model="${e(labels.get(key))}"><i class="dot" style="background:${seriesColor(j)}"></i>${e(labels.get(key))}</span>`).join("")}</div></div>`
  );
}
function comparisonResult(data) {
  return (
    notice(e(data.explanation)) +
    data.groups
      .map(
        (g, i) =>
          `<section class="panel"><div class="panel-title"><div><h2>Comparison group ${i + 1}</h2><small>${g.runs.length} competitions; same rules, seeds and fixed opponents</small></div>${badge(g.protocol.simulated ? "Simulation" : "Real API calls", g.protocol.simulated ? "blue" : "orange")}</div>${lineChart(g)}<div style="margin-top:22px">${table(
            [
              "Model / condition",
              "Size (B)",
              "Mean score",
              "Included conversations",
              "Incomplete",
              "Competitions",
              "API cost",
              "Input / output",
              "Errors",
            ],
            g.models.map(
              (m) =>
                `<tr><td><strong>${e(m.model)}</strong><small>${e(m.participant?.provider)} · ${e(m.participant?.model || m.participant?.profile)}</small>${raw(m.participant, "Participant configuration")}<small>${generationLabel(m.generation)} · ${text(m.condition)}</small></td><td>${fmt(m.participant?.model_size_billion,3)}</td><td class="score">${pct(m.score)}</td><td>${m.conversations}</td><td>${m.excluded}</td><td>${m.runs}</td><td>${money(m.cost_usd)}</td><td>${fmt(m.input_tokens)} / ${fmt(m.output_tokens)}</td><td>${fmt(m.errors)}</td></tr>`,
            ),
          )}</div>${raw(g, "Individual points and group protocol")}</section>`,
      )
      .join("") +
    (data.excluded.length
      ? `<section class="panel"><h2>Excluded competitions</h2>${data.excluded.map((r) => `<div class="info-row"><strong>${e(r.run)}</strong><span>${e(r.reason)}</span></div>`).join("")}</section>`
      : "") +
    (!data.groups.length
      ? empty(
          "No comparable group for this selection",
          "Select an initial and improved strategies experiment with a completed fixed-opponent evaluation.",
        )
      : "")
  );
}
function helpPage() {
  return (
    head("Help", "Experiment design, scoring and recorded data.") +
    `<section class="panel"><h2>Documentation</h2><div class="actions">${btn("Interface guide", "reference", 'data-document="ui"')}${btn("API providers and pricing", "reference", 'data-document="providers"')}${btn("Strategy authoring", "reference", 'data-document="authoring"')}${btn("Game rules", "reference", 'data-document="rules"')}${btn("Realistic stats", "reference", 'data-document="stats"')}${btn("API usage guide", "reference", 'data-document="api-guide"')}${btn("LeekScript API reference", "reference", 'data-document="api"')}</div></section>` +
    `<div class="help-grid">${[
      [
        "Participants and conversations",
        "A profile selects a provider, exact model, parameters and prices. Each repetition starts an independent conversation and produces LeekScript 4 code.",
      ],
      [
        "Initial and improved strategies",
        "Later rounds continue two tracks from their submitted files. The feedback track can inspect previous tournament results; the no-feedback track cannot.",
      ],
      [
        "Scores and panels",
        "A win earns 1 point, a draw 0.5 and a loss 0. Scores average completed ranked matches; self-play is excluded. The full reference panel includes frozen initial strategies and fixed handwritten controls.",
      ],
      [
        "Mock participants",
        "Mocks follow predefined scripts. Compilation, diagnostics and Java matches are real, but the generated strategies do not measure LLM performance.",
      ],
      [
        "Preparation limits and quality benchmarks",
        "A model call is one API response; tool calls are the requested actions such as writing code or testing a team. New competitions have no arena preparation limits. Leave optional limits blank to compare final strategy quality and measure the resources each model actually uses. Existing configurations and demos retain their limits.",
      ],
      [
        "Team building and equipment",
        "Shared mode fixes the team and equipment for all participants. Participant mode lets each model choose up to the maximum team size, a script per member, weapons and chips. Members can have different stats; realistic mode validates each capital allocation. Allowlists, slots and member level restrict equipment. In realistic mode, RAM also sets chip capacity; weapon capacity is 2 below level 100, 3 below 200, then 4. Competition caps can only reduce these capacities. Successful configure_team calls create team.json versions, inherited by improvement branches. The item selector shows the pinned player equipment catalog; items above the leek level are locked in realistic mode. Weapon IDs use the catalog item field; chip IDs use catalog keys. Replay events use template IDs.",
      ],
      [
        "Costs and tokens",
        "Prices are dated USD rates per million tokens. Costs use reported usage. Missing usage stays unknown. Reservations are estimates, not confirmed provider bills.",
      ],
      [
        "File history",
        "Successful tool writes create versions. Failed proposals remain in the conversation but do not create versions. Submitted sources are frozen.",
      ],
      [
        "Match replay",
        "The schematic replay shows positions, attacks, HP, healing and deaths. Some effects are not animated. Raw engine events remain available.",
      ],
      [
        "Match matrix",
        "Click wins, draws, losses or failures to open matching fights. Scores link to completed fights. Filters include stage, participant, opponent and outcome. Wins and losses use the row participant as the reference, regardless of its match side.",
      ],
      [
        "Comparing competitions",
        "Scores against fixed opponents are averaged per complete conversation. Different scenarios, seeds, engines, budgets or mock/real modes form separate groups.",
      ],
      [
        "Stop and resume",
        "Stopping keeps checkpoints. Resume verifies code, engine, sources and settings. Calls with unknown outcomes require billing reconciliation. Clone a configuration to start a different run.",
      ],
      [
        "Model seeds",
        "OpenAI and Gemini accept seeds on supported models. Anthropic does not expose a seed. A seed does not guarantee identical output. Compare the full recorded request, not just the system prompt.",
      ],
      [
        "Local files and keys",
        "UI settings and logs are in .arena/ui; results are in runs. Keys entered in the UI stay in server memory until shutdown. Keys supplied through environment variables remain managed by your system.",
      ],
    ]
      .map(
        ([title, body]) =>
          `<section class="panel"><h2>${title}</h2><p class="muted">${body}</p></section>`,
      )
      .join("")}</div>`
  );
}
document.addEventListener("click", async (event) => {
  const node = event.target.closest("[data-action]");
  if (!node || node.disabled) return;
  event.preventDefault();
  const a = node.dataset.action;
  try {
    if (a === 'participant-groups' || a === 'new-participant-group') participantGroupDialog();
    else if (a === 'edit-participant-group') participantGroupDialog(node.dataset.id);
    else if (a === 'profile-groups') profileGroupsDialog(node.dataset.id);
    else if (a === 'delete-participant-group') {
      const group=S.boot.participant_groups.find(g=>g.id===node.dataset.id);
      openDialog('Delete group',group.name,`<p>Profiles and competition selections are kept.</p><form data-form="delete-participant-group" data-id="${e(group.id)}"><div class="form-footer">${btn('Cancel','close-dialog')}<button type="submit" class="button primary">Delete group</button></div></form>`);
    } else if (a === 'group-select-visible' || a === 'group-clear-visible') {
      for(const row of $$('.group-member:not([hidden])'))$('input',row).checked=a==='group-select-visible';
    } else if (a === 'add-competition-group') {
      const id=$('[name=participant_group]', $('#competition-form')).value;
      const group=S.boot.participant_groups.find(g=>g.id===id);
      if(!group)throw Error('Choose a participant group first.');
      let added=0;
      for(const checkbox of $$('#competition-form input[name=participant]'))if(group.members.includes(checkbox.value)&&!checkbox.checked){checkbox.checked=true;added++;}
      updateCompetitionSelection();
      $('#group-selection-status').textContent=`${added} added from ${group.name}. ${$$('#competition-form input[name=participant]:checked').length} participants selected.`;
    } else if (a === 'clear-competition-participants') {
      for(const checkbox of $$('#competition-form input[name=participant]'))checkbox.checked=false;
      updateCompetitionSelection();
      $('#group-selection-status').textContent='No participants selected.';
    } else if (a === 'new-workspace') workspaceDialog();
    else if (a === 'edit-workspace') workspaceDialog(node.dataset.id);
    else if (a === 'open-workspace') await chooseWorkspace(node.dataset.id);
    else if (a === 'reload-workspace') await renderRoute();
    else if (a === 'workspace-members') workspaceMembers(node.dataset.id);
    else if (a === 'workspace-select-visible' || a === 'workspace-clear-visible') {
      for(const row of $$('.workspace-member:not([hidden])'))$('input',row).checked=a==='workspace-select-visible';
    }
    else if (a === 'move-workspace') {
      const row=S.boot.runs.find(r=>r.id===node.dataset.run);
      openDialog('Move competition',row.name,`<form data-form="move-workspace" data-run="${e(row.id)}">${selectField('Workspace','workspace_id',workspaceOptions(),row.workspace_id||'')}<button type="submit" class="button primary">Move</button></form>`);
    } else if (a === 'delete-workspace') {
      openDialog('Delete workspace',workspaceName(node.dataset.id),`<p>Competitions and configurations will become unassigned. Their files and results are kept.</p><form data-form="delete-workspace" data-id="${e(node.dataset.id)}"><div class="form-footer">${btn('Cancel','close-dialog')}<button type="submit" class="button primary">Delete workspace</button></div></form>`);
    } else if (a === 'providers' || a === 'new-provider') providersDialog();
    else if (a === 'edit-provider') providersDialog(node.dataset.id);
    else if (a === 'provider-models') {node.disabled=true;try{await providerModels(node.dataset.id);}finally{node.disabled=false;}}
    else if (a === 'delete-provider') {await api('/api/provider/delete',{id:node.dataset.id},true);await refreshBoot();providersDialog();}
    else if (a === "go") navigate(node.dataset.view);
    else if (a === "character-tab") {
      $$("[data-member-build]").forEach((card) => {
        card.hidden = card.dataset.memberBuild !== node.dataset.index;
      });
      $$(".character-tabs button").forEach((button) => {
        const selected = button === node;
        button.setAttribute("aria-pressed", String(selected));
        button.classList.toggle("primary", selected);
      });
    } else if (a === "reference") {
      const document = await api("/api/reference", {
        document: node.dataset.document,
      });
      openDialog(
        document.title,
        "Repository documentation",
        `<div class="markdown">${markdownView(document.content)}</div>`,
      );
    } else if (a === "refresh") {
      runReadCache.clear();S.detailFetchedAt=0;
      await refreshBoot();
      await renderRoute();
      toast("Data refreshed.");
    } else if (a === "new-participant") participantDialog();
    else if (a === "list-models") {
      const form = node.closest("form"),
        f = new FormData(form);
      node.disabled = true;
      try {
        const data = await api(
          "/api/models",
          {
            provider: f.get("provider"),
            api_key_env: f.get("api_key_env"),
            secret: f.get("secret") || null,
            endpoint: f.get("endpoint") || null,
          },
          true,
        );
        if (!form.isConnected) return;
        S.catalogModels = data.models;
        $("#available-models").hidden = false;
        $("#model-search-field").hidden = false;
        $("#model-search").value = "";
        renderModelCatalog();
        const excluded = data.excluded || [];
        $("#excluded-models").hidden = !excluded.length;
        $("#excluded-model-list").innerHTML = excluded
          .map((m) => `<p><code>${e(m.id)}</code><br>${e(m.reason)}</p>`)
          .join("");
        $("#model-list-status").textContent =
          `${data.models.length} candidate models listed by this API key · ${excluded.length} incompatible models excluded${data.truncated ? " · partial catalog" : ""}. Catalog visibility does not guarantee chat/tool access; no generation request was made.`;
      } catch (error) {
        if (form.isConnected)
          $("#model-list-status").textContent =
            error.message + "; manual entry is available.";
      } finally {
        node.disabled = false;
      }
    } else if (a === "select-model") {
      node.closest("form").elements.model.value = node.dataset.model;
      $("#model-search").value = node.dataset.model;
      renderModelCatalog();
    } else if(a==='test-model') {
      openDialog('Test model',node.dataset.id,`<p>One small request per test. May incur API charges; usage and cost are saved separately from competitions.</p><div class="actions">${btn('Connection · 16 output tokens','run-model-test',`data-id="${e(node.dataset.id)}" data-mode="text"`)}${btn('Tools · 128 output tokens','run-model-test',`data-id="${e(node.dataset.id)}" data-mode="tools"`)}</div><div id="model-test-result" role="status"></div>`);
    } else if(a==='run-model-test') {
      const buttons=$$('[data-action=run-model-test]');buttons.forEach(button=>button.disabled=true);
      const resultElement=$('#model-test-result');resultElement.textContent='Waiting for the provider…';
      try {
        const result=await api('/api/model-test',{id:node.dataset.id,mode:node.dataset.mode},true);
        if(resultElement.isConnected)resultElement.innerHTML=`<p><strong>${e(result.accepted?'API accepted the request':result.error)}</strong></p><p>${Number(result.seconds).toFixed(2)} s · Output cap ${result.output_cap} · Cost ${result.cost_usd==null?'unknown':'$'+e(result.cost_usd)}${result.mode==='tools'?' · '+(result.tool_call_returned?'Tool call received':'No tool call returned at this output cap'):''}</p><details><summary>Usage and diagnostics</summary><pre>${e(pretty(result))}</pre></details>`;
      } finally {buttons.forEach(button=>button.disabled=false);}
    } else if (a === "edit-participant") participantDialog(node.dataset.id);
    else if (a === "delete-participant") {
      await api("/api/participant/delete", { id: node.dataset.id }, true);
      await refreshBoot();
      await renderRoute();
      toast("Profile removed. Existing competitions keep their settings.");
    } else if (a === "close-dialog") {
      $("#dialog").close();
      S.logJob = null;
    } else if (a === "new-competition" || a === "new-demo") {
      if(node.dataset.workspace)setWorkspace(node.dataset.workspace);
      S.editDraft = null;
      S.editConfig =
        a === "new-demo" ? structuredClone(S.boot.demo_config) : freshConfig();
      navigate("editor");
      if (S.view === "editor") await renderRoute();
    } else if (
      a === "preset-simple" ||
      a === "preset-dream" ||
      a === "preset-dream-json" ||
      a === "preset-dream-refresh" ||
      a === "preset-llm"
    ) {
      const config = readCompetition($("#competition-form"));
      node.disabled = true;
      try {
        if (a === "preset-simple")
          config.scenario = structuredClone(S.boot.default_config.scenario);
        else if (a === "preset-llm")
          config.scenario = structuredClone(S.boot.participant_scenario);
        else {
          $("#preset-status").textContent =
            a === "preset-dream-refresh"
              ? "Refreshing the saved public team…"
              : "Loading the saved Dream team preset…";
          const args =
            a === "preset-dream-json"
              ? { snapshot: JSON.parse($("#dream-snapshot").value) }
              : a === "preset-dream-refresh"
                ? { refresh: true }
                : {};
          config.scenario = (await api("/api/dream-team", args, true)).scenario;
        }
        S.editConfig = config;
        await renderRoute();
      } catch (error) {
        $("#preset-status").textContent =
          error.message + ". The current roster was kept.";
        throw error;
      } finally {
        node.disabled = false;
      }
    } else if (a === "edit-draft") {
      const d = S.boot.drafts.find((d) => d.id === node.dataset.id);
      S.editDraft = d.id;
      S.editConfig = structuredClone(d.config);
      navigate("editor");
    } else if (a === 'expand-activity') {
      const details=$('#competition-activity-details');
      if(details){details.open=true;$('summary',details).focus();}
    } else if (a === "delete-draft") {
      const draft=S.boot.drafts.find(d=>d.id===node.dataset.id);
      if(!draft)throw new Error('Saved configuration no longer exists.');
      openDialog('Delete competition configuration?',draft.config.name,
        `<p>This permanently deletes this saved configuration and its settings. Existing runs, conversations, strategies and match results are kept.</p><form data-form="delete-draft" data-id="${e(draft.id)}"><div class="form-footer">${btn('Cancel','close-dialog')}<button type="submit" class="button danger">Delete configuration</button></div></form>`);
      $('#dialog .form-footer [data-action="close-dialog"]').focus();
    } else if (a === "clone-run") {
      S.editDraft = null;
      S.editConfig = structuredClone(S.detail.metadata.config);
      S.editConfig.name += " (copy)";
      navigate("editor");
    } else if (a === "preview-plan") {
      const config = readCompetition($("#competition-form")),
        p = await api("/api/plan", { config }, true);
      $("#plan-preview").innerHTML = planMarkup(p);
    } else if (a === "import-config") {
      const config = JSON.parse($("#import-config").value);
      await api("/api/plan", { config }, true);
      S.editConfig = config;
      $("#main").innerHTML = competitionEditor();
      updateStatPreviews();
      toast("Configuration imported. Review before saving.");
    } else if (a === "show-training")
      navigate("run", { run: S.run, tab: "matches", kind: "training" });
    else if (a === 'show-engine-failures')
      navigate('run',{run:S.run,tab:'matches',kind:'all',stage:node.dataset.stage,outcome:'failure'});
    else if (a === "launch") await launchDialog(node.dataset.id);
    else if (a === "edit-run-participants") await runParticipantsDialog();
    else if (a === "run-metric-collection") runMetricCollectionDialog();
    else if (a === 'live-fight-workers') {
      const workers=S.activity?.requested_parallel_fights??S.detail.execution_control?.parallel_fights??S.detail.roster?.parallel_fights??S.detail.metadata.config?.parallel_fights??1;
      openDialog('Fight workers','Apply during execution, without Stop / Resume.',`<form data-form="live-fight-workers">${field('Simultaneous fights','parallel_fights',workers,'number','Lowering this value lets current fights finish; new jobs use the new limit. No upper cap.','required min="1" step="1"')}<div class="form-footer">${btn('Cancel','close-dialog')}<button type="submit" class="button primary">Apply now</button></div></form>`);
    }
    else if (a === 'retry-failed-fights') {
      await api('/api/run/retry-fights',{run:S.run},true);toast('Engine fight retries requested. Model conversations are not restarted.');await refreshBoot();
    }
    else if(a==='provider-limits') {
      const data=await api('/api/run/provider-limits',{run:S.run});
      S.providerLimitEndpoints=data.endpoints;
      openDialog('Provider concurrency','Applies while this competition runs',`<form data-form="provider-limits"><p>Maximum simultaneous API requests per endpoint, shared by all its models and repetitions. Local endpoints default to one. Blank means only the competition-wide limit applies. Existing requests finish normally.</p>${data.endpoints.map((item,index)=>field(item.endpoint,'endpoint-'+index,item.limit??'','number',item.models.join(', '),'min="1" step="1"')).join('')}<div class="form-footer">${btn('Cancel','close-dialog')}<button type="submit" class="button primary">Save limits</button></div></form>`);
    }
    else if(a==='toggle-automatic-retries') {
      const paused=node.dataset.paused==='true';
      await api('/api/conversation/retry-policy',{run:S.run,session:node.dataset.session,paused},true);
      toast(paused?'Automatic retries paused. Any current request can finish.':'Automatic retries enabled. Continue now to retry immediately.');
      await renderRoute();
    }
    else if (a === "resume") await launchDialog(null, S.run);
    else if (a === "reconcile-session") reconciliationDialog(node.dataset.session);
    else if (a === 'recover-conversation' || a === 'restart-conversation') {
      if (a==='restart-conversation') {
        openDialog('Restart preparation',strategyName(node.dataset.session),`<p>Start a fresh conversation with an empty workspace for this round. Previous exchanges and files are archived. Active preparation statistics and session limits start afresh. Previous attempts remain archived; their API charges still count toward the shared spending limit. Other participants and completed competition fights are kept.</p><form data-form="restart-conversation" data-session="${e(node.dataset.session)}"><div class="form-footer">${btn('Cancel','close-dialog')}<button type="submit" class="button primary">Restart preparation</button></div></form>`);
      } else {
        await api('/api/conversation/recover',{run:S.run,session:node.dataset.session,action:'continue'},true);
        toast(node.textContent.includes('Finalize')?'Finalization queued. No further request will be sent for this preparation.':'Continuation queued. Other conversations keep running.');await refreshBoot();
      }
    }
    else if (a === "retry-session") await retryDialog(node.dataset.session);
    else if (a === "open-run") navigate("run", { run: node.dataset.run });
    else if (a === "tab")
      navigate("run", {
        run: S.run,
        tab: node.dataset.tab,
        session: S.session,
        model: S.modelFilter,
      });
    else if (a === "conversation-journal")
      navigate("run", {
        run: S.run,
        tab: "events",
        model: S.modelFilter,
        session: S.session,
      });
    else if (a === "test-provider") {
      openDialog("Test provider API", "One billed request; returned tools are never executed.",
        `<form data-form="provider-probe" data-session="${e(node.dataset.session)}"><label>Request<select name="mode"><option value="minimal">Minimal prompt + one simple tool</option><option value="current">Current prompt + full arena tool set</option></select></label><p>Stop the competition first if it is running. Uses this conversation's saved model and reasoning settings. Output is capped at 1,024 tokens. Usage and charges count toward the existing limits; files, history and submitted strategies are preserved.</p><label class="check"><input type="checkbox" name="confirm_paid" required>I authorize this billed API diagnostic.</label><div class="form-footer">${btn("Cancel", "close-dialog")}<button class="button primary" type="submit">Run API test</button></div></form>`);
    }
    else if (a === 'copy-scheduling-diagnostics') {
      const data=await api('/api/schedule-audit',{run:S.run,generation:S.activity?.round?S.activity.round-1:undefined});
      const content=pretty(data);
      try {await navigator.clipboard.writeText(content);toast('Scheduling diagnostics copied.');}
      catch {openDialog('Scheduling diagnostics','Submitted strategies, scheduled fights and saved results.',`<textarea readonly class="mono" rows="18">${e(content)}</textarea>`);}
    }
    else if (a === "copy-provider-diagnostics" || a === "copy-usage-diagnostics") {
      const data = a === "copy-usage-diagnostics" ? {
        run: S.run,
        models: (S.detail.metadata.config?.models || []).map(m=>({id:m.id,provider:m.provider,model:m.model,pricing:m.pricing})),
        sessions: S.detail.sessions.map(s=>({id:s.id,model:s.model,status:s.status,calls:s.calls,
          input_tokens:s.input_tokens,output_tokens:s.output_tokens,token_usage_known:s.token_usage_known,
          cost_spent:s.cost_spent,money_reserved:s.money_reserved,in_flight:s.in_flight,usage_receipts:s.usage_receipts})),
      } : await api("/api/provider-diagnostics", {run:S.run, session:node.dataset.session});
      const content = pretty(data);
      let copied = false;
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(content);
          copied = true;
        }
      } catch (_) { /* Offer selectable text when clipboard access is denied. */ }
      if (copied) toast("Diagnostics copied. No keys or prompt contents included.");
      else openDialog("Provider diagnostics", "No keys or prompt contents included", `<textarea readonly rows="18">${e(content)}</textarea>`);
    }
    else if (a === "editor-section") {
      const section = document.getElementById(node.dataset.section);
      if (section?.tagName === "DETAILS") section.open = true;
      section?.scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block:"start"});
      section?.setAttribute("tabindex", "-1");
      section?.focus({preventScroll:true});
    }
    else if (a === "conversation-top") {
      cancelConversationAnimation();
      if (S.offset > 0) {
        S.offset = 0; S.explicitOffset = true;
        const url = new URL(location.href), q = new URLSearchParams(url.hash.slice(1));
        q.set("offset", "0"); url.hash = q.toString(); history.replaceState(null, "", url);
        await renderRun(S.epoch);
      }
      if (S.liveConversation) S.liveConversation.userPaused = true;
      $("#conversation-scroll")?.scrollTo({top:0, behavior:matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth"});
    }
    else if (a === "conversation-bottom") {
      if (S.liveConversation?.next < S.liveConversation?.total) {
        S.offset = 0; S.explicitOffset = false;
        await renderRun(S.epoch);
      }
      if (S.liveConversation) { S.liveConversation.armed = true; S.liveConversation.userPaused = false; }
      animateConversationTail();
    }
    else if (a === "conversation-latest") {
      await refreshLiveConversation(S.epoch, true);
    } else if (a === "session-diagnostics") {
      const data = await api("/api/session-diagnostics", {
        run: S.run,
        session: node.dataset.session,
      });
      openDialog(
        "Strategy diagnostics",
        strategyName(node.dataset.session),
        sessionDiagnostics(data, true),
      );
    } else if (a === 'saved-source') {
      $('#dialog').close(); navigate('run',{run:node.dataset.run,tab:'code',session:node.dataset.session});
    } else if (a === 'add-reference') {
      const catalog=await api('/api/reference-strategies');
      openDialog('Add reference strategy','Fixed weapons-only opponents',`<form data-form="reference-strategy">${selectField('Reference','reference',catalog.strategies.map(row=>[row.id,row.name]),'passive')}${field('Participant ID','id','reference-passive','text','','required pattern="[a-zA-Z0-9][a-zA-Z0-9_-]{0,39}"')}<p>Adapts to the competition scenario when added. Weapon scripts use its supplied equipment; they do not implement chip or summon tactics. These are practical baselines, not certified difficulty levels.</p>${catalog.strategies.map(row=>`<p><strong>${e(row.name)}</strong>: ${e(row.description)} ${row.source ? `<a href="${e(row.source)}" target="_blank" rel="noreferrer">Source (${e(row.license)})</a>` : ''}</p>`).join('')}<button type="submit" class="button primary">Add participant</button></form>`);
    } else if (a === "save-strategy") {
      const sid=node.dataset.session;
      openDialog('Save strategy as participant',strategyName(sid),`<form data-form="saved-strategy" data-session="${e(sid)}">${field('Participant ID','id',sid.slice(0,30)+'-fixed','text','Frozen submitted files and team; no LLM calls. Requires the original scenario.','required pattern="[a-zA-Z0-9][a-zA-Z0-9_-]{0,39}"')}<button type="submit" class="button primary">Save participant</button></form>`);
    } else if (a === "session-conversation")
      navigate("run", {
        run: S.run,
        tab: "conversation",
        session: node.dataset.session,
      });
    else if (a === "conversation-page" || a === "event-page")
      navigate("run", {
        run: S.run,
        tab: S.tab,
        session: S.session,
        model: S.modelFilter,
        offset: node.dataset.offset,
      });
    else if (a === "version") {
      S.version = Number(node.dataset.version);
      S.previous = null;
      await renderRun(S.epoch);
    } else if (a === "version-message")
      navigate("run", {
        run: S.run,
        tab: "conversation",
        session: S.session,
        model: S.modelFilter,
        offset: Math.floor(Number(node.dataset.message) / 25) * 25,
      });
    else if (a === "file-mode") {
      S.fileMode = node.dataset.mode;
      renderFileView();
    } else if (a === "file") await loadFile(node.dataset.path);
    else if (a === 'open-errors') navigate('run',{run:S.run,tab:'faults'});
    else if (a === 'match-source') await matchSourceDialog(node.dataset.path,Number(node.dataset.side));
    else if (a === "clear-match-filters")
      navigate("run", { run: S.run, tab: "matches" });
    else if (a === "overview-failures") {
      const detail = $("#overview-conversations");
      detail.open = true;
      detail.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (a === "match") {
      S.matchPath = node.dataset.path;
      await loadMatch();
    } else if (a === "replay-play") playReplay();
    else if (a === "replay-prev") renderReplay(R.index - 1);
    else if (a === "replay-next") renderReplay(R.index + 1);
    else if (a === "replay-step") renderReplay(Number(node.dataset.index));
    else if (a === "compare-selection") {
      const runs = $$("input[name=compare-run]:checked").map((n) => n.value);
      S.compareSelection = runs;
      S.comparison = await api("/api/aggregate", { runs }, true);
      $("#comparison-result").innerHTML = comparisonResult(S.comparison);
    } else if (a === "event") {
      const data = await api("/api/event", { run: S.run, id: node.dataset.id });
      openDialog(
        "Event " + node.dataset.id,
        "Artifact SHA-256 verified.",
        `<pre>${e(pretty(data))}</pre>`,
      );
    } else if (a === "export-run") {
      node.disabled = true;
      const result = await api("/api/export", { run: S.run }, true);
      await refreshBoot();
      toast("Export created: " + result.run);
    } else if (a === "stop-job") {
      await api("/api/stop", { id: node.dataset.id }, true);
      toast("Stop requested. Checkpoints are kept.");
    } else if (a === "copy-log") {
      const content = $("#job-log-live").textContent;
      if (navigator.clipboard?.writeText)
        await navigator.clipboard.writeText(content);
      else {
        const input = document.createElement("textarea");
        input.value = content;
        $("#dialog").append(input);
        input.select();
        const copied = document.execCommand("copy");
        input.remove();
        if (!copied)
          throw new Error(
            "Clipboard unavailable; select and copy the log text.",
          );
      }
      toast("Log copied");
    } else if (a === "message-anchor") {
      event.preventDefault();
      const message = $("#message-" + node.dataset.index), pane = $("#conversation-scroll");
      if (message && pane) {
        if (S.liveConversation) S.liveConversation.userPaused = true;
        pane.scrollTo({top:pane.scrollTop + message.getBoundingClientRect().top - pane.getBoundingClientRect().top - pane.clientHeight/2,
          behavior:matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth"});
      }
    } else if (a === "job-log") {
      S.logJob = node.dataset.id;
      const data = await api("/api/job", { id: S.logJob });
      openDialog(
        "Run log",
        `${data.job.name} · ${text(data.job.status)}`,
        `${btn("Copy log", "copy-log")}<pre id="job-log-live" class="run-log">${e(data.content || "Initialization...")}</pre><small>Last 128 KB of the log.</small>`,
      );
    }
  } catch (error) {
    showError(error);
  } finally {
    node.disabled = false;
  }
});
document.addEventListener("submit", async (event) => {
  if(event.target.dataset.form==='restart-conversation') {
    event.preventDefault();
    try {
      await api('/api/conversation/recover',{run:S.run,session:event.target.dataset.session,action:'restart'},true);
      $('#dialog').close();toast('Restart queued. Earlier files and usage are preserved.');await refreshBoot();
    } catch(error) {toast(error.message,true);}
    return;
  }

  const form = event.target;
  if (!form.dataset.form) return;
  event.preventDefault();
  const submit = event.submitter || $("button[type=submit]", form);
  if (submit) submit.disabled = true;
  try {
    const f = new FormData(form),
      type = form.dataset.form;
    if(type === 'participant-group') {
      const saved=await api('/api/participant-group',{id:form.dataset.id||null,name:f.get('name'),members:f.getAll('member')},true);
      await refreshBoot();await renderRoute();participantGroupDialog(saved.id);toast('Group saved.');
    } else if(type === 'profile-groups') {
      await api('/api/participant/groups',{participant:form.dataset.id,groups:f.getAll('group')},true);
      $('#dialog').close();await refreshBoot();await renderRoute();toast('Memberships saved.');
    } else if(type === 'delete-participant-group') {
      await api('/api/participant-group/delete',{id:form.dataset.id},true);
      await refreshBoot();await renderRoute();participantGroupDialog();toast('Group deleted. Profiles are kept.');
    } else if(type === 'workspace') {
      const saved=await api('/api/workspace',{id:form.dataset.id||null,name:f.get('name'),description:f.get('description')},true);
      $('#dialog').close();await refreshBoot();await chooseWorkspace(saved.id);toast('Workspace saved.');
    } else if(type === 'delete-draft') {
      await api('/api/competition/delete',{id:form.dataset.id},true);
      $('#dialog').close();await refreshBoot();await renderRoute();
      toast('Configuration removed. Runs were kept.');
    } else if(type === 'delete-workspace') {
      await api('/api/workspace/delete',{id:form.dataset.id},true);
      $('#dialog').close();setWorkspace('');await refreshBoot();await chooseWorkspace('');toast('Workspace deleted. Competitions are kept.');
    } else if(type === 'workspace-members') {
      await api('/api/workspace/members',{workspace_id:form.dataset.id,runs:f.getAll('runs'),drafts:f.getAll('drafts'),replace:true},true);
      $('#dialog').close();await refreshBoot();await renderRoute();toast('Workspace updated.');
    } else if(type === 'move-workspace') {
      await api('/api/workspace/members',{workspace_id:f.get('workspace_id')||null,runs:[form.dataset.run]},true);
      $('#dialog').close();await refreshBoot();await renderRoute();toast('Competition moved.');
    } else if (type === 'provider') {
      const spec={id:f.get('id'),provider:f.get('provider'),api_key_env:f.get('api_key_env')};
      if(f.get('endpoint'))spec.endpoint=f.get('endpoint');
      await api('/api/provider',{spec,secret:f.get('secret')||null},true);
      await refreshBoot();providersDialog(spec.id);
    } else if (type === 'provider-participants') {
      const models=f.getAll('selected').map(index=>{
        const input=f.get('input-'+index),output=f.get('output-'+index);
        if(input===''||output==='')throw Error('Enter input and output prices for every selected model. Use 0 for free/local models.');
        const row={id:f.get('id-'+index),model:S.providerModelCatalog[Number(index)].id,pricing:{currency:'USD',date:new Date().toISOString().slice(0,10),input_per_million:input,output_per_million:output}};
        if(f.has('max-'+index))row.max_output_tokens=Number(f.get('max-'+index));
        if(f.get('size-'+index))row.model_size_billion=Number(f.get('size-'+index));
        return row;
      });
      const result=await api('/api/provider/participants',{id:form.dataset.provider,models},true);
      await refreshBoot();$('#dialog').close();await renderRoute();toast(result.created.length+' participants created.');
    } else if (type === 'reference-strategy') {
      await api('/api/participant/reference',{reference:f.get('reference'),id:f.get('id')},true);
      await refreshBoot(); $('#dialog').close(); await renderRoute(); toast('Reference participant created');
    } else if (type === 'saved-strategy') {
      await api('/api/participant/import',{run:S.run,session:form.dataset.session,id:f.get('id')},true);
      await refreshBoot(); $('#dialog').close(); toast('Saved strategy participant created');
    } else if (type === "participant") {
      const provider = f.get("provider"),
        spec = { id: f.get("id"), provider };
      if (provider === "mock") spec.profile = f.get("profile");
      else {
        Object.assign(spec, {
          model: f.get("model"),
          api_key_env: f.get("api_key_env"),
          timeout_seconds: Number(f.get("timeout_seconds")),
          inactivity_timeout_seconds: Number(f.get("inactivity_timeout_seconds")),
          max_retries: Number(f.get("max_retries")),
          parameters: JSON.parse(f.get("parameters") || "{}"),
          pricing: {
            date: f.get("pricing_date"),
            currency: "USD",
            input_per_million: f.get("input_price"),
            output_per_million: f.get("output_price"),
          },
        });
        for (const key of ["max_input_tokens_per_call", "max_output_tokens", "model_size_billion"]) {
          if (String(f.get(key) || "").trim()) spec[key] = Number(f.get(key));
        }
        const effortField = form.elements.namedItem("reasoning_effort");
        if (effortField) {
          if (effortField.value) spec.parameters.reasoning_effort = effortField.value;
          else delete spec.parameters.reasoning_effort;
        }
        if (f.has("model_seed")) {
          if (f.get("model_seed") !== "")
            spec.parameters.seed = Number(f.get("model_seed"));
          else delete spec.parameters.seed;
        }
        if (f.get("endpoint")) spec.endpoint = f.get("endpoint");
        if (f.get("cached_price") !== "")
          spec.pricing.cached_input_per_million = f.get("cached_price");
        if (f.get("creation_price") !== "")
          spec.pricing.cache_creation_per_million = f.get("creation_price");
      }
      await api(
        "/api/participant",
        { spec, secret: f.get("secret") || null },
        true,
      );
      $("#dialog").close();
      await refreshBoot();
      await renderRoute();
      toast("Participant saved.");
    } else if (type === "competition") {
      const config = readCompetition(form);
      await api("/api/competition", { config, id: S.editDraft, workspace_id:f.get("workspace_id")||null }, true);
      if(S.workspace)setWorkspace(f.get('workspace_id')||'unassigned');
      await refreshBoot();
      navigate("competitions");
      toast("Configuration saved. No API calls made.");
    } else if (type === "provider-probe") {
      const result = await api("/api/provider-probe", {run:S.run,session:form.dataset.session,
        mode:f.get("mode"),confirm_paid:f.has("confirm_paid")},true);
      openDialog("API test result", result.accepted ? "Request accepted" : "Request rejected",
        `<textarea readonly rows="20">${e(pretty(result))}</textarea>`);
    } else if (type === "reconcile") {
      await api("/api/reconcile", {run:S.run, session:form.dataset.session,
        cost_usd:f.get("cost_usd"), note:f.get("note")}, true);
      $("#dialog").close();
      await renderRoute();
      toast("Billing recorded. Resume the competition or retry this conversation.");
    } else if(type==='provider-limits') {
      const endpoint_limits=Object.fromEntries(S.providerLimitEndpoints.map((item,index)=>[item.endpoint,f.get('endpoint-'+index)===''?null:Number(f.get('endpoint-'+index))]));
      await api('/api/run/provider-limits',{run:S.run,endpoint_limits},true);
      $('#dialog').close();toast('Provider concurrency limits saved. Running requests are kept; new requests use these limits.');
    } else if(type==='live-fight-workers') {
      const applied=await api('/api/run/execution',{run:S.run,parallel_fights:Number(f.get('parallel_fights'))},true);
      S.detail.execution_control=applied;
      $('#dialog').close();toast('Worker count requested; applies to the running fight pool.');await refreshBoot();await refreshCompetitionActivity();
    } else if (type === "run-metrics") {
      const selected=S.detail.roster?.active||S.detail.metadata.config.models.filter(model=>!S.detail.roster?.withdrawn.includes(model.id)).map(model=>model.id);
      await api('/api/run/participants',{run:S.run,participants:selected,compare_previous_round:f.has('compare_previous_round'),parallel_fights:Number(f.get('parallel_fights')),request_order:f.get('request_order'),parallel_requests:Number(f.get('parallel_requests'))},true);
      $('#dialog').close();await refreshBoot();await renderRoute();
      toast('Execution and metric settings saved. Resume to continue.');
    } else if (type === "run-participants") {
      const frozenTracks={};
      for(const track of ['control','feedback']) for(const id of f.getAll('freeze-'+track)) (frozenTracks[id] ||= []).push(track);
      await api('/api/run/participants',{run:S.run,participants:f.getAll('participant'),frozen_tracks:frozenTracks},true);
      $('#dialog').close();
      await refreshBoot();
      await renderRoute();
      toast('Participants saved. Resume this competition to continue.');
    } else if (type === "launch") {
      const launch = S.launch;
      const job = await api(
        "/api/launch",
        {
          draft_id: launch.draftId,
          run: launch.runId,
          retry_session: launch.retrySession,
          retry_reasoning_effort: launch.retrySession && form.elements.namedItem("reasoning_effort") ? (form.elements.namedItem("reasoning_effort").value || "provider-default") : undefined,
          allow_updated_runner: !!launch.runId,
          expected_config_sha256: launch.expectedHash,
          confirm_paid: f.has("confirm_paid"),
          ceiling: launch.config.spending.max_total_usd,
        },
        true,
      );
      $("#dialog").close();
      await refreshBoot();
      navigate("run", {
        run: job.run,
        ...(launch.retrySession
          ? { tab: "conversation", session: launch.retrySession }
          : {}),
      });
      toast(
        launch.retrySession
          ? "Retry started. Other submissions are preserved."
          : "Competition started.",
      );
    }
  } catch (error) {
    showError(error);
  } finally {
    if (submit) submit.disabled = false;
  }
});
document.addEventListener("change", async (event) => {
  const n = event.target;
  try {
    if(n.name==='executed-source-file') {
      const source=await api('/api/match/source',{run:S.run,...S.matchSource,file:n.value});
      if(n.isConnected && n.value===source.path) {$('#executed-source-content').textContent=source.content;$('#executed-source-hash').textContent='SHA-256: '+source.sha256;}
      return;
    }
    if(['fault_model','fault_round','fault_condition','fault_metric'].includes(n.name)) {
      S[{fault_model:'faultModel',fault_round:'faultRound',fault_condition:'faultCondition',fault_metric:'faultMetric'}[n.name]]=n.value;
      $('#faults-content').outerHTML=faultsPage();
      return;
    }
    if(n.matches('#competition-form input[name=participant]') || n.id==='competition-selected-only') {
      updateCompetitionSelection();
    } else if(n.matches('[data-resource-axis]')) {
      S.resourceMetric=n.value;const context=n.dataset.resourceAxis;clearChartHover();$('#'+context+'-resource-chart').innerHTML=renderResourceChart(context);
    } else if(n.matches('[data-resource-view]')) {
      S.resourceView=n.value;clearChartHover();$('#'+n.dataset.resourceView+'-resource-chart').innerHTML=renderResourceChart(n.dataset.resourceView);
    } else if(n.matches('[data-learning-mode],[data-learning-view]')) {
      const key=n.matches('[data-learning-mode]')?'progressionMode':'progressionView';overviewSettings()[key]=n.value;clearChartHover();
      LiveDOM.replace($('#learning-progress'),learningProgression(S.detail));
    } else if(n.matches('[data-evolution-view]')) {
      overviewSettings().evolution=n.value;clearChartHover();$('#overview-evolution-chart').innerHTML=n.value==='lines'?overviewEvolutionLines(overviewData(S.detail)):overviewEvolutionBars(overviewData(S.detail));
    } else if(n.name==='participant_group_filter') {
      S.participantGroup=n.value;refreshParticipantCards();
    } else if(n.id === 'workspace-picker') {
      await chooseWorkspace(n.value);
    } else if(n.id === 'workspace-group') {
      S.workspaceGroup=Number(n.value);$('#workspace-performance').innerHTML=workspacePerformance(S.workspaceSummary.groups[S.workspaceGroup]);
    } else if (n.name === 'saved_provider') {
      const spec=S.boot.providers.find(row=>row.spec.id===n.value)?.spec;
      participantDialog(null,spec?.provider||'mock',spec||null);
    } else if (n.name === 'reference'  && n.closest('[data-form=reference-strategy]')) {
      const id=n.form.elements.id;
      if (id.value.startsWith('reference-')) id.value='reference-'+n.value;
    } else if (n.name === "provider" && n.closest("[data-form=participant]")) {
      const old = [...new FormData(n.form)],
        provider = n.value;
      participantDialog(S.editParticipant, provider);
      for (const [key, value] of old) {
        if (["provider", "secret", "api_key_env", "model_seed"].includes(key))
          continue;
        const target = $(`[name="${key}"]`, $("#dialog"));
        if (target && !target.readOnly) target.value = value;
      }
      const env = $("[name=api_key_env]", $("#dialog"));
      if (env)
        env.value =
          provider === "anthropic"
            ? "ARENA_ANTHROPIC_KEY"
            : provider === "gemini"
              ? "ARENA_GEMINI_KEY"
              : "ARENA_OPENAI_KEY";
    } else if (n.matches(".equipment-check")) {
      const picker = n.closest(".equipment-picker");
      const checked = $$(".equipment-check:checked", picker).map((el) =>
        Number(el.value),
      );
      const previous = String(n.form.elements[picker.dataset.name].value)
        .split(",")
        .filter((id) => id.trim())
        .map(Number);
      const ids = [
        ...previous.filter((id) => checked.includes(id)),
        ...checked.filter((id) => !previous.includes(id)),
      ];
      n.form.elements[picker.dataset.name].value = ids.join(", ");
      $(".equipment-selection", picker).textContent =
        ids
          .map((id) => S.equipment[picker.dataset.kind][id]?.name || id)
          .join(", ") || picker.dataset.empty;
      if (picker.dataset.kind === "components")
        syncComponentStats(picker.closest("[data-member-build]"));
      updateStatPreviews(false);
    } else if (n.name === "realistic_stats" || n.name === "team_size") {
      await rebuildStatFields();
    } else if (n.name === "entity_level") {
      $$("[data-member-level]", n.form).forEach((input) => {
        input.value = n.value;
      });
      updateStatPreviews();
    } else if (n.matches("input[data-stat]")) {
      if ($("#member-stat-builds").dataset.mode === "realistic-v1") {
        const level = Number(
          $("[data-member-level]", n.closest("[data-member-build]")).value,
        );
        const bonus =
          componentBonuses(
            selectedComponents(n.closest("[data-member-build]")),
          )[n.dataset.stat] || 0;
        const current = Number(n.value) - bonus;
        const choice = statChoices(n.dataset.stat, level).find(
          (c) => c.value >= current,
        );
        if (choice) n.value = choice.value + bonus;
      }
      updateStatPreviews(false);
    } else if (n.matches("[data-member-level]")) {
      updateStatPreviews();
    } else if (n.name === "round_stop") {
      n.form.elements.generations.disabled = n.value === "manual";
    } else if (n.name === "team_mode") {
      updateTeamMode();
    } else if (n.id === "metric-set") {
      S.metricSet = n.value;
      if (S.combatStatistics)
        $(".combat-statistics").outerHTML = combatStatistics(
          S.combatStatistics,
        );
    } else if (n.id === "engine-files") {
      $("#file-list").innerHTML = fileButtons(S.files);
    } else if (n.id === "conversation-model")
      navigate("run", { run: S.run, tab: S.tab, model: n.value });
    else if (n.id === "session-choice")
      navigate("run", {
        run: S.run,
        tab: S.tab,
        model: S.modelFilter,
        session: n.value,
      });
    else if (n.matches("[data-overview-filter]")) {
      overviewSettings()[n.dataset.overviewFilter] = n.value;
      LiveDOM.update($("#run-content"),summary(S.detail, S.statistics));
      $(`[data-overview-filter="${n.dataset.overviewFilter}"]`)?.focus({
        preventScroll: true,
      });
    } else if (n.id === "source-file") {
      S.file = n.value;
      await loadSource();
    } else if (n.id === "source-previous") {
      S.previous = Number(n.value);
      await loadSource();
    } else if (n.id === "event-session")
      navigate("run", {
        run: S.run,
        tab: "events",
        model: S.modelFilter,
        session: n.value,
      });
    else if (n.id === "follow-live") {
      S.follow = n.checked;
      S.livePreferences ||= {};
      S.livePreferences[S.run] = n.checked;
      if (n.checked && S.tab === "conversation")
        await refreshLiveConversation(S.epoch);
    } else if (n.name === "match-kind")
      navigate("run", { run: S.run, tab: "matches", kind: n.value });
    else if (
      [
        "match-model",
        "match-opponent-model",
        "match-round",
        "match-track",
        "match-outcome",
      ].includes(n.name)
    )
      await filterMatches();
    else if (n.id === "replay-speed" && replayTimer) {
      clearInterval(replayTimer);
      replayTimer = null;
      playReplay();
    }
  } catch (error) {
    showError(error);
  }
});
document.addEventListener("click", event => {
  if (event.target.closest(".skip-link")) {
    event.preventDefault();
    $("#main").focus({preventScroll:true});
    window.scrollTo({top:0,behavior:"instant"});
  }
  $$(".action-menu[open]").forEach(menu=>{
    if (!menu.contains(event.target) || event.target.closest("[data-action]")) menu.open=false;
  });
});
document.addEventListener("keydown", event => {
  if (event.key === "Escape") $$(".action-menu[open]").forEach(menu=>{menu.open=false; menu.querySelector("summary").focus();});
});
document.addEventListener("invalid", event => {
  let parent = event.target.parentElement;
  while (parent) {
    if (parent.tagName === "DETAILS") parent.open = true;
    parent = parent.parentElement;
  }
}, true);
document.addEventListener("input", (event) => {
  const n = event.target;
  if(n.id==='workspace-member-search') {
    for(const row of $$('.workspace-member'))row.hidden=!row.textContent.toLowerCase().includes(n.value.toLowerCase());
  }
  if (n.id === "participant-search") refreshParticipantCards();
  if(n.id === "competition-participant-search") updateCompetitionSelection();
  if(n.id === "group-member-search")for(const row of $$(".group-member"))row.hidden=!row.textContent.toLowerCase().includes(n.value.toLowerCase());
  if (n.id === "run-search")
    $("#run-table").innerHTML = runTable(
      scoped(S.boot.runs).filter((r) =>
        `${r.name} ${r.id}`.toLowerCase().includes(n.value.toLowerCase()),
      ),
    );
  if (n.id === "file-search")
    $("#file-list").innerHTML = fileButtons(
      S.files.filter((f) =>
        f.path.toLowerCase().includes(n.value.toLowerCase()),
      ),
    );
  if (n.matches("[data-stat-slider]")) {
    const section = n.closest("[data-member-build]"),
      key = n.dataset.statSlider;
    const level = Number($("[data-member-level]", section).value);
    const components = selectedComponents(section),
      bonus = componentBonuses(components);
    let value = Number(n.value);
    if ($("#member-stat-builds").dataset.mode === "realistic-v1")
      value =
        statChoices(key, level).reduce((best, c) =>
          Math.abs(c.value + (bonus[key] || 0) - value) <
          Math.abs(best.value + (bonus[key] || 0) - value)
            ? c
            : best,
        ).value + (bonus[key] || 0);
    $(`[data-stat="${key}"]`, section).value = value;
    updateStatPreviews(false);
  }
  if (n.matches("input[data-stat]") || n.matches("[data-member-level]"))
    updateStatPreviews(false);
  if (n.matches(".equipment-search")) {
    for (const item of $$(".equipment-option", n.closest(".equipment-picker")))
      item.hidden = !item.dataset.search.includes(n.value.toLowerCase());
  }
  if (n.id === "model-search") renderModelCatalog();
  if (n.id === 'provider-model-search') {
    for(const section of $$('[data-provider-model]'))section.hidden=!S.providerModelCatalog[Number(section.dataset.providerModel)].id.toLowerCase().includes(n.value.toLowerCase());
  }
  if (n.id === 'run-participant-search') {
    for(const row of $$('[data-run-profile]')) row.hidden=!row.dataset.runProfile.includes(n.value.toLowerCase());
  }
  if (n.id === "match-search") filterMatches().catch(showError);
  if (n.id === "replay-range") renderReplay(Number(n.value));
});
$("#dialog").addEventListener("close", () => {
  hideHelp();
  document.body.appendChild($("#toast"));
  S.logJob = null;
});
document.addEventListener("toggle", event => {
  const node=event.target;
  if(node.id==='competition-activity-details' && node.isConnected) {
    S.activityExpanded ||= {};S.activityExpanded[S.run]=node.open;
  }
  if(node.matches?.('details[data-fault-event]') && node.isConnected) {
    S.faultOpen ||= {};
    S.faultOpen[node.dataset.faultRun+'/'+node.dataset.faultEvent]=node.open;
  }
  if(node.matches?.("details[data-recovery-run]")) {
    S.recoveryOpen ||= {};
    // Ignore toggle events queued by a panel replaced during a live refresh.
    if(node.isConnected) S.recoveryOpen[node.dataset.recoveryRun]=node.open;
  }
}, true);
window.addEventListener("hashchange", route);
let polling = false;
setInterval(async () => {
  if (!S.boot || polling || document.hidden) return;
  polling = true;
  try {
    const data = await api("/api/runs");
    S.boot.runs = data.runs;
    S.boot.jobs = data.jobs;
    syncLiveMode();
    const liveToggle = $("#follow-live");
    if (liveToggle) liveToggle.checked = !!S.follow;
    updateChrome();
    if(S.view==='run') {
      try {await refreshCompetitionActivity(S.epoch);}
      catch(error) {const panel=$('#competition-activity');if(panel)panel.dataset.stale='true';}
    }
    if(S.view==='run' && S.tab==='summary' && S.follow && !$('#dialog').open && Date.now()-(S.overviewFaultTime||0)>10000) {
      const epoch=S.epoch,run=S.run;
      const faults=await api('/api/faults',{run});
      if(epoch!==S.epoch||run!==S.run)return;
      S.overviewFaults=faults;S.overviewFaultRun=run;S.overviewFaultTime=Date.now();
      const chart=$('#overview-errors');if(chart)LiveDOM.replace(chart,overviewErrors(S.detail,overviewData(S.detail)));
    }
    if (S.logJob && $("#job-log-live")) {
      const log = await api("/api/job", { id: S.logJob });
      $("#job-log-live").textContent = log.content;
    }
    if (S.view === "run" && S.tab === "conversation" && S.follow && !$("#dialog").open) {
      try {
        await refreshLiveConversation(S.epoch);
      } catch (error) {
        const banner = $("#conversation-live-status");
        if (banner) banner.textContent = "Live update interrupted. Retrying automatically…";
      }
    }
    if (
      S.view === "run" &&
      !$("#dialog").open &&
      S.follow &&

      !(S.tab === "matches" && replayTimer) &&
      (activeJobs().some((j) => j.run === S.run) ||
        S.boot.runs.some(
          (r) =>
            r.id === S.run && pretty(r.report) !== pretty(S.detail?.report),
        ) ||
        S.renderedJobState !== S.boot.jobs.find((j) => j.run === S.run)?.status)
    ) {
      const old = pretty(S.detail?.sessions),
        epoch = S.epoch,
        d = await api("/api/run", { run: S.run });
      if (epoch !== S.epoch) return;
      if (
        d.revision !== S.detail?.revision ||
        old !== pretty(d.sessions) ||
        pretty(S.detail.report) !== pretty(d.report) ||
        S.renderedJobState !== S.boot.jobs.find((j) => j.run === S.run)?.status
      ) {
        S.detail = d;
        if (S.tab === "conversation" && S.liveConversation?.session === S.session) {
          const toolbar=$('#session-toolbar');
          if(toolbar)LiveDOM.replace(toolbar,sessionChooser(d));
          return;
        }
        if (S.follow && S.tab === "events" && !S.explicitOffset) {
          const events = await api("/api/events", {
            run: S.run,
            session: S.session || undefined,
            model: S.modelFilter || undefined,
            limit: 1,
          });
          S.offset = Math.floor(Math.max(0, events.total - 1) / 100) * 100;
        }
        await renderRun(epoch,true);
      }
    }
  } catch (error) {
    /* A manual refresh exposes errors without repeated background notifications. */
  } finally {
    polling = false;
  }
}, 3000);
refreshBoot()
  .then(route)
  .catch((error) => {
    $("#main").innerHTML = empty(
      "Connection failed",
      error.message,
      btn("Retry", "refresh"),
    );
    showError(error);
  });

function markdownInline(source) {
  // Escape HTML first. Only explicit HTTP(S) and fragment links are clickable.
  return e(source)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+|#[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noreferrer noopener">$1</a>',
    );
}
function markdownView(source) {
  const allLines = source.slice(0, 300000).replace(/\r\n/g, "\n").split("\n");
  const lines = allLines.slice(0, 3000),
    blocks = [];
  if (source.length > 300000 || allLines.length > 3000)
    blocks.push(
      notice(
        "Rendered preview truncated. The full text is available in Raw view or as a download.",
      ),
    );
  let code = null,
    list = null;
  const closeList = () => {
    if (list) {
      blocks.push(`</${list}>`);
      list = null;
    }
  };
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^\s*```/.test(line)) {
      closeList();
      if (code === null) code = [];
      else {
        blocks.push(`<pre><code>${e(code.join("\n"))}</code></pre>`);
        code = null;
      }
    } else if (code !== null) code.push(line);
    else if (
      /^\s*\|?\s*:?-{3,}/.test(lines[i + 1] || "") &&
      line.includes("|")
    ) {
      closeList();
      const cells = (l) =>
        l
          .trim()
          .replace(/^\||\|$/g, "")
          .split("|")
          .map(markdownInline);
      const headers = cells(line),
        rows = [];
      i += 2;
      while (i < lines.length && lines[i].includes("|")) {
        rows.push(
          `<tr>${cells(lines[i])
            .map((c) => `<td>${c}</td>`)
            .join("")}</tr>`,
        );
        i++;
      }
      i--;
      blocks.push(table(headers, rows));
    } else if (/^#{1,6}\s/.test(line)) {
      closeList();
      const [, marks, title] = line.match(/^(#{1,6})\s+(.*)$/);
      blocks.push(
        `<h${marks.length}>${markdownInline(title)}</h${marks.length}>`,
      );
    } else if (/^\s*(?:[-*+] |\d+\. )/.test(line)) {
      const kind = /^\s*\d/.test(line) ? "ol" : "ul";
      if (list !== kind) {
        closeList();
        list = kind;
        blocks.push(`<${kind}>`);
      }
      blocks.push(
        `<li>${markdownInline(line.replace(/^\s*(?:[-*+] |\d+\. )/, ""))}</li>`,
      );
    } else {
      closeList();
      if (line.trim()) blocks.push(`<p>${markdownInline(line)}</p>`);
    }
  }
  closeList();
  if (code !== null)
    blocks.push(`<pre><code>${e(code.join("\n"))}</code></pre>`);
  return blocks.join("");
}
function jsonView(value, key = "JSON", depth = 0, budget = { left: 2500 }) {
  if (--budget.left < 0 || depth > 20)
    return `<small>More content is available in Raw view.</small>`;
  if (value === null || typeof value !== "object")
    return `<div class="json-leaf"><strong>${e(key)}</strong> <code>${e(JSON.stringify(value))}</code></div>`;
  const entries = Object.entries(value);
  const children = [];
  for (const [k, v] of entries.slice(0, 500)) {
    if (budget.left <= 0) break;
    children.push(jsonView(v, k, depth + 1, budget));
  }
  return `<details ${depth < 2 ? "open" : ""}><summary>${e(key)} <small>${Array.isArray(value) ? "[" + entries.length + "]" : "{" + entries.length + "}"}</small></summary><div class="json-children">${children.join("")}${children.length < entries.length ? "<small>More content is available in Raw view.</small>" : ""}</div></details>`;
}
function renderFileView(liveUpdate=false) {
  const originalNode = $("#file-content"), node = liveUpdate ? document.createElement("div") : originalNode;
  if (!originalNode || !S.filePreview) return;
  const { path, content } = S.filePreview;
  originalNode.classList.add('file-preview');
  node.className = "file-preview";
  if (S.fileMode === "rendered" && /\.md$/i.test(path))
    node.innerHTML = markdownView(content);
  else if (S.fileMode === "rendered" && /\.json$/i.test(path)) {
    try {
      node.innerHTML = jsonView(JSON.parse(content));
    } catch {
      node.innerHTML =
        notice("Invalid JSON") + `<pre class="source">${e(content)}</pre>`;
    }
  } else node.innerHTML = `<pre class="source">${e(content)}</pre>`;
  $$("[data-action=file-mode]").forEach((n) =>
    n.classList.toggle("primary", n.dataset.mode === (S.fileMode || "raw")),
  );
  if(liveUpdate)LiveDOM.update(originalNode,node.innerHTML);
}

const COMBAT_COLUMNS = [
  ["ai_turns", "Played turns"],
  ["operations", "Operations"],
  ["actions", "Actions"],
  ["shots", "Shots"],
  ["chips", "Chips"],
  ["weapon_changes", "Weapons"],
  ["moves", "Moves"],
  ["cells_moved", "Cells"],
  ["tp_lost", "AP removed"],
  ["mp_lost", "MP removed"],
  ["damage_dealt", "Damage dealt"],
  ["damage_taken", "Damage taken"],
  ["healing_given", "Healing given"],
  ["healing_received", "Healing received"],
  ["erosion_dealt", "Erosion dealt"],
  ["erosion_taken", "Erosion taken"],
  ["deaths", "Deaths"],
  ["errors", "Errors"],
  ["operation_limit_hits", "Operation limits hit"],
  ["stack_overflows", "Stack overflows"],
];
const METRIC_SETS = {
  overview: ["operations", "actions", "moves", "damage_dealt", "damage_taken"],
  compute: [
    "ai_turns",
    "operations",
    "errors",
    "operation_limit_hits",
    "stack_overflows",
  ],
  actions: [
    "actions",
    "shots",
    "chips",
    "weapon_changes",
    "moves",
    "cells_moved",
    "tp_lost",
    "mp_lost",
  ],
  damage: [
    "damage_dealt",
    "damage_taken",
    "healing_given",
    "healing_received",
    "erosion_dealt",
    "erosion_taken",
    "deaths",
  ],
};
function metricSetPicker() {
  return `<label class="field">Metrics<select id="metric-set">${[
    ["overview", "Overview"],
    ["compute", "Computation and errors"],
    ["actions", "Actions and movement"],
    ["damage", "Damage and healing"],
    ["all", "All metrics"],
  ]
    .map(
      ([value, label]) =>
        `<option value="${value}" ${value === (S.metricSet || "overview") ? "selected" : ""}>${label}</option>`,
    )
    .join("")}</select></label>`;
}
function combatTable(rows, perTurn = false) {
  const selection = S.metricSet || "overview";
  const columns =
    selection === "all"
      ? COMBAT_COLUMNS
      : COMBAT_COLUMNS.filter(([key]) => METRIC_SETS[selection].includes(key));
  const mean = columns.some(([key]) => key === "operations");
  const showLimit = rows.some((row) => row.operations_limit_per_turn != null);
  return table(
    [
      ...(perTurn ? ["Turn"] : []),
      "Leek / strategy",
      ...columns.map(([, label]) => label),
      ...(mean ? ["Ops / played turn"] : []),
      ...(showLimit ? ["Ops limit / turn"] : []),
    ],
    rows.map(
      (row) =>
        `<tr>${perTurn ? `<td>${e(row.turn)}</td>` : ""}<td>${e(row.name || strategyName(row.id))}${row.side != null ? `<small>Side ${row.side + 1} · #${row.entity}</small>` : ""}</td>${columns.map(([key]) => `<td>${fmt(row[key])}</td>`).join("")}${mean ? `<td>${fmt(row.operations != null && row.ai_turns ? row.operations / row.ai_turns : null, 1)}</td>` : ""}${showLimit ? `<td>${fmt(row.operations_limit_per_turn)}</td>` : ""}</tr>`,
    ),
  );
}
function combatStatistics(data) {
  return `<section class="combat-statistics"><h3>Match statistics</h3>${metricSetPicker()}<p class="muted">Limit: ${data.operation_limits?.length > 1 ? "varies by leek; see the per-leek rows" : fmt(data.operations_limit_per_turn) + " operations per played turn and leek"} (${e(data.limit_source)}). ${e(data.action_definition)}</p>${data.missing.map((m) => notice(e(m))).join("")}<h3>Match and team totals</h3>${combatTable([data.total, ...data.sides])}<h3>Totals by leek</h3>${combatTable(data.entities)}<details><summary>Totals by turn</summary>${combatTable(data.rounds, true)}</details><details><summary>Details by turn and leek</summary>${combatTable(data.turns, true)}</details></section>`;
}
async function filterMatches(clear = false) {
  const form = $(".match-filters");
  if (!form) return;
  if (clear) {
    S.matchFilters = {};
    for (const n of $$("input, select", form)) n.value = "";
    $("[name=match-kind]").value = "competition";
  } else
    S.matchFilters = {
      ...S.matchFilters,
      search: $("#match-search").value,
      kind: $("[name=match-kind]")?.value || "competition",
      stage:undefined,entrant:undefined,opponent:undefined,
      entrant_model: $("[name=match-model]", form).value,
      opponent_model: $("[name=match-opponent-model]", form).value,
      round: $("[name=match-round]", form).value,
      track: $("[name=match-track]", form).value,
      outcome: $("[name=match-outcome]", form).value,
    };
  $('#match-origin-scope')?.remove();
  const filters = Object.fromEntries(
    Object.entries(S.matchFilters).filter(([, v]) => v),
  );
  history.replaceState(
    null,
    "",
    "#" + query({ view: "run", run: S.run, tab: "matches", ...filters }),
  );
  const rows = matchSubset();
  $("#match-filter-count").textContent =
    `${rows.length} / ${S.matches.filter((m) => matchCategory(m,S.matchFilters.kind)).length} matches in this category`;
  if (!$("#match-list")) return;
  $("#match-list").innerHTML = matchButtons(rows);
  const path =
    rows.find((m) => m.path === S.matchPath)?.path || rows[0]?.path || null;
  if (!path) {
    clearInterval(replayTimer);
    replayTimer = null;
    R = null;
    S.matchPath = null;
    $("#match-detail").innerHTML = empty(
      "No matches found",
      "Change or clear the filters.",
    );
  } else if (path !== S.matchPath) {
    S.matchPath = path;
    await loadMatch();
  }
}
function countLabel(count, noun, plural = noun + "s") {
  return `${count} ${count === 1 ? noun : plural}`;
}
function matrixLink(stage, entrant, opponent, outcome, value, description, category=null) {
  const href =
    "#" +
    query({
      view: "run",
      run: S.run,
      tab: "matches",
      stage,
      kind: category || (stage.endsWith("-previous") ? "progression" : stage.startsWith("evaluations/") ? "evaluation" : "competition"),
      entrant,
      opponent,
      outcome,
    });
  return `<a href="${e(href)}" aria-label="${e(`${strategyName(entrant)} vs ${strategyName(opponent)}: ${description}`)}">${e(value)}</a>`;
}

// Numeric column sorting also works for live-generated statistics tables.
document.addEventListener("click", (event) => {
  const header = event.target.closest("th");
  if (!header) return;
  const table = header.closest("table"),
    index = header.cellIndex;
  const body = table.tBodies[0];
  if (!body || !body.rows.length) return;
  const value = (row) => {
    const cell = row.cells[index];
    const raw =
      cell?.dataset.sortValue ??
      (cell?.firstChild?.textContent || cell?.textContent || "")
        .trim()
        .split(/\s*\/\s*|\n/)[0];
    return raw && /^[+$−-]?[\d,.]+%?$/.test(raw)
      ? Number(raw.replace(/[$,%+]/g, ""))
      : null;
  };
  if (![...body.rows].some((row) => value(row) != null)) return;
  const direction = header.dataset.sortDirection === "desc" ? "asc" : "desc";
  for (const th of table.querySelectorAll("th"))
    th.removeAttribute("aria-sort");
  header.dataset.sortDirection = direction;
  header.setAttribute(
    "aria-sort",
    direction === "desc" ? "descending" : "ascending",
  );
  const rows = [...body.rows].sort((a, b) => {
    const x = value(a),
      y = value(b);
    return x == null
      ? y == null
        ? 0
        : 1
      : y == null
        ? -1
        : direction === "desc"
          ? y - x
          : x - y;
  });
  body.append(...rows);
});

const sortableObserver = new MutationObserver(() => {
  for (const table of document.querySelectorAll(
    "#main table:not(.overview-matrix)",
  )) {
    const rows = [...(table.tBodies[0]?.rows || [])];
    for (const header of table.querySelectorAll("thead th")) {
      if (
        header.dataset.sortReady ||
        !rows.some((row) =>
          /^[+$-]?[\d,.]+%?(?:\s|$)/.test(
            (
              row.cells[header.cellIndex]?.firstChild?.textContent ||
              row.cells[header.cellIndex]?.textContent ||
              ""
            ).trim(),
          ),
        )
      )
        continue;
      header.dataset.sortReady = "true";
      const button = document.createElement("button");
      button.className = "table-button";
      button.textContent = header.textContent + " ↕";
      button.title = "Sort by " + header.textContent;
      header.replaceChildren(button);
    }
  }
});
sortableObserver.observe(document.querySelector("#main"), {
  childList: true,
  subtree: true,
});

// Updating the exact model changes which effort levels are valid, without choosing one silently.
document.addEventListener("input", event => {
  if (event.target.name !== "model" || event.target.form?.dataset.form !== "participant") return;
  const effort = event.target.form.elements.namedItem("reasoning_effort");
  if (!effort) return;
  const restricted = event.target.value.toLowerCase() === "gpt-6.1-sol";
  for (const option of effort.options) option.disabled = restricted && ["none", "minimal"].includes(option.value);
});
