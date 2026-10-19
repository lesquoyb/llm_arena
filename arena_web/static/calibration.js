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
function fill(config) {
  referenceEdits=structuredClone(config.reference_documents || {});
  $('reference-path').replaceChildren();
  Object.keys(boot.reference_documents).forEach(path=>option($('reference-path'),path,path));
  referencePath=$('reference-path').value;
  $('reference-content').value=referenceEdits[referencePath] ?? boot.reference_documents[referencePath];
  $("name").value = config.name;
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
    ([id, key]) => ($(id).value = config.optimizer[key]),
  );
  $("parameter-grid").value = json(config.optimizer.parameter_grid);
  $("simulation-note").textContent =
    config.target.provider === "mock"
      ? "Mock models are offline fixtures. Their scores do not measure a real model’s learning."
      : "";
  updateRoundStop();
}
function config() {
  saveReferenceEdit();
  const value = {
    ...structuredClone(boot.config),
    name: $("name").value,
    prompt: $("prompt").value,
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
    ([id, key]) => (value.optimizer[key] = Number($(id).value)),
  );
  value.optimizer.parameter_grid = JSON.parse($("parameter-grid").value);
  if ($("mode").value === "manual") value.optimizer.parameter_grid = {};
  if ($("mode").value === "automatic") {
    value.analyst = JSON.parse($("analyst-json").value);
    value.optimizer.parameter_grid = {};
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
  selected = identifier;
  $("inspection").hidden = false;
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
        data.state.audit.map((a) => pct(a.score)).join(", ")
      : "");
  const trials = data.state.trials || [];
  $("trial-comparison").replaceChildren(
    table(
      ["Candidate", "Validation", "Convergence", "Tokens", "Decision"],
      trials.map((t, i) => [
        String(i + 1),
        pct(t.report.validation_score),
        t.report.converged === false
          ? "Not reached"
          : t.report.convergence_round,
        t.report.tokens ?? "Unknown",
        button(
          t.accepted ? "Kept · review change" : "Rejected · review change",
          async () => {
            const candidate = await api(
              qs("/api/candidate", { trial: t.directory }),
            );
            await reveal(
              "Candidate " + (i + 1) + " · change review",
              candidate,
            );
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
  if (retain && [...$("trial").options].some((o) => o.value === previous))
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
    "Score by round: green training, blue validation",
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
  for (const [key, color] of [
    ["training", "#94e1c4"],
    ["validation", "#83b9ff"],
  ]) {
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
  add("text", { x: 50, y: 18, fill: "#94e1c4", "font-size": 13 }, "Training");
  add(
    "text",
    { x: 160, y: 18, fill: "#83b9ff", "font-size": 13 },
    "Validation (hidden from target)",
  );
  add("text", { x: 370, y: 252, fill: "#b7c9e0", "font-size": 13 }, "Round");
  $("chart").append(svg);
  $("rounds-table").append(
    table(
      [
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
        `${r.training.wins}/${r.training.draws}/${r.training.losses}`,
        pct(r.training.score),
        pct(r.validation.score),
        pct(r.previous_versions?.score),
        r.validity,
        r.calls,
        r.input_tokens === null ? "Unknown" : r.input_tokens + r.output_tokens,
      ]),
    ),
  );
}
async function loadTrial() {
  selectedTrial = $("trial").value;
  $("fork").disabled = selectedTrial.startsWith("proposals/");
  $("replicate").replaceChildren();
  const report = currentReport();
  (report?.replicates || [{ replicate: 0 }]).forEach((r) =>
    option(
      $("replicate"),
      String(r.replicate),
      "Replicate " + (r.replicate + 1),
    ),
  );
  draw();
  if (!selectedTrial) return;
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
  $("dialog-content").textContent =
    typeof value === "string" ? value : json(value);
  if (!$("dialog").open) $("dialog").showModal();
}
async function history(offset, refresh = false) {
  const params = { trial: selectedTrial, session: $("session").value },
    view = $("view").value;
  const identity =
    selected + "|" + selectedTrial + "|" + params.session + "|" + view;
  const same = refresh && historyIdentity === identity;
  const following =
    same &&
    document.documentElement.scrollHeight - window.scrollY - innerHeight < 100;
  if (same && view === "conversation" && !following) return;
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
      ...(offset !== undefined ? { offset } : {}),
    }),
  );
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
    button("Initial prompt", () => history(0)),
    button("This round", () => history(data.round_start)),
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
      if (message.file_exchange && block.kind === "tool_result") return;
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
            node("pre", typeof value === "string" ? value : json(value)),
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
  if (same && following)
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
    });
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
$("trial").onchange = guard(loadTrial);
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
  navigator.clipboard.writeText($("dialog-content").textContent),
);
$("error").onclick = () => ($("error").hidden = true);
function setMode() {
  const active = $("mode").value === "automatic";
  $("analyst-label").hidden = !active;
  $("analyst-key").closest("label").hidden = !active;
  $("analyst-json").closest("label").hidden = !active;
  if ($("mode").value === "grid" && $("parameter-grid").value.trim() === "{}")
    $("parameter-grid").value = json({ temperature: [0, 0.3, 0.7] });
}
$("mode").onchange = setMode;
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
        polling ||
        $("dialog").open ||
        $("history").querySelector("details[open]")
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

function updateRoundStop() {
  const mode = $("round-stop").value;
  $("rounds").disabled = mode === "manual";
  for (const id of ["minimum", "patience", "epsilon"])
    $(id).disabled = mode !== "plateau";
  if (mode === "manual") $("replicates").value = 1;
  $("replicates").disabled = mode === "manual";
}
$("round-stop").onchange = updateRoundStop;
