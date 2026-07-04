// Automated end-to-end test of the DocuIntelAI frontend's three actions
// (upload, list, query) driven through a real headless Chromium against a
// running backend. Exits non-zero on any failed assertion.
//
// Env:
//   APP_URL   (default http://127.0.0.1:5500/index.html)
//   API_URL   (default http://127.0.0.1:8000)
//   API_KEY   (default demo-key)
//
// Run via ./run.sh, which boots the backend + static server first.

const assert = require("node:assert");
const os = require("node:os");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const APP = process.env.APP_URL || "http://127.0.0.1:5500/index.html";
const API = process.env.API_URL || "http://127.0.0.1:8000";
const KEY = process.env.API_KEY || "demo-key";

(async () => {
  const tmp = path.join(os.tmpdir(), `fe-e2e-${Date.now()}.txt`);
  fs.writeFileSync(
    tmp,
    "The Kestrel Mark IV turbine operates at 12000 RPM and uses a magnetic " +
      "bearing system rated for 40000 hours of continuous operation. It was " +
      "manufactured in Reykjavik."
  );

  const captured = {};
  // Use bundled chromium when PW_CHANNEL=chromium (CI); otherwise system Chrome.
  const launchOpts = { headless: true };
  if ((process.env.PW_CHANNEL || "chrome") !== "chromium") launchOpts.channel = "chrome";
  const browser = await chromium.launch(launchOpts);
  const page = await browser.newContext().then((c) => c.newPage());
  page.on("response", async (res) => {
    if (!res.url().startsWith(API)) return;
    let body;
    try { body = await res.json(); } catch { body = await res.text().catch(() => null); }
    captured[res.request().method() + " " + res.url().slice(API.length)] = { status: res.status(), body };
  });

  try {
    await page.goto(APP, { waitUntil: "networkidle" });

    // Connect.
    await page.fill("#baseUrl", API);
    await page.fill("#apiKey", KEY);
    await page.click("#saveConn");
    await page.waitForSelector("#banner.ok", { timeout: 20000 });

    // ACTION 1: upload (UI auto-ingests).
    await page.setInputFiles("#file", tmp);
    await page.click("#uploadBtn");
    await page.waitForFunction(
      () => {
        const b = document.getElementById("banner");
        return b.classList.contains("ok") && /ingested/.test(b.textContent);
      },
      undefined,
      { timeout: 120000 }
    );

    // ACTION 2: list shows the uploaded document.
    await page.click("#refreshBtn");
    await page.waitForSelector("#docsWrap table tbody tr", { timeout: 20000 });
    const filenames = await page.$$eval("#docsWrap table tbody tr td:first-child", (t) => t.map((e) => e.textContent));
    assert.ok(filenames.some((f) => f.endsWith(".txt")), "uploaded .txt not shown in document list");

    // ACTION 3: query returns an answer with sources.
    await page.fill("#question", "How many RPM does the Kestrel Mark IV turbine operate at?");
    await page.click("#askBtn");
    await page.waitForSelector("#result", { state: "visible", timeout: 120000 });
    await page.waitForFunction(
      () => document.getElementById("answer").textContent.trim().length > 0,
      undefined,
      { timeout: 120000 }
    );
    const answer = (await page.textContent("#answer")).trim();
    const sources = await page.$$eval("#sources .chip", (els) => els.map((e) => e.textContent));
    const conf = await page.textContent("#confVal");

    assert.ok(answer.length > 0, "answer is empty");
    assert.ok(sources.length > 0, "no sources returned");

    // Evidence.
    const feat = captured["GET /features"];
    console.log("embedding_backend:", feat && feat.body && feat.body.embedding_backend);
    console.log("answer:", answer);
    console.log("sources:", JSON.stringify(sources));
    console.log("confidence:", conf);
    console.log("\nRAW /query/documents response:");
    console.log(JSON.stringify(captured["POST /query/documents"], null, 2));

    console.log("\nPASS: upload + list + query all succeeded via the UI.");
    await browser.close();
    process.exit(0);
  } catch (e) {
    console.error("FAIL:", e.message);
    try { await page.screenshot({ path: path.join(os.tmpdir(), "fe-e2e-fail.png") }); } catch {}
    await browser.close();
    process.exit(1);
  } finally {
    fs.rmSync(tmp, { force: true });
  }
})();
