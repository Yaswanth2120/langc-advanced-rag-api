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
  const marker = `fe-e2e-${Date.now()}.txt`;
  const tmp = path.join(os.tmpdir(), marker);
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

    // created_at must render as a formatted locale date (timestamptz handled),
    // not "Invalid Date" and not a raw ISO string slice.
    const createdCell = (await page.textContent("#docsWrap table tbody tr td:nth-child(4)")).trim();
    assert.ok(createdCell.length > 0, "Created cell is empty");
    assert.ok(!createdCell.includes("Invalid Date"), `Created cell failed to parse: ${createdCell}`);
    assert.ok(!/^\d{4}-\d{2}-\d{2}T/.test(createdCell), `Created cell is a raw ISO string, not formatted: ${createdCell}`);
    console.log("rendered Created cell:", createdCell);

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

    // ---- Network-level assertions: status codes AND body contents of every
    // ---- backend response the UI triggered (not just "nothing threw").

    // Upload: 200, body is the DocumentMetadata for our marker file.
    const up = captured["POST /documents/upload"];
    assert.ok(up, "no /documents/upload response captured");
    assert.strictEqual(up.status, 200, `upload status ${up.status}: ${JSON.stringify(up.body)}`);
    assert.ok(up.body && up.body.document_id, "upload body missing document_id");
    assert.strictEqual(up.body.filename, marker, "upload body filename mismatch");
    assert.strictEqual(up.body.status, "uploaded", "upload body status != 'uploaded'");
    const docId = up.body.document_id;

    // Ingest: 200, body is a non-empty chunk array for that document.
    const ingKey = Object.keys(captured).find((k) => k === `POST /documents/${docId}/ingest`);
    assert.ok(ingKey, "no /documents/{id}/ingest response captured");
    const ing = captured[ingKey];
    assert.strictEqual(ing.status, 200, `ingest status ${ing.status}: ${JSON.stringify(ing.body)}`);
    assert.ok(Array.isArray(ing.body) && ing.body.length >= 1, "ingest body is not a non-empty chunk array");
    assert.strictEqual(ing.body[0].document_id, docId, "ingest chunk document_id mismatch");
    assert.ok(ing.body[0].text.includes("12000 RPM"), "ingest chunk text missing document content");

    // List: 200, body contains the uploaded document's row.
    const list = captured["GET /documents"];
    assert.ok(list, "no /documents response captured");
    assert.strictEqual(list.status, 200, `list status ${list.status}: ${JSON.stringify(list.body)}`);
    assert.ok(Array.isArray(list.body), "list body is not an array");
    const row = list.body.find((r) => r.document_id === docId);
    assert.ok(row, "uploaded document not present in GET /documents body");
    assert.strictEqual(row.filename, marker, "listed filename mismatch");

    // Query: 200, grounded answer citing the uploaded document.
    const q = captured["POST /query/documents"];
    assert.ok(q, "no /query/documents response captured");
    assert.strictEqual(q.status, 200, `query status ${q.status}: ${JSON.stringify(q.body)}`);
    assert.ok(q.body.answer.includes("12000"), `answer not grounded in document: ${q.body.answer}`);
    assert.ok(Array.isArray(q.body.sources) && q.body.sources.includes(docId),
      `sources ${JSON.stringify(q.body.sources)} do not cite uploaded doc ${docId}`);
    assert.ok(q.body.confidence_score > 0, `confidence_score not > 0: ${q.body.confidence_score}`);

    // DOM-level assertions: what the user actually sees matches the API body.
    assert.ok(answer.includes("12000"), "rendered answer missing document fact");
    assert.deepStrictEqual(sources, q.body.sources, "rendered source chips != API sources");
    assert.strictEqual(Number(conf), q.body.confidence_score, "rendered confidence != API value");

    // Evidence.
    const feat = captured["GET /features"];
    console.log("embedding_backend:", feat && feat.body && feat.body.embedding_backend);
    console.log("answer:", answer);
    console.log("sources:", JSON.stringify(sources));
    console.log("confidence:", conf);
    console.log("\nRAW /query/documents response:");
    console.log(JSON.stringify(captured["POST /query/documents"], null, 2));

    console.log("\nPASS: upload + list + query all succeeded via the UI, with status/body assertions.");
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
