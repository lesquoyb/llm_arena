"use strict";
const $ = (id) => document.getElementById(id);
let boot,
  selected,
  selectedState,
  selectedTrial,
  sessionRows = [],
  polling = false,
  historyOffset,
  lastStudySignature,
  historyIdentity,
  historyNext,
  baselineId = localStorage.getItem("arena-calibration-baseline");
const showError = (error) => {
  $("error").textContent = error.message || String(error);
  $("error").hidden = false;
};
const guard =
  (fn) =>
  async (...args) => {
    try {
      await fn(...args);
    } catch (error) {
      showError(error);
    }
  };
async function api(path, data) {
  const response = await fetch(
    path,
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Arena-Token": boot.token,
          },
          body: JSON.stringify(data),
        },
  );
  const body = await response.json();
  if (!response.ok) throw Error(body.error || response.statusText);
  return body;
}
const qs = (route, params = {}) =>
  route + "?" + new URLSearchParams({ study: selected, ...params });
const node = (tag, text, cls) => {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (cls) el.className = cls;
  return el;
};
function option(select, value, label) {
  const opt = node("option", label);
  opt.value = value;
  select.append(opt);
}
const json = (value) => JSON.stringify(value, null, 2);
const pct = (value) =>
  typeof value === "number" ? (100 * value).toFixed(1) + "%" : "Unknown";
