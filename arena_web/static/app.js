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
    : `Round ${Number(value) + 1}: improved strategy`;
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
async function api(path, args = {}, post = false) {
  const response = await fetch(
    path + (post ? "" : Object.keys(args).length ? "?" + query(args) : ""),
    post
      ? {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Arena-Token": S.boot.token,
          },
          body: JSON.stringify(args),
        }
      : {},
  );
  const value = await response.json();
  if (!response.ok)
    throw new Error(value.error || `HTTP error ${response.status}`);
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
      "entrant_model",
      "opponent_model",
      "round",
      "scored",
    ].map((k) => [k, q.get(k) || ""]),
  );
  S.version = null;
  S.versions = null;
  S.previous = null;
  S.file = null;
  S.matchPath = null;
  renderRoute().catch(showError);
}
function showError(error) {
  toast(error.message, true);
  $("#main").classList.remove("busy");
}
async function refreshBoot() {
  S.boot = await api("/api/bootstrap");
  S.equipment ||= await api("/api/equipment");
  syncLiveMode();
  updateChrome();
}
function syncLiveMode() {
  S.livePreferences ||= {};
  if (activeJobs().some((job) => job.run === S.run)) S.autoLiveRun = S.run;
  S.follow = S.livePreferences[S.run] ?? S.autoLiveRun === S.run;
}
function runningPhase(d) {
  const states = d.sessions,
    config = d.metadata.config;
  if (!config) return "Evaluating frozen strategies";
  const generation = Math.max(0, ...states.map(s => Number(s.generation || 0)));
  const round = states.filter(s => Number(s.generation || 0) === generation);
  const expected = config.models.length * config.replicates *
    (generation ? (config.improvement_conditions?.length || 2) : 1);
  const finished = round.filter(s => s.status !== "running").length;
  if (round.length < expected || round.some(s => s.status === "running"))
    return `Round ${generation + 1} · ${finished}/${expected} preparations finished · Evaluation waits for all`;
  return `Round ${generation + 1} · Evaluating frozen strategies`;
}
function activeJobs() {
  return S.boot.jobs.filter((j) => ["running", "stopping"].includes(j.status));
}
function updateChrome() {
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
  $$("[data-nav]").forEach((n) =>
    n.classList.toggle(
      "active",
      n.dataset.nav ===
        (S.view === "run" || S.view === "editor" ? "competitions" : S.view),
    ),
  );
  $("#breadcrumb").textContent =
    "" +
    ({
      dashboard: "Overview",
      participants: "Participants",
      competitions: "Competitions",
      run: "Exploration",
      editor: "Configuration",
      compare: "Comparison",
      help: "Guide",
    }[S.view] || "Overview");
}
async function renderRoute() {
  hideHelp();
  const epoch = ++S.epoch;
  clearInterval(replayTimer);
  replayTimer = null;
  R = null;
  updateChrome();
  if (S.view === "run") {
    syncLiveMode();
    const d = await api("/api/run", { run: S.run }).catch(async (error) => {
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
    return;
  }
  if (S.view === "editor" && !S.equipment) {
    S.equipment = await api("/api/equipment");
    if (epoch !== S.epoch) return;
  }
  const renderers = {
    dashboard: dashboard,
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
    return `<tr><td><button class="table-button" data-action="open-run" data-run="${e(r.id)}">${e(r.name)}</button><small>${e(r.id)}</small></td><td>${job && ["running", "stopping"].includes(job.status) ? status(job.status === "failed" && r.report?.incomplete ? "incomplete" : job.status) : r.error ? status("failed") : r.complete ? status("completed") : badge("Review needed", "orange")}</td><td>${r.simulated === true ? badge("Simulation", "blue") : r.simulated === false ? badge("Real API calls", "orange") : badge("Strategies")}</td><td class="numeric">${fmt(r.report?.sessions ?? r.models)}</td><td class="numeric">${fmt(completed(r.report))}</td><td class="numeric">${r.report?.cost_usd === undefined ? "N/A" : money(r.report.cost_usd)}</td><td>${date(r.created_at)}</td></tr>`;
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
function dashboard() {
  const runs = S.boot.runs.filter((r) => !r.archived),
    known = runs.filter((r) => r.report?.cost_usd != null),
    unknown = runs.filter((r) => r.report && r.report.cost_usd === null).length;
  return (
    head(
      "Overview",
      "Competitions, participants and results.",
      btn("＋ New competition", "new-competition", "", true),
    ) +
    `<div class="metrics">${metric("Competitions", fmt(runs.length), `${activeJobs().length} running`, "⚑")}${metric("Configured participants", fmt(S.boot.participants.length), "Reusable profiles", "♧")}${metric("Completed matches", fmt(runs.reduce((n, r) => n + completed(r.report), 0)), "All evaluation stages", "⚔")}${metric("Known API cost", money(known.reduce((n, r) => n + Number(r.report.cost_usd), 0)), unknown ? `${unknown} costs still unknown` : "Excludes infrastructure; includes mock runs", "↗")}</div>` +
    (!S.boot.engine.ready
      ? notice(
          `The engine is not ready. Existing results are still readable. Run <code>python scripts/bootstrap.py</code> after installing JDK 25. ${e(S.boot.engine.error)}`,
          "warn",
        )
      : "") +
    `<section class="panel flush"><div class="panel-head"><div><h2>Recent competitions</h2><p>Original runs. Exported copies are excluded.</p></div>${btn("View all", "go", 'data-view="competitions"')}</div>${runTable(runs.slice(0, 8))}</section>` +
    `<div class="grid two"><section class="panel"><h2>Try the offline demo</h2><p class="muted">Mock participants, real matches, no API calls.</p>${btn("Configure demo", "new-demo")}</section><section class="panel"><h2>Reading scores</h2><p class="muted">A win earns 1 point, a draw 0.5, a loss 0. A score of 70% means 70% of available points, excluding mirrors.</p>${btn("Scoring guide", "go", 'data-view="help"')}</section></div>`
  );
}
function participants() {
  return (
    head(
      "Participants",
      "Models, parameters and prices used by competitions.",
      btn("＋ Add participant", "new-participant", "", true),
    ) +
    `<section class="panel flush">${table(
      [
        "Participant",
        "Provider / model",
        "Input / output price",
        "API key",
        "",
      ],
      S.boot.participants.map(
        ({ spec: m, key_configured, key_optional }) =>
          `<tr><td><strong>${e(m.id)}</strong><small>${m.provider === "mock" ? "Mock participant" : "Configured model"}</small></td><td>${e(m.provider)}<small>${e(m.model || m.profile)}</small></td><td>${m.pricing ? `${e(m.pricing.input_per_million)} / ${e(m.pricing.output_per_million)} $<small>Per million tokens · ${e(m.pricing.date)}</small>` : "No API calls"}</td><td>${m.provider === "mock" ? "N/A" : badge(key_optional && !key_configured ? "Not required (local)" : key_configured ? "Configured" : "Missing", key_configured || key_optional ? "green" : "orange")}</td><td><div class="actions">${btn("Edit", "edit-participant", `data-id="${e(m.id)}"`)}<button class="icon-button" data-action="delete-participant" data-id="${e(m.id)}" title="Remove this profile" aria-label="Remove ${e(m.id)}">×</button></div></td></tr>`,
      ),
    )}</section>` +
    notice(
      "Enter dated prices in USD per million tokens. Keys entered here stay in server memory and are not saved to files.",
    ) +
    `<section class="panel"><h2>Profiles and submissions</h2><p class="muted">A profile selects a model and its settings. Each repetition starts an independent conversation and produces a strategy. Mock profiles use predefined scripts.</p></section>`
  );
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
function competitions() {
  return (
    head(
      "Competitions",
      "Saved settings and run history.",
      btn("＋ New competition", "new-competition", "", true),
    ) +
    `<section class="panel flush"><div class="panel-head"><div><h2>Saved configurations</h2><p>Editable until launch. Each run keeps its own copy.</p></div></div>${
      S.boot.drafts.length
        ? table(
            ["Configuration", "Participants", "Repetitions", "Stages", ""],
            S.boot.drafts.map(
              (d) =>
                `<tr><td><strong>${e(d.config.name)}</strong><small>Updated ${date(d.updated_at)}</small></td><td>${d.config.models.map((m) => e(m.id)).join(", ")}</td><td>${d.config.replicates}</td><td>${d.config.generations === null ? "Until manual stop" : `${d.config.generations || 1} round(s)`}</td><td><div class="actions">${btn("Configure", "edit-draft", `data-id="${e(d.id)}"`)}${btn("▷ Launch", "launch", `data-id="${e(d.id)}"`, true)}${btn("Remove", "delete-draft", `data-id="${e(d.id)}"`)}</div></td></tr>`,
            ),
          )
        : empty(
            "No saved configurations",
            "Use the demo settings or create a configuration.",
            btn("Create configuration", "new-competition"),
          )
    }</section>` +
    `<section class="panel flush"><div class="panel-head"><div><h2>Run history</h2><p>Exported copies are excluded from aggregates.</p></div><input type="search" id="run-search" placeholder="Search competitions..." aria-label="Search competitions"></div><div id="run-table">${runTable(S.boot.runs)}</div></section>` +
    (S.boot.jobs.length
      ? `<section class="panel flush"><div class="panel-head"><h2>Runs started from this interface</h2></div>${table(
          ["Name", "Status", "Started", ""],
          S.boot.jobs
            .slice(0, 12)
            .map(
              (j) =>
                `<tr><td>${e(j.name)}<small>${e(j.run)}</small></td><td>${status(j.status)}</td><td>${date(j.started_at)}</td><td>${btn("Journal", "job-log", `data-id="${e(j.id)}"`)}</td></tr>`,
            ),
        )}</section>`
      : "")
  );
}
function openDialog(title, subtitle, body) {
  hideHelp();
  $("#dialog-content").innerHTML =
    `<div class="dialog-head"><div><h2>${e(title)}</h2><p>${e(subtitle)}</p></div><button class="icon-button" data-action="close-dialog" aria-label="Close">×</button></div><div id="dialog-error" class="notice error dialog-error" role="alert" tabindex="-1" hidden></div>${body}`;
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
function participantDialog(identifier = null, provider = null) {
  const m = identifier
    ? S.boot.participants.find((p) => p.spec.id === identifier).spec
    : {};
  S.editParticipant = identifier;
  const p = provider || m.provider || "mock",
    pricing = m.pricing || {};
  openDialog(
    identifier ? "Edit participant" : "New participant",
    "",
    `<form data-form="participant"><div class="form-grid">${field("Participant ID", "id", m.id || "", "text", "Letters, digits and hyphens; up to 40 characters.", `required pattern="[a-zA-Z0-9][a-zA-Z0-9_-]{0,39}" ${identifier ? "readonly" : ""}`)}${selectField(
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
     : `<h3 class="field full">API connection</h3>${field("API key environment variable", "api_key_env", m.api_key_env || (p === "anthropic" ? "ARENA_ANTHROPIC_KEY" : p === "gemini" ? "ARENA_GEMINI_KEY" : "ARENA_OPENAI_KEY"), "text", "Name of the server environment variable containing the key, or the name under which to store a session key entered below.", "required")}<label class="field full">API key (this server session only)<input name="secret" type="password" autocomplete="new-password" placeholder="Optional for local compatible servers; otherwise leave blank to keep the key"><small>Not returned to the browser or written to configuration files.</small></label>${p === "openai-compatible" ? field("Full API endpoint", "endpoint", m.endpoint || "", "url", "Ollama: http://localhost:11434/v1/chat/completions. HTTP is allowed on loopback; remote servers require HTTPS. API keys are optional for local compatible servers.", "required") : m.endpoint ? field("HTTPS endpoint", "endpoint", m.endpoint, "url") : ""}<h3 class="field full">Model</h3><div class="field full">${btn("Load models", "list-models")}<label class="field" hidden id="model-search-field">Search models<input type="search" id="model-search" placeholder="Filter by model name or ID"></label><div id="available-models" class="model-catalog" role="group" aria-label="Available models" hidden></div><small id="model-list-status">Load models available to the configured API key. You can also enter an ID manually.</small><details id="excluded-models" hidden><summary>Excluded models</summary><div id="excluded-model-list"></div></details></div>${field("Exact model ID", "model", m.model || "", "text", "The exact ID accepted by the API.", "required")}${field("Input price / million tokens ($)", "input_price", pricing.input_per_million ?? "", "number", "", 'required min="0" step="any"')}${field("Output price / million tokens ($)", "output_price", pricing.output_per_million ?? "", "number", "", 'required min="0" step="any"')}${field("Price date", "pricing_date", pricing.date || new Date().toISOString().slice(0, 10), "date", "", "required")}${field("Cache read price / million ($), optional", "cached_price", pricing.cached_input_per_million ?? "", "number", "Blank uses the standard input price.", 'min="0" step="any"')}${field("Cache write price / million ($), optional", "creation_price", pricing.cache_creation_per_million ?? "", "number", "", 'min="0" step="any"')}${field("Maximum input per call (tokens)", "max_input_tokens_per_call", m.max_input_tokens_per_call ?? "", "number", "Optional. Blank disables local input admission limits.", 'min="1"')}${field("Maximum output per call (tokens)", "max_output_tokens", m.max_output_tokens ?? "", "number", p === "anthropic" ? "Required by Anthropic (max_tokens)." : "Optional. Blank uses the API default; one call may exceed the remaining financial budget.", p === "anthropic" ? 'required min="1"' : 'min="1"')}${field("Call timeout (seconds)", "timeout_seconds", m.timeout_seconds || 60, "number", "", 'required min="1" max="3600"')}${field("Retries on HTTP 429", "max_retries", m.max_retries ?? 1, "number", "Calls with unknown outcomes are not retried automatically.", 'required min="0" max="3"')}${p === "anthropic" ? `<p class="muted">Seed: not available in the Anthropic API.</p>` : field("Model seed", "model_seed", m.parameters?.seed ?? (identifier ? "" : 0), "number", p === "openai-compatible" ? "Server support varies. Identical output is not guaranteed." : "Sent with every call when supported by the model. Identical output is not guaranteed.", 'min="0" max="2147483647"')}<label class="field full">Model parameters (JSON)<textarea name="parameters" class="mono">${e(pretty(m.parameters || {}))}</textarea><small>API-specific options such as temperature and top_p. Set the seed above.</small></label>`
 }</div><div class="form-footer">${btn("Cancel", "close-dialog")}<button type="submit" class="button primary">Save participant</button></div></form>`,
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
    `<form data-form="competition" id="competition-form"><div class="grid asymmetric"><div><section class="panel"><h2>Name and participants</h2><p class="muted">Each repetition starts an independent conversation.</p><div class="form-grid">${field("Competition name", "name", c.name, "text", "", "required")}${field("Repetitions per participant", "replicates", c.replicates, "number", "", 'required min="1" max="20"')}${selectField(
      "Round stopping rule",
      "round_stop",
      [
        ["fixed", "Fixed number of rounds"],
        ["manual", "Continue until I press Stop"],
      ],
      c.generations === null ? "manual" : "fixed",
    )}${field("Number of rounds", "generations", c.generations ?? 2, "number", "Includes the initial round. Each later round continues both improvement tracks.", c.generations === null ? 'disabled min="1" step="1"' : 'min="1" step="1"')}</div><h3 class="section-label">Selected participants</h3>${S.choiceModels.map((m) => `<label class="choice"><input type="checkbox" name="participant" value="${e(m.id)}" ${c.models.some((v) => v.id === m.id) ? "checked" : ""}><span><strong>${e(m.id)}</strong><small>${e(m.provider)} · ${e(m.model || m.profile)}</small></span></label>`).join("")}${btn("Manage profiles", "go", 'data-view="participants"')}</section>
 <section class="panel"><h2>Scenario</h2><div class="scenario-presets">${btn("Simple duel · level 300", "preset-simple")}${btn("Dream team · saved preset", "preset-dream")}${btn("LLM builds its team", "preset-llm")}</div><p id="preset-status" role="status" class="muted">${c.scenario.source ? `Based on public team · original snapshot ${e(c.scenario.source.snapshot_sha256.slice(0, 12))}. The roster below can be edited. Published final stats include component bonuses; component selections and alteration deltas are preserved without adding bonuses twice.` : c.scenario.preset === "llm-team" ? "Each LLM freely chooses 1–4 leeks, their levels (1–301), stats, scripts, equipment and component alterations. preview_build and validate_team check official game rules. No character stats or equipment lists are imposed." : "Starting preset: one level-300 gunner per team, direct-damage weapons, no chips. Edit each character independently below."}</p>${c.scenario.source ? raw(c.scenario.source, "Public source and frozen snapshot") : ""}<details><summary>Refresh or replace the saved Dream team</summary>${btn("Refetch current top farmer", "preset-dream-refresh")}<p class="muted">Only this button reads the current farmer ranking and fetches four leeks of its first player. The saved preset is reused until an explicit refresh; existing competitions keep their frozen roster.</p><p class="muted">Use scripts/import_dream_team.py on a machine with access to leekwars.com, then paste its snapshot JSON here.</p><textarea id="dream-snapshot" class="mono" aria-label="Public team snapshot JSON" rows="4"></textarea>${btn("Import snapshot", "preset-dream-json")}</details></section><section class="panel"><h2>Match rules</h2><p class="muted">Matches alternate sides. Use a shared roster or let each LLM build its own team under official game rules.</p><div class="form-grid">${selectField(
   "Team setup",
   "team_mode",
   [
     ["fixed", "Same roster for every participant"],
     ["participant", "Participants choose teams and equipment"],
   ],
   c.scenario.team_selection ? "participant" : "fixed",
 )}${field("Team size", "team_size", c.scenario.team_size, "number", "Exact size in shared mode; maximum size when participants choose.", 'required min="1" max="8"')}${field("Maximum turns", "max_turns", c.scenario.max_turns, "number", "", 'required min="1" max="1000"')}${field("Initial / feedback seeds", "seeds", c.seeds.join(", "), "text", "Map generation seeds, for example 101, 202.", "required")}${field("Final evaluation seeds", "final_seeds", (c.final_seeds || []).join(", "), "text", "Separate from initial strategy seeds and training seed 17.")}</div><div id="team-selection-rules" ${c.scenario.team_selection ? "" : "hidden"}><p class="muted">Each LLM freely chooses 1–4 leeks: levels from 1 to 301, names, scripts, capital allocations, weapons, chips, components and alterations. Only official game rules apply. Character stats below are not imposed on its team. Preparation tests use a separate fixed reference team.</p></div><label class="check" style="margin-top:15px"><input type="checkbox" name="include_mirrors" ${c.include_mirrors ? "checked" : ""}>Include mirror matches (excluded from score)</label><fieldset id="fixed-roster" style="border:0;padding:0;margin-top:15px" ${c.scenario.team_selection ? "hidden disabled" : ""}>${statsEditor(c.scenario)}</fieldset><details><summary>Custom map</summary><div class="form-grid" style="margin-top:15px"><label class="field full">Custom map (JSON, optional)<textarea name="map" class="mono">${c.scenario.map ? e(pretty(c.scenario.map)) : ""}</textarea><small>Without a custom map, the seed determines the map and starting positions.</small></label></div></details></section>
 <section class="panel"><h2>Optional limits</h2><p class="muted">Leave blank to let each model work until submission. Calls, tools, matches, tokens, elapsed time and costs are recorded regardless. Improvement branches use the same optional limits.</p><div class="form-grid">${field("Model calls", "max_calls", b.max_calls ?? "", "number", "Maximum API responses, including responses after tool results. Blank means unlimited.", 'min="1"')}${field("Tool calls", "max_agent_steps", b.max_agent_steps ?? "", "number", "Maximum tool invocations. Blank means unlimited.", 'min="1"')}${field("Preparation matches", "max_test_matches", b.max_test_matches ?? "", "number", "One test runs two matches, one per side. Blank means unlimited.", 'min="0"')}${field("Preparation time (seconds)", "max_wall_seconds", b.max_wall_seconds ?? "", "number", "Blank means no session time limit.", 'min="1"')}${field("Total input tokens", "max_input_tokens", b.max_input_tokens ?? "", "number", "Optional. Blank means no conversation token limit.", 'min="1"')}${field("Total output tokens", "max_output_tokens", b.max_output_tokens ?? "", "number", "Optional. Blank means no conversation token limit.", 'min="1"')}${field("API spending limit per conversation ($)", "max_cost_usd", b.max_cost_usd ?? "", "number", "Blank means no financial limit.", 'min="0" step="any"')}${field("API spending limit for the experiment ($)", "max_total_usd", c.models.every((m) => m.provider === "mock") ? "" : (c.spending.max_total_usd ?? ""), "number", "Includes all branches. Blank means no financial limit.", 'min="0" step="any"')}</div><label class="check" style="margin-top:15px"><input type="checkbox" name="allow_paid_calls" ${c.spending.allow_paid_calls ? "checked" : ""}>Authorize API calls for this configuration</label><small>Mock runs have no API cost. API runs require this authorization even when an API key is saved; when unchecked, the configuration is rejected before any API call. Optional financial limits are checked between calls. Without an output cap, a call can exceed a configured financial limit.</small></section>
 <section class="panel"><details><summary>Import a JSON configuration</summary><textarea id="import-config" class="mono" style="width:100%;margin-top:12px" placeholder="Paste an experiment manifest"></textarea><div style="margin-top:10px">${btn("Apply configuration", "import-config")}</div></details></section></div>
 <aside class="panel sticky"><div class="eyebrow">Before launching</div><h2>Schedule</h2><p class="muted">Review the schedule and spending limit before launching.</p><div id="plan-preview">${notice("Both improvement branches start from the same initial history. One receives match feedback.")}</div>${btn("Calculate schedule", "preview-plan")}<div class="divider"></div><button type="submit" class="button primary" style="width:100%">Save configuration</button><p class="muted" style="font-size:10px;margin-top:12px">Saving does not start a run.</p></aside></div></form>`
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
  return `<div class="info-row"><span>Conversations</span><strong>${p.sessions == null ? "Until manual stop" : fmt(p.sessions)}</strong></div><div class="info-row"><span>Evaluation matches</span><strong>${p.sessions == null ? "Until manual stop" : fmt(total)}</strong></div><div class="info-row"><span>Maximum preparation matches</span><strong>${p.max_preparation_matches == null ? "Unlimited" : fmt(p.max_preparation_matches)}</strong></div><div class="info-row"><span>Total API spending limit</span><strong>${p.simulated ? "$0 (mock)" : p.max_cost_usd == null ? "No limit" : money(p.max_cost_usd)}</strong></div><p class="muted" style="font-size:10px;margin-top:12px">Schedule assuming every participant submits a strategy. ${p.simulated ? "Mock run with no API calls." : "Reservations estimate cost; they do not confirm provider billing."}</p>`;
}
async function launchDialog(draftId = null, runId = null) {
  if (runId) {
    S.detail = await api("/api/run", {run:runId});
    const blocked = S.detail.sessions.filter(s => s.reconciliation_required);
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
  const p = await api("/api/plan", { config, frozen: !!runId }, true);
  config = p.config;
  S.launch = { draftId, runId, config, expectedHash: p.config_sha256 };
  openDialog(
    runId ? "Resume competition" : "Launch competition",
    config.name,
    `<form data-form="launch">${runId ? notice("Failed conversations will be continued from their checkpoints. Application updates are recorded in the journal; frozen documentation and completed matches are retained.") : ""}${planMarkup(p)}${p.simulated ? notice("Mock participants, real matches. No LLM calls or API charges.") : notice("Calls use the configured keys and prices. Calculated costs are not confirmed provider bills.", "warn")}<div>${config.models.map((m) => `<div class="info-row"><span>${e(m.id)}${m.provider !== "mock" ? `<small>${e(m.endpoint || (m.provider === "anthropic" ? "https://api.anthropic.com/v1/messages" : m.provider === "gemini" ? "https://generativelanguage.googleapis.com/v1beta" : "https://api.openai.com/v1/chat/completions"))}<br>Key: ${e(m.api_key_env)}</small>` : ""}</span><strong>${e(m.model || m.profile)}${m.provider !== "mock" ? `<small>Seed: ${m.parameters?.seed ?? (m.provider === "anthropic" ? "not available" : "not set")}</small>` : ""}</strong></div>`).join("")}</div>${!p.simulated ? `<label class="check" style="margin-top:20px"><input type="checkbox" name="confirm_paid" required>I authorize API calls ${config.spending.max_total_usd == null ? "without an arena spending limit" : "with a configured total spending limit of " + money(config.spending.max_total_usd)}.</label>` : ""}<div class="form-footer">${btn("Cancel", "close-dialog")}<button type="submit" class="button primary">${runId ? "Resume" : "Start competition"}</button></div></form>`,
  );
}
function retryButton(session) {
  if (session?.reconciliation_required && !S.detail.archived &&
      !activeJobs().some(j => j.run === S.run))
    return btn("Resolve billing", "reconcile-session", `data-session="${e(session.id)}"`);
  return session?.retry_allowed && !S.detail.archived
    ? btn(
        "Retry conversation",
        "retry-session",
        `data-session="${e(session.id)}"`,
      )
    : "";
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
  const reviewed = await api("/api/plan", { config, frozen: true }, true);
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
    `<form data-form="launch"><p>Continue this conversation from its saved files and history. Other models' submissions and completed matches are kept.</p><p>Usage counters and configured limits are preserved. If this recovers an initial strategy, its previously unavailable improvement branches can also run.</p><div class="info-row"><span>Model</span><strong>${e(model.id)} · ${e(model.model || model.profile)}</strong></div><div class="info-row"><span>Previous usage</span><strong>${session.calls} model calls · ${session.steps} tool calls</strong></div>${paid ? `<label class="check"><input type="checkbox" name="confirm_paid" required>I authorize API calls for this model${config.spending.max_total_usd == null ? " without an arena spending limit" : " within the existing competition limit of " + money(config.spending.max_total_usd)}.</label>` : ""}<div class="form-footer">${btn("Cancel", "close-dialog")}<button type="submit" class="button primary">Retry conversation</button></div></form>`,
  );
}
const TABS = [
  ["summary", "Summary"],
  ["conversation", "Conversations"],
  ["code", "Code & versions"],
  ["matches", "Matches"],
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
  return (
    head(
      config.name,
      "Results, conversations and files.",
      `${active ? btn("■ Stop", "stop-job", `data-id="${e(job.id)}"`) : experiment && !d.archived ? btn("Resume", "resume") : ""}${experiment ? btn("Clone configuration", "clone-run") : ""}${experiment ? btn("Export", "export-run") : ""}`,
    ) +
    (d.sessions.some(s => s.continuation_identity) ? notice("Continued after an application update. Version changes are recorded in the journal.") : "") +
    (!active && !d.archived ? d.sessions.filter(s => s.reconciliation_required).map(s =>
      notice(`${e(s.model)} · ${e(sessionLabel(s))}: request billing needs review. ${btn("Resolve billing", "reconcile-session", `data-session="${e(s.id)}"`)}`, "warn")).join("") : "") +
    `<div class="toolbar">${config.models ? (config.models.every((m) => m.provider === "mock") ? badge("MOCK RUN (no LLM calls)", "blue") : badge("REAL API CALLS", "orange")) : badge("Provided strategies")}${d.archived ? badge("Exported copy", "orange") : ""}${job ? status(job.status === "failed" && d.report?.incomplete ? "incomplete" : job.status) : ""}<span class="mono muted" style="font-size:10px">${e(S.run)}</span><span class="spacer"></span>${job && ["running", "stopping"].includes(job.status) ? badge(runningPhase(d), "blue") : ""}<label class="check"><input id="follow-live" type="checkbox" ${S.follow ? "checked" : ""}>Live updates</label>${job ? btn("Run log", "job-log", `data-id="${e(job.id)}"`) : ""}</div><div class="tabs">${TABS.map(([key, label]) => `<button class="tab ${S.tab === key ? "active" : ""}" data-action="tab" data-tab="${key}">${label}</button>`).join("")}</div>`
  );
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
  const session = S.detail?.sessions.find((s) => s.id === id);
  const match = String(id || "").match(
    /^(.*)-r(\d+)(?:-g1-(control|feedback))?$/,
  );
  if (!session && !match) return id || "Competition";
  const model = session?.model || match[1],
    repetition = Number(session?.replicate ?? match?.[2] ?? 0) + 1;
  const improved = session?.generation || match?.[3];
  const condition = session?.condition || match?.[3];
  return `Round ${improved ? 2 : 1} · ${model} · repetition ${repetition} · ${improved ? `improved ${condition === "feedback" ? "with" : "without"} feedback` : "initial strategy"}`;
}
function sessionLabel(session) {
  return `Repetition ${Number(session.replicate || 0) + 1} · ${generationLabel(session.generation)}${session.generation ? " · " + text(session.condition) : ""} · ${text(session.status)}`;
}
function sessionChooser(d) {
  const selected = d.sessions.find((s) => s.id === S.session);
  const models = runModels(d);
  if (!models.some((m) => m.id === S.modelFilter))
    S.modelFilter = selected?.model || models[0]?.id || null;
  const sessions = d.sessions.filter((s) => s.model === S.modelFilter);
  if (!sessions.some((s) => s.id === S.session)) {
    S.session = sessions[0]?.id || null;
    S.offset = 0;
  }
  return `<div class="toolbar">${modelPicker(d)}<label for="session-choice">Conversation</label><select id="session-choice" ${sessions.length ? "" : "disabled"}>${sessions.map((s) => `<option value="${e(s.id)}" ${s.id === S.session ? "selected" : ""}>${e(sessionLabel(s))}</option>`).join("") || "<option>No conversations yet</option>"}</select>${S.session ? btn("Conversation journal", "conversation-journal") : ""}${retryButton(d.sessions.find((s) => s.id === S.session))}<span class="spacer"></span></div>`;
}
async function renderRun(epoch) {
  const d = S.detail;
  let body = "";
  if (S.tab === "summary") {
    const [statistics, fights] = await Promise.all([
      api("/api/statistics", { run: S.run }),
      api("/api/matches", { run: S.run }),
    ]);
    if (epoch !== S.epoch) return;
    S.overviewMatches = fights.matches;
    S.statistics = statistics;
    body = summary(d, statistics);
  } else if (S.tab === "config")
    body = `<section class="panel"><h2>Frozen configuration and provenance</h2><p class="muted">These settings are frozen. Clone the configuration to run a different experiment.</p><pre>${e(pretty(d.metadata))}</pre></section>`;
  else if (S.tab === "conversation" || S.tab === "code") {
    const chooser = sessionChooser(d);
    if (d.sessions.length && !S.session)
      body =
        chooser +
        empty(
          "No conversations for this model",
          "Conversations appear when this participant starts.",
        );
    else if (!d.sessions.length && S.tab === "code") {
      S.files = (await api("/api/files", { run: S.run })).files.filter((f) =>
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
        run: S.run,
        session: S.session,
        model: S.modelFilter,
        offset: S.offset,
      });
      if (epoch !== S.epoch) return;
      // Opening a conversation follows its tail; explicit page links retain history.
      if (!S.explicitOffset && data.total > data.messages.length) {
        S.offset = Math.max(0, data.total - 25);
        data = await api("/api/conversation", {
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
        '<div id="conversation-transcript">' +
        conversation(data) +
        '</div><div id="conversation-live-status" aria-live="polite">' +
        conversationLiveStatus(S.liveConversation, false) + '</div>';
    } else {
      S.versions = await api("/api/versions", {
        run: S.run,
        session: S.session,
        model: S.modelFilter,
      });
      body = chooser + codePage(S.versions);
    }
  } else if (S.tab === "matches") {
    S.matches = (await api("/api/matches", { run: S.run })).matches;
    body = matchesPage();
  } else if (S.tab === "files") {
    S.files = (await api("/api/files", { run: S.run })).files;
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
  $("#main").innerHTML =
    '<div id="run-chrome">' + runHeader(d) + "</div>" + body;
  if (S.tab === "conversation" && S.follow && !S.explicitOffset)
    animateConversationTail();
  if (S.tab === "code" && d.sessions.length && S.versions?.versions?.length)
    await loadSource();
  if (S.tab === "matches" && S.matchPath) await loadMatch();
  if (
    (S.tab === "files" || (S.tab === "code" && !d.sessions.length)) &&
    S.files.length
  )
    await loadFile(
      S.files.find((f) => f.path === S.file)?.path ||
        S.files.find((f) => f.path === "report.md")?.path ||
        S.files[0].path,
    );
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
  const known = real.filter((s) => s.token_usage_known);
  if (!known.length) return "Unavailable from provider";
  return `${fmt(known.reduce((n, s) => n + (s.input_tokens || 0), 0))} / ${fmt(known.reduce((n, s) => n + (s.output_tokens || 0), 0))}${known.length < real.length ? " (partial)" : ""}`;
}
// One scope drives every section of the competition overview.
function overviewSettings() {
  S.overviews ||= {};
  return (S.overviews[S.run] ||= {
    round: "all",
    model: "",
    source: "competition",
  });
}
function overviewIdentity(id) {
  const session = S.detail?.sessions.find((s) => s.id === id);
  const parts = String(id || "").match(
    /^(.*)-r(\d+)(?:-g(\d+)-(control|feedback))?$/,
  );
  return {
    id,
    model: session?.model || parts?.[1] || id,
    condition: session?.condition || parts?.[4] || "initial",
    generation: Number(session?.generation ?? parts?.[3] ?? 0),
    replicate: Number(session?.replicate ?? parts?.[2] ?? 0),
  };
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
        match.kind !== "evaluation" ||
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
function overviewData(d) {
  const scope = overviewSettings(),
    all = (S.overviewMatches || []).filter(
      (m) =>
        !m.mirror &&
        m.kind === scope.source &&
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
      const other = overviewIdentity(match.sides[1 - item.side]).model;
      if (scope.source === "competition" && other === item.model) continue;
      const pair = JSON.stringify([item.model, other]);
      if (!matrix.has(pair))
        matrix.set(pair, {
          who: item.model,
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
    overviewAccept(overviewIdentity(v.id), scope),
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
  const hasImprovement =
    d.sessions.some((s) => s.generation > 0) ||
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
          d.sessions
            .filter((v) => v.generation > 0)
            .map((v) => overviewRoundKey(overviewIdentity(v.id))),
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
      ["evaluation", "Reference tests"],
    ],
    data.scope.source,
  )}</select></label><span class="overview-scope">${data.selected.length} fights · ${data.models.length} models</span></div>`;
}
function overviewRanking(data) {
  if (!data.models.length)
    return '<div class="overview-empty">No scored matches in this selection.</div>';
  return `<ol class="overview-ranking">${data.models.map((r, i) => `<li><span class="overview-rank">${i + 1}</span><div class="overview-rank-body"><div><strong>${e(r.model)}</strong><span>${pct(r.score)}</span></div><div class="overview-bar"><span style="width:${100 * (r.score || 0)}%;background:${overviewColor(r.model)}"></span></div><small>${r.wins}W · ${r.draws}D · ${r.losses}L${r.failures ? ` · ${r.failures} failed` : ""}</small></div></li>`).join("")}</ol>`;
}
function overviewColor(model) {
  const names = [
    ...new Set(
      (S.overviewMatches || []).flatMap((m) =>
        m.sides.map((id) => overviewIdentity(id).model),
      ),
    ),
  ].sort();
  return COLORS[Math.max(0, names.indexOf(model)) % COLORS.length];
}
function overviewEvolution(data) {
  if (!data.history.length)
    return '<div class="overview-empty">Evolution appears as rounds finish.</div>';
  const models = [...new Set(data.history.map((r) => r.model))];
  const generations = [...new Set(data.history.map((r) => r.generation))].sort(
    (a, b) => a - b,
  );
  const width = innerWidth < 600 ? 420 : 560,
    height = 210;
  const x = (g) =>
    45 +
    (generations.indexOf(g) * (width - 80)) /
      Math.max(1, generations.length - 1);
  const y = (v) => 165 - v * 140;
  const ticks = generations.filter(
    (g, i) =>
      i === 0 ||
      i === generations.length - 1 ||
      i % Math.max(1, Math.ceil(generations.length / 8)) === 0,
  );
  return `<svg class="overview-evolution" viewBox="0 0 ${width} ${height}" role="img" aria-label="Model scores across strategy rounds">${[0, 0.5, 1].map((v) => `<line x1="38" x2="${width - 25}" y1="${y(v)}" y2="${y(v)}" stroke="#e7ebf2"/><text x="0" y="${y(v) + 4}">${v * 100}%</text>`).join("")}${ticks.map((g) => `<text x="${x(g)}" y="195" text-anchor="middle">R${g + 1}</text>`).join("")}${models
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
              return `${prev?.score != null ? `<path d="M${x(prev.generation)},${y(prev.score)} L${x(r.generation)},${y(r.score)}" fill="none" stroke="${color}" stroke-width="2" ${condition === "control" ? 'stroke-dasharray="4 4"' : ""}/>` : ""}<circle cx="${x(r.generation)}" cy="${y(r.score)}" r="4" fill="${color}" tabindex="0"><title>${e(model)} · ${overviewRound(r.condition, r.generation)}: ${pct(r.score)} (${r.completed} appearances)</title></circle>`;
            })
            .join("");
        })
        .join("");
    })
    .join(
      "",
    )}</svg><div class="overview-legend">${models.map((model) => `<span><i style="background:${overviewColor(model)}"></i>${e(model)}</span>`).join("")}<span>Solid: feedback · Dashed: no feedback</span></div>`;
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
    ids[0] !== opponents[0]
  )
    return matrixLink(
      stages[0],
      ids[0],
      opponents[0],
      outcome,
      value,
      description,
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
  const rows = data.models
    .map((r) => r.model)
    .filter((who) => data.matrix.some((r) => r.who === who))
    .sort();
  const short = (name) => (name.length > 18 ? name.slice(0, 16) + "…" : name);
  const label = (name) =>
    `<abbr title="${e(name)}" tabindex="0">${e(short(name))}</abbr>`;
  return `<div class="overview-matrix-wrap"><table class="overview-matrix" style="min-width:${names.length > 5 ? (names.length + 1) * 96 : 0}px" aria-label="Model head-to-head results"><thead><tr><th scope="col">vs</th>${names.map((name) => `<th scope="col">${label(name)}</th>`).join("")}</tr></thead><tbody>${rows
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
    )}</tbody></table></div><div class="overview-caption">Row vs column · score and wins / draws / losses</div>`;
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
    ["Model", "Score", "Wins", "Draws", "Losses", "Appearances", "Failures"],
    data.models.map(
      (r) =>
        `<tr><td>${e(r.model)}</td><td>${pct(r.score)}</td><td>${r.wins}</td><td>${r.draws}</td><td>${r.losses}</td><td>${r.completed}</td><td>${r.failures}</td></tr>`,
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
              `<tr><td>${e(s.model)}</td><td>${overviewRound(overviewIdentity(s.id).condition, s.generation)}<small>Repetition ${s.replicate + 1}</small></td><td>${status(s.status)} ${s.validation_status && !["valid", "not_submitted"].includes(s.validation_status) ? badge(s.validation_status === "pending" ? "Validation pending" : "Validation: " + text(s.validation_status), s.validation_status === "pending" ? "blue" : "orange") : ""}</td><td>${fmt(s.calls)}</td><td>${money(s.cost_spent)}</td><td>${btn("Open", "session-conversation", `data-session="${e(s.id)}"`)}${btn("Diagnostics", "session-diagnostics", `data-session="${e(s.id)}"`)}${retryButton(s)}</td></tr>`,
          ),
        )
      : "<p>No conversations recorded.</p>"
  }</div></details>
  <details class="overview-details"><summary>Usage & match accounting</summary><div class="overview-detail-body"><h3>Selected versions</h3><p>Tokens: ${e(tokenDisplay({ ...d, sessions: data.sessions }))} · ${fmt(data.sessions.reduce((n, s) => n + (s.calls || 0), 0))} model calls · ${fmt(data.sessions.reduce((n, s) => n + (s.steps || 0), 0))} tool calls</p><h3>Whole competition</h3><dl class="overview-accounting"><div><dt>All completed fights</dt><dd>${fmt(count((m) => m.kind !== "training"))}</dd></div><div><dt>Round 1 tournament</dt><dd>${fmt(count((m) => m.kind === "competition" && !/^g\d+-tournament$/.test(m.stage)))}</dd></div><div><dt>Improvement tournaments</dt><dd>${fmt(count((m) => /^g\d+-tournament$/.test(m.stage)))}</dd></div><div><dt>Reference evaluations</dt><dd>${fmt(count((m) => m.kind === "evaluation"))}</dd></div><div><dt>Preparation tests (unscored)</dt><dd>${fmt(statistics?.training_matches || 0)}</dd></div><div><dt>Diagnostic mirrors (included above)</dt><dd>${fmt(count((m) => m.mirror))}</dd></div></dl>${btn("View preparation tests", "show-training")}</div></details>
  <details class="overview-details"><summary>How to read these results</summary><div class="overview-detail-body"><p>Score = (wins + 0.5 × draws) / completed appearances. 50% can mean all draws. Failures do not earn points and remain visible separately.</p><p>The feedback and no-feedback tracks share the initial submission, then continue independently. Every round finishes its tournament before the next preparation begins. Tournament opponents change between rounds. Reference tests use the frozen Round 1 strategies and built-in scripts for a common comparison.</p><p>Filters apply to all charts, the matrix and details. The model filter selects the candidate; opponents remain visible. Tournament mirrors and preparation tests are excluded from scored results. Multiple versions of the same model are grouped; appearances can exceed the number of unique fights. Tournament diagonals are omitted.</p><p>Cost and tokens measure preparation of selected versions, independently of the match category. Unknown provider usage stays unknown. Zero configured prices still allow token measurement.</p></div></details>`;
}
function summary(d, statistics = null) {
  const data = overviewData(d),
    sessions = data.sessions;
  const failures = sessions.filter(
    (s) =>
      [
        "provider_unavailable",
        "needs_reconciliation",
        "generation_failed",
        "no_submission",
        "budget_exhausted",
      ].includes(s.status) ||
      (s.validation_status &&
        !["valid", "pending", "not_submitted"].includes(s.validation_status)),
  );
  const known = sessions.filter((s) => s.token_usage_known),
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
  return `<div class="competition-overview">${overviewFilters(d, data)}${failures.length ? `<div class="overview-alert">${failures.length} conversation${failures.length === 1 ? "" : "s"} need attention. <button class="table-button" data-action="overview-failures">Review & retry</button></div>` : ""}<div class="overview-kpis"><div><span>Completed fights</span><strong>${fmt(data.selected.filter((v) => v.match.result.status === "completed").length)}</strong><small>${data.selected.filter((v) => v.match.result.status !== "completed").length} failed</small></div><div><span>Submitted strategies</span><strong>${sessions.length ? sessions.filter((s) => s.submission || s.status === "submitted").length : data.models.length}${sessions.length ? `<small> / ${sessions.length}</small>` : ""}</strong><small>${new Set(sessions.map((s) => s.model)).size || data.models.length} models</small></div><div><span>API cost</span><strong>${sessions.length ? (costUnknown ? "Unknown" : money(cost)) : "N/A"}</strong><small>Selected versions</small></div><div><span>Tokens</span><strong>${known.length ? fmt(tokens) : real.length ? "Unknown" : "N/A"}</strong><small>${known.length ? (known.length < real.length ? "Partial reported usage" : "Input + output") : real.length ? "Not reported by provider" : "No measured LLM usage"}</small></div></div>
  <div class="overview-charts"><section class="overview-card"><div class="overview-section-head"><h2>Model ranking</h2><span>Score</span></div>${overviewRanking(data)}</section><section class="overview-card"><div class="overview-section-head"><h2>Evolution</h2><span>Score by version</span></div>${overviewEvolution(data)}</section></div>
  ${data.matrix.length ? `<section class="overview-card overview-head-to-head"><div class="overview-section-head"><h2>Match matrix</h2><span>Click a result to see fights</span></div>${overviewMatrix(data)}</section>` : `<div class="overview-empty">${data.selected.length ? "No head-to-head pairs in this selection." : `No ${data.scope.source === "competition" ? "tournament" : "reference"} matches yet.`}${statistics?.training_matches ? ` ${statistics.training_matches} preparation tests recorded; excluded from standings. ${btn("View preparation tests", "show-training")}` : ""}</div>`}
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
function providerOutput(message, index) {
  const blocks = (message.output_blocks || []).filter(
    (b) => !(message.file_exchange && b.kind === "tool_result"),
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
  if (!data) return "";
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
    `<div><strong>${e(p.phase)} · ${e(text(p.status))}</strong><p>${e(p.message)}</p>${p.sides ? `<small>${e(p.sides.map(strategyName).join(" vs "))} · Seed ${e(p.seed)}</small>` : ""}${p.path ? `<small class="mono">${e(p.path)}</small>` : ""}</div>`;
  const errors = compilation.filter((row) => row.severity === "error").length;
  const warnings = compilation.filter(
    (row) => row.severity === "warning",
  ).length;
  return `<div class="notice ${problems.length ? "error" : ""}" data-session-diagnostics><strong>${data.has_submission ? "Strategy submitted" : e(text(data.generation_status))}</strong> · ${e(validation)}<p>${fmt(data.matches.completed)} completed fights across all categories · ${fmt(data.matches.failed)} engine failures</p><small>${fmt(data.matches.competition_completed)} scored tournament fights · ${fmt(data.matches.reference_completed)} reference evaluations · ${fmt(data.matches.mirror_completed)} tournament mirrors · ${fmt(data.matches.preparation_completed)} preparation fights</small>${validationProblems.map(problem).join("")}${
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
  const target = Math.max(
    0,
    document.documentElement.scrollHeight - innerHeight,
  );
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
    window.scrollTo({ top: target, behavior: "instant" });
    return;
  }
  const start = window.scrollY,
    started = performance.now();
  let expected = start;
  const tick = (now) => {
    // A wheel, scrollbar drag or script moving the viewport cancels following.
    if (Math.abs(window.scrollY - expected) > 2) {
      cancelConversationAnimation();
      return;
    }
    const progress = Math.min(1, (now - started) / 320),
      eased = 1 - Math.pow(1 - progress, 3);
    window.scrollTo({
      top: start + (target - start) * eased,
      behavior: "instant",
    });
    expected = window.scrollY;
    conversationAnimation = progress < 1 ? requestAnimationFrame(tick) : null;
  };
  conversationAnimation = requestAnimationFrame(tick);
}
window.addEventListener(
  "wheel",
  (event) => {
    cancelConversationAnimation();
    if (event.deltaY < 0 && S.tab === "conversation" && S.liveConversation)
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
  return (
    document.documentElement.scrollHeight - window.scrollY - innerHeight < 100
  );
}
function conversationLiveStatus(live, following) {
  const remaining = Math.max(0, live.total - live.next);
  return remaining
    ? `${remaining} new message${remaining === 1 ? "" : "s"} ${btn("Follow latest", "conversation-latest")}`
    : following
      ? "<small>Following new messages</small>"
      : "<small>Reading history. Return to the bottom to follow new messages.</small>";
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
        run: live.run, session: live.session, offset: S.offset,
      });
      if (epoch !== S.epoch || live !== S.liveConversation || mount !== $("#conversation-transcript")) return true;
      mount.innerHTML = conversation(data);
      live.next = data.offset + data.messages.length;
      live.total = data.total;
      live.armed = true;
      const banner = $("#conversation-live-status");
      if (banner) banner.innerHTML = conversationLiveStatus(live, following);
      return true;
    }
    const scrollWithMessages =
      following &&
      (force || nearConversationEnd()) &&
      (force || !$(".chat-message details[open]"));
    const preservedScroll = window.scrollY;
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
    if (following && diagnosis && !diagnosis.querySelector("details[open]")) {
      const html = sessionDiagnostics(data.diagnostics);
      if (diagnosis.dataset.signature !== html) {
        const holder = document.createElement("template");
        holder.innerHTML = html;
        const replacement = holder.content.firstElementChild;
        replacement.dataset.signature = html;
        diagnosis.replaceWith(replacement);
      }
    }
    const pager = $(".pager", mount),
      first = S.offset + 1;
    if (pager)
      pager.innerHTML = `<span>${fmt(live.total)} messages · ${status(data.status)} · Showing ${first}–${live.next}</span><div class="actions">${btn("← Previous", "conversation-page", `data-offset="${Math.max(0, S.offset - 25)}" ${S.offset === 0 ? "disabled" : ""}`)}${btn("Next →", "conversation-page", `data-offset="${live.next}" ${live.next >= live.total ? "disabled" : ""}`)}</div>`;
    const banner = $("#conversation-live-status");
    if (banner) banner.innerHTML = conversationLiveStatus(live, following);
    if (scrollWithMessages && data.messages.length) animateConversationTail();
    const chrome = $("#run-chrome");
    if (chrome) chrome.innerHTML = runHeader(S.detail);
    if (!scrollWithMessages)
      window.scrollTo({ top: preservedScroll, behavior: "instant" });
    return true;
  } finally {
    live.refreshing = false;
  }
}
let conversationScrollTimer;
window.addEventListener(
  "scroll",
  () => {
    clearTimeout(conversationScrollTimer);
    conversationScrollTimer = setTimeout(async () => {
      const live = S.liveConversation;
      if (
        live?.userPaused &&
        document.documentElement.scrollHeight - window.scrollY - innerHeight < 4
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
  { passive: true },
);

function conversation(data, append = false) {
  if (!append) conversationValues = [];
  const failure = data.failure;
  return (
    (failure
      ? notice(
          `<strong>${e(text(data.status))}</strong><p>${e(failure.message)}</p><small>${e(failure.phase)} · ${date(failure.at)}${failure.retryable ? " · Retryable API error" : ""}${failure.uncertain ? " · Check billing before resuming" : ""}</small>`,
          "error",
        )
      : "") +
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
            ? m.content
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
        return `${data.generation > 0 && absolute === data.instruction_index ? `<div class="notice"><strong>Round ${data.generation + 1} starts here · ${e(text(data.condition))}</strong></div>` : ""}<article class="chat-message ${e(m.role)} ${resultError ? "tool-error" : ""}" id="message-${absolute}"><div class="message-head"><strong>${e(direction)}${m.simulated ? " · predefined strategy" : ""}</strong><span>Message ${absolute + 1} · ${data.times?.[index] ? date(data.times[index]) : "Time not recorded"}</span></div>${display.reply_to != null ? `<p class="message-reply">Result of tool request in message ${display.reply_to + 1}${display.reply_to >= S.offset && display.reply_to < S.offset + 25 ? ` · <a href="#message-${display.reply_to}" data-action="message-anchor" data-index="${display.reply_to}">Go to request</a>` : ""}${m.call_id ? " · " + e(m.call_id) : ""}</p>` : ""}${resultError ? badge("Tool error", "red") : ""}${snippet ? `<div class="message-content">${e(snippet)}${m.output_text_truncated || content.length > 1800 ? "\n[Preview truncated; open the full record below.]" : ""}</div>` : m.role === "assistant" && calls ? '<p class="muted">The model requested tools without a text response.</p>' : ""}${m.briefing ? `<div class="game-brief"><strong>Game briefing sent to the model</strong><p>${e(m.briefing.game)}</p><p>${e(m.briefing.objective)}</p><p>${e(m.briefing.team_mode)}</p></div>` : ""}${m.role === "user" ? feedbackView(m.feedback) : ""}${calls}${fileExchange(m, absolute)}${providerOutput(m, absolute)}${m.role === "user" ? conversationData(Object.fromEntries(Object.entries(m).filter(([key]) => !["role", "content", "request_recorded", "request_seed"].includes(key))), m.generation ? "Full improvement instruction and supplied feedback" : "Scenario, roster, ID guide and preparation rules sent to the model") : ""}${m.usage ? `<small>Input ${fmt(m.usage.input_tokens)} · Output ${fmt(m.usage.output_tokens)} · Cost ${money(m.cost_usd)} · Response took ${fmt(m.elapsed_seconds, 3)} s</small>` : ""}${m.request_metrics ? `<small>Context: ${fmt(m.request_metrics.history_messages)} messages · ${fmt(m.request_metrics.request_characters)} request characters · ${fmt(m.request_metrics.request_setup_seconds, 2)} s local request setup${m.usage?.output_tokens != null && m.elapsed_seconds > 0 ? ` · ${fmt(m.usage.output_tokens / m.elapsed_seconds, 2)} output tokens/s including input processing and API waits` : ""}</small>` : ""}${m.request_recorded ? `<p class="muted">Sent seed: ${e(m.request_seed ?? "not set")}${m.stop_reason ? " · Stop reason: " + e(m.stop_reason) : ""}</p>` : ""}<details data-message-record="${absolute}" data-record-run="${e(S.run)}" data-record-session="${e(S.session)}"><summary>Full record: exact request, native response and metadata</summary><pre></pre></details></article>`;
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
        output.textContent = pretty(
          conversationValues[Number(node.dataset.conversationValue)],
        );
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
    `<div class="code-grid"><section class="panel"><h3>File write history</h3><div class="version-list">${data.versions.map((v) => `<button class="version-button ${v.index === S.version ? "active" : ""}" data-action="version" data-version="${v.index}"><strong>Version ${v.index + 1} <span class="timeline-tag">${generationLabel(v.generation)}</span></strong>${e(v.path)}<small>After message ${v.message + 1} · ${v.files.length} files</small></button>`).join("")}</div></section><section class="panel"><div class="toolbar"><select id="source-file" aria-label="File">${current.files.map((f) => `<option ${f === S.file ? "selected" : ""}>${e(f)}</option>`).join("")}</select><span class="spacer"></span>${btn("Open conversation", "version-message", `data-message="${current.message}"`)}</div><div class="toolbar"><label for="source-previous">Compare with</label><select id="source-previous"><option value="-1">Empty state</option>${data.versions
      .slice(0, S.version)
      .map(
        (v) =>
          `<option value="${v.index}" ${v.index === (S.previous ?? S.version - 1) ? "selected" : ""}>Version ${v.index + 1} · ${generationLabel(v.generation)}</option>`,
      )
      .join(
        "",
      )}</select></div><div id="source-content">Loading...</div></section></div>`
  );
}
async function loadSource() {
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
  $("#source-content").innerHTML =
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
}
function filesPage() {
  return `<div class="files-grid"><section class="panel"><h3>Experiment files</h3><input id="file-search" type="search" placeholder="Filter paths..." aria-label="Filter files" style="width:100%;margin-bottom:12px"><label class="check"><input id="engine-files" type="checkbox">Include static engine data</label><small>${fmt(S.files.length)} available files</small><div id="file-list" class="file-list">${fileButtons(S.files)}</div></section><section class="panel"><div id="file-title" class="panel-title"></div><div id="file-content">Select a file.</div></section></div>`;
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
async function loadFile(path) {
  S.file = path;
  const epoch = S.epoch;
  $("#file-title").innerHTML =
    `<h3 class="mono" style="overflow-wrap:anywhere">${e(path)}</h3>${/\.(md|json)$/i.test(path) ? `<div class="actions">${btn("Raw", "file-mode", 'data-mode="raw"')}${btn("Rendered", "file-mode", 'data-mode="rendered"')}</div>` : ""}<a class="button small" href="/api/file?${query({ run: S.run, path, download: 1 })}" download>Download</a>`;
  const response = await fetch("/api/file?" + query({ run: S.run, path }));
  const content = await response.text();
  if (epoch !== S.epoch || S.file !== path) return;
  S.filePreview = {
    path,
    content: response.ok ? content : JSON.parse(content).error || content,
  };
  renderFileView();
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
    if (f.kind !== "all" && kind !== (f.kind || "competition")) return false;
    if (f.stage && m.stage !== f.stage) return false;
    if (f.scored && m.mirror) return false;
    let scopedSide = null;
    if (f.entrant_model || f.round) {
      const candidates = overviewEntries(m).filter(
        (item) =>
          overviewAccept(item, {
            model: f.entrant_model,
            round: f.round || "all",
          }) &&
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
        m.mirror ||
        m.sides[0] === m.sides[1] ||
        (f.entrant && m.sides[1 - m.sides.indexOf(f.entrant)] !== f.opponent))
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
      side = scopedSide ?? (f.entrant ? m.sides.indexOf(f.entrant) : 0);
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
  const f = S.matchFilters || {},
    stages = [
      ...new Set(
        S.matches
          .filter(
            (m) => f.kind === "all" || m.kind === (f.kind || "competition"),
          )
          .map((m) => m.stage),
      ),
    ],
    participants = [...new Set(S.matches.flatMap((m) => m.sides))].sort();
  const rows = matchSubset();
  const categoryTotal = S.matches.filter(
    (m) => f.kind === "all" || m.kind === (f.kind || "competition"),
  ).length;
  const trainingCount = S.matches.filter((m) => m.kind === "training").length;
  S.matchPath =
    rows.find((m) => m.path === S.matchPath)?.path || rows[0]?.path || null;
  return `${notice("Preparation tests use editable scripts and never count toward standings. Competition rounds use frozen submissions; improvements happen after the initial round.")}${trainingCount ? `<p id="training-count">${trainingCount} preparation tests stored separately. ${btn("View preparation tests", "show-training")}</p>` : ""}${selectField(
    "Match category",
    "match-kind",
    [
      ["competition", "Competition rounds"],
      ["training", "Preparation tests (unscored)"],
      ["evaluation", "Reference evaluations (frozen scripts)"],
      ["all", "All fights"],
    ],
    f.kind || "competition",
  )}${f.entrant_model ? notice(`Filtered from overview: ${e(f.entrant_model)} vs ${e(f.opponent_model || "all opponents")} · ${e(f.round === "all" ? "All rounds" : overviewRound(f.round))}`) : ""}<div class="match-filters">${field("Search", "match-search", f.search || "", "search", "", 'id="match-search"')}${selectField("Stage", "match-stage", [["", "All stages"], ...stages.map((s) => [s, stageText(s)])], f.stage || "")}${selectField("Participant", "match-entrant", [["", "All participants"], ...participants.map((p) => [p, strategyName(p)])], f.entrant || "")}${selectField("Opponent", "match-opponent", [["", "All opponents"], ...participants.map((p) => [p, strategyName(p)])], f.opponent || "")}${selectField(
    "Outcome for participant (or side 1)",
    "match-outcome",
    [
      ["", "All outcomes"],
      ["win", "Wins"],
      ["draw", "Draws"],
      ["loss", "Losses"],
      ["failure", "Failures"],
      ["completed", "Completed"],
    ],
    f.outcome || "",
  )}<div class="actions">${btn("Clear filters", "clear-match-filters")}<span id="match-filter-count" class="muted">${rows.length} / ${categoryTotal} matches in this category</span></div></div>${S.matches.length ? `<div class="match-layout"><div id="match-list" class="match-list">${matchButtons(rows)}</div><section class="panel" id="match-detail">${rows.length ? "Loading match..." : !categoryTotal && (!f.kind || f.kind === "competition") ? empty("No competition matches yet", "Models may still be preparing their strategies.", btn("View preparation tests", "show-training")) : empty("No matches found", "Change or clear the filters.")}</section></div>` : empty("No competition matches yet", "Models may still be preparing their strategies.", btn("View preparation tests", "show-training"))}`;
}
function matchButtons(rows) {
  return (
    rows
      .slice(0, 800)
      .map(
        (m) =>
          `<button class="match-card ${m.path === S.matchPath ? "active" : ""}" data-action="match" data-path="${e(m.path)}"><span class="badge ${m.stage.includes("panel") ? "blue" : ""}">${e(stageText(m.stage))}</span>${m.kind === "training" ? badge("Excluded from standings", "orange") : ""}<strong>${e(strategyName(m.sides[0]))}<br><span class="muted">vs</span> ${e(strategyName(m.sides[1]))}</strong><small>Seed ${e(m.seed)} · ${m.mirror ? "mirror · " : ""}${m.result.status === "completed" ? (m.result.winner_side === -1 ? "Draw" : "Winner: " + e(strategyName(m.sides[m.result.winner_side]))) : e(text(m.result.status))}</small></button>`,
      )
      .join("") +
    (rows.length > 800 ? "<small>Filter to find more matches.</small>" : "")
  );
}
async function loadMatch() {
  clearInterval(replayTimer);
  replayTimer = null;
  const path = S.matchPath,
    epoch = S.epoch,
    data = await api("/api/match", { run: S.run, path });
  if (epoch !== S.epoch || S.matchPath !== path) return;
  const row = S.matches.find((m) => m.path === path),
    result = data.result;
  $("#match-detail").innerHTML =
    `<div class="panel-title"><div><h2>${result.status === "completed" ? (result.winner_side === -1 ? "Draw" : "Winner: " + e(strategyName(row.sides[result.winner_side]))) : e(text(result.status))}</h2><small>Seed ${e(row.seed)} · ${result.turns == null ? "N/A turns" : countLabel(result.turns, "turn")} · ${fmt(result.elapsed_seconds, 2)} s</small></div>${status(result.status)}</div>${row.kind === "training" ? notice("Preparation test requested by the model. Editable scripts; excluded from competition standings and matrices.", "warn") : notice("Frozen strategies: these scripts cannot change during this round.")}${row.mirror ? notice("Mirror match: excluded from the standings.") : ""}${
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
    }${data.statistics ? combatStatistics(data.statistics) : ""}${raw(result, "Full metrics: computation, errors and result")}${data.scenario ? raw(data.scenario, "Exact match scenario") : ""}${raw(data.provenance, "Strategies, hashes and provenance")}${data.outcome ? raw(data.outcome, "Full raw replay, actions and logs") : ""}`;
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
  const runs = S.boot.runs.filter((r) => !r.archived && !r.error),
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
        )}" fill="none" stroke="${COLORS[j % COLORS.length]}" stroke-width="2"/>${points
        .filter(Boolean)
        .map(
          (p) =>
            `<circle cx="${p.x}" cy="${p.y}" r="4" fill="${COLORS[j % COLORS.length]}"><title>${e(label)} · ${e(p.id)} : ${pct(p.v)}</title></circle>`,
        )
        .join("")}`;
    })
    .join("")}</svg>`;
  return (
    chart +
    `<div class="chart-legend">${[...series.keys()].map((key, j) => `<span><i class="dot" style="background:${COLORS[j % COLORS.length]}"></i>${e(labels.get(key))}</span>`).join("")}</div>`
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
                `<tr><td><strong>${e(m.model)}</strong><small>${e(m.participant?.provider)} · ${e(m.participant?.model || m.participant?.profile)}</small>${raw(m.participant, "Participant configuration")}<small>${generationLabel(m.generation)} · ${text(m.condition)}</small></td><td class="score">${pct(m.score)}</td><td>${m.conversations}</td><td>${m.excluded}</td><td>${m.runs}</td><td>${money(m.cost_usd)}</td><td>${fmt(m.input_tokens)} / ${fmt(m.output_tokens)}</td><td>${fmt(m.errors)}</td></tr>`,
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
        "The initial strategy is improved in two branches that inherit the same initial history and code. Control receives only the improvement request; feedback also receives selected match results.",
      ],
      [
        "Scores and panels",
        "A win earns 1 point, a draw 0.5 and a loss 0. Scores average completed non-mirror matches. The full reference panel includes frozen initial strategies and fixed handwritten controls.",
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
    if (a === "go") navigate(node.dataset.view);
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
    } else if (a === "delete-draft") {
      await api("/api/competition/delete", { id: node.dataset.id }, true);
      await refreshBoot();
      await renderRoute();
      toast("Configuration removed. Runs were kept.");
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
    else if (a === "launch") await launchDialog(node.dataset.id);
    else if (a === "resume") await launchDialog(null, S.run);
    else if (a === "reconcile-session") reconciliationDialog(node.dataset.session);
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
      $("#message-" + node.dataset.index)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
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
  const form = event.target;
  if (!form.dataset.form) return;
  event.preventDefault();
  const submit = $("button[type=submit]", form);
  if (submit) submit.disabled = true;
  try {
    const f = new FormData(form),
      type = form.dataset.form;
    if (type === "participant") {
      const provider = f.get("provider"),
        spec = { id: f.get("id"), provider };
      if (provider === "mock") spec.profile = f.get("profile");
      else {
        Object.assign(spec, {
          model: f.get("model"),
          api_key_env: f.get("api_key_env"),
          timeout_seconds: Number(f.get("timeout_seconds")),
          max_retries: Number(f.get("max_retries")),
          parameters: JSON.parse(f.get("parameters") || "{}"),
          pricing: {
            date: f.get("pricing_date"),
            currency: "USD",
            input_per_million: f.get("input_price"),
            output_per_million: f.get("output_price"),
          },
        });
        for (const key of ["max_input_tokens_per_call", "max_output_tokens"]) {
          if (String(f.get(key) || "").trim()) spec[key] = Number(f.get(key));
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
      await api("/api/competition", { config, id: S.editDraft }, true);
      await refreshBoot();
      navigate("competitions");
      toast("Configuration saved. No API calls made.");
    } else if (type === "reconcile") {
      await api("/api/reconcile", {run:S.run, session:form.dataset.session,
        cost_usd:f.get("cost_usd"), note:f.get("note")}, true);
      $("#dialog").close();
      await renderRoute();
      toast("Billing recorded. Resume the competition or retry this conversation.");
    } else if (type === "launch") {
      const launch = S.launch;
      const job = await api(
        "/api/launch",
        {
          draft_id: launch.draftId,
          run: launch.runId,
          retry_session: launch.retrySession,
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
    if (n.name === "provider" && n.closest("[data-form=participant]")) {
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
      $("#main").innerHTML =
        runHeader(S.detail) + summary(S.detail, S.statistics);
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
        "match-stage",
        "match-entrant",
        "match-opponent",
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
document.addEventListener("input", (event) => {
  const n = event.target;
  if (n.id === "run-search")
    $("#run-table").innerHTML = runTable(
      S.boot.runs.filter((r) =>
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
  if (n.id === "match-search") filterMatches().catch(showError);
  if (n.id === "replay-range") renderReplay(Number(n.value));
});
$("#dialog").addEventListener("close", () => {
  hideHelp();
  document.body.appendChild($("#toast"));
  S.logJob = null;
});
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

      !(S.tab === "summary" && $(".overview-details[open]")) &&
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
        const scroll = window.scrollY;
        const replay =
          S.tab === "matches" && R
            ? { path: S.matchPath, index: R.index }
            : null;
        if (S.tab === "conversation" && S.liveConversation?.session === S.session)
          return;
        if (S.follow && S.tab === "events") {
          const events = await api("/api/events", {
            run: S.run,
            session: S.session || undefined,
            model: S.modelFilter || undefined,
            limit: 1,
          });
          S.offset = Math.floor(Math.max(0, events.total - 1) / 100) * 100;
        }
        if (S.follow && S.tab === "code") {
          S.version = null;
          S.previous = null;
        }
        await renderRun(epoch);
        if (replay && R && replay.path === S.matchPath)
          renderReplay(Math.min(replay.index, R.events.length));
        window.scrollTo(0, scroll);
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
function renderFileView() {
  const node = $("#file-content");
  if (!node || !S.filePreview) return;
  const { path, content } = S.filePreview;
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
      stage: $("[name=match-stage]", form).value,
      entrant: $("[name=match-entrant]", form).value,
      opponent: $("[name=match-opponent]", form).value,
      outcome: $("[name=match-outcome]", form).value,
    };
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
    `${rows.length} / ${S.matches.filter((m) => S.matchFilters.kind === "all" || m.kind === (S.matchFilters.kind || "competition")).length} matches in this category`;
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
function matrixLink(stage, entrant, opponent, outcome, value, description) {
  const href =
    "#" +
    query({
      view: "run",
      run: S.run,
      tab: "matches",
      stage,
      kind: stage.startsWith("evaluations/") ? "evaluation" : "competition",
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
