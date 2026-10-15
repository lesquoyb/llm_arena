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
    ? "—"
    : Number(v).toLocaleString("fr-FR", { maximumFractionDigits: digits });
const pct = (v) => (v == null ? "—" : fmt(v * 100, 1) + " %");
const money = (v) => (v == null ? "Inconnu" : fmt(v, 6) + " $");
const date = (v) =>
  v
    ? new Date(v * 1000).toLocaleString("fr-FR", {
        dateStyle: "short",
        timeStyle: "short",
      })
    : "—";
const COLORS = [
  "#5278e5",
  "#c18a4f",
  "#8f75c8",
  "#3e9b87",
  "#cb718b",
  "#7e91ad",
];
const LABELS = {
  submitted: "Soumise",
  running: "En cours",
  stopping: "Arrêt en cours",
  stopped: "Arrêtée",
  completed: "Terminée",
  failed: "Échec",
  interrupted: "Interrompue",
  needs_reconciliation: "Facturation à vérifier",
  budget_exhausted: "Budget atteint",
  no_submission: "Sans soumission",
  generation_failed: "Génération échouée",
  provider_unavailable: "API indisponible",
  valid: "Valide",
  invalid: "Invalide",
  initial: "Première version",
  control: "Sans feedback",
  feedback: "Avec feedback",
  all: "Panel complet",
  g0: "Stratégies G0 figées",
  controls: "Stratégies fixes",
  timeout: "Délai dépassé",
  engine_error: "Erreur moteur",
};
const text = (v) => LABELS[v] || v || "—";
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
const raw = (value, title = "Données complètes") =>
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
const field = (label, name, value = "", type = "text", help = "", attrs = "") =>
  `<label class="field">${e(label)}<input type="${type}" name="${name}" value="${e(value)}" ${attrs}>${help ? `<small>${e(help)}</small>` : ""}</label>`;
