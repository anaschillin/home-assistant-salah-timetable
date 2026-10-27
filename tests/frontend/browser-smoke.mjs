/** Real Chromium smoke tests using CDP; no browser automation dependency. */
import test from "node:test";
import assert from "node:assert/strict";
import {access, mkdir, mkdtemp, readFile, rm, writeFile} from "node:fs/promises";
import {constants} from "node:fs";
import {createServer} from "node:http";
import {tmpdir} from "node:os";
import {resolve, join} from "node:path";
import {fileURLToPath} from "node:url";
import {spawn} from "node:child_process";
import {waitForDebuggerPort} from "./browser-startup.mjs";

const root = resolve(fileURLToPath(new URL("../../", import.meta.url)));
let browser;
for (const candidate of [process.env.CHROME_BIN, "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/opt/google/chrome/chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"].filter(Boolean)) {
  try { await access(candidate, constants.X_OK); browser = candidate; break; } catch { /* Try the next installed browser. */ }
}
const skip = !browser && process.env.REQUIRE_BROWSER_TESTS !== "1" && process.env.REQUIRE_BROWSER !== "1" ? "Chromium/Chrome is not installed; set CHROME_BIN or REQUIRE_BROWSER_TESTS=1" : false;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const widths = [320, 360, 400, 900];
const fixtures = widths.flatMap(width => ["en", "ar"].flatMap(language => [false, true].map(bilingual => ({width, language, bilingual}))));

async function connectDebugger(url) {
  const socket = new WebSocket(url);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => { socket.close(); reject(new Error("Browser debugger connection timed out")); }, 3000);
    socket.addEventListener("open", () => { clearTimeout(timer); resolve(); }, {once: true});
    socket.addEventListener("error", () => { clearTimeout(timer); reject(new Error("Browser debugger connection failed")); }, {once: true});
  });
  let sequence = 0;
  const pending = new Map();
  const rejectPending = () => {
    for (const {reject, timer} of pending.values()) { clearTimeout(timer); reject(new Error("Browser debugger disconnected")); }
    pending.clear();
  };
  socket.addEventListener("close", rejectPending);
  socket.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    const request = pending.get(message.id);
    if (!request) return;
    pending.delete(message.id); clearTimeout(request.timer);
    if (message.error) request.reject(new Error(JSON.stringify(message.error)));
    else request.resolve(message.result);
  });
  return {
    call(method, params = {}) {
      return new Promise((resolve, reject) => {
        const id = ++sequence;
        const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Browser command timed out: ${method}`)); }, 4000);
        pending.set(id, {resolve, reject, timer}); socket.send(JSON.stringify({id, method, params}));
      });
    },
    close() { rejectPending(); socket.close(); },
  };
}

async function waitForPageTarget(port, timeoutMs = 20000, intervalMs = 250) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/list`, {
        signal: AbortSignal.timeout(Math.min(5000, Math.max(1, deadline - Date.now()))),
      });
      if (!response.ok) throw new Error(`Chrome target discovery returned HTTP ${response.status}`);
      const targets = await response.json();
      if (Array.isArray(targets) && targets.some(target => target.type === "page" && target.webSocketDebuggerUrl)) return targets;
    } catch {
      // Chrome may not have exposed a page target yet.
    }

    const remaining = deadline - Date.now();
    if (remaining > 0) await pause(Math.min(intervalMs, remaining));
  }

  throw new Error(`Chrome never exposed a page target on port ${port}`);
}

function stopBrowser(child) {
  if (!child?.pid) return;
  // Kill the temporary browser's own process group, including its renderers.
  try { process.kill(process.platform === "win32" ? child.pid : -child.pid, "SIGKILL"); } catch { /* Already exited. */ }
}

