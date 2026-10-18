/* Offline browser integration: real local engine, no provider API calls. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");
const python =
  process.env.ARENA_UI_TEST_PYTHON || path.join(root, ".venv", "bin", "python");
(async () => {
  const output = fs.mkdtempSync(
    path.join(os.tmpdir(), "arena-calibration-browser-"),
  );
  const server = spawn(
    python,
    ["-m", "arena", "calibrate", "serve", "--port", "0", "--out", output],
    { cwd: root, stdio: ["ignore", "pipe", "inherit"] },
  );
  let browser;
  try {
    const url = await new Promise((resolve, reject) => {
      const timeout = setTimeout(
        () => reject(Error("Workshop startup timed out")),
        20000,
      );
      server.stdout.on("data", (chunk) => {
        const match = chunk.toString().match(/http:\/\/127\.0\.0\.1:\d+/);
        if (match) {
          clearTimeout(timeout);
          resolve(match[0]);
        }
      });
      server.on("exit", (code) => reject(Error("Workshop exited " + code)));
    });
    browser = await chromium.launch({
      executablePath:
        process.env.ARENA_BROWSER_EXECUTABLE || "/usr/bin/chromium",
      headless: true,
      args: ["--no-sandbox"],
    });
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(url);
    await page.waitForFunction(
      () => document.querySelector("#prompt").value.length > 10,
    );
    await page.evaluate(() => {
      for (const details of document.querySelectorAll("#editor details"))
        details.open = true;
      const values = {
        name: "Browser manual",
        rounds: 4,
        minimum: 3,
        patience: 2,
        replicates: 1,
        opponents: "passive",
        training: "101",
        validation: "301",
        audit: "701",
        "candidate-count": 2,
        "search-patience": 1,
      };
      for (const [id, value] of Object.entries(values))
        document.getElementById(id).value = value;
      document.getElementById("previous-versions").checked = false;
      const scenario = JSON.parse(document.getElementById("scenario").value);
      scenario.max_turns = 2;
      document.getElementById("scenario").value = JSON.stringify(scenario);
    });
    async function waitAPI(route, predicate) {
      const deadline = Date.now() + 180000;
      while (Date.now() < deadline) {
        const response = await page.request.get(url + route);
        const value = await response.json();
        if (predicate(value)) return value;
        await page.waitForTimeout(250);
      }
      throw Error("Timed out waiting for " + route);
    }
    async function run() {
      const started = page.waitForResponse((response) =>
        response.url().endsWith("/api/start"),
      );
      await page.locator("#start").click();
      const result = await (await started).json();
      assert.ok(result.id, JSON.stringify(result));
      await waitAPI(
        "/api/studies",
        (rows) => rows.find((r) => r.id === result.id)?.status === "completed",
      );
      await page.locator("#refresh").click();
      await page.waitForFunction(() =>
        document
          .querySelector("#status")
          .textContent.toLowerCase()
          .includes("completed"),
      );
      await page.waitForTimeout(300);
      assert.equal(
        await page.locator("#error").isVisible(),
        false,
        await page.locator("#error").textContent(),
      );
    }
    await page.locator("#round-stop").selectOption("fixed");
    await run();
    assert.equal(await page.locator("#chart svg").count(), 1);
    assert.equal(await page.locator("#rounds-table tbody tr").count(), 4);
    await page.locator("#show-prompt").click();
    await page.locator("#dialog").waitFor({ state: "visible" });
    assert.match(
      await page.locator("#dialog-content").textContent(),
      /LeekScript/,
    );
    await page.locator("#close").click();
    await page.locator("#session").selectOption("target-r0-g0");
    await page.locator("#view").selectOption("fights");
    await page.waitForFunction(() =>
      document.querySelector("#history").textContent.includes("training"),
    );
    await page.locator("#view").selectOption("events");
    await page.waitForFunction(() =>
      document.querySelector("#history").textContent.includes("model"),
    );
    await page.locator("#view").selectOption("conversation");
    await page.waitForFunction(() =>
      document.querySelector("#history").textContent.includes("prompt"),
    );
    await page.locator("#fork").click();
    await page
      .locator("#prompt")
      .fill(
        (await page.locator("#prompt").inputValue()) +
          "\nCheck movement before attacking.",
      );
    await page.locator("#mode").selectOption("automatic");
    await run();
    assert.equal(await page.locator("#trial-comparison tbody tr").count(), 2);
    await page.locator("#trial").selectOption("proposals/001");
    await page.waitForFunction(
      () => document.querySelector("#session").value === "analyst-r0",
    );
    await page.locator("#show-prompt").click();
    await page.locator("#dialog").waitFor({ state: "visible" });
    assert.match(
      await page.locator("#dialog-content").textContent(),
      /prompt/i,
    );
    await page.locator("#close").click();
    await page.locator("#mode").selectOption("manual");
    await page.locator("#round-stop").selectOption("manual");
    assert(await page.locator("#rounds").isDisabled());
    assert.equal(await page.locator("#replicates").inputValue(), "1");
    const started = page.waitForResponse((response) =>
      response.url().endsWith("/api/start"),
    );
    await page.locator("#start").click();
    const endless = await (await started).json();
    assert.ok(endless.id, JSON.stringify(endless));
    await waitAPI("/api/study?study=" + endless.id, (study) =>
      study.progress.some((p) => p.value.rounds.length >= 2),
    );
    await page.locator("#stop").click();
    await waitAPI(
      "/api/studies",
      (studies) =>
        studies.find((s) => s.id === endless.id)?.status === "stopped",
    );
    await page.locator("#refresh").click();
    await page.waitForFunction(() =>
      document
        .querySelector("#status")
        .textContent.toLowerCase()
        .includes("stopped"),
    );
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      true,
      "Page overflows mobile viewport",
    );
    assert.deepEqual(errors, []);
    console.log(
      "Calibration browser checks passed: fixed rounds, manual stop, automatic, history, prompt inspection, mobile.",
    );
  } finally {
    if (browser) await browser.close();
    server.kill("SIGINT");
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