function table(headers, rows) {
  const wrap = node("div", undefined, "scroll"),
    tbl = node("table"),
    head = node("thead"),
    tr = node("tr");
  headers.forEach((h) => tr.append(node("th", h)));
  head.append(tr);
  tbl.append(head);
  const body = node("tbody");
  rows.forEach((row) => {
    const tr = node("tr");
    row.forEach((value) => {
      const td = node("td");
      td.append(
        value instanceof Node ? value : document.createTextNode(String(value)),
      );
      tr.append(td);
    });
    body.append(tr);
  });
  tbl.append(body);
  wrap.append(tbl);
  return wrap;
}
function button(label, fn) {
  const b = node("button", label, "secondary");
  b.onclick = guard(fn);
  return b;
}
let referenceEdits = {}, referencePath = null;
function saveReferenceEdit() {
  if (referencePath) {
    const text=$('reference-content').value;
    if (text===boot.reference_documents[referencePath]) delete referenceEdits[referencePath];
    else referenceEdits[referencePath]=text;
  }
}
$('reference-path').onchange=()=>{
  saveReferenceEdit(); referencePath=$('reference-path').value;
  $('reference-content').value=referenceEdits[referencePath] ?? boot.reference_documents[referencePath];
};
let dialogPayload='', livePolling=false, lastReviewKey='', pinnedCandidate=false, previousLiveIdentity='', previousInFlight=false, reviewEpoch=0;
function inlineText(parent,text) {
  for (const part of String(text).split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g)) {
    if (part.startsWith('**') && part.endsWith('**')) parent.append(node('strong',part.slice(2,-2)));
    else if (part.startsWith('`') && part.endsWith('`')) parent.append(node('code',part.slice(1,-1)));
    else {
      const link=part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
      if(link){const a=node('a',link[1]);a.href=link[2];a.target='_blank';a.rel='noreferrer';parent.append(a)}
      else parent.append(document.createTextNode(part));
    }
  }
}
function formatted(value) {
  const wrap=node('div',undefined,'formatted-text');
  if (typeof value!=='string') {
    if(value && typeof value==='object' && typeof (value.text ?? value.content)==='string') {
      wrap.append(formatted(value.text ?? value.content));
      const extra=Object.fromEntries(Object.entries(value).filter(([k])=>!['text','content','type','role'].includes(k)));
      if(Object.keys(extra).length){const d=node('details');d.append(node('summary','Structured fields'),node('pre',json(extra),'record-code'));wrap.append(d)}
    } else wrap.append(node('pre',json(value),'record-code'));
    return wrap;
  }
  let code=null,list=null;
  for(const line of value.split('\n')) {
    if(/^\s*```/.test(line)){if(code){wrap.append(code);code=null}else code=node('pre','','record-code');list=null;continue}
    if(code){code.textContent+=line+'\n';continue}
    const heading=line.match(/^(#{1,4})\s+(.*)$/), item=line.match(/^\s*(?:[-*]|\d+\.)\s+(.*)$/);
    if(heading){const h=node('h'+Math.min(heading[1].length+1,4));inlineText(h,heading[2]);wrap.append(h);list=null}
    else if(item){if(!list){list=node('ul');wrap.append(list)}const li=node('li');inlineText(li,item[1]);list.append(li)}
    else if(line.trim()){const p=node('p');inlineText(p,line);wrap.append(p);list=null}
    else list=null;
  }
  if(code)wrap.append(code);
  return wrap;
}
function diffView(text) {
  const pre=node('pre',undefined,'record-code');
  for(const line of text.split('\n')) pre.append(node('span',line+'\n','diff-line '+(line.startsWith('+')&&!line.startsWith('+++')?'diff-add':line.startsWith('-')&&!line.startsWith('---')?'diff-remove':'')));
  return pre;
}
async function reviewCandidate(directory) {
  const epoch=++reviewEpoch, study=selected;
  const value=await api(qs(directory.startsWith('proposals/')?'/api/proposal':'/api/candidate',{trial:directory}));
  if(study!==selected || epoch!==reviewEpoch)return;
  const mount=$('analyst-content');mount.replaceChildren();
  mount.append(node('span',`Candidate ${value.candidate} · ${value.decision}`,'decision'));
  if(value.decision_reason) mount.append(node('p',value.decision_reason));
  mount.append(formatted(value.baseline?'This is the baseline. No analyst changes have been proposed for it.':value.rationale || 'No rationale recorded.'));
  if(value.metrics_after){const metrics=node('div',undefined,'review-metrics');for(const [key,label,format] of [['validation_score','Evaluation score',pct],['judge_score','Laya score',pct],['utility','Objective utility',x=>typeof x==='number'?x.toFixed(4):'Unknown'],['convergence_round','Convergence round',x=>x??'Not reached'],['tokens','Target tokens',x=>x??'Unknown']]){if(key==='judge_score' && value.metrics_after.evaluation_mode==='conversation')continue;const box=node('div');box.append(node('span',key==='validation_score' && value.metrics_after.evaluation_mode==='conversation'?'Laya reasoning score':label),node('strong',key==='convergence_round'&&value.metrics_after.converged===false?'Not reached':format(value.metrics_after[key])));if(value.metrics_before)box.append(node('small','Previous: '+(key==='convergence_round'&&value.metrics_before.converged===false?'Not reached':format(value.metrics_before[key]))));metrics.append(box)}mount.append(metrics)}
  if(value.rl)mount.append(node('p',`RL action: ${value.rl.action} · Reward: ${value.rl.reward.toFixed(4)} · Learned value: ${value.rl.q_after.toFixed(4)}`));
  if(value.config.evaluation?.mode && value.config.evaluation.mode!=='fights')mount.append(button('Inspect Laya scores and rubric',async()=>reveal('Local Laya judge',await api(qs('/api/judge',{trial:'trials/'+String(value.candidate-1).padStart(3,'0')})))));
  let changes=0;
  const addDiff=(title,text)=>{if(!text)return;changes++;const d=node('details');d.append(node('summary',title),diffView(text));mount.append(d)};
  addDiff('System prompt changes',value.prompt_diff);
  Object.entries(value.document_diffs || {}).forEach(([path,text])=>addDiff('Document: '+path,text));
  if(json([...value.tools_before].sort())!==json([...value.tools_after].sort())){changes++;mount.append(node('h4','Enabled tools'),node('pre',json({before:value.tools_before,after:value.tools_after}),'record-code'))}
  if(json(value.parameters_before)!==json(value.parameters_after)){changes++;mount.append(node('h4','Model parameters'),node('pre',json({before:value.parameters_before,after:value.parameters_after}),'record-code'))}
  if(!changes)mount.append(node('p',value.baseline?'The original prompt and documents are unchanged.':'No prompt, document, tool-selection or parameter changes.'));
  if(value.tool_requests?.length){mount.append(node('h4','Tool improvement requests'));value.tool_requests.forEach(request=>mount.append(formatted(`**${request.kind}: ${request.tool || 'Tools/documentation'}**\n${request.problem}\n${request.proposed_change}\n${request.expected_benefit || ''}`)))}
  if(!value.baseline)mount.append(node('p','The analyst proposes changes. Kept/rejected is decided by paired validation results and the configured objective, not by the analyst’s opinion.'));
  const actions=node('div',undefined,'review-actions');actions.append(button('Inspect analyst conversation',async()=>{const proposal='proposals/'+String(value.candidate-1).padStart(3,'0');if(![...$('trial').options].some(o=>o.value===proposal))option($('trial'),proposal,'Analyst for candidate '+value.candidate);$('trial').value=proposal;await loadTrial();$('history').scrollIntoView({behavior:'smooth',block:'center'})}),button('Raw review data',()=>reveal('Candidate review data',value)));
  if(!value.baseline)mount.append(actions);
}
function budgetFields(value) {
  for(const [id,key] of [['limit-calls','max_calls'],['limit-tools','max_agent_steps'],['limit-fights','max_test_matches']])$(id).value=value[key]??'';
  $('budget-preview').textContent=Object.keys(value).length?'These limits are sent to the target at the start of every round. One test runs two preparation fights.':'No preparation limits. Add a limit for quick diagnostic trials.';
}
$('short-budget').onclick=()=>{const value={...JSON.parse($('budget').value || '{}'),max_calls:8,max_agent_steps:20,max_test_matches:4};$('budget').value=json(value);budgetFields(value)};
$('budget').oninput=()=>{try{budgetFields(JSON.parse($('budget').value))}catch{}};
for(const [id,key] of [['limit-calls','max_calls'],['limit-tools','max_agent_steps'],['limit-fights','max_test_matches']])$(id).oninput=()=>{try{const value=JSON.parse($('budget').value||'{}');if($(id).value==='')delete value[key];else value[key]=Number($(id).value);$('budget').value=json(value);budgetFields(value)}catch(error){showError(error)}};
$('history-top').onclick=()=>{$('follow-live').checked=false;$('history').scrollTo({top:0,behavior:'smooth'})};
$('history-bottom').onclick=guard(async()=>{$('follow-live').checked=true;await history(Math.max(0,(lastConversationTotal||25)-25));$('history').scrollTo({top:$('history').scrollHeight,behavior:'smooth'})});
let lastConversationTotal=0;
async function refreshLiveOutput() {
  if(livePolling || !selected || !selectedTrial || !$('session').value || document.hidden || $('inspection').hidden)return;
  livePolling=true;
  const identity=[selected,selectedTrial,$('session').value].join('|');
  try {
    const data=await api(qs('/api/live-response',{trial:selectedTrial,session:$('session').value}));
    if(identity!==[selected,selectedTrial,$('session').value].join('|'))return;
    if(previousLiveIdentity===identity && previousInFlight && !data.in_flight) await history(undefined,true);
    previousLiveIdentity=identity;previousInFlight=!!data.in_flight;
    const budget=$('session-budget');budget.replaceChildren();
    if(data.budget){const strip=node('div',undefined,'budget-strip');for(const [key,value] of Object.entries(data.budget.limits))strip.append(node('span',`${({calls:'Model calls',steps:'Tool calls',test_matches:'Preparation fights'})[key]||key}: ${value.used??'?'} / ${value.limit} · ${value.remaining??'?'} left`));budget.append(strip)}
    $('live-status').textContent=data.in_flight?'Model request in progress'+(data.live?.phase==='streaming'?' · receiving output':(data.streaming_supported?' · waiting for output':' · this provider updates after each complete response')):data.status;
    const mount=$('live-output');
    if(!data.live || !data.in_flight && data.live.phase!=='interrupted'){mount.replaceChildren();delete mount.dataset.signature;return}
    if(!$('follow-live').checked)return;
    const live=data.live, signature=identity+'|'+live.call+'|'+live.updated_at+'|'+live.phase;
    if(mount.dataset.signature===signature)return;
    mount.dataset.signature=signature;
    const atBottom=mount.scrollHeight-mount.scrollTop-mount.clientHeight<60;
    mount.replaceChildren(node('strong',`Live response · call ${live.call}${live.phase==='interrupted'?' · interrupted, partial output':''}`));
    if(live.reasoning){const details=node('details');details.open=mount.dataset.reasoningOpen==='1';details.append(node('summary','Provider-exposed reasoning'),node('pre',live.reasoning,'record-code'));details.ontoggle=()=>mount.dataset.reasoningOpen=details.open?'1':'';mount.append(details)}
    if(live.text)mount.append(formatted(live.text));
    if(live.tools?.length)mount.append(node('pre',json(live.tools),'record-code'));
    if(!live.text&&!live.reasoning&&!live.tools?.length)mount.append(node('p','Waiting for the provider’s first output.'));
    if(live.preview_truncated)mount.append(node('p','Live preview shows the latest text. Full output is retained in the completed record.'));
    if(atBottom)mount.scrollTop=mount.scrollHeight;
  } catch(error){$('live-status').textContent='Live preview unavailable; retrying.'}finally{livePolling=false}
}
setInterval(refreshLiveOutput,700);

function fill(config) {
  referenceEdits=structuredClone(config.reference_documents || {});
  $('reference-path').replaceChildren();
  Object.keys(boot.reference_documents).forEach(path=>option($('reference-path'),path,path));
  referencePath=$('reference-path').value;
  $('reference-content').value=referenceEdits[referencePath] ?? boot.reference_documents[referencePath];
  $("name").value = config.name;
  const learning=config.rl || {learning_rate:0.25,exploration:0.2,minimum_episodes:10,plateau_patience:8,minimum_improvement:0.001,seed:0,stop_on_plateau:true};
  for(const [id,key] of Object.entries({'rl-rate':'learning_rate','rl-exploration':'exploration','rl-minimum':'minimum_episodes','rl-patience':'plateau_patience','rl-improvement':'minimum_improvement','rl-seed':'seed'}))$(id).value=learning[key];
  $('rl-plateau').checked=learning.stop_on_plateau;
  const evaluation=config.evaluation || {mode:'fights',weight:0.05,model:'convaiinnovations/laya',device:'cpu'};
  $('judge-evidence').value=evaluation.evidence || 'reasoning';$('reward-mode').value=evaluation.mode;$('judge-model').value=evaluation.model;$('judge-device').value=evaluation.device;$('judge-weight').value=evaluation.weight;
  $("stream-responses").checked=config.stream_responses!==false;
  $("round-stop").value =
    config.max_rounds === null
      ? "manual"
      : config.stop_on_plateau === false
        ? "fixed"
        : "plateau";
  $("scenario-preset").value = config.scenario.preset || "custom";
  $("prompt").value = config.prompt;
  $("target-json").value = json(config.target);
  $("analyst-json").value = json(config.analyst || config.target);
  $("target").value = config.target.id;
  $("analyst").value = config.analyst?.id || config.target.id;
  for (const [id, key] of [
    ["rounds", "max_rounds"],
    ["minimum", "min_rounds"],
    ["patience", "patience"],
    ["replicates", "replicates"],
  ])
    $(id).value = config[key];
  for (const [id, key] of [
    ["training", "training_seeds"],
    ["validation", "validation_seeds"],
    ["audit", "audit_seeds"],
    ["opponents", "opponents"],
  ])
    $(id).value = config[key].join(", ");
  for (const [id, key] of [
    ["scenario", "scenario"],
    ["budget", "budget_per_session"],
  ])
    $(id).value = json(config[key]);
  $("tools").replaceChildren();
  boot.tools.forEach((tool) => {
    const label = node("label"),
      checkbox = node("input");
    checkbox.type = "checkbox";
    checkbox.value = tool.name;
    checkbox.checked = config.tools.includes(tool.name);
    if (["write_file", "submit"].includes(tool.name)) checkbox.disabled = true;
    label.append(checkbox, document.createTextNode(tool.name));
    const help = node("small", tool.description);
    label.append(help);
    $("tools").append(label);
  });
  $("epsilon").value = config.min_improvement;
  $("previous-versions").checked = config.evaluate_previous;
  $("api-enabled").checked = config.spending.allow_paid_calls;
  $("cost-ceiling").value =
    Number(config.spending.max_total_usd) === 0
      ? ""
      : (config.spending.max_total_usd ?? "");
  const map = {
    "candidate-count": "max_trials",
    "search-patience": "patience",
    "score-tolerance": "score_tolerance",
    "round-penalty": "round_penalty",
    "token-penalty": "token_penalty_per_million",
    "evidence-limit": "evidence_characters",
    "editor-retries": "editor_retries",
  };
  Object.entries(map).forEach(
    ([id, key]) => ($(id).value = (config.optimizer[key] ?? "")),
  );
  $("parameter-grid").value = json(config.optimizer.parameter_grid);
  $("simulation-note").textContent =
    config.target.provider === "mock"
      ? "Mock models are offline fixtures. Their scores do not measure a real model’s learning."
      : "";
  budgetFields(config.budget_per_session);
  updateRoundStop();
}
function config() {
  saveReferenceEdit();
  const value = {
    ...structuredClone(boot.config),
    name: $("name").value,
    prompt: $("prompt").value,
    stream_responses:$("stream-responses").checked,
    reference_documents:structuredClone(referenceEdits),
    target: JSON.parse($("target-json").value),
    tools: [...$("tools").querySelectorAll("input:checked")].map(
      (el) => el.value,
    ),
    min_improvement: Number($("epsilon").value),
    stop_on_plateau: $("round-stop").value === "plateau",
    evaluate_previous: $("previous-versions").checked,
  };
  for (const [id, key] of [
    ["rounds", "max_rounds"],
    ["minimum", "min_rounds"],
    ["patience", "patience"],
    ["replicates", "replicates"],
  ])
    value[key] = Number($(id).value);
  if ($("round-stop").value === "manual") value.max_rounds = null;
  for (const [id, key] of [
    ["training", "training_seeds"],
    ["validation", "validation_seeds"],
    ["audit", "audit_seeds"],
  ])
    value[key] = $(id).value.split(",").map(Number);
  value.opponents = $("opponents")
    .value.split(",")
    .map((s) => s.trim());
  for (const [id, key] of [
    ["scenario", "scenario"],
    ["budget", "budget_per_session"],
  ])
    value[key] = JSON.parse($(id).value);
  value.spending = { allow_paid_calls: $("api-enabled").checked };
  if ($("cost-ceiling").value !== "")
    value.spending.max_total_usd = $("cost-ceiling").value;
  const map = {
    "candidate-count": "max_trials",
    "search-patience": "patience",
    "score-tolerance": "score_tolerance",
    "round-penalty": "round_penalty",
    "token-penalty": "token_penalty_per_million",
    "evidence-limit": "evidence_characters",
    "editor-retries": "editor_retries",
  };
  Object.entries(map).forEach(
    ([id, key]) => (value.optimizer[key] = id === "candidate-count" && $(id).value === "" ? null : Number($(id).value)),
  );
  value.rl={stop_on_plateau:$('rl-plateau').checked};
  for(const [id,key] of Object.entries({'rl-rate':'learning_rate','rl-exploration':'exploration','rl-minimum':'minimum_episodes','rl-patience':'plateau_patience','rl-improvement':'minimum_improvement','rl-seed':'seed'}))value.rl[key]=Number($(id).value);
  value.evaluation={mode:$('reward-mode').value,evidence:$('judge-evidence').value,model:$('judge-model').value,device:$('judge-device').value,weight:Number($('judge-weight').value)};
  value.optimizer.parameter_grid = JSON.parse($("parameter-grid").value);
  if ($("mode").value === "manual") value.optimizer.parameter_grid = {};
  if ($("mode").value === "automatic" || ($('reward-mode').value!=='fights' && $('judge-evidence').value==='summary')) {
    value.analyst = JSON.parse($("analyst-json").value);
    if ($("mode").value === "automatic") value.optimizer.parameter_grid = {};
  }
  if (
    $("mode").value === "grid" &&
    !Object.keys(value.optimizer.parameter_grid).length
  )
    throw Error(
      'Enter a parameter_grid in optimizer settings, for example {"temperature":[0,0.3,0.7]}',
    );
  if (value.spending.allow_paid_calls && value.spending.max_total_usd === "0")
    throw Error(
      "Use a positive spending ceiling or leave it blank for unlimited requests.",
    );
  return value;
}
function keys() {
  const value = {};
  for (const role of ["target", "analyst"]) {
    const model = JSON.parse($(role + "-json").value);
    if ($(role + "-key").value) value[model.id] = $(role + "-key").value;
  }
  return value;
}
async function listing() {
  const studies = await api("/api/studies");
  const baseline = studies.find((s) => s.id === baselineId),
    reference = baseline?.trials[baseline.incumbent]?.report;
  $("comparison-note").textContent = baseline
    ? `Comparison baseline: ${baseline.name}. Deltas are shown only when model, scenario, panels, round settings and runner match.`
    : "Choose a study as a comparison baseline. Every edited prompt starts a fresh study.";
  const delta = (value, old, digits = 3) =>
    typeof value === "number" && typeof old === "number"
      ? (value - old >= 0 ? "+" : "") + (value - old).toFixed(digits)
      : "";
  $("studies").replaceChildren(
    table(
      [
        "Study",
        "State",
        "Validation",
        "Convergence",
        "Tokens",
        "Target cost (USD)",
        "Compared with baseline",
        "",
      ],
      studies.map((row) => {
        const best = row.trials[row.incumbent]?.report,
          same = baseline && row.comparison_key === baseline.comparison_key;
        const compare =
          same && best && reference
            ? `Score ${delta(best.validation_score, reference.validation_score)} · rounds ${delta(best.convergence_round, reference.convergence_round, 1)}${best.tokens != null && reference.tokens != null ? " · tokens " + delta(best.tokens, reference.tokens, 0) : ""}`
            : baseline
              ? "Different settings"
              : "";
        return [
          button(row.name, () => inspect(row.id)),
          row.running ? "Running" : row.status,
          pct(best?.validation_score),
          best?.converged === false
            ? "Not reached"
            : (best?.convergence_round ?? ""),
          best?.tokens ?? (best?.simulated ? "Simulated" : "Unknown"),
          best?.cost_usd ?? "",
          compare,
          button(
            row.id === baselineId ? "Baseline" : "Use as baseline",
            async () => {
              baselineId = row.id;
              localStorage.setItem("arena-calibration-baseline", row.id);
              await listing();
            },
          ),
        ];
      }),
    ),
  );
  if (!studies.length) $("studies").textContent = "No calibrations yet.";
  return studies;
}
async function inspect(identifier, retain = false) {
  if (selected!==identifier) pinnedCandidate=false;
  selected = identifier;
  $("inspection").hidden = false;
  $("setup").open = false;
  const data = await api(qs("/api/study"));
  if (selected !== identifier) return;
  const keepSession = $("session").value;
  selectedState = data;
  $("study-title").textContent = data.config.name;
  $("status").textContent =
    (data.runtime_status || data.state.status || "Starting") +
    (data.state.accounting
      ? ` · Target cost $${data.state.accounting.target_cost_usd} · Analyst cost $${data.state.accounting.analyst_cost_usd}`
      : "") +
    (data.state.error ? ": " + data.state.error : "") +
    (data.state.audit
      ? " · Final audit: " +
        (Array.isArray(data.state.audit)?data.state.audit.map((a) => pct(a.score)).join(", "):"Not measured (conversation-only reward)")
      : "");
  const trials = data.state.trials || [];
  renderLearning(data.state);
  const automatic=data.state.automatic ?? false;
  $('workflow-status').textContent=!automatic ? 'Manual study: inspect results, then use Edit selected prompt to create the next candidate. No analyst is run automatically.' : data.state.active_proposal != null && data.state.status==='running' && data.state.active_trial < data.state.active_proposal ? 'Analyst is reviewing the completed trajectory and proposing a new candidate.' : data.state.status==='completed' ? 'Study complete. Review the learning rewards, proposed changes and evaluation decisions below.' : 'Target model is preparing and evaluating rounds. The analyst starts only after the candidate finishes all configured rounds/replicates or reaches its plateau.';
  const reviewKey=selected+'|'+JSON.stringify([data.proposals, trials.map(t=>[t.directory,t.accepted]),data.state.active_proposal]);
  if(reviewKey!==lastReviewKey){lastReviewKey=reviewKey;const latest=data.proposals?.at(-1);if(latest)await reviewCandidate(latest.directory);else{ $('analyst-content').replaceChildren(node('p',automatic?'No analyst proposal yet. Completing one target conversation does not finish the full candidate evaluation.':'Manual mode does not generate analyst findings. Review scores and edit the learning material yourself.')); }}
  $("trial-comparison").replaceChildren(
    table(
      ["Candidate", "Evaluation", "Laya", "Convergence", "Tokens", "Decision"],
      trials.map((t, i) => [
        String(i + 1),
        pct(t.report.validation_score),
        t.report.judge_score==null?"Not used":pct(t.report.judge_score),
        t.report.converged === false
          ? "Not reached"
          : t.report.convergence_round,
        t.report.tokens ?? "Unknown",
        button(
          t.accepted ? "Kept · review change" : "Rejected · review change",
          async () => {
            await reviewCandidate(t.directory);
            $('analyst-review').scrollIntoView({behavior:'smooth',block:'start'});
          },
        ),
      ]),
    ),
  );
  const previous = $("trial").value;
  $("trial").replaceChildren();
  trials.forEach((t, i) =>
    option(
      $("trial"),
      t.directory,
      "Candidate " + (i + 1) + (t.accepted ? " · Kept" : " · Rejected"),
    ),
  );
  data.progress.forEach((p) => {
    const path = "trials/" + p.trial;
    if (![...$("trial").options].some((o) => o.value === path))
      option(
        $("trial"),
        path,
        "Candidate " + (Number(p.trial) + 1) + " · Running",
      );
  });
  for (const path of data.trial_directories || [])
    if (![...$("trial").options].some((o) => o.value === path))
      option(
        $("trial"),
        path,
        "Candidate " + (Number(path.split("/").pop()) + 1) + " · Preparing",
      );
  for (const path of data.proposal_directories || [])
    option(
      $("trial"),
      path,
      "Analyst proposal " + (Number(path.split("/").pop()) + 1),
    );
  const activeDirectory=data.state.active_proposal>data.state.active_trial ? 'proposals/'+String(data.state.active_proposal).padStart(3,'0') : 'trials/'+String(data.state.active_trial??0).padStart(3,'0');
  if(retain && !pinnedCandidate && $('follow-live').checked && data.runtime_status==='running' && [...$('trial').options].some(o=>o.value===activeDirectory))
    $('trial').value=activeDirectory;
  else if (retain && [...$("trial").options].some((o) => o.value === previous))
    $("trial").value = previous;
  else if (data.state.incumbent !== undefined && trials[data.state.incumbent])
    $("trial").value = trials[data.state.incumbent].directory;
  if (!retain) {
    $("inspection").scrollIntoView({ behavior: "smooth" });
    await loadTrial();
  } else {
    draw();
    if (selectedTrial !== $("trial").value) await loadTrial();
    else await refreshSessions(keepSession);
  }
}
function currentReport() {
  return (
    selectedState?.state.trials?.find((t) => t.directory === $("trial").value)
      ?.report || selectedState?.active_reports?.[$("trial").value]
  );
}
function draw() {
  const report = currentReport();
  const conversationOnly=(report?.evaluation_mode || selectedState?.config.evaluation?.mode)==='conversation';
  const active = selectedState?.progress.find(
    (p) => "trials/" + p.trial === $("trial").value,
  )?.value;
  const keep = $("replicate").value,
    ids = [
      ...new Set([
        ...(report?.replicates || []).map((r) => r.replicate),
        ...(active ? [active.replicate] : []),
      ]),
    ];
  $("replicate").replaceChildren();
  ids.forEach((id) =>
    option($("replicate"), String(id), "Replicate " + (id + 1)),
  );
  if (ids.includes(Number(keep))) $("replicate").value = keep;
  let rounds = report?.replicates.find(
    (r) => String(r.replicate) === $("replicate").value,
  )?.rounds;
  if (!rounds)
    rounds =
      active && String(active.replicate) === $("replicate").value
        ? active.rounds
        : [];
  $("chart").replaceChildren();
  $("rounds-table").replaceChildren();
  if (!rounds.length) return;
  const NS = "http://www.w3.org/2000/svg",
    svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 800 260");
  svg.setAttribute("role", "img");
  svg.setAttribute(
    "aria-label",
    conversationOnly ? "Laya reasoning score by round" : "Score by round: green training, blue validation",
  );
  function add(tag, attrs, text) {
    const el = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
    if (text !== undefined) el.textContent = text;
    svg.append(el);
    return el;
  }
  const x = (i) => 50 + (i * 710) / Math.max(1, rounds.length - 1),
    y = (v) => 205 - 170 * v;
  [0, 0.5, 1].forEach((v) => {
    add("line", { x1: 50, x2: 770, y1: y(v), y2: y(v), stroke: "#334257" });
    add(
      "text",
      { x: 8, y: y(v) + 5, fill: "#b7c9e0", "font-size": 13 },
      pct(v),
    );
  });
  for (const [key, color] of (conversationOnly ? [["training", "#94e1c4"]] : [
    ["training", "#94e1c4"],
    ["validation", "#83b9ff"],
  ])) {
    add("polyline", {
      points: rounds.map((r, i) => `${x(i)},${y(r[key].score)}`).join(" "),
      fill: "none",
      stroke: color,
      "stroke-width": 3,
    });
    rounds.forEach((r, i) => {
      const c = add("circle", {
        cx: x(i),
        cy: y(r[key].score),
        r: 4,
        fill: color,
      });
      const title = document.createElementNS(NS, "title");
      title.textContent = `Round ${r.round} · ${key}: ${pct(r[key].score)}`;
      c.append(title);
    });
  }
  rounds.forEach((r, i) =>
    add(
      "text",
      {
        x: x(i),
        y: 228,
        fill: "#b7c9e0",
        "font-size": 12,
        "text-anchor": "middle",
      },
      r.round,
    ),
  );
  add("text", { x: 50, y: 18, fill: "#94e1c4", "font-size": 13 }, conversationOnly ? "Laya reasoning score (not combat performance)" : "Training");
  add(
    "text",
    { x: 160, y: 18, fill: "#83b9ff", "font-size": 13 },
    conversationOnly ? "" : "Validation (hidden from target)",
  );
  add("text", { x: 370, y: 252, fill: "#b7c9e0", "font-size": 13 }, "Round");
  $("chart").append(svg);
  $("rounds-table").append(
    table(
      conversationOnly ? ["Round","Laya score","Validity","Calls","Tokens"] : [
        "Round",
        "Training W/D/L",
        "Training",
        "Validation",
        "Previous versions",
        "Validity",
        "Calls",
        "Tokens",
      ],
      rounds.map((r) => [
        button(String(r.round), async () => {
          $("session").value = r.session;
          await history();
        }),
        ...(conversationOnly ? [pct(r.training.score)] : [`${r.training.wins}/${r.training.draws}/${r.training.losses}`,
        pct(r.training.score),
        pct(r.validation.score),
        pct(r.previous_versions?.score)]),
        r.validity,
        r.calls,
        r.input_tokens === null ? "Unknown" : r.input_tokens + r.output_tokens,
      ]),
    ),
  );
}
async function loadTrial() {
  $("live-output").replaceChildren();
  $("session-budget").replaceChildren();
  selectedTrial = $("trial").value;
  $("fork").disabled = selectedTrial.startsWith("proposals/");
  $("replicate").replaceChildren();
  const report = currentReport();
  const conversationOnly=(report?.evaluation_mode || selectedState?.config.evaluation?.mode)==='conversation';
  (report?.replicates || [{ replicate: 0 }]).forEach((r) =>
    option(
      $("replicate"),
      String(r.replicate),
      "Replicate " + (r.replicate + 1),
    ),
  );
  draw();
  if (!selectedTrial) return;
  if(selectedTrial.startsWith('trials/')) await reviewCandidate(selectedTrial);
  else if(selectedState?.proposals?.some(p=>p.directory===selectedTrial)) await reviewCandidate(selectedTrial);
  await refreshSessions();
}
async function refreshSessions(keepSession) {
  if (!selectedTrial) return;
  const requestedStudy = selected,
    requestedTrial = selectedTrial;
  const rows = await api(qs("/api/sessions", { trial: selectedTrial }));
  if (selected !== requestedStudy || selectedTrial !== requestedTrial) return;
  sessionRows = rows;
  sessionRows.sort(
    (a, b) =>
      (a.replicate || 0) - (b.replicate || 0) ||
      (a.generation || 0) - (b.generation || 0),
  );
  $("session").replaceChildren();
  sessionRows.forEach((s) =>
    option(
      $("session"),
      s.id,
      s.id.startsWith("analyst")
        ? "Analyst"
        : `Round ${s.generation + 1} · Replicate ${Number(s.id.match(/-r(\d+)/)?.[1] || 0) + 1} · ${s.status}`,
    ),
  );
  if (keepSession && sessionRows.some((s) => s.id === keepSession))
    $("session").value = keepSession;
  else if ($("session").options.length)
    $("session").selectedIndex = $("session").options.length - 1;
  const chosen = sessionRows.find((s) => s.id === $("session").value);
  if (
    chosen &&
    [...$("replicate").options].some(
      (o) => Number(o.value) === chosen.replicate,
    )
  ) {
    $("replicate").value = chosen.replicate;
    draw();
  }
  await history(
    keepSession && $("session").value === keepSession
      ? historyOffset
      : undefined,
    !!keepSession,
  );
}
async function reveal(title, value) {
  $("dialog-title").textContent = title;
  dialogPayload=typeof value === 'string' ? value : json(value);
  $('dialog-content').replaceChildren(formatted(value));
  if (!$("dialog").open) $("dialog").showModal();
}
async function history(offset, refresh = false) {
  const requestedStudy=selected;
  const params = { trial: selectedTrial, session: $("session").value },
    view = $("view").value;
  const identity =
    selected + "|" + selectedTrial + "|" + params.session + "|" + view;
  const same = refresh && historyIdentity === identity;
  const following =
    same &&
    $('follow-live').checked && $('history').scrollHeight-$('history').scrollTop-$('history').clientHeight<100;
  if (same && view === "conversation" && !following) { $("live-status").textContent="Reading earlier messages · use Latest to follow"; return; }
  if (same && view === "conversation" && following) {
    const indices = [
      ...$("history").querySelectorAll("[data-message-index]"),
    ].map((el) => Number(el.dataset.messageIndex));
    if (indices.length) offset = Math.max(...indices) + 1;
  }
  if (!same) {
    $("history").replaceChildren();
    historyIdentity = identity;
    historyOffset = offset;
  }
  if (view === "files") {
    if (same) return;
    const files = await api(qs("/api/files", params)),
      select = node("select");
    option(select, "", "Select a source snapshot or report");
    files
      .filter(
        (f) =>
          !f.path.startsWith("artifacts/") &&
          (f.path.endsWith(".leek") ||
            f.path.endsWith("team.json") ||
            f.path.endsWith("assessment.json") ||
            f.path === "report.json" ||
            f.path === "calibration.json"),
      )
      .forEach((f) => option(select, f.path, `${f.path} (${f.bytes} bytes)`));
    select.onchange = guard(async () => {
      if (!select.value) return;
      const data = await api(
        qs("/api/file", { ...params, path: select.value }),
      );
      await reveal(
        select.value,
        data.content + (data.truncated ? "\n[First 1 MB shown]" : ""),
      );
    });
    $("history").append(select);
    return;
  }
  if (view === "fights") {
    const fights = await api(qs("/api/fights", params));
    $("history").replaceChildren(
      table(
        ["Panel", "Opponent", "Own side", "Seed", "Result", ""],
        fights.map((f) => [
          f.panel,
          f.opponent,
          f.side,
          f.seed,
          f.result.status === "completed"
            ? f.result.winner_side === -1
              ? "Draw"
              : f.result.winner_side === f.side
                ? "Win"
                : "Loss"
            : f.result.status,
          button("Inspect fight", async () =>
            reveal(
              "Fight events and metrics",
              await api(qs("/api/fight", { ...params, path: f.path })),
            ),
          ),
        ]),
      ),
    );
    return;
  }
  if (!params.session) return;
  if (view === "events") {
    if (same) return;
    const events = await api(
      qs("/api/events", { ...params, offset: offset || 0 }),
    );
    events.forEach((event) =>
      $("history").append(
        button(`${event.id} · ${event.kind}`, async () =>
          reveal(
            event.kind,
            await api(qs("/api/event", { ...params, id: event.id })),
          ),
        ),
      ),
    );
    if (events.length === 50)
      $("history").append(
        button("Next events", () => history((offset || 0) + 50)),
      );
    return;
  }
  const data = await api(
    qs("/api/conversation", {
      ...params,
      ...(offset !== undefined ? { offset } : $("follow-live").checked ? {tail:1} : {}),
    }),
  );
  if(requestedStudy!==selected || identity!==historyIdentity)return;
  lastConversationTotal=data.total;
  if (!same) historyOffset = data.offset;
  historyNext = data.next;
  const existing = new Map(
    [...$("history").querySelectorAll("[data-message-index]")].map((el) => [
      Number(el.dataset.messageIndex),
      el,
    ]),
  );
  const controls = node("div", undefined, "actions");
  controls.append(
    button("Initial prompt", () => {$("follow-live").checked=false;return history(0)}),
    button("This round", () => {$("follow-live").checked=false;return history(data.round_start)}),
  );
  if (data.offset > 0)
    controls.append(
      button("Previous messages", () => history(Math.max(0, data.offset - 25))),
    );
  if (data.next !== null)
    controls.append(button("Next messages", () => history(data.next)));
  const old = $("history").querySelector(".actions");
  if (old) old.replaceWith(controls);
  else $("history").append(controls);
  data.messages.forEach((message) => {
    if (existing.has(message.index)) return;
    const div = node(
      "div",
      undefined,
      "message " + message.role + (same ? " arrival" : ""),
    );
    div.dataset.messageIndex = message.index;
    div.append(
      node(
        "h3",
        `${message.index + 1} · ${message.role === "assistant" ? "Model" : message.role === "tool" ? "Tool result" : message.role === "system" ? "System" : "Arena"}${message.time ? " · " + new Date(message.time * 1000).toLocaleTimeString() : ""}`,
      ),
    );
    if (message.file_exchange) {
      const info = message.file_exchange,
        writing = info.name === "write_file";
      div.append(
        node(
          "p",
          `${writing ? (info.saved ? "Saved" : "Rejected write") : "Read"} ${info.path}${writing ? " · " + info.characters + " characters" : " · characters " + info.offset + "–" + info.end_offset + " · " + (info.truncated ? "partial read, next offset " + info.next_offset : "end of file")}`,
        ),
      );
      const details = node("details"),
        summary = node(
          "summary",
          writing ? "Written content and diff" : "Excerpt sent to the model",
        );
      details.append(summary);
      let loaded = false;
      details.ontoggle = guard(async () => {
        if (!details.open || loaded) return;
        loaded = true;
        try {
          const record = await api(
            qs("/api/tool-exchange", { ...params, index: message.index }),
          );
          details.append(
            node(
              "pre",
              writing
                ? (record.diff || "No changes.") +
                    "\n\nComplete written file:\n" +
                    record.after
                : record.content || record.error || "No content returned.",
            ),
          );
        } catch (error) {
          loaded = false;
          throw error;
        }
      });
      div.append(details);
    }
    message.blocks.forEach((block, index) => {
      if (block.hidden || (message.file_exchange && block.kind === "tool_result")) return;
      const details = node("details"),
        summary = node("summary", block.label || block.kind);
      details.append(summary);
      let loaded = false;
      details.ontoggle = guard(async () => {
        if (!details.open || loaded) return;
        loaded = true;
        try {
          const value = await api(
            qs("/api/message", {
              ...params,
              index: message.index,
              block: index,
            }),
          );
          details.append(
            formatted(value),
          );
        } catch (error) {
          loaded = false;
          throw error;
        }
      });
      div.append(details);
    });
    if (!message.blocks.length)
      div.append(
        node(
          "p",
          "No text returned. The journal contains the exact request and response.",
        ),
      );
    $("history").append(div);
  });
  if (same && following) {
    const cards = [...$("history").querySelectorAll("[data-message-index]")];
    cards
      .slice(0, Math.max(0, cards.length - 200))
      .forEach((el) => el.remove());
    historyOffset = Number(
      $("history").querySelector("[data-message-index]")?.dataset
        .messageIndex || historyOffset,
    );
  }
  if (same && following) $('history').scrollTo({top:$('history').scrollHeight,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
}
$("start").onclick = guard(async () => {
  $("start").disabled = true;
  try {
    const value = config();
    const result = await api("/api/start", {
      config: value,
      automatic: $("mode").value !== "manual",
      keys: keys(),
    });
    await listing();
    await inspect(result.id);
  } finally {
    $("start").disabled = false;
  }
});
$("resume").onclick = guard(async () => {
  await api("/api/resume", { id: selected, keys: keys() });
  await listing();
});
$("stop").onclick = guard(async () => {
  await api("/api/stop", { id: selected });
  await listing();
});
$("fork").onclick = guard(async () => {
  const candidate =
    selectedTrial ||
    selectedState.state.trials?.[selectedState.state.incumbent]?.directory;
  const value = candidate?.startsWith("trials/")
    ? JSON.parse(
        (
          await api(
            qs("/api/file", { trial: candidate, path: "calibration.json" }),
          )
        ).content,
      ).config
    : selectedState.config;
  baselineId = selected;
  localStorage.setItem("arena-calibration-baseline", selected);
  fill(value);
  $("setup").open=true;
  $("name").value = value.name + " · revised";
  $("editor").scrollIntoView({ behavior: "smooth" });
  $("prompt").focus();
});
$("show-prompt").onclick = guard(async () => {
  if (selectedTrial.startsWith("proposals/")) {
    const value = await api(
      qs("/api/message", {
        trial: selectedTrial,
        session: "analyst-r0",
        index: 0,
        block: 0,
      }),
    );
    await reveal("Analyst system prompt", value.content || value);
    return;
  }
  const value = await api(qs("/api/candidate", { trial: selectedTrial }));
  await reveal("Initial prompt and reference changes", {prompt:value.config.prompt,reference_documents:value.config.reference_documents || {},document_diffs:value.document_diffs || {}});
});
$("tool-requests").onclick = guard(async () => {
  const reports = await api(qs("/api/tool-requests"));
  const text = reports.flatMap(report=>report.requests.map((request,index)=>
    `Candidate ${report.candidate} · ${index+1}. ${request.kind} · ${request.tool || "Arena tools"}\nProblem: ${request.problem}\nProposed change: ${request.proposed_change}\nExpected benefit: ${request.expected_benefit || "Not specified"}\nEvidence:\n${(request.evidence || []).join("\n")}\n`)).join("\n");
  await reveal("Tool improvement report", text || "No tool improvement requests recorded. Recommendations are reports only; they do not install or modify tools.");
});
$("log").onclick = guard(async () => {
  const data = await api(qs("/api/log"));
  await reveal("Run log · last 128 KB", data.content);
});
$("export").onclick = guard(async () => {
  const blob = new Blob([json(config()) + "\n"], { type: "application/json" }),
    a = node("a");
  a.href = URL.createObjectURL(blob);
  a.download = "calibration.json";
  a.click();
  URL.revokeObjectURL(a.href);
});
$("refresh").onclick = guard(async () => {
  await listing();
  if (selected) await inspect(selected, true);
});
$("trial").onchange = guard(async()=>{pinnedCandidate=true;await loadTrial()});
$("session").onchange = guard(() => history());
$("view").onchange = guard(() => history());
$("replicate").onchange = guard(async () => {
  draw();
  const sid = sessionRows.find((s) =>
    s.id.includes("-r" + $("replicate").value + "-"),
  );
  if (sid) {
    $("session").value = sid.id;
    await history();
  }
});
$("close").onclick = () => $("dialog").close();
$("copy").onclick = guard(() =>
  navigator.clipboard.writeText(dialogPayload),
);
$("error").onclick = () => ($("error").hidden = true);
function setMode() {
  updateLoopPlan();
  const active = $("mode").value === "automatic" || ($('reward-mode').value!=='fights' && $('judge-evidence').value==='summary');
  $("analyst-label").hidden = !active;
  $("candidate-count-label").hidden=$("mode").value==='manual';
  $("analyst-key").closest("label").hidden = !active;
  $("analyst-json").closest("label").hidden = !active;
  if ($("mode").value === "grid" && $("parameter-grid").value.trim() === "{}")
    $("parameter-grid").value = json({ temperature: [0, 0.3, 0.7] });
}
$("mode").onchange = setMode;
$("judge-evidence").onchange=setMode;$("reward-mode").onchange=setMode;
$("scenario-preset").onchange = () => {
  const preset = boot.scenarios[$("scenario-preset").value];
  if (preset) $("scenario").value = json(preset);
};
for (const role of ["target", "analyst"])
  $(role).onchange = () => {
    if (role === "target")
      $("simulation-note").textContent =
        boot.participants.find((p) => p.spec.id === $(role).value).spec
          .provider === "mock"
          ? "Mock models are offline fixtures. Their scores do not measure a real model’s learning."
          : "";
    $(role + "-json").value = json(
      boot.participants.find((p) => p.spec.id === $(role).value).spec,
    );
  };
guard(async () => {
  boot = await api("/api/bootstrap");
  if (!boot.participants.some((p) => p.spec.id === boot.config.target.id))
    boot.participants.unshift({ spec: boot.config.target });
  for (const role of ["target", "analyst"])
    boot.participants.forEach((p) =>
      option($(role), p.spec.id, p.spec.id + " · " + p.spec.provider),
    );
  fill(boot.config);
  setMode();
  await listing();
  setInterval(
    guard(async () => {
      if (
        polling || document.hidden ||
        $("dialog").open
      )
        return;
      polling = true;
      try {
        const rows = await listing();
        const row = rows.find((r) => r.id === selected),
          signature = JSON.stringify(row);
        if (
          selected &&
          row &&
          (row.running || signature !== lastStudySignature)
        ) {
          await inspect(selected, true);
          lastStudySignature = signature;
        }
      } finally {
        polling = false;
      }
    }),
    4000,
  );
})();

function updateLoopPlan() {
  const rounds=$('round-stop').value==='manual'?'until manually stopped':($('round-stop').value==='plateau'?'up to ':'')+$('rounds').value+' script round(s)';
  const repeats=Number($('replicates').value)||1, candidates=$('candidate-count').value || 'unlimited';
  $('loop-plan').textContent=$('mode').value==='automatic'
    ? `${rounds} × ${repeats} fresh repetition(s) → RL-selected edit → analyst proposal → reward → policy update → repeat (${candidates} candidates). Stop on reward plateau if enabled, or manually. No manual relaunch between candidates.`
    : $('mode').value==='grid' ? `${rounds} × ${repeats} fresh repetition(s) per parameter configuration, up to ${candidates} configurations. No analyst editing.`
    : `${rounds} × ${repeats} fresh repetition(s) for this prompt. After evaluation, edit and launch the next candidate manually.`;
}
function observationPreset(quick) {
  $('round-stop').value=quick?'fixed':'plateau';
  $('rounds').value=quick?'1':'10';$('minimum').value=quick?'1':'3';
  if(quick){$('replicates').value='1';$('short-budget').click();}
  $('round-penalty').value=quick?'0':'0.002';
  updateRoundStop();
}
$('quick-observation').onclick=()=>observationPreset(true);
$('learning-observation').onclick=()=>observationPreset(false);
for(const id of ['rounds','replicates','candidate-count'])$(id).addEventListener('input',updateLoopPlan);
function updateRoundStop() {
  const mode = $("round-stop").value;
  $("rounds").disabled = mode === "manual";
  for (const id of ["minimum", "patience", "epsilon"])
    $(id).disabled = mode !== "plateau";
  if (mode === "manual") $("replicates").value = 1;
  $("replicates").disabled = mode === "manual";
  updateLoopPlan();
}
$("round-stop").onchange = updateRoundStop;

function renderLearning(state){
  const mount=$('rl-progress');mount.replaceChildren();
  const episodes=(state.trials||[]).filter(t=>t.rl);
  mount.append(node('p',episodes.length?`${episodes.length} learning episodes · ${(state.stop_reason || 'Learning in progress').replaceAll('_',' ')} · Best candidate ${(state.incumbent??0)+1}`:'Baseline evaluation. Learning starts with the first prompt revision.'));
  if(!episodes.length)return;
  const NS='http://www.w3.org/2000/svg',svg=document.createElementNS(NS,'svg');svg.setAttribute('viewBox','0 0 800 170');svg.setAttribute('role','img');svg.setAttribute('aria-label','Reward per prompt revision, zero at the middle line');
  const line=document.createElementNS(NS,'line');for(const [k,v]of Object.entries({x1:30,x2:770,y1:85,y2:85,stroke:'currentColor',opacity:'.3'}))line.setAttribute(k,v);svg.append(line);
  const max=Math.max(.01,...episodes.map(t=>Math.abs(t.rl.reward)));
  const path=document.createElementNS(NS,'polyline');path.setAttribute('fill','none');path.setAttribute('stroke','#6ecbb2');path.setAttribute('stroke-width','3');path.setAttribute('points',episodes.map((t,i)=>`${30+i*740/Math.max(1,episodes.length-1)},${85-t.rl.reward/max*65}`).join(' '));svg.append(path);
  episodes.forEach((t,i)=>{const dot=document.createElementNS(NS,'circle');dot.setAttribute('cx',30+i*740/Math.max(1,episodes.length-1));dot.setAttribute('cy',85-t.rl.reward/max*65);dot.setAttribute('r','4');dot.setAttribute('fill','#6ecbb2');const title=document.createElementNS(NS,'title');title.textContent=`Episode ${i+1}: ${t.rl.reward.toFixed(4)}`;dot.append(title);svg.append(dot)});
  for(const [label,y]of [[`+${max.toFixed(3)}`,16],['0',82],[`−${max.toFixed(3)}`,165]]){const text=document.createElementNS(NS,'text');text.textContent=label;text.setAttribute('x','4');text.setAttribute('y',y);text.setAttribute('fill','currentColor');text.setAttribute('font-size','11');svg.append(text)}
  mount.append(svg);
  mount.append(table(['Episode','Edit action','Exploration','Reward','Learned value'],episodes.slice(-30).map((t,i)=>[Math.max(0,episodes.length-30)+i+1,t.rl.action,t.rl.exploring?'Yes':'No',t.rl.reward.toFixed(4),t.rl.q_after.toFixed(4)])));
  if(episodes.length>30)mount.append(node('p','Showing the latest 30 episodes in the table; the chart covers the full history.'));
  const policy=node('details');policy.append(node('summary','Learned policy'),node('pre',json(state.policy),'record-code'));mount.append(policy);
}