test("real Chromium card and editor smoke", {skip, timeout: 90000}, async t => {
  assert.ok(browser, "A Chromium browser is required for this run");
  t.diagnostic(`Browser executable: ${browser}`);
  const directory = await mkdtemp(join(tmpdir(), "salah-card-browser-"));
  const main = `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}#result{display:none}</style></head><body><pre id="result">pending</pre><script>
// Run one fixture at a time so synchronous layout checks cannot starve CDP.
// Retain completed frames in fixture order for optional screenshots.
const fixtures = ${JSON.stringify(fixtures)};
let activeFrame;
window.salahBrowserReports = [];
function nextFixture() {
  const fixture = fixtures[window.salahBrowserReports.length];
  if (!fixture) return;
  activeFrame = document.createElement('iframe');
  activeFrame.style.cssText = 'display:block;border:0;height:1500px;width:'+fixture.width+'px';
  activeFrame.src = '/frame.html?'+new URLSearchParams(fixture);
  document.body.append(activeFrame);
}
window.addEventListener('message', event => {
  if(event.origin !== location.origin || event.source !== activeFrame?.contentWindow || event.data.kind !== 'salah-browser-result') return;
  window.salahBrowserReports.push(event.data);
  document.querySelector('#result').textContent = JSON.stringify(window.salahBrowserReports);
  activeFrame = undefined;
  setTimeout(nextFixture, 0);
});
nextFixture();
</script></body></html>`;
  const frame = '<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;padding:8px;box-sizing:border-box;font-family:sans-serif}html{--primary-text-color:rgb(20,20,20);--primary-color:#387f8d;--secondary-text-color:#687478;--secondary-background-color:#f2f5f5;--divider-color:#ddd;--card-background-color:white}</style></head><body><script type="module" src="/tests/frontend/browser-harness.js"></script></body></html>';
  const files = new Map([
    ["/tests/frontend/browser-harness.js", join(root, "tests/frontend/browser-harness.js")],
    ["/custom_components/salah_timetable/frontend/salah-timetable-card.js", join(root, "custom_components/salah_timetable/frontend/salah-timetable-card.js")],
    ["/custom_components/salah_timetable/frontend/card-utils.js", join(root, "custom_components/salah_timetable/frontend/card-utils.js")],
    ["/custom_components/salah_timetable/frontend/card-i18n.js", join(root, "custom_components/salah_timetable/frontend/card-i18n.js")],
  ]);
  const server = createServer(async (request, response) => {
    const path = new URL(request.url, "http://127.0.0.1").pathname;
    try {
      if (path === "/" || path === "/frame.html") { response.writeHead(200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}); response.end(path === "/" ? main : frame); }
      else if (files.has(path)) { response.writeHead(200, {"Content-Type": "text/javascript; charset=utf-8", "Cache-Control": "no-store"}); response.end(await readFile(files.get(path))); }
      else { response.writeHead(404); response.end(); }
    } catch { response.writeHead(500); response.end(); }
  });
  let child; let debuggerSession; let deadline; let stderr = "";
  try {
    await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
    const args = ["--headless", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-background-networking", "--no-first-run", "--no-default-browser-check", `--user-data-dir=${directory}`, "--remote-debugging-port=0", "about:blank"];
    child = spawn(browser, args, {detached: process.platform !== "win32", stdio: ["ignore", "ignore", "pipe"]});
    child.stderr.on("data", value => { stderr = (stderr + value).slice(-4000); });
    // Allow startup and fixture budgets to complete; retain a watchdog only for a hung browser.
    deadline = setTimeout(() => stopBrowser(child), 85000);
    const port = await waitForDebuggerPort(child, directory, {
      timeoutMs: 30000,
      stderr: () => stderr
    });
    const targets = await waitForPageTarget(port);
    const page = targets.find(target => target.type === "page");
    assert.ok(page?.webSocketDebuggerUrl, "Browser did not expose a page debugger");
    debuggerSession = await connectDebugger(page.webSocketDebuggerUrl);
    await debuggerSession.call("Page.enable");
    await debuggerSession.call("Emulation.setDeviceMetricsOverride", {width: 1000, height: 2600, deviceScaleFactor: 1, mobile: false});
    await debuggerSession.call("Page.navigate", {url: `http://127.0.0.1:${server.address().port}/`});
    let reports = [];
    const reportDeadline = Date.now() + 30000;
    while (Date.now() < reportDeadline) {
      const evaluation = await debuggerSession.call("Runtime.evaluate", {expression: "JSON.stringify(window.salahBrowserReports || [])", returnByValue: true});
      reports = JSON.parse(evaluation.result?.value || "[]");
      if (reports.length === fixtures.length) break;
      await pause(100);
    }
    assert.equal(reports.length, fixtures.length, `Browser completed ${reports.length}/${fixtures.length} fixtures: ${JSON.stringify(reports)}\n${stderr}`);
    for (const {width, language, bilingual} of fixtures) await t.test(`${width}px ${language}${bilingual ? " bilingual" : ""} native DOM, theme and editor`, () => {
      const report = reports.find(item => item.width === width && item.language === language && item.bilingual === bilingual);
      assert.ok(report, `No report for ${width}px ${language} bilingual=${bilingual}: ${JSON.stringify(reports)}`);
      assert.equal(report.status, "passed", report.error);
      for (const name of ["card contains 200% text without overflowing", "Gregorian and calculated Hijri dates are visible", "Hijri date appears before the independent Gregorian date", "Gregorian can be hidden while Hijri remains visible", "Hijri can be hidden while Gregorian remains visible", "mosque-configured Hijri visibility remains authoritative", "countdown tick preserves table keyboard focus", "ordinary ticks retain table nodes and text selection", "numeric times use LTR isolation", "prayer labels use the selected languages", "long mixed-direction title fits without overflow", "graphical language and bilingual controls round trip", "all graphical options survive configuration reload", "RTL overflow uses Chromium negative scrollLeft"]) assert.ok(report.checks.includes(name), `Missing browser check: ${name}`);
      for (const option of ["show_hijri_date", "show_gregorian_date", "show_salah_countdown", "show_jamaat_countdown", "show_ramadan_details", "show_sehri_countdown", "show_iftar_countdown", "show_timezone_note"]) for (const value of [false, true]) assert.ok(report.checks.includes(`editor ${option}=${value} changes the expected visible content`), `Missing browser visibility check: ${option}=${value}`);
    });
    if (process.env.BROWSER_SCREENSHOT_DIR) {
      await debuggerSession.call("Runtime.evaluate", {expression: "window.scrollTo(0,0);for(const frame of document.querySelectorAll('iframe'))frame.contentWindow.scrollTo(0,0)"});
      await debuggerSession.call("Runtime.evaluate", {expression: "new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))", awaitPromise: true});
      const output = resolve(process.env.BROWSER_SCREENSHOT_DIR);
      await mkdir(output, {recursive: true});
      const rectangles = await debuggerSession.call("Runtime.evaluate", {expression: "JSON.stringify([...document.querySelectorAll('iframe')].map(frame => {const bounds=frame.getBoundingClientRect(); const card=frame.contentDocument.querySelector('salah-timetable-card').getBoundingClientRect();return {x:bounds.x+window.scrollX+card.x,y:bounds.y+window.scrollY+card.y,width:card.width,height:card.height,scale:1}}))", returnByValue: true});
      for (const [index, clip] of JSON.parse(rectangles.result.value).entries()) {
        const screenshot = await debuggerSession.call("Page.captureScreenshot", {format: "png", captureBeyondViewport: true, clip});
        const {width, language, bilingual} = fixtures[index];
        const suffix = language === "en" && !bilingual ? "" : `-${language}${bilingual ? "-bilingual" : ""}`;
        await writeFile(join(output, `salah-card-${width}${suffix}.png`), Buffer.from(screenshot.data, "base64"));
      }
    }
  } finally {
    clearTimeout(deadline);
    debuggerSession?.close(); stopBrowser(child);
    server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
    await pause(100); await rm(directory, {recursive: true, force: true});
  }
});