const selectField = (label, name, values, current, help = "") =>
  `<label class="field">${e(label)}<select name="${name}">${values.map(([v, l]) => `<option value="${e(v)}" ${v === current ? "selected" : ""}>${e(l)}</option>`).join("")}</select>${help ? `<small>${e(help)}</small>` : ""}</label>`;
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
  panel: "all",
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
    throw new Error(value.error || `Erreur HTTP ${response.status}`);
  return value;
}
function toast(message, error = false) {
  const node = $("#toast");
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
  S.offset = Number(q.get("offset") || 0);
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
  updateChrome();
}
function activeJobs() {
  return S.boot.jobs.filter((j) => ["running", "stopping"].includes(j.status));
}
function updateChrome() {
  const ready = S.boot.engine.ready;
  $("#engine-status").className = "badge " + (ready ? "green" : "orange");
  $("#engine-status").textContent = ready
    ? "● Moteur prêt"
    : "Moteur à installer";
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
      dashboard: "Vue d’ensemble",
      participants: "Participants",
      competitions: "Compétitions",
      run: "Exploration",
      editor: "Configuration",
      compare: "Comparaison",
      help: "Guide",
    }[S.view] || "Vue d’ensemble");
}
async function renderRoute() {
  const epoch = ++S.epoch;
  clearInterval(replayTimer);
  replayTimer = null;
  R = null;
  updateChrome();
  if (S.view === "run") {
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
        "Préparation de la compétition",
        "Le moteur initialise les premiers checkpoints…",
      );
      return;
    }
    S.detail = d;
    await renderRun(epoch);
    return;
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
    return `<tr><td><button class="table-button" data-action="open-run" data-run="${e(r.id)}">${e(r.name)}</button><small>${e(r.id)}</small></td><td>${job && ["running", "stopping"].includes(job.status) ? status(job.status) : r.error ? status("failed") : r.complete ? status("completed") : badge("À examiner", "orange")}</td><td>${r.simulated === true ? badge("Simulation", "blue") : r.simulated === false ? badge("API réelles", "orange") : badge("Stratégies")}</td><td class="numeric">${fmt(r.report?.sessions ?? r.models)}</td><td class="numeric">${fmt(completed(r.report))}</td><td class="numeric">${r.report?.cost_usd === undefined ? "—" : money(r.report.cost_usd)}</td><td>${date(r.created_at)}</td></tr>`;
  });
}
function runTable(runs) {
  return runs.length
    ? table(
        [
          "Compétition",
          "État",
          "Mode",
          "Sessions",
          "Combats terminés",
          "Coût API",
          "Création",
        ],
        runRows(runs),
      )
    : empty(
        "Votre première compétition commence ici",
        "Configurez les participants et lancez la démo pour explorer toute la chaîne.",
        btn("＋ Créer une compétition", "new-competition", "", true),
      );
}
function dashboard() {
  const runs = S.boot.runs.filter((r) => !r.archived),
    known = runs.filter((r) => r.report?.cost_usd != null),
    unknown = runs.filter((r) => r.report && r.report.cost_usd === null).length;
  return (
    head(
      "Vue d’ensemble",
      "Compétitions, participants et résultats.",
      btn("＋ Nouvelle compétition", "new-competition", "", true),
    ) +
    `<div class="metrics">${metric("Compétitions", fmt(runs.length), `${activeJobs().length} en cours`, "⚑")}${metric("Participants configurés", fmt(S.boot.participants.length), "Profils réutilisables", "♧")}${metric("Combats terminés", fmt(runs.reduce((n, r) => n + completed(r.report), 0)), "Toutes les étapes d’évaluation", "⚔")}${metric("Coût API connu", money(known.reduce((n, r) => n + Number(r.report.cost_usd), 0)), unknown ? `${unknown} coût(s) encore inconnu(s)` : "Hors infrastructure ; simulations incluses", "↗")}</div>` +
    (!S.boot.engine.ready
      ? notice(
          `Le moteur n’est pas prêt. L’interface reste consultable. Installer avec <code>python scripts/bootstrap.py</code> après avoir installé un JDK 25. ${e(S.boot.engine.error)}`,
          "warn",
        )
      : "") +
    `<section class="panel flush"><div class="panel-head"><div><h2>Compétitions récentes</h2><p>Les exécutions originales, sans compter deux fois les exports.</p></div>${btn("Tout voir →", "go", 'data-view="competitions"')}</div>${runTable(runs.slice(0, 8))}</section>` +
    `<div class="grid two"><section class="panel"><h2>Commencer sans frais d’API</h2><p class="muted">Participants simulés, combats réels, aucun appel API.</p>${btn("Configurer la démo", "new-demo")}</section><section class="panel"><h2>Lire un score</h2><p class="muted">Une victoire vaut 1 point, un nul 0,5, une défaite 0. Un score de 70 % représente 70 % des points possibles, hors miroirs.</p>${btn("Comprendre les comparaisons", "go", 'data-view="help"')}</section></div>`
  );
}
function participants() {
  return (
    head(
      "Participants",
      "Modèles, paramètres et tarifs utilisés par les compétitions.",
      btn("＋ Ajouter un participant", "new-participant", "", true),
    ) +
    `<section class="panel flush">${table(
      [
        "Participant",
        "Fournisseur / modèle",
        "Tarif entrée / sortie",
        "Clé API",
        "",
      ],
      S.boot.participants.map(
        ({ spec: m, key_configured }) =>
          `<tr><td><strong>${e(m.id)}</strong><small>${m.provider === "mock" ? "Participant simulé" : "Modèle configuré"}</small></td><td>${e(m.provider)}<small>${e(m.model || m.profile)}</small></td><td>${m.pricing ? `${e(m.pricing.input_per_million)} / ${e(m.pricing.output_per_million)} $<small>Par million de tokens · ${e(m.pricing.date)}</small>` : "Sans appel API"}</td><td>${m.provider === "mock" ? "—" : badge(key_configured ? "Configurée" : "À renseigner", key_configured ? "green" : "orange")}</td><td><div class="actions">${btn("Modifier", "edit-participant", `data-id="${e(m.id)}"`)}<button class="icon-button" data-action="delete-participant" data-id="${e(m.id)}" title="Retirer ce profil" aria-label="Retirer ${e(m.id)}">×</button></div></td></tr>`,
      ),
    )}</section>` +
    notice(
      "Les tarifs sont saisis par vous, en USD par million de tokens, à une date précise. Les clés entrées dans cette interface restent en mémoire jusqu’à sa fermeture ; elles ne sont pas enregistrées dans les fichiers.",
    ) +
    `<section class="panel"><h2>Un profil n’est pas une soumission</h2><p class="muted">Un participant décrit comment contacter une IA. Chaque répétition ouvre une conversation indépendante et produit sa propre stratégie. Les profils « mock » fournissent des scripts prédéfinis ; ils ne représentent aucun modèle réel.</p></section>`
  );
}
function freshConfig() {
  const config = structuredClone(S.boot.default_config),
    catalog = S.boot.participants.map((p) => p.spec),
    ids = config.models.map((m) => m.id);
  config.models = structuredClone(catalog.filter((m) => ids.includes(m.id)));
  if (!config.models.length)
    config.models = structuredClone(catalog.slice(0, 2));
  return config;
}
function competitions() {
  return (
    head(
      "Compétitions",
      "Préparez une configuration, lancez une exécution et retrouvez chaque expérience.",
      btn("＋ Nouvelle compétition", "new-competition", "", true),
    ) +
    `<section class="panel flush"><div class="panel-head"><div><h2>Configurations enregistrées</h2><p>Modifiables jusqu’au lancement. Chaque exécution conserve ensuite sa propre copie.</p></div></div>${
      S.boot.drafts.length
        ? table(
            ["Configuration", "Participants", "Répétitions", "Étapes", ""],
            S.boot.drafts.map(
              (d) =>
                `<tr><td><strong>${e(d.config.name)}</strong><small>Modifiée le ${date(d.updated_at)}</small></td><td>${d.config.models.map((m) => e(m.id)).join(", ")}</td><td>${d.config.replicates}</td><td>${d.config.generations === 2 ? "G0 → G1, deux branches" : "G0"}</td><td><div class="actions">${btn("Configurer", "edit-draft", `data-id="${e(d.id)}"`)}${btn("▷ Lancer", "launch", `data-id="${e(d.id)}"`, true)}${btn("Retirer", "delete-draft", `data-id="${e(d.id)}"`)}</div></td></tr>`,
            ),
          )
        : empty(
            "Aucune configuration enregistrée",
            "La démo préremplit les paramètres pour commencer.",
            btn("Créer une configuration", "new-competition"),
          )
    }</section>` +
    `<section class="panel flush"><div class="panel-head"><div><h2>Historique des exécutions</h2><p>Les exports sont identifiés comme copies et exclus des agrégations.</p></div><input type="search" id="run-search" placeholder="Rechercher une compétition…" aria-label="Rechercher une compétition"></div><div id="run-table">${runTable(S.boot.runs)}</div></section>` +
    (S.boot.jobs.length
      ? `<section class="panel flush"><div class="panel-head"><h2>Exécutions lancées depuis l’interface</h2></div>${table(
          ["Nom", "État", "Démarrage", ""],
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
  $("#dialog-content").innerHTML =
    `<div class="dialog-head"><div><h2>${e(title)}</h2><p>${e(subtitle)}</p></div><button class="icon-button" data-action="close-dialog" aria-label="Fermer">×</button></div>${body}`;
  if (!$("#dialog").open) $("#dialog").showModal();
}
function participantDialog(identifier = null, provider = null) {
  const m = identifier
    ? S.boot.participants.find((p) => p.spec.id === identifier).spec
    : {};
  S.editParticipant = identifier;
  const p = provider || m.provider || "mock",
    pricing = m.pricing || {};
  openDialog(
    identifier ? "Modifier le participant" : "Nouveau participant",
    "",
    `<form data-form="participant"><div class="form-grid">${field("Identifiant du participant", "id", m.id || "", "text", "Lettres, chiffres, tirets ; 40 caractères maximum.", `required pattern="[a-zA-Z0-9][a-zA-Z0-9_-]{0,39}" ${identifier ? "readonly" : ""}`)}${selectField(
      "Fournisseur",
      "provider",
      [
        ["mock", "Simulation (aucun appel API)"],
        ["openai", "OpenAI"],
        ["anthropic", "Anthropic"],
        ["gemini", "Google Gemini"],
        ["openai-compatible", "API compatible OpenAI"],
      ],
      p,
    )}
 ${
   p === "mock"
     ? selectField(
         "Comportement simulé",
         "profile",
         S.boot.profiles.map((v) => [v, v]),
         m.profile || "single-shot",
         "single-shot tire une fois ; repair-and-submit corrige un script puis soumet rush.",
       )
     : `${field("Identifiant exact du modèle", "model", m.model || "", "text", "Le nom accepté par l’API choisie.", "required")}<div class="field full"><div class="actions">${btn("Charger les modèles", "list-models")}<select id="available-models" aria-label="Modèles disponibles"><option value="">Catalogue non chargé</option></select></div><small id="model-list-status">Liste fournie par l’API avec la clé configurée. Saisie manuelle possible.</small></div>${field("Variable de la clé API", "api_key_env", m.api_key_env || (p === "anthropic" ? "ARENA_ANTHROPIC_KEY" : p === "gemini" ? "ARENA_GEMINI_KEY" : "ARENA_OPENAI_KEY"), "text", "Une clé déjà définie dans l’environnement est également utilisable.", "required")}<label class="field full">Clé API — pour cette session uniquement<input name="secret" type="password" autocomplete="new-password" placeholder="Laisser vide pour conserver la clé disponible"><small>Jamais renvoyée au navigateur ni écrite dans les configurations.</small></label>${p === "openai-compatible" ? field("Endpoint HTTPS complet", "endpoint", m.endpoint || "", "url", "Inclure le chemin de l’API, sans clé ni paramètres dans l’URL.", "required") : m.endpoint ? field("Endpoint HTTPS", "endpoint", m.endpoint, "url") : ""}${field("Prix entrée / million de tokens ($)", "input_price", pricing.input_per_million ?? "", "number", "", 'required min="0" step="any"')}${field("Prix sortie / million de tokens ($)", "output_price", pricing.output_per_million ?? "", "number", "", 'required min="0" step="any"')}${field("Date de ces tarifs", "pricing_date", pricing.date || new Date().toISOString().slice(0, 10), "date", "", "required")}${field("Prix cache lu / million ($), facultatif", "cached_price", pricing.cached_input_per_million ?? "", "number", "Vide : utilise le tarif d’entrée.", 'min="0" step="any"')}${field("Prix cache créé / million ($), facultatif", "creation_price", pricing.cache_creation_per_million ?? "", "number", "", 'min="0" step="any"')}${field("Entrée maximale par appel (tokens)", "max_input_tokens_per_call", m.max_input_tokens_per_call || 150000, "number", "Borne d’admission conservatrice.", 'required min="1"')}${field("Sortie maximale par appel (tokens)", "max_output_tokens", m.max_output_tokens || 12000, "number", "", 'required min="1"')}${field("Délai par appel (secondes)", "timeout_seconds", m.timeout_seconds || 60, "number", "", 'required min="1" max="300"')}${field("Nouvelles tentatives sur HTTP 429", "max_retries", m.max_retries ?? 1, "number", "Les réponses incertaines ne sont pas relancées automatiquement.", 'required min="0" max="3"')}${p === "anthropic" ? `<p class="muted">Seed : non disponible dans l’API Anthropic.</p>` : field("Seed du modèle", "model_seed", m.parameters?.seed ?? (identifier ? "" : 0), "number", p === "openai-compatible" ? "Prise en charge selon le serveur ; aucune garantie de réponse identique." : "Valeur envoyée à chaque appel. Reproductibilité au mieux, selon le modèle ; aucune garantie de réponse identique.", 'min="0" max="2147483647"')}<label class="field full">Paramètres du modèle (JSON)<textarea name="parameters" class="mono">${e(pretty(m.parameters || {}))}</textarea><small>Options selon l’API : temperature, top_p, etc. Seed réglée ci-dessus.</small></label>`
 }</div><div class="form-footer">${btn("Annuler", "close-dialog")}<button type="submit" class="button primary">Enregistrer le participant</button></div></form>`,
  );
}
const ENTITY_FIELDS = [
  ["level", "Niveau", 100],
  ["life", "PV", 600],
  ["strength", "Force", 100],
  ["agility", "Agilité", 0],
  ["frequency", "Fréquence", 100],
  ["wisdom", "Sagesse", 0],
  ["resistance", "Résistance", 0],
  ["science", "Science", 0],
  ["magic", "Magie", 0],
  ["tp", "PA par tour", 12],
  ["mp", "PM par tour", 5],
  ["cores", "Cœurs", 10],
  ["ram", "RAM LeekScript", 10],
];
function competitionEditor() {
  const c = S.editConfig || structuredClone(S.boot.default_config),
    b = c.budget_per_session;
  const choices = new Map(c.models.map((m) => [m.id, m]));
  S.boot.participants.forEach(({ spec: m }) => {
    if (!choices.has(m.id)) choices.set(m.id, m);
  });
  S.choiceModels = [...choices.values()];
  return (
    head(
      S.editDraft ? "Modifier la compétition" : "Nouvelle compétition",
      "Les règles et budgets sont communs à tous les participants. Aucune API n’est appelée pendant la configuration.",
    ) +
    `<form data-form="competition" id="competition-form"><div class="grid asymmetric"><div><section class="panel"><h2>Identité et participants</h2><p class="muted">Chaque répétition crée une nouvelle conversation, indépendante des autres.</p><div class="form-grid">${field("Nom de la compétition", "name", c.name, "text", "", "required")}${field("Répétitions par participant", "replicates", c.replicates, "number", "", 'required min="1" max="20"')}${selectField(
      "Cycle d’évaluation",
      "generations",
      [
        ["1", "G0 : première stratégie"],
        ["2", "G0 → G1 : avec et sans feedback"],
      ],
      String(c.generations || 1),
    )}</div><h3 class="section-label">Participants inscrits</h3>${S.choiceModels.map((m) => `<label class="choice"><input type="checkbox" name="participant" value="${e(m.id)}" ${c.models.some((v) => v.id === m.id) ? "checked" : ""}><span><strong>${e(m.id)}</strong><small>${e(m.provider)} · ${e(m.model || m.profile)}</small></span></label>`).join("")}${btn("Gérer les profils", "go", 'data-view="participants"')}</section>
 <section class="panel"><h2>Règles du terrain</h2><p class="muted">Deux équipes identiques en statistiques et équipement, avec positions alternées.</p><div class="form-grid">${field("Entités par équipe", "team_size", c.scenario.team_size, "number", "", 'required min="1" max="8"')}${field("Tours maximum", "max_turns", c.scenario.max_turns, "number", "", 'required min="1" max="64"')}${field("Seeds G0 / feedback", "seeds", c.seeds.join(", "), "text", "Identifiants des tirages de carte. Exemple : 101, 202.", "required")}${field("Seeds finales G1", "final_seeds", (c.final_seeds || []).join(", "), "text", "Distinctes des seeds G0 et de la seed d’entraînement 17.")}</div><label class="check" style="margin-top:15px"><input type="checkbox" name="include_mirrors" ${c.include_mirrors ? "checked" : ""}>Ajouter les matchs miroirs (exclus du score)</label><details><summary>Statistiques, équipement et carte personnalisée</summary><div class="form-grid three" style="margin-top:15px">${ENTITY_FIELDS.map(([key, label, def]) => field(label, "entity_" + key, c.scenario.entity[key] ?? def, "number", "", 'required min="0"')).join("")}</div><div class="form-grid" style="margin-top:15px">${field("Identifiants des armes", "weapons", c.scenario.entity.weapons.join(", "), "text", "Exemple : 37 pour l’équipement de la démo.")}${field("Identifiants des puces", "chips", c.scenario.entity.chips.join(", "), "text", "Laisser vide pour aucune puce.")}<label class="field full">Carte personnalisée (JSON, facultatif)<textarea name="map" class="mono">${c.scenario.map ? e(pretty(c.scenario.map)) : ""}</textarea><small>Sans carte personnalisée, la carte et les positions dépendent de la seed.</small></label></div></details></section>
 <section class="panel"><h2>Budgets par conversation</h2><p class="muted">Les deux branches G1 disposent des mêmes limites supplémentaires.</p><div class="form-grid">${field("Appels au modèle", "max_calls", b.max_calls, "number", "", 'required min="1"')}${field("Appels aux outils", "max_agent_steps", b.max_agent_steps, "number", "", 'required min="1"')}${field("Combats de préparation", "max_test_matches", b.max_test_matches, "number", "Un essai aller-retour consomme deux combats.", 'required min="0"')}${field("Temps de préparation (secondes)", "max_wall_seconds", b.max_wall_seconds, "number", "", 'required min="1"')}${field("Tokens d’entrée cumulés", "max_input_tokens", b.max_input_tokens || 1000000, "number", "Pour les API réelles.", 'required min="1"')}${field("Tokens de sortie cumulés", "max_output_tokens", b.max_output_tokens || 100000, "number", "", 'required min="1"')}${field("Plafond API par conversation ($)", "max_cost_usd", b.max_cost_usd ?? "1", "number", "", 'required min="0" step="any"')}${field("Plafond API de toute l’expérience ($)", "max_total_usd", c.spending.max_total_usd || "5", "number", "G0 et toutes les branches G1 inclus.", 'required min="0" step="any"')}</div><label class="check" style="margin-top:15px"><input type="checkbox" name="allow_paid_calls" ${c.spending.allow_paid_calls ? "checked" : ""}>Autoriser les API payantes pour cette configuration</label><small>La démo simulée conserve automatiquement un budget API nul. Un lancement réel demandera de confirmer son plafond.</small></section>
 <section class="panel"><details><summary>Importer une configuration JSON complète</summary><textarea id="import-config" class="mono" style="width:100%;margin-top:12px" placeholder="Coller un manifeste d’expérience existant"></textarea><div style="margin-top:10px">${btn("Appliquer cette configuration", "import-config")}</div></details></section></div>
 <aside class="panel sticky"><div class="eyebrow">Avant le premier appel</div><h2>Préparer le calendrier</h2><p class="muted">Vérifiez le nombre de conversations, de combats et le plafond financier avant de lancer.</p><div id="plan-preview">${notice("Le cycle complet compare une amélioration avec feedback à une amélioration sans feedback, à partir du même historique G0.")}</div>${btn("Calculer le calendrier", "preview-plan")}<div class="divider"></div><button type="submit" class="button primary" style="width:100%">Enregistrer la configuration</button><p class="muted" style="font-size:10px;margin-top:12px">L’enregistrement ne lance aucune compétition.</p></aside></div></form>`
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
  base.generations = n("generations");
  base.schema_version = 2;
  base.improvement_conditions = ["control", "feedback"];
  base.prompt_language = "fr";
  base.seeds = array("seeds");
  base.final_seeds = base.generations === 2 ? array("final_seeds") : [];
  base.include_mirrors = f.has("include_mirrors");
  base.scenario.team_size = n("team_size");
  base.scenario.max_turns = n("max_turns");
  ENTITY_FIELDS.forEach(
    ([key]) => (base.scenario.entity[key] = n("entity_" + key)),
  );
  base.scenario.entity.weapons = array("weapons");
  base.scenario.entity.chips = array("chips");
  if (String(f.get("map")).trim()) base.scenario.map = JSON.parse(f.get("map"));
  else delete base.scenario.map;
  base.budget_per_session = {
    max_calls: n("max_calls"),
    max_agent_steps: n("max_agent_steps"),
    max_test_matches: n("max_test_matches"),
    max_wall_seconds: n("max_wall_seconds"),
  };
  if (real)
    Object.assign(base.budget_per_session, {
      max_input_tokens: n("max_input_tokens"),
      max_output_tokens: n("max_output_tokens"),
      max_cost_usd: f.get("max_cost_usd"),
    });
  base.spending = real
    ? {
        allow_paid_calls: f.has("allow_paid_calls"),
        max_total_usd: f.get("max_total_usd"),
      }
    : { allow_paid_calls: false, max_total_usd: 0 };
  return base;
}
function planMarkup(p) {
  const total =
    p.ranked_matches_if_all_submit +
    p.mirrors_if_all_submit +
    p.g1_contemporary_matches +
    p.common_reference_matches;
  return `<div class="info-row"><span>Conversations</span><strong>${fmt(p.sessions)}</strong></div><div class="info-row"><span>Combats d’évaluation</span><strong>${fmt(total)}</strong></div><div class="info-row"><span>Essais de préparation, au plus</span><strong>${fmt(p.max_preparation_matches)}</strong></div><div class="info-row"><span>Plafond API global</span><strong>${money(p.max_cost_usd)}</strong></div><p class="muted" style="font-size:10px;margin-top:12px">Calendrier si toutes les IA soumettent une stratégie. ${p.simulated ? "Simulation sans appel API." : "Les réservations financières restent une estimation prudente, pas une facture garantie."}</p>`;
}
async function launchDialog(draftId = null, runId = null) {
  const config = draftId
      ? S.boot.drafts.find((d) => d.id === draftId).config
      : S.detail.metadata.config,
    p = await api("/api/plan", { config }, true);
  S.launch = { draftId, runId, config };
  openDialog(
    runId ? "Reprendre la compétition" : "Lancer la compétition",
    config.name,
    `<form data-form="launch">${planMarkup(p)}${p.simulated ? notice("Participants simulés, combats réels. Aucun appel à un LLM ni frais d’API.") : notice("Les appels utiliseront les clés configurées. Les prix sont ceux de votre configuration ; les montants ne constituent pas une facture fournisseur.", "warn")}<div>${config.models.map((m) => `<div class="info-row"><span>${e(m.id)}${m.provider !== "mock" ? `<small>${e(m.endpoint || (m.provider === "anthropic" ? "https://api.anthropic.com/v1/messages" : m.provider === "gemini" ? "https://generativelanguage.googleapis.com/v1beta" : "https://api.openai.com/v1/chat/completions"))}<br>Clé : ${e(m.api_key_env)}</small>` : ""}</span><strong>${e(m.model || m.profile)}${m.provider !== "mock" ? `<small>Seed : ${m.parameters?.seed ?? (m.provider === "anthropic" ? "non disponible" : "non fixée")}</small>` : ""}</strong></div>`).join("")}</div>${!p.simulated ? `<label class="check" style="margin-top:20px"><input type="checkbox" name="confirm_paid" required>J’autorise les appels API jusqu’au plafond global de ${money(config.spending.max_total_usd)}.</label>` : ""}<div class="form-footer">${btn("Annuler", "close-dialog")}<button type="submit" class="button primary">${runId ? "Reprendre" : "Démarrer la compétition"}</button></div></form>`,
  );
}
const TABS = [
  ["summary", "Synthèse"],
  ["conversation", "Conversations"],
  ["code", "Code & versions"],
  ["matches", "Combats"],
  ["files", "Fichiers"],
  ["events", "Journal"],
  ["config", "Configuration"],
];
function runHeader(d) {
  S.renderedJobState = S.boot.jobs.find((j) => j.run === S.run)?.status;
  const config = d.metadata.config || d.metadata.manifest,
    job = S.boot.jobs.find((j) => j.run === S.run),
    active = job && ["running", "stopping"].includes(job.status),
    experiment = !!d.metadata.config;
  return (
    head(
      config.name,
      "Résultats, conversations et fichiers.",
      `${active ? btn("■ Arrêter", "stop-job", `data-id="${e(job.id)}"`) : experiment && !d.archived ? btn("Reprendre", "resume") : ""}${experiment ? btn("Dupliquer la configuration", "clone-run") : ""}${experiment ? btn("Exporter", "export-run") : ""}`,
    ) +
    `<div class="toolbar">${config.models ? (config.models.every((m) => m.provider === "mock") ? badge("SIMULATION · aucun LLM appelé", "blue") : badge("API RÉELLES", "orange")) : badge("Stratégies fournies")}${d.archived ? badge("Copie exportée", "orange") : ""}${job ? status(job.status) : ""}<span class="mono muted" style="font-size:10px">${e(S.run)}</span><span class="spacer"></span>${job ? btn("Journal d’exécution", "job-log", `data-id="${e(job.id)}"`) : ""}</div><div class="tabs">${TABS.map(([key, label]) => `<button class="tab ${S.tab === key ? "active" : ""}" data-action="tab" data-tab="${key}">${label}</button>`).join("")}</div>`
  );
}
function sessionChooser(d) {
  if (!d.sessions.length) return "";
  S.session = d.sessions.some((s) => s.id === S.session)
    ? S.session
    : d.sessions[0].id;
  return `<div class="toolbar"><label for="session-choice">Conversation</label><select id="session-choice">${d.sessions.map((s) => `<option value="${e(s.id)}" ${s.id === S.session ? "selected" : ""}>${e(s.id)} · ${text(s.condition)} · ${text(s.status)}</option>`).join("")}</select><span class="spacer"></span><label class="check"><input id="follow-live" type="checkbox" ${S.follow ? "checked" : ""}>Suivre en direct</label></div>`;
}
async function renderRun(epoch) {
  const d = S.detail;
  let body = "";
  if (S.tab === "summary") {
    const statistics = await api("/api/statistics", { run: S.run });
    S.statistics = statistics;
    body = summary(d, statistics);
  } else if (S.tab === "config")
    body = `<section class="panel"><h2>Configuration figée et provenance</h2><p class="muted">Cette configuration décrit l’exécution enregistrée. Pour la modifier, créez une copie et lancez une nouvelle compétition.</p><pre>${e(pretty(d.metadata))}</pre></section>`;
  else if (S.tab === "conversation" || S.tab === "code") {
    const chooser = sessionChooser(d);
    if (!d.sessions.length && S.tab === "code") {
      S.files = (await api("/api/files", { run: S.run })).files.filter((f) =>
        f.path.endsWith(".leek"),
      );
      body =
        notice(
          "Sources figées du tournoi. Aucune génération ni écriture intermédiaire enregistrée.",
        ) + filesPage();
    } else if (!d.sessions.length)
      body = empty(
        "Pas de conversation enregistrée",
        "Ce tournoi reçoit directement du code .leek ; aucune requête de génération n’a été effectuée. Les participants simulés de la démo ont, eux, des conversations enregistrées.",
      );
    else if (S.tab === "conversation") {
      const data = await api("/api/conversation", {
        run: S.run,
        session: S.session,
        offset: S.offset,
      });
      body = chooser + conversation(data);
    } else {
      S.versions = await api("/api/versions", {
        run: S.run,
        session: S.session,
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
    S.events = await api("/api/events", {
      run: S.run,
      session: S.session || undefined,
      offset: S.offset,
    });
    body = eventsPage(S.events);
  }
  if (epoch !== S.epoch) return;
  $("#main").innerHTML = runHeader(d) + body;
  if (S.tab === "code" && d.sessions.length && S.versions?.versions?.length)
    await loadSource();
  if (S.tab === "matches" && S.matches.length) await loadMatch();
  if (
    (S.tab === "files" || (S.tab === "code" && !d.sessions.length)) &&
    S.files.length
  )
    await loadFile(
      S.files.find((f) => f.path === "report.md")?.path || S.files[0].path,
    );
}
function bars(rows) {
  if (!rows.length)
    return empty(
      "Pas encore de scores",
      "Les résultats apparaîtront après les combats.",
    );
  const width = 650,
    height = rows.length * 38 + 22;
  return `<svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Scores des stratégies">${rows.map((r, i) => `<text x="0" y="${i * 38 + 18}" class="chart-label">${e(r.label.length > 32 ? r.label.slice(0, 31) + "…" : r.label)}</text><rect x="258" y="${i * 38 + 5}" width="310" height="17" rx="4" fill="#f0f3fa"/><rect x="258" y="${i * 38 + 5}" width="${r.score == null ? 0 : 310 * r.score}" height="17" rx="4" fill="${COLORS[i % COLORS.length]}"/><text x="588" y="${i * 38 + 18}">${e(pct(r.score))}</text><title>${e(r.label)} : ${e(pct(r.score))}</title>`).join("")}</svg>`;
}
function summary(d, statistics = null) {
  const r = d.report,
    a = d.analysis,
    rows = (a?.rows || []).filter((v) => v.panel === S.panel),
    done = d.sessions.filter((s) => s.status !== "running").length;
  return (
    (r.simulated
      ? notice(
          "<strong>Participants simulés.</strong> Stratégies prédéfinies, combats réels, aucun appel API.",
        )
      : "") +
    (d.sessions.some((s) => s.status === "needs_reconciliation")
      ? notice(
          "Une réponse API est incertaine. Vérifiez les identifiants de requête, les usages et la facturation avant toute décision de reprise. Aucun paiement incertain n’est relancé automatiquement.",
          "warn",
        )
      : "") +
    `<div class="metrics">${metric("Sessions terminées", `${done} / ${d.sessions.length}`, `${r.valid_submissions ?? 0} soumissions valides`)}${metric("Combats terminés", fmt(completed(r)), "Évaluation ; préparation consultable à part", "⚔")}${metric("Coût API", r.cost_usd === undefined ? "—" : money(r.cost_usd), r.reserved_usd && Number(r.reserved_usd) > 0 ? `${money(r.reserved_usd)} réservés` : "Simulation ou coût calculé sur usage", "↗")}${metric("Tokens entrée / sortie", r.input_tokens == null ? "Non mesurés" : `${fmt(r.input_tokens)} / ${fmt(r.output_tokens)}`, r.simulated ? "Pas de tokens de LLM dans une simulation" : "Valeurs inconnues conservées comme telles", "≋")}</div>` +
    (statistics ? competitionStatistics(statistics) : "") +
    (a
      ? `<section class="panel"><div class="panel-title"><div><h2>Performance des stratégies</h2><small>G0 et G1 évaluées contre un même panel, sur les seeds finales.</small></div><select id="panel-choice" aria-label="Panel d’évaluation">${["all", "controls", "g0"].map((p) => `<option value="${p}" ${S.panel === p ? "selected" : ""}>${text(p)}</option>`).join("")}</select></div>${bars(rows.map((v) => ({ label: v.session, score: v.score })))}<p class="muted" style="font-size:11px;margin:13px 0 0">Score = (victoires + 0,5 × nuls) / combats terminés. Les miroirs sont séparés. « Panel complet » inclut les stratégies G0 figées et les contrôles écrits à la main.</p></section>
 <section class="panel flush"><div class="panel-head"><div><h2>Résultats détaillés</h2><p>Les opérations mesurent le calcul LeekScript, pas les tokens ni un coût en dollars.</p></div></div>${table(
   [
     "Stratégie",
     "Version",
     "Score",
     "Combats / pannes",
     "Opérations",
     "Erreurs / limite",
     "Entrée / sortie",
     "Coût API / trajectoire",
   ],
   rows.map(
     (v) =>
       `<tr><td><button class="table-button" data-action="session-conversation" data-session="${e(v.session)}">${e(v.session)}</button><small>${e(v.model)} · répétition ${v.replicate + 1}</small></td><td>G${v.generation}<small>${text(v.condition)}</small></td><td class="score numeric">${pct(v.score)}</td><td class="numeric">${fmt(v.completed)} / ${fmt(v.failed)}</td><td class="numeric">${fmt(v.operations)}</td><td class="numeric">${fmt(v.errors)} / ${fmt(v.operation_limit_hits)}</td><td class="numeric">${fmt(v.input_tokens)} / ${fmt(v.output_tokens)}</td><td class="numeric">${money(v.cost_usd)}<small>avec G0 : ${money(v.trajectory_cost_usd)}</small></td></tr>`,
   ),
 )}</section>
 <div class="grid two"><section class="panel"><h2>Le feedback a-t-il changé le résultat ?</h2><p class="muted">Différence G1 avec feedback − G1 sans feedback, à partir de la même conversation G0.</p>${(a.paired || []).map((p) => `<div class="info-row"><span>${e(p.parent)}</span><strong>${p.feedback_minus_control == null ? "Indisponible" : (p.feedback_minus_control >= 0 ? "+" : "") + fmt(p.feedback_minus_control * 100, 1) + " points"}</strong></div>`).join("")}<p class="muted" style="font-size:10px;margin-top:12px">${a.interval_95_exploratory ? `Intervalle exploratoire : ${e(pretty(a.interval_95_exploratory))}` : "Pas d’intervalle estimé : trop peu de conversations complètes."} Les démos simulées ne permettent aucune conclusion sur de vrais modèles.</p></section><section class="panel"><h2>Versions et conditions</h2><div class="info-row"><span>G0</span><strong>Première stratégie</strong></div><div class="info-row"><span>G1 sans feedback</span><strong>Amélioration sans résultats de combat</strong></div><div class="info-row"><span>G1 avec feedback</span><strong>Amélioration avec résultats</strong></div><p class="muted" style="font-size:11px;margin-top:13px">Les deux branches repartent du même code et du même historique. Leurs adversaires de mesure restent les mêmes.</p></section></div>`
      : "") +
    (d.standings
      ? `<section class="panel"><h2>Classement du tournoi</h2>${bars(d.standings.map((v) => ({ label: v.strategy || v.id, score: v.score })))}${raw(d.standings, "Toutes les statistiques du classement")}</section>`
      : "") +
    `<section class="panel flush"><div class="panel-head"><h2>État des conversations</h2></div>${
      d.sessions.length
        ? table(
            [
              "Session",
              "Condition",
              "État",
              "Appels / outils",
              "Préparation",
              "Temps",
              "",
            ],
            d.sessions.map(
              (s) =>
                `<tr><td><strong>${e(s.id)}</strong><small>${s.messages} messages</small></td><td>G${s.generation || 0} · ${text(s.condition)}</td><td>${status(s.status)} ${s.validity ? status(s.validity) : ""}</td><td>${s.calls} / ${s.steps}</td><td>${s.test_matches} combats</td><td>${fmt(s.wall_seconds, 1)} s</td><td>${btn("Explorer", "session-conversation", `data-session="${e(s.id)}"`)}</td></tr>`,
            ),
          )
        : empty(
            "Sessions en préparation",
            "Les états apparaîtront ici au fil de l’exécution.",
          )
    }</section>` +
    `<section class="panel">${raw(r, "Synthèse complète, métriques et résultats bruts")}${d.g0 ? raw(d.g0, "Tournoi contemporain G0 — classement et miroirs") : ""}${d.g1 ? raw(d.g1, "Tournoi contemporain G1 — classement et miroirs") : ""}${a ? raw(a, "Analyse complète, absences, agrégations et frontière coût / performance") : ""}</section>`
  );
}
function conversation(data) {
  return (
    notice(
      "Tous les messages enregistrés sont affichables : prompts, réponses exposées par l’API, appels d’outils et retours. Le raisonnement interne non fourni par une API n’est pas accessible.",
    ) +
    `<div class="pager"><span>${fmt(data.total)} messages · ${status(data.status)}</span><div class="actions">${btn("← Précédents", "conversation-page", `data-offset="${Math.max(0, S.offset - 25)}" ${S.offset === 0 ? "disabled" : ""}`)}<span>${S.offset + 1}–${Math.min(data.total, S.offset + 25)}</span>${btn("Suivants →", "conversation-page", `data-offset="${S.offset + 25}" ${S.offset + 25 >= data.total ? "disabled" : ""}`)}</div></div>` +
    data.messages
      .map((m, index) => {
        const native = m.native,
          content =
            m.role === "user"
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
                          .filter((p) => p.text)
                          .map((p) => p.text)
                          .join("\n")
                      : m.content || "";
        return `<article class="chat-message ${e(m.role)}" id="message-${S.offset + index}"><div class="message-head"><strong>${m.role === "user" ? "PROMPT / CONSIGNE" : m.role === "assistant" ? "RÉPONSE DE L’IA" : "RÉSULTAT D’OUTIL"} ${m.name ? "· " + e(m.name) : ""}</strong><span>Message ${S.offset + index + 1}${m.generation != null ? " · G" + m.generation : ""}${m.simulated ? " · simulé" : ""}</span></div>${content ? `<div class="message-content">${e(content)}</div>` : ""}${(m.tool_calls || []).map((c) => `<div class="tool-call"><strong>↳ ${e(c.name)}</strong><pre>${e(pretty(c.arguments))}</pre></div>`).join("")}${m.role === "user" && m.budgets ? raw({ budgets: m.budgets, scenario: m.scenario, feedback: m.feedback }, "Budgets, scénario et feedback inclus dans ce message") : ""}${m.usage ? `<div style="margin-top:12px"><small>Entrée ${fmt(m.usage.input_tokens)} · Sortie ${fmt(m.usage.output_tokens)} · Coût ${money(m.cost_usd)} · ${fmt(m.elapsed_seconds, 3)} s</small></div>` : ""}${m.sent_parameters ? `<div class="request-meta"><small>Seed envoyée : ${e(m.sent_parameters.seed ?? m.sent_parameters.generationConfig?.seed ?? (m.provider === "anthropic" ? "non disponible" : m.simulated ? "sans objet" : "non fixée"))}${m.model_version ? ` · Modèle retourné : ${e(m.model_version)}` : ""}${m.system_fingerprint ? ` · Backend : ${e(m.system_fingerprint)}` : ""}</small>${m.request_sha256 ? `<small class="mono">SHA-256 requête (JSON canonique) : ${e(m.request_sha256)}</small>` : ""}${raw(m.sent_parameters, "Requête envoyée — prompts, historique, outils et paramètres")}</div>` : ""}${raw(m, "Objet intégral enregistré — réponse native, requête, outils et métadonnées")}</article>`;
      })
      .join("")
  );
}
function codePage(data) {
  if (!data.versions.length)
    return empty(
      "Pas encore de fichier écrit",
      "Les versions apparaissent après chaque écriture confirmée par un outil. Les fichiers figés restent également accessibles dans l’onglet Fichiers.",
    );
  S.version = Math.min(
    S.version ?? data.versions.length - 1,
    data.versions.length - 1,
  );
  const current = data.versions[S.version];
  S.file = current.files.includes(S.file) ? S.file : current.files[0];
  return (
    notice(
      "Pas besoin de Git dans les dossiers des IA : le journal conserve les écritures et leurs empreintes. Ici, une version correspond à une écriture réussie. Les branches G1 incluent l’historique hérité de G0.",
    ) +
    `<div class="code-grid"><section class="panel"><h3>Historique des écritures</h3><div class="version-list">${data.versions.map((v) => `<button class="version-button ${v.index === S.version ? "active" : ""}" data-action="version" data-version="${v.index}"><strong>Version ${v.index + 1} <span class="timeline-tag">G${v.generation}</span></strong>${e(v.path)}<small>Après le message ${v.message + 1} · ${v.files.length} fichier(s)</small></button>`).join("")}</div></section><section class="panel"><div class="toolbar"><select id="source-file" aria-label="Fichier à consulter">${current.files.map((f) => `<option ${f === S.file ? "selected" : ""}>${e(f)}</option>`).join("")}</select><span class="spacer"></span>${btn("Voir la conversation", "version-message", `data-message="${current.message}"`)}</div><div class="toolbar"><label for="source-previous">Comparer à</label><select id="source-previous"><option value="-1">État vide</option>${data.versions
      .slice(0, S.version)
      .map(
        (v) =>
          `<option value="${v.index}" ${v.index === (S.previous ?? S.version - 1) ? "selected" : ""}>Version ${v.index + 1} · G${v.generation}</option>`,
      )
      .join(
        "",
      )}</select></div><div id="source-content">Chargement…</div></section></div>`
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
    `<h3>Code à la version ${v + 1}</h3><pre class="source">${e(d.after)}</pre><details open><summary>Différences avec l’état sélectionné</summary><pre class="source">${
      d.diff
        ? d.diff
            .split("\n")
            .map(
              (l) =>
                `<span class="diff-line ${l.startsWith("+") && !l.startsWith("+++") ? "add" : l.startsWith("-") && !l.startsWith("---") ? "remove" : l.startsWith("@@") ? "meta" : ""}">${e(l)}</span>`,
            )
            .join("")
        : "Aucun changement dans ce fichier."
    }</pre></details><small class="mono">SHA-256 : ${e(d.sha256)}</small>`;
}
function filesPage() {
  return `<div class="files-grid"><section class="panel"><h3>Fichiers de l’expérience</h3><input id="file-search" type="search" placeholder="Filtrer les chemins…" aria-label="Filtrer les fichiers" style="width:100%;margin-bottom:12px"><label class="check"><input id="engine-files" type="checkbox">Inclure les données statiques du moteur</label><small>${fmt(S.files.length)} fichiers consultables</small><div id="file-list" class="file-list">${fileButtons(S.files)}</div></section><section class="panel"><div id="file-title" class="panel-title"></div><div id="file-content">Choisir un fichier.</div></section></div>`;
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
    (files.length > 1500
      ? "<small>Filtrer pour retrouver les autres fichiers.</small>"
      : "")
  );
}
async function loadFile(path) {
  S.file = path;
  const epoch = S.epoch;
  $("#file-title").innerHTML =
    `<h3 class="mono" style="overflow-wrap:anywhere">${e(path)}</h3>${/\.(md|json)$/i.test(path) ? `<div class="actions">${btn("Brut", "file-mode", 'data-mode="raw"')}${btn("Interprété", "file-mode", 'data-mode="rendered"')}</div>` : ""}<a class="button small" href="/api/file?${query({ run: S.run, path, download: 1 })}" download>Télécharger</a>`;
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
  return `<section class="panel"><h2>Journal chronologique</h2><p class="muted">Intentions, réponses, réservations, outils et évaluations. Les artefacts sont vérifiés par empreinte lors de leur ouverture.</p><div class="toolbar"><select id="event-session" aria-label="Filtrer les événements par session"><option value="">Toutes les sessions</option>${S.detail.sessions.map((s) => `<option value="${e(s.id)}" ${S.session === s.id ? "selected" : ""}>${e(s.id)}</option>`).join("")}</select><span class="muted">${fmt(data.total)} événements</span></div>${table(
    ["N°", "Horodatage", "Session", "Type", ""],
    data.events.map(
      (v) =>
        `<tr><td>${v.id}</td><td>${date(v.at)}</td><td>${e(v.session)}</td><td><code>${e(v.kind)}</code></td><td>${btn("Voir l’artefact", "event", `data-id="${v.id}"`)}</td></tr>`,
    ),
  )}<div class="pager"><span>Événements ${S.offset + 1}–${Math.min(data.total, S.offset + 100)}</span><div class="actions">${btn("← Précédents", "event-page", `data-offset="${Math.max(0, S.offset - 100)}" ${S.offset === 0 ? "disabled" : ""}`)}${btn("Suivants →", "event-page", `data-offset="${S.offset + 100}" ${S.offset + 100 >= data.total ? "disabled" : ""}`)}</div></div></section>`;
}
function matchesPage() {
  const stages = [...new Set(S.matches.map((m) => m.stage))];
  S.matchPath = S.matchPath || S.matches[0]?.path;
  return (
    `<div class="toolbar"><input type="search" id="match-search" placeholder="Filtrer les adversaires ou la seed…" aria-label="Filtrer les combats"><select id="match-stage" aria-label="Étape de compétition"><option value="">Toutes les étapes</option>${stages.map((v) => `<option value="${e(v)}">${e(v === "." ? "Tournoi" : v)}</option>`).join("")}</select><span class="muted">${fmt(S.matches.length)} combats enregistrés, préparation incluse</span></div>` +
    (S.matches.length
      ? `<div class="match-layout"><div id="match-list" class="match-list">${matchButtons(S.matches)}</div><section class="panel" id="match-detail">Chargement du combat…</section></div>`
      : empty(
          "Les combats n’ont pas encore commencé",
          "Les replays et les échecs d’infrastructure apparaîtront ici au fil de l’exécution.",
        ))
  );
}
function matchButtons(rows) {
  return (
    rows
      .slice(0, 800)
      .map(
        (m) =>
          `<button class="match-card ${m.path === S.matchPath ? "active" : ""}" data-action="match" data-path="${e(m.path)}"><span class="badge ${m.stage.includes("panel") ? "blue" : ""}">${e(m.stage === "." ? "Tournoi" : m.stage)}</span><strong>${e(m.sides[0])}<br><span class="muted">contre</span> ${e(m.sides[1])}</strong><small>Seed ${e(m.seed)} · ${m.mirror ? "miroir · " : ""}${m.result.status === "completed" ? (m.result.winner_side === -1 ? "Match nul" : "Victoire : " + e(m.sides[m.result.winner_side])) : e(text(m.result.status))}</small></button>`,
      )
      .join("") +
    (rows.length > 800
      ? "<small>Filtrer pour retrouver les autres combats.</small>"
      : "")
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
    `<div class="panel-title"><div><h2>${result.status === "completed" ? (result.winner_side === -1 ? "Match nul" : "Victoire de " + e(row.sides[result.winner_side])) : e(text(result.status))}</h2><small>Seed ${e(row.seed)} · ${fmt(result.turns)} tours · ${fmt(result.elapsed_seconds, 2)} s</small></div>${status(result.status)}</div>${row.mirror ? notice("Match miroir : utile pour observer les effets de position ; exclu du score de classement.") : ""}${data.replay ? `<svg id="replay-board" class="board" role="img" aria-label="Carte du combat et positions des entités"></svg><div class="replay-controls">${btn("▷", "replay-play", 'id="replay-play" aria-label="Lire ou mettre en pause"')}${btn("←", "replay-prev", 'aria-label="Action précédente"')}<input id="replay-range" type="range" min="0" max="${data.replay.events.length}" value="0" aria-label="Position dans le replay">${btn("→", "replay-next", 'aria-label="Action suivante"')}<select id="replay-speed" aria-label="Vitesse de lecture"><option value="400">× 1</option><option value="150">× 2</option><option value="50">× 4</option></select></div><div class="toolbar"><strong id="replay-label" style="font-size:11px"></strong><span class="spacer"></span><span id="replay-count" class="muted" style="font-size:10px"></span></div><div id="replay-entities" class="entity-list"></div><div id="replay-events" class="event-list"></div><p class="muted" style="font-size:10px;margin-top:13px">${e(data.replay.note)}${data.replay.unknown_codes.length ? " Actions non projetées : " + e(data.replay.unknown_codes.join(", ")) + "." : ""}</p>` : notice(e(result.error || "Ce combat ne contient pas de replay exploitable."), "warn")}${data.statistics ? combatStatistics(data.statistics) : ""}${raw(result, "Métriques complètes : calcul, erreurs et résultat")}${data.scenario ? raw(data.scenario, "Scénario exact du combat") : ""}${raw(data.provenance, "Stratégies, empreintes et provenance")}${data.outcome ? raw(data.outcome, "Replay brut complet, actions et logs") : ""}`;
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
          { ...l, maxLife: l.life, alive: !l.summon },
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
    }
    if (code === 105 && entity(a[2]))
      Object.assign(entity(a[2]), {
        cellPos: a[3],
        life: a[4],
        maxLife: a[5],
        alive: true,
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
          `<polygon class="tile ${obstacles[c.id] ? "obstacle" : ""}" points="${c.x - 12},${c.y} ${c.x},${c.y - 6} ${c.x + 12},${c.y} ${c.x},${c.y + 6}"><title>Case ${c.id}${obstacles[c.id] ? " · obstacle" : ""}</title></polygon>`,
      )
      .join("") +
    (shot && origin
      ? `<line x1="${origin.x}" y1="${origin.y}" x2="${shot.x}" y2="${shot.y}" stroke="#df8f45" stroke-width="2" stroke-dasharray="3 2"/>`
      : "") +
    entities
      .filter((v) => !v.summon || v.alive)
      .map((v) => {
        const c = R.cellsById.get(v.cellPos);
        if (!c) return "";
        const color = v.team === 1 ? "#5278e5" : "#c77749";
        return `<g class="${v.alive ? "" : "dead"}"><ellipse cx="${c.x}" cy="${c.y + 2}" rx="10" ry="5" fill="${color}" opacity=".18"/>${state.actor === v.id ? `<circle cx="${c.x}" cy="${c.y - 5}" r="10" fill="none" stroke="${color}" stroke-width="1"/>` : ""}<circle cx="${c.x}" cy="${c.y - 5}" r="7" fill="${color}"/><text class="entity-label" x="${c.x}" y="${c.y - 5}">${v.id}</text><rect x="${c.x - 9}" y="${c.y - 16}" width="18" height="2" rx="1" fill="#cdd6e7"/><rect x="${c.x - 9}" y="${c.y - 16}" width="${18 * Math.max(0, Math.min(1, v.life / (v.maxLife || 1)))}" height="2" rx="1" fill="${color}"/><title>${e(v.name)} · ${v.life}/${v.maxLife} PV · case ${v.cellPos}</title></g>`;
      })
      .join("");
  $("#replay-range").value = index;
  $("#replay-label").textContent = state.last
    ? `Tour ${state.turn} · ${state.last.text}`
    : "Positions initiales";
  $("#replay-count").textContent = `Action ${index} / ${R.events.length}`;
  $("#replay-entities").innerHTML = entities
    .map(
      (v) =>
        `<div class="entity-card"><strong style="color:${v.team === 1 ? "#5278e5" : "#c77749"}">● ${e(v.name)} (#${v.id})</strong><span style="float:right">${v.life} / ${v.maxLife} PV</span><div class="hp-track"><div class="hp-fill" style="width:${Math.max(0, Math.min(100, (100 * v.life) / (v.maxLife || 1)))}%;background:${v.team === 1 ? "#5278e5" : "#c77749"}"></div></div></div>`,
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
    head(
      "Comparer les résultats",
      "Comparaison par modèle et par protocole de compétition.",
    ) +
    `<section class="panel"><h2>Choisir les compétitions</h2><p class="muted">Les expériences complètes sont comparées sur leurs adversaires fixes, indépendants des stratégies générées.</p><div class="comparison-select">${runs.map((r) => `<label class="choice"><input type="checkbox" name="compare-run" value="${e(r.id)}" ${selected.includes(r.id) ? "checked" : ""}><span><strong>${e(r.name)}</strong><small>${date(r.created_at)} · ${r.simulated ? "simulation" : r.simulated === false ? "API réelles" : "tournoi"}</small></span></label>`).join("")}</div><div class="form-footer">${btn("Comparer la sélection", "compare-selection", "", true)}</div></section><div id="comparison-result">${S.comparison ? comparisonResult(S.comparison) : notice("Les simulations et les appels réels restent dans des groupes séparés. Les exports ne sont jamais comptés une seconde fois.")}</div>`
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
      `${p.model} · G${p.generation} ${text(p.condition)} · ${p.model_id}`,
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
  const chart = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Évolution des scores entre compétitions">${[0, 0.25, 0.5, 0.75, 1].map((v) => `<line x1="${L}" x2="${right}" y1="${Y(v)}" y2="${Y(v)}" stroke="#e9edf5"/><text x="0" y="${Y(v) + 4}">${v * 100} %</text>`).join("")}${runs.map(([id, t], i) => `<text x="${X(i)}" y="240" text-anchor="middle">${e(new Date(t * 1000).toLocaleDateString("fr-FR"))}<title>${e(id)}</title></text>`).join("")}${[
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
          `<section class="panel"><div class="panel-title"><div><h2>Groupe comparable ${i + 1}</h2><small>${g.runs.length} compétition(s) · mêmes règles, mêmes seeds, mêmes adversaires fixes</small></div>${badge(g.protocol.simulated ? "Simulation" : "API réelles", g.protocol.simulated ? "blue" : "orange")}</div>${lineChart(g)}<div style="margin-top:22px">${table(
            [
              "Modèle / condition",
              "Score moyen",
              "Conversations retenues",
              "Incomplètes",
              "Compétitions",
              "Coût API",
              "Entrée / sortie",
              "Erreurs",
            ],
            g.models.map(
              (m) =>
                `<tr><td><strong>${e(m.model)}</strong><small>${e(m.participant?.provider)} · ${e(m.participant?.model || m.participant?.profile)}</small>${raw(m.participant, "Configuration du participant")}<small>G${m.generation} · ${text(m.condition)}</small></td><td class="score">${pct(m.score)}</td><td>${m.conversations}</td><td>${m.excluded}</td><td>${m.runs}</td><td>${money(m.cost_usd)}</td><td>${fmt(m.input_tokens)} / ${fmt(m.output_tokens)}</td><td>${fmt(m.errors)}</td></tr>`,
            ),
          )}</div>${raw(g, "Points individuels et protocole exact de ce groupe")}</section>`,
      )
      .join("") +
    (data.excluded.length
      ? `<section class="panel"><h2>Compétitions non agrégées</h2>${data.excluded.map((r) => `<div class="info-row"><strong>${e(r.run)}</strong><span>${e(r.reason)}</span></div>`).join("")}</section>`
      : "") +
    (!data.groups.length
      ? empty(
          "Aucun groupe comparable pour cette sélection",
          "Sélectionnez au moins une expérience G0/G1 ayant terminé son évaluation contre les stratégies fixes.",
        )
      : "")
  );
}
function helpPage() {
  return (
    head(
      "Comprendre l’arène",
      "Un guide de lecture pour savoir ce qui est mesuré, ce qui est simulé et où trouver les détails.",
    ) +
    `<div class="help-grid">${[
      [
        "Un participant, plusieurs conversations",
        "Un profil choisit le fournisseur, le modèle exact, ses paramètres et les tarifs. Chaque répétition crée une conversation indépendante. Sa stratégie est du code LeekScript 4 exécuté par le moteur officiel Leek Wars.",
      ],
      [
        "G0 et G1",
        "G0 est la première stratégie soumise. G1 est une amélioration. Deux copies du même historique G0 reçoivent soit une consigne d’amélioration seule (contrôle), soit cette consigne et les résultats des combats (feedback).",
      ],
      [
        "Scores et panels",
        "Victoire = 1, nul = 0,5, défaite = 0. Le score est la moyenne sur les combats terminés. Le panel complet contient les stratégies G0 figées et les contrôles écrits à la main. Les miroirs sont présentés à part.",
      ],
      [
        "Une simulation ne compare pas des LLM",
        "Les participants mock suivent un scénario programmé. Les diagnostics et les combats sont réels, mais le code produit est prédéfini. Le gain de leur branche feedback est construit par la démo : il ne prouve aucun apprentissage.",
      ],
      [
        "Coûts et tokens",
        "Les tarifs sont datés et exprimés en USD par million de tokens. Le coût calculé utilise les usages renvoyés par l’API. Une valeur inconnue n’est jamais remplacée par zéro. Les réservations en attente ne sont pas des factures confirmées.",
      ],
      [
        "Historique des fichiers",
        "Chaque écriture confirmée permet de reconstruire un état des fichiers et de le comparer au précédent. Les écritures proposées mais refusées sont visibles dans la conversation, sans devenir une version du code. Les sources soumises restent figées.",
      ],
      [
        "Replays",
        "Le lecteur montre une projection schématique de la carte et des actions du moteur : déplacements, attaques, PV, soins et éliminations. Les effets détaillés du client officiel ne sont pas tous animés. Les actions brutes et les métriques moteur font référence.",
      ],
      [
        "Comparer plusieurs compétitions",
        "Le tableau multi-compétitions utilise les mêmes contrôles fixes, et sépare les scénarios, seeds, moteurs et modes simulés/réels différents. Les scores sont moyennés par conversation complète. Il ne constitue pas un classement universel des modèles.",
      ],
      [
        "Arrêt et reprise",
        "Un arrêt conserve les checkpoints. Une reprise vérifie les sources, le code, le moteur et les paramètres. Si une réponse payante est incertaine, le journal doit être rapproché de la facturation avant toute décision. Dupliquer une configuration lance une nouvelle expérience.",
      ],
      [
        "Vos données",
        "Les configurations et les journaux de lancement de l’interface se trouvent dans .arena/ui. Les expériences sont dans runs. Les clés saisies ici restent en mémoire. Fermer le serveur les efface ; les clés déjà présentes dans son environnement restent gérées par votre système.",
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
    else if (a === "refresh") {
      await refreshBoot();
      await renderRoute();
      toast("Données actualisées.");
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
        $("#available-models").innerHTML =
          `<option value="">Choisir un modèle…</option>` +
          data.models
            .map(
              (m) =>
                `<option value="${e(m.id)}">${e(m.name)} · ${e(m.id)}</option>`,
            )
            .join("");
        $("#model-list-status").textContent =
          `${data.models.length} modèles${data.truncated ? " · liste partielle" : ""}. La disponibilité pour les conversations et les outils dépend du modèle.`;
      } catch (error) {
        if (form.isConnected)
          $("#model-list-status").textContent =
            error.message + " — saisie manuelle possible.";
      } finally {
        node.disabled = false;
      }
    } else if (a === "edit-participant") participantDialog(node.dataset.id);
    else if (a === "delete-participant") {
      await api("/api/participant/delete", { id: node.dataset.id }, true);
      await refreshBoot();
      await renderRoute();
      toast(
        "Profil retiré. Les compétitions existantes conservent leur configuration.",
      );
    } else if (a === "close-dialog") {
      $("#dialog").close();
      S.logJob = null;
    } else if (a === "new-competition" || a === "new-demo") {
      S.editDraft = null;
      S.editConfig =
        a === "new-demo"
          ? structuredClone(S.boot.default_config)
          : freshConfig();
      navigate("editor");
      if (S.view === "editor") await renderRoute();
    } else if (a === "edit-draft") {
      const d = S.boot.drafts.find((d) => d.id === node.dataset.id);
      S.editDraft = d.id;
      S.editConfig = structuredClone(d.config);
      navigate("editor");
    } else if (a === "delete-draft") {
      await api("/api/competition/delete", { id: node.dataset.id }, true);
      await refreshBoot();
      await renderRoute();
      toast("Configuration retirée. Les exécutions sont conservées.");
    } else if (a === "clone-run") {
      S.editDraft = null;
      S.editConfig = structuredClone(S.detail.metadata.config);
      S.editConfig.name += " — copie";
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
      toast(
        "Configuration importée. Vérifiez les champs avant de l’enregistrer.",
      );
    } else if (a === "launch") await launchDialog(node.dataset.id);
    else if (a === "resume") await launchDialog(null, S.run);
    else if (a === "open-run") navigate("run", { run: node.dataset.run });
    else if (a === "tab")
      navigate("run", {
        run: S.run,
        tab: node.dataset.tab,
        session: S.session,
      });
    else if (a === "session-conversation")
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
        offset: Math.floor(Number(node.dataset.message) / 25) * 25,
      });
    else if (a === "file-mode") {
      S.fileMode = node.dataset.mode;
      renderFileView();
    } else if (a === "file") await loadFile(node.dataset.path);
    else if (a === "match") {
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
        "Événement " + node.dataset.id,
        "Artefact vérifié par son empreinte SHA-256.",
        `<pre>${e(pretty(data))}</pre>`,
      );
    } else if (a === "export-run") {
      node.disabled = true;
      const result = await api("/api/export", { run: S.run }, true);
      await refreshBoot();
      toast("Export créé : " + result.run);
    } else if (a === "stop-job") {
      await api("/api/stop", { id: node.dataset.id }, true);
      toast("Arrêt demandé. Les checkpoints sont conservés.");
    } else if (a === "job-log") {
      S.logJob = node.dataset.id;
      const data = await api("/api/job", { id: S.logJob });
      openDialog(
        "Journal d’exécution",
        `${data.job.name} · ${text(data.job.status)}`,
        `<pre id="job-log-live" class="run-log">${e(data.content || "Initialisation…")}</pre><small>Derniers 128 Ko du journal.</small>`,
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
          max_input_tokens_per_call: Number(f.get("max_input_tokens_per_call")),
          max_output_tokens: Number(f.get("max_output_tokens")),
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
      toast("Participant enregistré.");
    } else if (type === "competition") {
      const config = readCompetition(form);
      await api("/api/competition", { config, id: S.editDraft }, true);
      await refreshBoot();
      navigate("competitions");
      toast("Configuration enregistrée. Aucun appel API effectué.");
    } else if (type === "launch") {
      const launch = S.launch;
      const job = await api(
        "/api/launch",
        {
          draft_id: launch.draftId,
          run: launch.runId,
          confirm_paid: f.has("confirm_paid"),
          ceiling: launch.config.spending.max_total_usd,
        },
        true,
      );
      $("#dialog").close();
      await refreshBoot();
      navigate("run", { run: job.run });
      toast("Compétition démarrée.");
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
    } else if (n.id === "available-models") {
      if (n.value) n.form.elements.model.value = n.value;
    } else if (n.id === "metric-set") {
      S.metricSet = n.value;
      if (S.tab === "summary")
        $("#statistics-stage-detail").innerHTML = statisticsStage(
          S.statistics.stages[Number($("#statistics-stage").value)],
        );
      else if (S.combatStatistics)
        $(".combat-statistics").outerHTML = combatStatistics(
          S.combatStatistics,
        );
    } else if (n.id === "statistics-stage") {
      $("#statistics-stage-detail").innerHTML = statisticsStage(
        S.statistics.stages[Number(n.value)],
      );
    } else if (n.id === "engine-files") {
      $("#file-list").innerHTML = fileButtons(S.files);
    } else if (n.id === "session-choice")
      navigate("run", { run: S.run, tab: S.tab, session: n.value });
    else if (n.id === "panel-choice") {
      S.panel = n.value;
      await renderRun(S.epoch);
    } else if (n.id === "source-file") {
      S.file = n.value;
      await loadSource();
    } else if (n.id === "source-previous") {
      S.previous = Number(n.value);
      await loadSource();
    } else if (n.id === "event-session")
      navigate("run", { run: S.run, tab: "events", session: n.value });
    else if (n.id === "follow-live") {
      S.follow = n.checked;
    } else if (n.id === "match-stage") filterMatches();
    else if (n.id === "replay-speed" && replayTimer) {
      clearInterval(replayTimer);
      replayTimer = null;
      playReplay();
    }
  } catch (error) {
    showError(error);
  }
});
function filterMatches() {
  const q = ($("#match-search")?.value || "").toLowerCase(),
    stage = $("#match-stage")?.value;
  $("#match-list").innerHTML = matchButtons(
    S.matches.filter(
      (m) =>
        (!stage || m.stage === stage) &&
        `${m.sides.join(" ")} ${m.seed}`.toLowerCase().includes(q),
    ),
  );
}
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
  if (n.id === "match-search") filterMatches();
  if (n.id === "replay-range") renderReplay(Number(n.value));
});
$("#dialog").addEventListener("close", () => {
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
    updateChrome();
    if (S.logJob && $("#job-log-live")) {
      const log = await api("/api/job", { id: S.logJob });
      $("#job-log-live").textContent = log.content;
    }
    if (
      S.view === "run" &&
      !$("#dialog").open &&
      (S.tab === "summary" || S.follow) &&
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
        old !== pretty(d.sessions) ||
        pretty(S.detail.report) !== pretty(d.report) ||
        S.renderedJobState !== S.boot.jobs.find((j) => j.run === S.run)?.status
      ) {
        S.detail = d;
        const scroll = window.scrollY;
        if (S.follow && S.tab === "conversation") {
          const session = d.sessions.find((v) => v.id === S.session);
          S.offset =
            Math.floor(Math.max(0, (session?.messages || 1) - 1) / 25) * 25;
        }
        if (S.follow && S.tab === "code") {
          S.version = null;
          S.previous = null;
        }
        await renderRun(epoch);
        window.scrollTo(
          0,
          S.follow && S.tab === "conversation"
            ? document.body.scrollHeight
            : scroll,
        );
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
      "Connexion impossible",
      error.message,
      btn("Réessayer", "refresh"),
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
        "Vue interprétée tronquée. Le texte intégral reste disponible en vue brute et au téléchargement.",
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
    return `<small>Suite disponible en vue brute.</small>`;
  if (value === null || typeof value !== "object")
    return `<div class="json-leaf"><strong>${e(key)}</strong> <code>${e(JSON.stringify(value))}</code></div>`;
  const entries = Object.entries(value);
  const children = [];
  for (const [k, v] of entries.slice(0, 500)) {
    if (budget.left <= 0) break;
    children.push(jsonView(v, k, depth + 1, budget));
  }
  return `<details ${depth < 2 ? "open" : ""}><summary>${e(key)} <small>${Array.isArray(value) ? "[" + entries.length + "]" : "{" + entries.length + "}"}</small></summary><div class="json-children">${children.join("")}${children.length < entries.length ? "<small>Suite disponible en vue brute.</small>" : ""}</div></details>`;
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
        notice("JSON invalide") + `<pre class="source">${e(content)}</pre>`;
    }
  } else node.innerHTML = `<pre class="source">${e(content)}</pre>`;
  $$("[data-action=file-mode]").forEach((n) =>
    n.classList.toggle("primary", n.dataset.mode === (S.fileMode || "raw")),
  );
}

const COMBAT_COLUMNS = [
  ["ai_turns", "Tours joués"],
  ["operations", "Opérations"],
  ["actions", "Actions"],
  ["shots", "Tirs"],
  ["chips", "Puces"],
  ["weapon_changes", "Armes"],
  ["moves", "Déplacements"],
  ["cells_moved", "Cases"],
  ["tp_lost", "PA retirés"],
  ["mp_lost", "PM retirés"],
  ["damage_dealt", "Dégâts donnés"],
  ["damage_taken", "Dégâts reçus"],
  ["healing_given", "Soins donnés"],
  ["healing_received", "Soins reçus"],
  ["erosion_dealt", "Érosion donnée"],
  ["erosion_taken", "Érosion reçue"],
  ["deaths", "Morts"],
  ["errors", "Erreurs"],
  ["operation_limit_hits", "Limites ops"],
  ["stack_overflows", "Pile dépassée"],
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
  return `<label class="field">Mesures<select id="metric-set">${[
    ["overview", "Vue d’ensemble"],
    ["compute", "Calcul et erreurs"],
    ["actions", "Actions et déplacements"],
    ["damage", "Dégâts et soins"],
    ["all", "Toutes les mesures"],
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
  return table(
    [
      ...(perTurn ? ["Tour"] : []),
      "Leek / stratégie",
      ...columns.map(([, label]) => label),
      ...(mean ? ["Ops / tour joué"] : []),
    ],
    rows.map(
      (row) =>
        `<tr>${perTurn ? `<td>${e(row.turn)}</td>` : ""}<td>${e(row.name || row.id)}${row.side != null ? `<small>Côté ${row.side + 1} · #${row.entity}</small>` : ""}</td>${columns.map(([key]) => `<td>${fmt(row[key])}</td>`).join("")}${mean ? `<td>${fmt(row.operations != null && row.ai_turns ? row.operations / row.ai_turns : null, 1)}</td>` : ""}</tr>`,
    ),
  );
}
function combatStatistics(data) {
  return `<section class="combat-statistics"><h3>Statistiques du combat</h3>${metricSetPicker()}<p class="muted">Limite : ${fmt(data.operations_limit_per_turn)} opérations par tour joué et par leek (${e(data.limit_source)}). ${e(data.action_definition)}</p>${data.missing.map((m) => notice(e(m))).join("")}<h3>Total du combat et par équipe</h3>${combatTable([data.total, ...data.sides])}<h3>Total par leek</h3>${combatTable(data.entities)}<details><summary>Total par tour</summary>${combatTable(data.rounds, true)}</details><details><summary>Détail par tour et par leek</summary>${combatTable(data.turns, true)}</details></section>`;
}
function competitionStatistics(data) {
  return `<section class="panel"><h2>Statistiques des combats</h2><p class="muted">Limite : ${fmt(data.operations_limit_per_turn)} opérations par tour joué et par leek. Actions = déplacements, changements d’arme, tirs et puces. Les totaux incluent les miroirs ; les matrices les excluent.</p><div class="form-grid">${metricSetPicker()}<label class="field">Étape<select id="statistics-stage">${data.stages.map((g, i) => `<option value="${i}">${e(g.stage === "." ? "Tournoi" : g.stage)}</option>`).join("")}</select></label></div><div id="statistics-stage-detail">${statisticsStage(data.stages[0])}</div></section>`;
}
function statisticsStage(group) {
  if (!group) return empty("Aucun combat enregistré", "");
  const names = [
    ...new Set(
      Object.entries(group.matrix).flatMap(([who, others]) => [
        who,
        ...Object.keys(others),
      ]),
    ),
  ].sort();
  return `<p class="muted">${group.matches} combats · ${group.with_replay} replays disponibles. — = donnée absente de l’archive. Détail par tour et par leek dans l’onglet Combats.</p>${combatTable(Object.values(group.strategies))}<h3>Matrice des combats</h3><p class="muted">Ligne contre colonne : victoires / nuls / défaites. Les pannes sont indiquées séparément.</p><div class="matrix">${table(
    ["Stratégie", ...names.map(e)],
    names.map(
      (who) =>
        `<tr><th>${e(who)}</th>${names
          .map((other) => {
            const r = group.matrix[who]?.[other];
            if (!r) return "<td>—</td>";
            const n = r.wins + r.draws + r.losses;
            return `<td style="background:${n ? `rgba(82,120,229,${((r.wins + 0.5 * r.draws) / n) * 0.18})` : "transparent"}">${r.wins} / ${r.draws} / ${r.losses}<small>${pct(n ? (r.wins + 0.5 * r.draws) / n : null)}${r.failures ? ` · ${r.failures} pannes` : ""}</small></td>`;
          })
          .join("")}</tr>`,
    ),
  )}</div>`;
}
