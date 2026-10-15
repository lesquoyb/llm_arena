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
    assert.equal(await page.locator("html").getAttribute("lang"), "en");
    await page
      .getByRole("heading", { name: "Overview", exact: true })
      .waitFor();
    await page.screenshot({
      path: path.join(artifacts, "dashboard.png"),
      fullPage: true,
    });
    await page
      .getByRole("link", { name: "Participants", exact: false })
      .click();
    await page.getByRole("button", { name: "Add participant" }).click();
    await page.getByLabel("Participant ID").fill("browser-api");
    await page.getByLabel("Provider").selectOption("openai");
    assert.equal(
      await page.getByLabel("Participant ID").inputValue(),
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
          models: [
            {
              id: "fixture-model",
              name: "Catalog model " + "long model name ".repeat(15),
            },
            { id: "other-model", name: "Other model" },
          ],
          excluded: [{ id: "image-model", reason: "Image generation only" }],
          truncated: false,
        },
      });
    });
    await page.getByRole("button", { name: "Load models" }).click();
    await page.getByLabel("Search models").fill("fixture");
    assert.equal(await page.locator(".model-option").count(), 1);
    const modelFits = await page
      .locator(".model-option strong")
      .evaluate((el) => el.scrollWidth <= el.clientWidth + 1);
    assert(modelFits, "Long model names must wrap without horizontal clipping");
    await page.locator(".model-option").click();
    await page.getByText("Excluded models", { exact: true }).click();
    await page
      .locator("#excluded-model-list")
      .getByText("Image generation only", { exact: false })
      .waitFor();
    assert.equal(
      await page.getByLabel("Exact model ID").inputValue(),
      "fixture-model",
    );
    assert.equal(
      await page.getByLabel("Maximum input per call").inputValue(),
      "",
    );
    assert.equal(
      await page.getByLabel("Maximum output per call").inputValue(),
      "",
    );
    await page.getByLabel("Model seed").fill("42");
    await page.getByLabel("Input price / million").fill("1.25");
    await page.getByLabel("Output price / million").fill("2.5");
    await page.getByLabel("Cache read price / million").fill("0.125");
    await page
      .getByLabel("API key (this server session only)")
      .fill("browser-only-secret");
    await page.route(
      "**/api/participant",
      (route) =>
        route.fulfill({
          status: 400,
          json: { error: "Fixture validation error: choose a valid model" },
        }),
      { times: 1 },
    );
    await page.getByRole("button", { name: "Save participant" }).click();
    await page.locator("#dialog-error").waitFor({ state: "visible" });
    assert(
      await page
        .locator("#dialog-error")
        .evaluate((el) => el.closest("dialog").open),
    );
    assert(
      (await page.locator("#dialog-error").textContent()).includes(
        "Fixture validation error",
      ),
    );
    assert.equal(
      await page.getByLabel("Participant ID").inputValue(),
      "browser-api",
    );
    await page.getByRole("button", { name: "Save participant" }).click();
    await page.getByText("browser-api", { exact: true }).waitFor();
    const boot = await page.request.get(url + "/api/bootstrap");
    const bootData = await boot.json();
    assert(!JSON.stringify(bootData).includes("browser-only-secret"));
    assert.equal(
      bootData.participants.find((p) => p.spec.id === "browser-api").spec
        .parameters.seed,
      42,
    );
    await page.getByRole("button", { name: "Add participant" }).click();
    await page.getByLabel("Provider").selectOption("gemini");
    assert.equal(
      await page.getByLabel("API key environment variable").inputValue(),
      "ARENA_GEMINI_KEY",
    );
    assert.equal(await page.getByLabel("Model seed").inputValue(), "0");
    await page.getByLabel("Provider").selectOption("anthropic");
    assert.equal(await page.getByLabel("Model seed").count(), 0);
    await page
      .getByText("Seed: not available in the Anthropic API.", { exact: true })
      .waitFor();
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await page
      .getByRole("link", { name: "Competitions", exact: false })
      .click();
    await page.getByRole("button", { name: "New competition" }).click();
    await page.getByLabel("Competition name").fill("Configuration navigateur");
    await page.getByLabel("Repetitions per participant").fill("2");
    await page.getByLabel("Evaluation cycle").selectOption("1");
    for (const name of [
      "Model calls",
      "Tool calls",
      "Preparation matches",
      "Preparation time (seconds)",
      "API spending limit per conversation",
      "API spending limit for the experiment",
    ]) {
      assert.equal(
        await page.getByLabel(name, { exact: false }).inputValue(),
        "",
      );
    }
    await page.getByLabel("Team setup").selectOption("participant");
    await page.getByLabel("Weapons per member").fill("1");
    await page.getByLabel("Chips per member").fill("0");
    const weaponPicker = page.locator(
      '.equipment-picker[data-name="team_allowed_weapons"]',
    );
    await weaponPicker.locator(":scope > summary").click();
    assert.equal(await weaponPicker.locator(".equipment-option").count(), 39);
    await weaponPicker.getByLabel("Search weapons").fill("pistol");
    const pistol = weaponPicker
      .locator(".equipment-option")
      .filter({ hasText: "pistol" })
      .first();
    await pistol.locator('input[type="checkbox"]').check();
    await pistol.getByText("Item details", { exact: true }).click();
    await pistol.getByText("Effects", { exact: true }).waitFor();
    assert.equal(
      await page.locator('[name="team_allowed_weapons"]').inputValue(),
      "1",
    );
    await page.screenshot({
      path: path.join(artifacts, "equipment-selector.png"),
      fullPage: true,
    });
    await weaponPicker.locator(":scope > summary").click();
    assert((await page.locator(".help-tip").count()) > 10);
    await page.locator(".help-tip").first().focus();
    await page
      .locator(".help-tip")
      .first()
      .locator(".help-bubble")
      .waitFor({ state: "visible" });
    await page
      .getByRole("button", { name: "Settings guide", exact: true })
      .click();
    await page
      .getByRole("dialog")
      .getByRole("heading", { name: "Competition settings", exact: true })
      .waitFor();
    await page.getByRole("button", { name: "Close", exact: true }).click();
    assert.equal(
      await page.getByLabel("Competition name").inputValue(),
      "Configuration navigateur",
    );

    await page.getByRole("button", { name: "Calculate schedule" }).click();
    await page
      .locator("#plan-preview")
      .getByText("Conversations", { exact: true })
      .waitFor();
    assert((await page.locator("#plan-preview").innerText()).includes("4"));
    await page.getByLabel("Repetitions per participant").fill("1");
    await page.getByLabel("Maximum turns").fill("1");
    await page.getByLabel("Include mirror matches").uncheck();
    await page.getByRole("button", { name: "Save configuration" }).click();
    const configRow = page
      .locator("tr")
      .filter({ hasText: "Configuration navigateur" });
    await configRow.waitFor();
    const configured = (
      await (await page.request.get(url + "/api/bootstrap")).json()
    ).drafts.find((d) => d.config.name === "Configuration navigateur").config;
    assert.deepEqual(configured.budget_per_session, {});
    assert.deepEqual(configured.scenario.team_selection.allowed_weapons, [1]);
    assert.equal(configured.scenario.team_selection.max_chips, 0);

    await configRow.getByRole("button", { name: "Launch" }).click();
    assert(
      (await page.getByRole("dialog").innerText()).includes("No LLM calls"),
    );
    assert.equal(
      await page.getByRole("dialog").locator("[name=confirm_paid]").count(),
      0,
    );
    if (process.env.ARENA_UI_LIVE_ENGINE === "1") {
      await page
        .getByRole("button", { name: "Start competition", exact: true })
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
      await page.getByRole("button", { name: "Close", exact: true }).click();
    await page
      .getByRole("link", { name: "Competitions", exact: false })
      .click();
    await page.getByRole("button", { name: "New competition" }).click();
    await page
      .getByLabel("Competition name")
      .fill("Configuration API non lancée");
    await page.locator("[name=participant][value=mock-repair]").uncheck();
    await page.locator("[name=participant][value=mock-single]").uncheck();
    await page.locator("[name=participant][value=browser-api]").check();
    await page.getByLabel("Allow paid APIs").check();
    await page.getByRole("button", { name: "Save configuration" }).click();
    await page
      .locator("tr")
      .filter({ hasText: "Configuration API non lancée" })
      .getByRole("button", { name: "Launch" })
      .click();
    const paid = page.getByRole("dialog").locator("[name=confirm_paid]");
    await paid.waitFor();
    assert.equal(await paid.isChecked(), false);
    assert.equal(await paid.getAttribute("required"), "");
    await page.getByRole("button", { name: "Close", exact: true }).click();
    // Matrix counts must keep the pair, stage and result perspective across side swaps.
    const matrixSummary = url + "/#view=run&run=matrix";
    const paths = async () =>
      page
        .locator(".match-card")
        .evaluateAll((nodes) => nodes.map((n) => n.dataset.path).sort());
    async function openMatrix(label, expected) {
      await page.goto(matrixSummary);
      await page.getByRole("link", { name: label, exact: true }).click();
      await page.waitForFunction(
        (n) => document.querySelectorAll(".match-card").length === n,
        expected.length,
      );
      assert.deepEqual(
        await paths(),
        expected.map((p) => `matches/${p}/attempt-1`).sort(),
      );
      const fragment = new URLSearchParams(new URL(page.url()).hash.slice(1));
      assert.equal(fragment.get("stage"), ".");
      assert.equal(fragment.get("tab"), "matches");
    }
    await openMatrix("A vs B: 2 wins", ["win-left", "win-right"]);
    await page.locator("#match-detail h2").waitFor();
    await page.screenshot({
      path: path.join(artifacts, "matrix-filtered.png"),
      fullPage: true,
    });
    const winsUrl = page.url();
    await page.getByLabel("Opponent", { exact: false }).selectOption("A");
    await page.getByRole("heading", { name: "No matches found" }).waitFor();
    await page.getByLabel("Opponent", { exact: false }).selectOption("B");
    await page.waitForFunction(
      () => document.querySelectorAll(".match-card").length === 2,
    );
    await page.reload();
    await page.waitForFunction(
      () => document.querySelectorAll(".match-card").length === 2,
    );
    assert.deepEqual(await paths(), [
      "matches/win-left/attempt-1",
      "matches/win-right/attempt-1",
    ]);
    await page.goBack();
    await page.getByRole("heading", { name: "Match matrix" }).waitFor();
    await openMatrix("A vs B: 1 draw", ["draw"]);
    await openMatrix("A vs B: 1 loss", ["loss"]);
    await openMatrix("A vs B: 1 failure", ["failure"]);
    await openMatrix("A vs B: 4 completed matches", [
      "win-left",
      "win-right",
      "draw",
      "loss",
    ]);
    await openMatrix("B vs A: 1 win", ["loss"]);
    await openMatrix("A vs C: 0 losses", []);
    await page.getByRole("heading", { name: "No matches found" }).waitFor();
    await page.getByRole("button", { name: "Clear filters" }).click();
    await page.waitForFunction(
      () => document.querySelectorAll(".match-card").length === 8,
    );
    await page.getByLabel("Stage", { exact: false }).selectOption("tournament");
    await page.waitForFunction(
      () => document.querySelectorAll(".match-card").length === 1,
    );
    assert.deepEqual(await paths(), [
      "tournament/matches/other-stage/attempt-1",
    ]);
    await page.goto(winsUrl);
    await page.waitForFunction(
      () => document.querySelectorAll(".match-card").length === 2,
    );
    await page.locator("#match-search").fill("seed-not-present");
    await page.getByRole("heading", { name: "No matches found" }).waitFor();
    await page.locator("#match-search").fill("301");
    await page.waitForFunction(
      () => document.querySelectorAll(".match-card").length === 2,
    );
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
    await page.getByText("No recorded conversation", { exact: true }).waitFor();
    await page.goto(url + "/#view=run&run=one");
    await page.getByRole("heading", { name: "Strategy performance" }).waitFor();
    await page.getByRole("heading", { name: "Match matrix" }).waitFor();
    await page.getByLabel("Metrics", { exact: false }).selectOption("damage");
    await page
      .locator("#statistics-stage-detail th")
      .filter({ hasText: "Damage dealt" })
      .waitFor();
    await page.getByLabel("Metrics", { exact: false }).selectOption("overview");
    await page.getByText("10,000,000", { exact: false }).first().waitFor();
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
        ?.textContent.includes("Code at version 1"),
    );
    assert(
      (await page.locator("#source-content pre").first().innerText()).includes(
        "var a = 1",
      ),
    );
    await page.getByRole("button", { name: "Matches", exact: true }).click();
    await page.locator("#replay-board circle").first().waitFor();
    await page.getByLabel("Metrics", { exact: false }).selectOption("compute");
    await page
      .locator(".combat-statistics th")
      .filter({ hasText: "Operations" })
      .first()
      .waitFor();
    await page.getByLabel("Metrics", { exact: false }).selectOption("overview");
    await page.locator("#replay-range").evaluate((n) => {
      n.value = n.max;
      n.dispatchEvent(new Event("input", { bubbles: true }));
    });
    assert((await page.locator("#replay-label").innerText()).includes("dies"));
    assert.equal(await page.locator("#replay-board .dead").count(), 1);
    await page.screenshot({
      path: path.join(artifacts, "replay.png"),
      fullPage: true,
    });
    await page.getByRole("button", { name: "Files", exact: true }).click();
    await page.locator("#file-search").fill("main.leek");
    await page.locator(".file-button").first().click();
    await page.waitForFunction(() =>
      document
        .querySelector("#file-content")
        ?.textContent.includes("var a = 2"),
    );
    const download = page.waitForEvent("download");
    await page.getByRole("link", { name: "Download" }).click();
    await (await download).saveAs(path.join(artifacts, "download-main.leek"));
    assert.equal(
      fs.readFileSync(path.join(artifacts, "download-main.leek"), "utf8"),
      "var a = 2\n",
    );
    await page.locator("#file-search").fill("report.md");
    await page.locator(".file-button").first().click();
    await page.getByRole("button", { name: "Rendered", exact: true }).click();
    await page.locator("#file-content h1").waitFor();
    assert.equal(await page.locator("#file-content img").count(), 0);
    assert.equal(await page.locator("#file-content table").count(), 1);
    await page.getByRole("button", { name: "Raw", exact: true }).click();
    assert(
      (await page.locator("#file-content pre").innerText()).includes(
        "# Rapport navigateur",
      ),
    );
    await page.locator("#file-search").fill("example.json");
    await page.locator(".file-button").first().click();
    await page.getByRole("button", { name: "Rendered", exact: true }).click();
    await page.locator("#file-content .json-children").first().waitFor();
    assert.equal(await page.locator("#file-content script").count(), 0);
    assert.equal(
      await page.evaluate(() => window.__arenaUnexpectedScript),
      undefined,
    );
    await page.getByRole("button", { name: "Journal", exact: true }).click();
    await page.getByRole("button", { name: "View artifact" }).first().click();
    await page
      .getByRole("dialog")
      .getByText('"test": "event"', { exact: false })
      .waitFor();
    await page.getByRole("button", { name: "Close", exact: true }).click();
    await page
      .getByRole("link", { name: "Compare results", exact: false })
      .click();
    await page.locator("[name=compare-run][value=one]").check();
    await page.locator("[name=compare-run][value=two]").check();
    await page.getByRole("button", { name: "Compare selected runs" }).click();
    await page.getByRole("heading", { name: "Comparison group 1" }).waitFor();
    assert(
      (await page.locator("#comparison-result").innerText()).includes("60%"),
    );
    await page.screenshot({
      path: path.join(artifacts, "comparison.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(url + "/#view=dashboard");
    await page
      .getByRole("heading", { name: "Overview", exact: true })
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
      "Browser checks passed: matrix links and filters, English UI, profiles, configuration, prompts, versions/diff, replay, download, journal, aggregation, mobile.",
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
