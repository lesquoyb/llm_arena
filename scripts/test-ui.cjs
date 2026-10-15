/* Browser-only development check. Production needs neither Node nor Playwright. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { once } = require("node:events");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");
const python =
  process.env.ARENA_UI_TEST_PYTHON ||
  (fs.existsSync(path.join(root, ".venv", "bin", "python"))
    ? path.join(root, ".venv", "bin", "python")
    : "python");
const artifacts =
  process.env.ARENA_UI_ARTIFACTS || path.join(root, "runs", "ui-browser");
async function main() {
  fs.mkdirSync(artifacts, { recursive: true });
  const server = spawn(
    python,
    [path.join(__dirname, "ui-browser-fixture.py")],
    {
      cwd: root,
      env: { ...process.env, PYTHONUTF8: "1" },
      stdio: ["ignore", "pipe", "inherit"],
    },
  );
  let browser;
  try {
    const url = await new Promise((resolve, reject) => {
      let text = "";
      const timer = setTimeout(
        () => reject(Error("Fixture server did not start")),
        20000,
      );
      server.stdout.on("data", (chunk) => {
        text += chunk.toString();
        if (text.includes("\n")) {
          clearTimeout(timer);
          try {
            resolve(JSON.parse(text.split("\n")[0]).url);
          } catch (error) {
            reject(error);
          }
        }
      });
      server.once("exit", (code) =>
        reject(Error("Fixture server exited " + code)),
      );
    });
    browser = await chromium.launch({
      headless: true,
      ...(process.env.ARENA_BROWSER_EXECUTABLE
        ? { executablePath: process.env.ARENA_BROWSER_EXECUTABLE }
        : {}),
      args: ["--no-sandbox"],
    });
    const page = await browser.newPage({
        viewport: { width: 1440, height: 1000 },
      }),
      errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("request", (r) => {
      if (!r.url().startsWith(url))
        errors.push("Unexpected external request: " + r.url());
    });
    await page.goto(url);
    await page
      .getByRole("heading", { name: "Vue d’ensemble", exact: true })
      .waitFor();
    await page.screenshot({
      path: path.join(artifacts, "dashboard.png"),
      fullPage: true,
    });
    await page
      .getByRole("link", { name: "Participants", exact: false })
      .click();
    await page.getByRole("button", { name: "Ajouter un participant" }).click();
    await page.getByLabel("Identifiant du participant").fill("browser-api");
    await page.getByLabel("Fournisseur").selectOption("openai");
    assert.equal(
      await page.getByLabel("Identifiant du participant").inputValue(),
      "browser-api",
    );
    const icon = await page.request.get(url + "/favicon.png");
    assert.equal(icon.status(), 200);
    assert.equal(icon.headers()["content-type"], "image/png");
    assert((await icon.body()).length > 1000);
    await page.route("**/api/models", async (route) => {
      const payload = route.request().postDataJSON();
      assert.equal(payload.provider, "openai");
      await route.fulfill({
        json: {
          models: [{ id: "fixture-model", name: "Modèle du catalogue" }],
          truncated: false,
        },
      });
    });
    await page.getByRole("button", { name: "Charger les modèles" }).click();
    await page.getByLabel("Modèles disponibles").selectOption("fixture-model");
    assert.equal(
      await page.getByLabel("Identifiant exact du modèle").inputValue(),
      "fixture-model",
    );
    await page.getByLabel("Seed du modèle").fill("42");
    await page.getByLabel("Prix entrée / million").fill("1.25");
    await page.getByLabel("Prix sortie / million").fill("2.5");
    await page.getByLabel("Prix cache lu / million").fill("0.125");
    await page
      .getByLabel("Clé API — pour cette session uniquement")
      .fill("browser-only-secret");
    await page
      .getByRole("button", { name: "Enregistrer le participant" })
      .click();
    await page.getByText("browser-api", { exact: true }).waitFor();
    const boot = await page.request.get(url + "/api/bootstrap");
    const bootData = await boot.json();
    assert(!JSON.stringify(bootData).includes("browser-only-secret"));
    assert.equal(
      bootData.participants.find((p) => p.spec.id === "browser-api").spec
        .parameters.seed,
      42,
    );
    await page.getByRole("button", { name: "Ajouter un participant" }).click();
    await page.getByLabel("Fournisseur").selectOption("gemini");
    assert.equal(
      await page.getByLabel("Variable de la clé API").inputValue(),
      "ARENA_GEMINI_KEY",
    );
    assert.equal(await page.getByLabel("Seed du modèle").inputValue(), "0");
    await page.getByLabel("Fournisseur").selectOption("anthropic");
    assert.equal(await page.getByLabel("Seed du modèle").count(), 0);
    await page
      .getByText("Seed : non disponible dans l’API Anthropic.", { exact: true })
      .waitFor();
    await page.getByRole("button", { name: "Annuler", exact: true }).click();
    await page
      .getByRole("link", { name: "Compétitions", exact: false })
      .click();
    await page.getByRole("button", { name: "Nouvelle compétition" }).click();
    await page
      .getByLabel("Nom de la compétition")
      .fill("Configuration navigateur");
    await page.getByLabel("Répétitions par participant").fill("2");
    await page.getByLabel("Cycle d’évaluation").selectOption("1");
    await page.getByRole("button", { name: "Calculer le calendrier" }).click();
    await page
      .locator("#plan-preview")
      .getByText("Conversations", { exact: true })
      .waitFor();
    assert((await page.locator("#plan-preview").innerText()).includes("4"));
    await page.getByLabel("Répétitions par participant").fill("1");
    await page.getByLabel("Tours maximum").fill("1");
    await page.getByLabel("Ajouter les matchs miroirs").uncheck();
    await page
      .getByRole("button", { name: "Enregistrer la configuration" })
      .click();
    const configRow = page
      .locator("tr")
      .filter({ hasText: "Configuration navigateur" });
    await configRow.waitFor();
    await configRow.getByRole("button", { name: "Lancer" }).click();
    assert(
      (await page.getByRole("dialog").innerText()).includes(
        "Aucun appel à un LLM",
      ),
    );
    assert.equal(
      await page.getByRole("dialog").locator("[name=confirm_paid]").count(),
      0,
    );
    if (process.env.ARENA_UI_LIVE_ENGINE === "1") {
      await page
        .getByRole("button", { name: "Démarrer la compétition", exact: true })
        .click();
      await page.waitForFunction(
        async () => {
          const run = new URLSearchParams(location.hash.slice(1)).get("run");
          if (!run) return false;
          const response = await fetch("/api/runs"),
            data = await response.json();
          const job = data.jobs.find((j) => j.run === run);
          if (job?.status === "failed") throw Error("Real UI job failed");
          return job?.status === "completed";
        },
        null,
        { timeout: 120000, polling: 1000 },
      );
      await page.waitForFunction(
        () =>
          document.querySelectorAll(".metrics .value")[1]?.textContent === "2",
      );
      await page.screenshot({
        path: path.join(artifacts, "live-competition.png"),
        fullPage: true,
      });
      console.log(
        "Real engine competition launched and monitored through browser.",
      );
    } else
      await page.getByRole("button", { name: "Fermer", exact: true }).click();
    await page
      .getByRole("link", { name: "Compétitions", exact: false })
      .click();
    await page.getByRole("button", { name: "Nouvelle compétition" }).click();
    await page
      .getByLabel("Nom de la compétition")
      .fill("Configuration API non lancée");
    await page.locator("[name=participant][value=mock-repair]").uncheck();
    await page.locator("[name=participant][value=mock-single]").uncheck();
    await page.locator("[name=participant][value=browser-api]").check();
    await page.getByLabel("Autoriser les API payantes").check();
    await page
      .getByRole("button", { name: "Enregistrer la configuration" })
      .click();
    await page
      .locator("tr")
      .filter({ hasText: "Configuration API non lancée" })
      .getByRole("button", { name: "Lancer" })
      .click();
    const paid = page.getByRole("dialog").locator("[name=confirm_paid]");
    await paid.waitFor();
    assert.equal(await paid.isChecked(), false);
    assert.equal(await paid.getAttribute("required"), "");
    await page.getByRole("button", { name: "Fermer", exact: true }).click();
    await page.goto(url + "/#view=run&run=legacy&tab=code");
    await page.waitForFunction(() =>
      document
        .querySelector("#file-content")
        ?.textContent.includes("stratégie fournie directement"),
    );
    assert(!(await page.locator("#toast").innerText()).includes("undefined"));
    await page
      .getByRole("button", { name: "Conversations", exact: true })
      .click();
    await page
      .getByText("Pas de conversation enregistrée", { exact: true })
      .waitFor();
    await page.goto(url + "/#view=run&run=one");
    await page
      .getByRole("heading", { name: "Performance des stratégies" })
      .waitFor();
    await page.getByRole("heading", { name: "Matrice des combats" }).waitFor();
    await page.getByLabel("Mesures", { exact: false }).selectOption("damage");
    await page
      .locator("#statistics-stage-detail th")
      .filter({ hasText: "Dégâts donnés" })
      .waitFor();
    await page.getByLabel("Mesures", { exact: false }).selectOption("overview");
    await page.getByText("20 000 000", { exact: false }).first().waitFor();
    assert((await page.locator(".matrix").innerText()).includes("1 / 0 / 0"));
    await page.screenshot({
      path: path.join(artifacts, "summary.png"),
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Conversations", exact: true })
      .click();
    await page.locator(".chat-message.user").first().waitFor();
    assert(
      (await page.locator(".chat-message.user").first().innerText()).includes(
        "<script>not executable</script>",
      ),
    );
    assert.equal(
      await page.evaluate(() => window.__arenaUnexpectedScript),
      undefined,
    );
    await page
      .getByRole("button", { name: "Code & versions", exact: true })
      .click();
    await page.locator("#source-content pre").first().waitFor();
    assert.equal(await page.locator(".version-button").count(), 2);
    assert(
      (await page.locator("#source-content").innerText()).includes(
        "+var a = 2",
      ),
    );
    await page.locator(".version-button").first().click();
    await page.waitForFunction(() =>
      document
        .querySelector("#source-content")
        ?.textContent.includes("Code à la version 1"),
    );
    assert(
      (await page.locator("#source-content pre").first().innerText()).includes(
        "var a = 1",
      ),
    );
    await page.getByRole("button", { name: "Combats", exact: true }).click();
    await page.locator("#replay-board circle").first().waitFor();
    await page.getByLabel("Mesures", { exact: false }).selectOption("compute");
    await page
      .locator(".combat-statistics th")
      .filter({ hasText: "Opérations" })
      .first()
      .waitFor();
    await page.getByLabel("Mesures", { exact: false }).selectOption("overview");
    await page.locator("#replay-range").evaluate((n) => {
      n.value = n.max;
      n.dispatchEvent(new Event("input", { bubbles: true }));
    });
    assert(
      (await page.locator("#replay-label").innerText()).includes("éliminé"),
    );
    assert.equal(await page.locator("#replay-board .dead").count(), 1);
    await page.screenshot({
      path: path.join(artifacts, "replay.png"),
      fullPage: true,
    });
    await page.getByRole("button", { name: "Fichiers", exact: true }).click();
    await page.locator("#file-search").fill("main.leek");
    await page.locator(".file-button").first().click();
    await page.waitForFunction(() =>
      document
        .querySelector("#file-content")
        ?.textContent.includes("var a = 2"),
    );
    const download = page.waitForEvent("download");
    await page.getByRole("link", { name: "Télécharger" }).click();
    await (await download).saveAs(path.join(artifacts, "download-main.leek"));
    assert.equal(
      fs.readFileSync(path.join(artifacts, "download-main.leek"), "utf8"),
      "var a = 2\n",
    );
    await page.locator("#file-search").fill("report.md");
    await page.locator(".file-button").first().click();
    await page.getByRole("button", { name: "Interprété", exact: true }).click();
    await page.locator("#file-content h1").waitFor();
    assert.equal(await page.locator("#file-content img").count(), 0);
    assert.equal(await page.locator("#file-content table").count(), 1);
    await page.getByRole("button", { name: "Brut", exact: true }).click();
    assert(
      (await page.locator("#file-content pre").innerText()).includes(
        "# Rapport navigateur",
      ),
    );
    await page.locator("#file-search").fill("example.json");
    await page.locator(".file-button").first().click();
    await page.getByRole("button", { name: "Interprété", exact: true }).click();
    await page.locator("#file-content .json-children").first().waitFor();
    assert.equal(await page.locator("#file-content script").count(), 0);
    assert.equal(
      await page.evaluate(() => window.__arenaUnexpectedScript),
      undefined,
    );
    await page.getByRole("button", { name: "Journal", exact: true }).click();
    await page.getByRole("button", { name: "Voir l’artefact" }).first().click();
    await page
      .getByRole("dialog")
      .getByText('"test": "event"', { exact: false })
      .waitFor();
    await page.getByRole("button", { name: "Fermer", exact: true }).click();
    await page
      .getByRole("link", { name: "Comparer les résultats", exact: false })
      .click();
    await page.locator("[name=compare-run][value=one]").check();
    await page.locator("[name=compare-run][value=two]").check();
    await page.getByRole("button", { name: "Comparer la sélection" }).click();
    await page.getByRole("heading", { name: "Groupe comparable 1" }).waitFor();
    assert(
      (await page.locator("#comparison-result").innerText()).includes("60 %"),
    );
    await page.screenshot({
      path: path.join(artifacts, "comparison.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(url + "/#view=dashboard");
    await page
      .getByRole("heading", { name: "Vue d’ensemble", exact: true })
      .waitFor();
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
      "Mobile page overflows horizontally",
    );
    await page.screenshot({
      path: path.join(artifacts, "mobile.png"),
      fullPage: true,
    });
    assert.deepEqual(errors, []);
    console.log(
      "Browser checks passed: profiles, configuration, prompts, versions/diff, replay, download, journal, aggregation, mobile.",
    );
  } finally {
    if (browser) await browser.close();
    server.kill("SIGINT");
    await Promise.race([
      once(server, "exit"),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]);
    if (server.exitCode === null) server.kill("SIGKILL");
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
