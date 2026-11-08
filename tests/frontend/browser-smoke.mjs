/** Real Chromium smoke tests using CDP; no browser automation dependency. */
import test from "node:test";
import assert from "node:assert/strict";
import {access, mkdir, mkdtemp, readFile, readdir, rm, writeFile} from "node:fs/promises";
import {constants} from "node:fs";
import {createServer} from "node:http";
import {tmpdir} from "node:os";
import {resolve, join} from "node:path";
import {fileURLToPath} from "node:url";
import {spawn} from "node:child_process";
import {waitForDebuggerPort} from "./browser-startup.mjs";
import {MOSQUE_BACKGROUNDS} from "../../custom_components/salah_timetable/frontend/mosque-backgrounds.js";

const root = resolve(fileURLToPath(new URL("../../", import.meta.url)));
const JS_EMBED_ESCAPE_MAP = {
  "<": "\\u003C",
  ">": "\\u003E",
  "/": "\\u002F",
  "\\": "\\\\",
  "\b": "\\b",
  "\f": "\\f",
  "\n": "\\n",
  "\r": "\\r",
  "\t": "\\t",
  "\0": "\\0",
  "\u2028": "\\u2028",
  "\u2029": "\\u2029",
};
const JS_EMBED_UNSAFE_PATTERN = /[<>/\\\b\f\n\r\t\0\u2028\u2029]/g;
const escapeForJsEmbedding = value => value.replace(JS_EMBED_UNSAFE_PATTERN, char => JS_EMBED_ESCAPE_MAP[char]);
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

async function captureWidget(debuggerSession, index, source, name) {
  if (!process.env.BROWSER_WIDGET_SCREENSHOT_DIR) return;
  const output = resolve(process.env.BROWSER_WIDGET_SCREENSHOT_DIR);
  await mkdir(output, {recursive: true});
  const evaluation = await debuggerSession.call("Runtime.evaluate", {
    expression: `(async () => {
      const frame=document.querySelectorAll('iframe')[${index}];
      const f=frame.contentWindow.widgetFixture;
      const element=${source};
      element.scrollIntoView({block:'start',inline:'nearest'});
      await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
      const bounds=element.getBoundingClientRect();
      const outer=frame.getBoundingClientRect();
      return {x:outer.x+window.scrollX+bounds.x,y:outer.y+window.scrollY+bounds.y,width:bounds.width,height:bounds.height,scale:1};
    })()`, awaitPromise: true, returnByValue: true,
  });
  assert.ok(!evaluation.exceptionDetails, evaluation.exceptionDetails?.exception?.description);
  const screenshot = await debuggerSession.call("Page.captureScreenshot", {format: "png", captureBeyondViewport: true, clip: evaluation.result.value});
  await writeFile(join(output, name), Buffer.from(screenshot.data, "base64"));
}

test("real Chromium card, editor and reminder wizard smoke", {skip, timeout: 90000}, async t => {
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
    ["/custom_components/salah_timetable/frontend/reminder-wizard.js", join(root, "custom_components/salah_timetable/frontend/reminder-wizard.js")],
    ["/tests/frontend/browser-harness.js", join(root, "tests/frontend/browser-harness.js")],
    ["/tests/frontend/widget-browser-fixture.js", join(root, "tests/frontend/widget-browser-fixture.js")],
    ["/custom_components/salah_timetable/frontend/salah-timetable-card.js", join(root, "custom_components/salah_timetable/frontend/salah-timetable-card.js")],
    ["/custom_components/salah_timetable/frontend/card-utils.js", join(root, "custom_components/salah_timetable/frontend/card-utils.js")],
    ["/custom_components/salah_timetable/frontend/card-i18n.js", join(root, "custom_components/salah_timetable/frontend/card-i18n.js")],
    ["/custom_components/salah_timetable/frontend/card-styles.js", join(root, "custom_components/salah_timetable/frontend/card-styles.js")],
    ["/custom_components/salah_timetable/frontend/mosque-backgrounds.js", join(root, "custom_components/salah_timetable/frontend/mosque-backgrounds.js")],
  ]);
  // Resolve imported helpers from the shipped frontend directory only. Keeping
  // an explicit filesystem inventory supports new bundled modules without an
  // unrestricted static server or path traversal through the request URL.
  const frontendDirectory = join(root, "custom_components/salah_timetable/frontend");
  for (const entry of await readdir(frontendDirectory, {withFileTypes: true})) {
    if (entry.isFile() && entry.name.endsWith(".js")) {
      files.set(`/custom_components/salah_timetable/frontend/${entry.name}`, join(frontendDirectory, entry.name));
    }
  }
  for (const photo of MOSQUE_BACKGROUNDS) files.set(photo.path, join(root, "custom_components/salah_timetable/frontend/backgrounds", `${photo.id}.webp`));
  const server = createServer(async (request, response) => {
    const path = new URL(request.url, "http://127.0.0.1").pathname;
    try {
      if (path === "/" || path === "/frame.html") { response.writeHead(200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}); response.end(path === "/" ? main : frame); }
      else if (files.has(path)) { response.writeHead(200, {"Content-Type": path.endsWith(".webp") ? "image/webp" : "text/javascript; charset=utf-8", "Cache-Control": "no-store"}); response.end(await readFile(files.get(path))); }
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
      for (const name of ["card contains 200% text without overflowing", "Gregorian and calculated Hijri dates are visible", "Hijri date appears before the independent Gregorian date", "Gregorian can be hidden while Hijri remains visible", "Hijri can be hidden while Gregorian remains visible", "mosque-configured Hijri visibility remains authoritative", "countdown tick preserves table keyboard focus", "reminder opens native modal", "reminder review contains full configuration", "reminder no write before Finish", "reminder saves one normal automation", "reminder duplicate Finish blocked", "reminder review fits mobile", "beginning delivery opens Notifications tab", "Sound tab keyboard selection retains focus", "Jamaat delivery is separate", "saved delivery preserves category routing", "Companion app filter includes both notification routes", "Music Assistant filter separates duplicate speaker names", "filters retain hidden speaker and media settings", "Back retains category-specific filters", "date navigation retains keyboard focus on tab 2", "date navigation retains keyboard focus on tab 0", "date navigation retains keyboard focus on tab 1", "ordinary ticks retain table nodes and text selection", "numeric times use LTR isolation", "prayer labels use the selected languages", "long mixed-direction title fits without overflow", "graphical language and bilingual controls round trip", "all graphical options survive configuration reload", "RTL overflow uses Chromium negative scrollLeft"]) assert.ok(report.checks.includes(name), `Missing browser check: ${name}`);
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
    for (const [index, {width, language, bilingual}] of fixtures.entries()) {
      if (bilingual) continue;
      await t.test(`${width}px ${language} timetable action placement and pointer navigation`, async () => {
        const evaluate = async source => {
          const result = await debuggerSession.call("Runtime.evaluate", {
            // Runtime.evaluate receives raw JavaScript over CDP JSON, not HTML. Escape
            // interpolated string literals above, but preserve executable source syntax.
            expression: `(() => {const frame = document.querySelectorAll('iframe')[${index}]; ${source}})()`,
            returnByValue: true,
          });
          assert.ok(!result.exceptionDetails, result.exceptionDetails?.exception?.description);
          return result.result.value;
        };
        const click = async selector => {
          const point = await evaluate(`
            const button = frame.contentWindow.actionFixture.actionCard.shadowRoot.querySelector(${escapeForJsEmbedding(JSON.stringify(selector))});
            button.scrollIntoView({block: "center", inline: "nearest"});
            const rect = button.getBoundingClientRect();
            const offset = frame.getBoundingClientRect();
            return {x: offset.left + rect.left + rect.width / 2, y: offset.top + rect.top + rect.height / 2};
          `);
          await debuggerSession.call("Input.dispatchMouseEvent", {type: "mousePressed", button: "left", clickCount: 1, ...point});
          await debuggerSession.call("Input.dispatchMouseEvent", {type: "mouseReleased", button: "left", clickCount: 1, ...point});
        };
        for (const [mode, daily, monthly] of [
          ["compact", ".summary-shell .card-menu-items", ".summary-shell .card-menu-items"],
          ["standard", ".header .card-action-strip", ".header .card-action-strip"],
          ["detailed", ".header .card-action-strip", ".header .card-action-strip"],
        ]) {
          await evaluate(`frame.contentWindow.actionFixture = frame.contentWindow.mountActionCard(${escapeForJsEmbedding(JSON.stringify(mode))});`);
          const placement = (selector, surface) => evaluate(`
            const root = frame.contentWindow.actionFixture.actionCard.shadowRoot;
            const container = root.querySelector(${escapeForJsEmbedding(JSON.stringify(selector))});
            const buttons = [...(container?.querySelectorAll("button") || [])];
            const bounds = container?.closest(${escapeForJsEmbedding(JSON.stringify(surface))})?.getBoundingClientRect();
            return buttons.length && buttons.every(button => {
              const rect = button.getBoundingClientRect();
              return rect.width > 0 && rect.height > 0 && bounds &&
                rect.left >= bounds.left - 1 && rect.right <= bounds.right + 1 &&
                rect.top >= bounds.top - 1 && rect.bottom <= bounds.bottom + 1;
            }) ? buttons.length : 0;
          `);
          // Compact popovers may overlay the monthly panel, so their visible
          // hit targets must fit the whole card rather than the short summary.
          const dailySurface = mode === "compact" ? "ha-card" : ".summary-shell";
          const monthlySurface = mode === "compact" ? "ha-card" : ".summary-shell";
          const compactLayout = () => evaluate(`
            const root = frame.contentWindow.actionFixture.actionCard.shadowRoot;
            const summary = root.querySelector(".summary-shell");
            const header = root.querySelector(".header");
            const below = root.querySelector(".timetable-shell, .monthly-shell");
            const menu = root.querySelector(".card-actions-menu");
            const dropdown = root.querySelector(".card-menu-items");
            const trigger = root.querySelector(".card-more-toggle");
            const summaryRect = summary.getBoundingClientRect();
            const triggerRect = trigger.getBoundingClientRect();
            const dropdownRect = dropdown.getBoundingClientRect();
            return {
              summaryHeight: summaryRect.height,
              headerHeight: header.getBoundingClientRect().height,
              belowOffset: below.getBoundingClientRect().top - summaryRect.top,
              open: menu.open,
              overlay: frame.contentWindow.getComputedStyle(dropdown).position === "absolute" &&
                frame.contentWindow.getComputedStyle(summary).overflow === "visible" &&
                dropdownRect.width > 0 && dropdownRect.height > 0 &&
                dropdownRect.top >= triggerRect.bottom + 4 &&
                dropdownRect.left >= summaryRect.left - 1 &&
                dropdownRect.right <= summaryRect.right + 1
            };
          `);
          const assertCompactOverlay = (closed, opened, label) => {
            assert.equal(opened.open && opened.overlay, true, `${label}: More menu floats below trigger and inside card`);
            for (const measure of ["summaryHeight", "headerHeight", "belowOffset"]) {
              assert.ok(Math.abs(opened[measure] - closed[measure]) <= 1,
                `${label}: opening More must not change ${measure} (${closed[measure]} -> ${opened[measure]})`);
            }
          };
          try {
            if (mode === "compact") {
              const closed = await compactLayout();
              await click(".card-more-toggle");
              assertCompactOverlay(closed, await compactLayout(), "Daily Compact");
              assert.equal(await evaluate(`
                const button = frame.contentWindow.actionFixture.actionCard.shadowRoot.querySelector(".card-menu-items .month-toggle");
                const label = button?.querySelector("span");
                return Boolean(label?.textContent?.trim()) &&
                  label.textContent === button.getAttribute("aria-label") &&
                  frame.contentWindow.getComputedStyle(label).display !== "none" &&
                  label.getClientRects().length > 0;
              `), true, "Compact More displays the Monthly timetable label alongside the icon");
            }
            assert.equal(await placement(daily, dailySurface), 1, `${mode}: daily action fits its surface`);
            await click(`${daily} .month-toggle`);
            assert.deepEqual(await evaluate("return frame.contentWindow.actionFixture.requests;"), [
              {type: "salah_timetable/month", entity_id: "sensor.example_prayer_timetable", year: 2026, month: 10},
            ], `${mode}: click requests the active timetable month`);
            assert.equal(await evaluate(`
              return frame.contentWindow.actionFixture.actionCard.shadowRoot.querySelector(".monthly-table tbody td")?.textContent;
            `), "05:45", `${mode}: monthly view renders the response`);
            if (mode === "compact") {
              const closed = await compactLayout();
              await click(".card-more-toggle");
              assertCompactOverlay(closed, await compactLayout(), "Monthly Compact");
              assert.equal(await evaluate(`
                const buttons = [...frame.contentWindow.actionFixture.actionCard.shadowRoot.querySelectorAll(".card-menu-items button")];
                return buttons.length === 4 && buttons.every(button => {
                  const label = button.querySelector("span");
                  return Boolean(label?.textContent?.trim()) &&
                    label.textContent === button.getAttribute("aria-label") &&
                    frame.contentWindow.getComputedStyle(label).display !== "none" &&
                    label.getClientRects().length > 0;
                });
              `), true, "Compact More displays all four monthly action labels");
            }
            assert.equal(await placement(monthly, monthlySurface), 4, `${mode}: all monthly actions fit their surface`);
            await click(`${monthly} .month-toggle`);
            assert.equal(await evaluate(`
              const root = frame.contentWindow.actionFixture.actionCard.shadowRoot;
              return !root.querySelector(".monthly-shell") && !!root.querySelector(".timetable-shell .date-tabs");
            `), true, `${mode}: Return to daily restores the daily timetable`);
          } finally {
            await evaluate("frame.contentWindow.actionFixture.actionCard.remove();");
          }
        }
      });
    }
    for (const [index, {width, language, bilingual}] of fixtures.entries()) {
      await t.test(`${width}px ${language}${bilingual ? " bilingual" : ""} standalone status widgets and grouped selection`, async () => {
        const evaluate = async source => {
          const result = await debuggerSession.call("Runtime.evaluate", {
            expression: `(async () => {const frame = document.querySelectorAll('iframe')[${index}]; const f = frame.contentWindow.widgetFixture; ${source}})()`,
            awaitPromise: true, returnByValue: true,
          });
          assert.ok(!result.exceptionDetails, result.exceptionDetails?.exception?.description);
          return result.result?.value;
        };
        await evaluate(`
          const helpers = await frame.contentWindow.eval("import('/tests/frontend/widget-browser-fixture.js')");
          frame.contentWindow.widgetFixture = helpers.mountWidgetFixture(${JSON.stringify({language, bilingual})});
        `);
        try {
          const initial = await evaluate(`
            const changes = f.changes.shadowRoot;
            const health = f.health.shadowRoot;
            const adminLink = health.querySelector('.widget-action');
            return {
              changeRows: changes.querySelectorAll('.widget-change-row').length,
              pending: Boolean(health.querySelector('.pending-review')),
              action: adminLink?.getAttribute('href'),
              dates: [...changes.querySelectorAll('.widget-change-times')].map(node => node.textContent),
              selected: [f.selector, f.changes, f.health].map(card => card._activeEntity()),
              natural: [f.changes, f.health].every(card => {
                const surface = card.shadowRoot.querySelector('ha-card');
                return surface.classList.contains('standalone-widget') &&
                  frame.contentWindow.getComputedStyle(surface).minHeight === '0px' &&
                  !surface.classList.contains('has-mosque-background');
              }),
              fits: [f.changes, f.health].every(card => {
                const surface = card.shadowRoot.querySelector('ha-card').getBoundingClientRect();
                return [...card.shadowRoot.querySelectorAll('.widget-panel, .widget-change-row, .widget-health-row')].every(node => {
                  const bounds = node.getBoundingClientRect();
                  return bounds.left >= surface.left - 1 && bounds.right <= surface.right + 1;
                });
              }),
            };
          `);
          assert.ok(initial.changeRows > 0, "Approved tomorrow changes render as published field rows");
          assert.ok(initial.dates.every(value => value.trim().length > 0), "Every change row shows the published comparison times");
          assert.equal(initial.pending, true, "Pending manual imports display even without a URL source");
          assert.match(initial.action, /\/config\/integrations\/integration\/salah_timetable\?config_entry=entry_0$/);
          assert.equal(initial.natural, true, "Standalone widgets retain their natural content height without a photo canvas");
          assert.equal(initial.fits, true, "Status content fits its card at the actual container width");
          assert.deepEqual(initial.selected, ["sensor.widget_first_prayer_timetable", "sensor.widget_first_prayer_timetable", "sensor.widget_first_prayer_timetable"]);

          assert.deepEqual(await evaluate(`
            f.select(f.second);
            return [f.selector, f.changes, f.health].map(card => card._activeEntity());
          `), Array(3).fill("sensor.widget_second_prayer_timetable"), "One selector changes every member of its group");
          assert.equal(await evaluate(`return f.health.shadowRoot.querySelector('.widget-action')?.getAttribute('href');`), "/config/integrations/integration/salah_timetable?config_entry=entry_20", "Review action follows the selected mosque");

          const isolation = await evaluate(`
            const wrapper = frame.contentDocument.createElement('hui-card-options');
            f.view.append(wrapper);
            const preview = f.mount('salah-widget-mosque-selector', {selection_group:'browser-status-widgets'}, wrapper);
            const chooser = preview.shadowRoot.querySelector('.mosque-select');
            chooser.value = f.first;
            chooser.dispatchEvent(new frame.contentWindow.Event('change', {bubbles:true}));
            const restricted = f.mount('salah-widget-timetable-health', {selection_group:'browser-status-widgets',mosque_entities:[f.first]});
            const ungrouped = f.mount('salah-widget-timetable-health');
            const view = frame.contentDocument.createElement('hui-view');
            f.view.after(view);
            const otherView = f.mount('salah-widget-timetable-health', {selection_group:'browser-status-widgets'}, view);
            const result = {
              live: f.health._activeEntity(), preview: preview._activeEntity(),
              restricted: Boolean(restricted.shadowRoot.querySelector('.group-selection-error')),
              independent: ungrouped._activeEntity(), otherView: otherView._activeEntity(),
            };
            view.remove();wrapper.remove();
            return result;
          `);
          assert.equal(isolation.live, "sensor.widget_second_prayer_timetable", "Dashboard edit previews cannot switch the live group");
          assert.equal(isolation.preview, "sensor.widget_first_prayer_timetable");
          assert.equal(isolation.restricted, true, "An excluded group mosque shows an explicit error instead of a fallback mosque");
          assert.equal(isolation.independent, "sensor.widget_first_prayer_timetable");
          assert.equal(isolation.otherView, "sensor.widget_first_prayer_timetable", "Identical group names are isolated between dashboard views");

          const nonAdmin = await evaluate(`
            f.health.hass = {...f.hass,user:{is_admin:false}};
            return f.health.shadowRoot.querySelectorAll('.widget-action').length;
          `);
          assert.equal(nonAdmin, 0, "Non-administrators see status without integration-management actions");

          const refreshed = await evaluate(`
            const state = f.hass.states[f.second];
            const next = {...f.hass,states:{...f.hass.states,[f.second]:{
              ...state,attributes:{...state.attributes,timetable_health:{...state.attributes.timetable_health,
                source:{...state.attributes.timetable_health.source,pending_review:false}}}
            }}};
            f.health.hass = next;
            return !f.health.shadowRoot.querySelector('.pending-review');
          `);
          assert.equal(refreshed, true, "New source status updates the widget without a card reload");
          const disconnected = await evaluate(`
            for (const card of [f.health, f.changes]) card.hass = {...f.hass,connection:{connected:false}};
            return {
              healthUnavailable: Boolean(f.health.shadowRoot.querySelector('.widget-health .widget-status')) &&
                !f.health.shadowRoot.querySelector('.pending-review, .widget-action'),
              changesUnavailable: Boolean(f.changes.shadowRoot.querySelector('.widget-changes .widget-status')) &&
                !f.changes.shadowRoot.querySelector('.widget-change-row'),
            };
          `);
          assert.equal(disconnected.healthUnavailable, true, "Disconnected health does not retain a current pending/review presentation");
          assert.equal(disconnected.changesUnavailable, true, "Disconnected change data is explicitly unavailable");
        } finally {
          await evaluate("f.destroy(); delete frame.contentWindow.widgetFixture;");
        }
      });
    }
    for (const [index, {width, language, bilingual}] of fixtures.entries()) {
      await t.test(`${width}px ${language}${bilingual ? " bilingual" : ""} independent widgets, custom arrangement and visual editor`, async () => {
        const evaluate = async source => {
          const result = await debuggerSession.call("Runtime.evaluate", {
            expression: `(async () => {const frame = document.querySelectorAll('iframe')[${index}]; const f = frame.contentWindow.widgetFixture; ${source}})()`,
            awaitPromise: true, returnByValue: true,
          });
          assert.ok(!result.exceptionDetails, result.exceptionDetails?.exception?.description);
          return result.result?.value;
        };
        await evaluate(`
          const helpers = await frame.contentWindow.eval("import('/tests/frontend/widget-browser-fixture.js')");
          frame.contentWindow.widgetFixture = helpers.mountWidgetFixture(${JSON.stringify({language, bilingual})});
        `);
        try {
          const standalone = await evaluate(`
            const module = await frame.contentWindow.eval("import('/custom_components/salah_timetable/frontend/widget-utils.js?v=3.1.0')");
            f.widgetModule = module;
            f.standalone = module.SECTIONS.map(({id, show}) => {
              const type = module.widgetType(id).slice('custom:'.length);
              const card = f.mount(type, {[show]:false});
              return {id, card};
            });
            return f.standalone.map(({id,card}) => ({
              id,
              registered: Boolean(frame.contentWindow.customElements.get(module.widgetType(id).slice('custom:'.length))),
              picker: frame.contentWindow.customCards.some(item => item.type === module.widgetType(id).slice('custom:'.length)),
              content: card.shadowRoot.querySelector('ha-card.standalone-widget')?.textContent.trim(),
              section: Boolean(card.shadowRoot.querySelector('[data-section="'+id+'"]')),
            }));
          `);
          assert.equal(standalone.length, 10);
          for (const item of standalone) {
            assert.equal(item.registered && item.picker, true, `${item.id} has its own registered Add card entry`);
            assert.ok(item.content, `${item.id} always has useful standalone content`);
            if (item.id !== "mosque_selector") assert.equal(item.section, true, `${item.id} renders its requested section rather than only a mosque title`);
          }
          assert.equal(await evaluate(`return Boolean(f.standalone.find(item=>item.id==='timetable').card.shadowRoot.querySelector('table, .kiosk-prayer-strip'));`), true, "Standalone timetable renders despite its section visibility flag");
          assert.equal(await evaluate(`return Boolean(f.standalone.find(item=>item.id==='ramadan').card.shadowRoot.querySelector('.widget-status'));`), true, "Inactive standalone Ramadan explains its unavailable content");
          assert.equal(await evaluate(`return Boolean(f.standalone.find(item=>item.id==='night_calculations').card.shadowRoot.querySelector('.night-calculations'));`), true, "Standalone calculated-night data is available without an enabling section switch");

          const arrangement = await evaluate(`
            f.custom = f.mount('salah-timetable-card', {
              detail_level:'compact',show_mosque_selector:false,show_dates:true,show_timetable:true,
              show_salah_countdown:true,show_jamaat_countdown:true,show_clock:false,
              show_ramadan_details:false,show_night_calculations:false,
              show_jamaat_changes:false,show_timetable_health:false,
              arrangement:{sections:[{id:'salah',width:'half'},{id:'jamaat',width:'half'},{id:'timetable',width:'full'},{id:'dates',width:'full'}]},
            });
            const root = f.custom.shadowRoot;
            const grid = root.querySelector('.arrangement-grid');
            const cells = [...grid.querySelectorAll(':scope > .arrangement-section')];
            const bounds = grid.getBoundingClientRect();
            const rect = element => {const b=element.getBoundingClientRect();return {top:b.top,bottom:b.bottom,left:b.left,width:b.width};};
            return {
              order:cells.map(cell=>cell.getAttribute('data-section')),
              table:Boolean(root.querySelector('table')),
              dates:Boolean(root.querySelector('.hijri, .gregorian')),
              first:rect(cells[0]),second:rect(cells[1]),full:rect(cells[2]),
              fits:cells.every(cell=>{const b=cell.getBoundingClientRect();return b.left>=bounds.left-1&&b.right<=bounds.right+1;}),
            };
          `);
          assert.deepEqual(arrangement.order, ["salah", "jamaat", "timetable", "dates"], "Saved custom order also defines DOM order");
          assert.equal(arrangement.table && arrangement.dates, true, "Explicit arrangement can show dates and timetable in Compact mode");
          assert.equal(arrangement.fits, true, "Every arranged section stays inside the card container");
          if (width < 600) assert.ok(arrangement.second.top >= arrangement.first.bottom - 1, "Half-width sections stack on narrow cards");
          else {
            assert.ok(Math.abs(arrangement.first.top - arrangement.second.top) <= 1, "Half-width sections share a row on wider cards");
            assert.ok(arrangement.full.width > arrangement.first.width * 1.8, "Full-width timetable spans both grid columns");
          }
          const ticking = await evaluate(`
            const root=f.custom.shadowRoot;
            const table=root.querySelector('table');
            const clock=root.querySelector('[data-panel="salah"] .count');
            const before=clock.textContent;
            f.custom._tick(f.now+1000);
            return {tableSame:root.querySelector('table')===table,clockSame:root.querySelector('[data-panel="salah"] .count')===clock,changed:before!==clock.textContent};
          `);
          assert.deepEqual(ticking, {tableSame: true, clockSame: true, changed: true}, "Custom arrangement retains live countdown nodes and table focus targets on ticks");

          await evaluate(`
            f.editorState=f.mountEditor({selection_group:'browser-status-widgets',arrangement:f.custom._config.arrangement,
              show_salah_countdown:true,show_jamaat_countdown:true,show_timetable:true,show_dates:true});
            f.editorState.editor.shadowRoot.querySelector('[data-editor-tab="layout"]').click();
          `);
          const controls = await evaluate(`
            const root=f.editorState.editor.shadowRoot;
            return {rows:root.querySelectorAll('[data-layout-section]').length,
              labelled:[...root.querySelectorAll('[data-layout-action]')].every(control=>Boolean(control.getAttribute('aria-label'))),
              preview:Boolean(root.querySelector('[data-layout-preview-card]')),
              settingsHidden:frame.contentWindow.getComputedStyle(root.querySelector('.form')).display==='none'};
          `);
          assert.equal(controls.rows, 10);
          assert.equal(controls.labelled && controls.preview, true, "Layout controls have accessible labels and a preview of the actual card");
          assert.equal(controls.settingsHidden, true, "The Settings panel is visually hidden while Layout is selected");
          assert.equal(await evaluate(`
            const editor=f.mountEditor({type:'custom:salah-widget-timetable-health'}).editor;
            return frame.contentWindow.getComputedStyle(editor.shadowRoot.querySelector('.editor-tabs')).display==='none';
          `), true, "Standalone widget editors visually hide the composite Layout tabs");

          const ordering = await evaluate(`
            const root=f.editorState.editor.shadowRoot;
            const helper=root.querySelector('.layout-editor');
            const start=f.editorState.config;
            const source=root.querySelector('[data-layout-section="jamaat"]');
            const up=source.querySelector('[data-layout-action="up"]');
            up.focus();up.click();
            const arrow=f.editorState.config.arrangement.sections.map(item=>item.id);
            const focused=root.activeElement?.closest('[data-layout-section]')?.getAttribute('data-layout-section');
            f.editorState.editor.setConfig(start);
            const from=root.querySelector('[data-layout-section="jamaat"] [data-layout-action="drag"]');
            const to=root.querySelector('[data-layout-section="salah"]');
            const transfer=new frame.contentWindow.DataTransfer();
            from.dispatchEvent(new frame.contentWindow.DragEvent('dragstart',{bubbles:true,dataTransfer:transfer}));
            to.dispatchEvent(new frame.contentWindow.DragEvent('dragover',{bubbles:true,cancelable:true,dataTransfer:transfer}));
            to.dispatchEvent(new frame.contentWindow.DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:transfer}));
            from.dispatchEvent(new frame.contentWindow.DragEvent('dragend',{bubbles:true,dataTransfer:transfer}));
            return {arrow,drag:f.editorState.config.arrangement.sections.map(item=>item.id),focused};
          `);
          assert.deepEqual(ordering.drag, ordering.arrow, "Native drag/drop and Move up produce identical saved arrangements");
          assert.equal(ordering.focused, "jamaat", "Moving a section preserves focus within that section after configuration echo");

          const edited = await evaluate(`
            const root=f.editorState.editor.shadowRoot;
            const row=root.querySelector('[data-layout-section="jamaat"]');
            const width=row.querySelector('[data-layout-action="width"]');
            width.value='full';width.dispatchEvent(new frame.contentWindow.Event('change',{bubbles:true}));
            const visibility=row.querySelector('[data-layout-action="visible"]');
            visibility.checked=false;visibility.dispatchEvent(new frame.contentWindow.Event('change',{bubbles:true}));
            return {width:f.editorState.config.arrangement.sections.find(item=>item.id==='jamaat').width,
              visible:f.editorState.config.show_jamaat_countdown};
          `);
          assert.deepEqual(edited, {width: "full", visible: false}, "Layout width and visibility edit the saved per-card settings");

          for (const [device, expectedWidth] of [["phone", 360], ["tablet", 768], ["desktop", 1280]]) {
            const preview = await evaluate(`
              const root=f.editorState.editor.shadowRoot;
              const control=root.querySelector('[data-layout-device]');
              control.value=${JSON.stringify(device)};control.dispatchEvent(new frame.contentWindow.Event('change',{bubbles:true}));
              const card=root.querySelector('[data-layout-preview-card]');
              const viewport=root.querySelector('[data-layout-preview-frame]');
              const inner=viewport.firstElementChild;
              return {width:inner.style.width,preview:card.preview,group:card._config.selection_group,
                fits:card.getBoundingClientRect().width<=viewport.getBoundingClientRect().width+1};
            `);
            assert.equal(preview.width, `${expectedWidth}px`, `${device} preview uses its advertised logical device width`);
            assert.equal(preview.preview && preview.fits, true, `${device} preview scales inside the editor`);
            assert.ok(!preview.group, "Device previews are isolated from live mosque groups");
          }
          if (!bilingual && ((width === 360 && language === "en") || (width === 900 && language === "en") || (width === 400 && language === "ar"))) {
            const suffix = `${width}-${language}`;
            await captureWidget(debuggerSession, index, "f.custom", `custom-layout-${suffix}.png`);
            await captureWidget(debuggerSession, index, "f.health", `health-widget-${suffix}.png`);
            await captureWidget(debuggerSession, index, "f.editorState.editor.shadowRoot.querySelector('[data-layout-preview-frame]')", `layout-preview-${suffix}.png`);
          }
          const reset = await evaluate(`
            const root=f.editorState.editor.shadowRoot;
            const before=f.editorState.config;
            root.querySelector('[data-layout-reset]').click();
            return {custom:Boolean(f.editorState.config.arrangement),entity:f.editorState.config.entity,
              language:f.editorState.config.language,mosques:f.editorState.config.mosque_entities,
              initialEntity:before.entity,initialLanguage:before.language,initialMosques:before.mosque_entities};
          `);
          assert.equal(reset.custom, false, "Reset restores the legacy mode arrangement");
          assert.equal(reset.entity, reset.initialEntity);
          assert.equal(reset.language, reset.initialLanguage);
          assert.deepEqual(reset.mosques, reset.initialMosques, "Reset preserves selected mosques");
        } finally {
          await evaluate("f.destroy(); delete frame.contentWindow.widgetFixture;");
        }
      });
    }
    for (const language of ["en", "ar"]) {
      await t.test(`1280px ${language} custom wall layout`, async () => {
        const index = fixtures.findIndex(fixture => fixture.width === 900 && fixture.language === language && !fixture.bilingual);
        await debuggerSession.call("Emulation.setDeviceMetricsOverride", {width: 1400, height: 1200, deviceScaleFactor: 1, mobile: false});
        const evaluate = async source => {
          const result = await debuggerSession.call("Runtime.evaluate", {
            expression: `(async () => {const frame=document.querySelectorAll('iframe')[${index}];const f=frame.contentWindow.widgetFixture;${source}})()`,
            awaitPromise: true, returnByValue: true,
          });
          assert.ok(!result.exceptionDetails, result.exceptionDetails?.exception?.description);
          return result.result?.value;
        };
        await evaluate(`
          frame.style.width='1280px';
          frame.style.height='1200px';
          const helpers=await frame.contentWindow.eval("import('/tests/frontend/widget-browser-fixture.js')");
          frame.contentWindow.widgetFixture=helpers.mountWidgetFixture({language:${JSON.stringify(language)}});
        `);
        try {
          const wall = await evaluate(`
            const module=await frame.contentWindow.eval("import('/custom_components/salah_timetable/frontend/widget-utils.js?v=3.1.0')");
            f.wall=f.mount('salah-timetable-card', {...module.applyPreset(f.base,'wall'),show_jamaat_changes:false,show_timetable_health:false});
            const root=f.wall.shadowRoot;
            const grid=root.querySelector('.arrangement-grid');
            const bounds=grid.getBoundingClientRect();
            const cells=[...grid.querySelectorAll(':scope>.arrangement-section')];
            const count=root.querySelector('[data-panel="salah"] .count');
            const before=count.textContent;
            f.wall._tick(f.now+1000);
            return {kiosk:f.wall._config.kiosk_mode,
              clock:Boolean(root.querySelector('.kiosk-clock')),
              strip:root.querySelectorAll('.kiosk-strip .kiosk-tile').length,
              fullscreen:Boolean(root.querySelector('.kiosk-fullscreen')),
              dateTabs:Boolean(root.querySelector('[data-section="timetable"] .date-tabs')),
              live:count.textContent!==before,
              fits:cells.every(cell=>{const b=cell.getBoundingClientRect();return b.left>=bounds.left-1&&b.right<=bounds.right+1;})};
          `);
          assert.equal(wall.kiosk && wall.clock && wall.fullscreen && wall.dateTabs && wall.live && wall.fits, true, "Custom wall arrangements retain clock, published timetable, navigation, fullscreen and live timers without clipping");
          assert.equal(wall.strip, 5, "Kiosk uses the existing five published daily-prayer tiles");
          await captureWidget(debuggerSession, index, "f.wall", `custom-kiosk-1280-${language}.png`);
        } finally {
          await evaluate("f.destroy();delete frame.contentWindow.widgetFixture;frame.style.width='900px';frame.style.height='1500px';");
        }
      });
    }
  } finally {
    clearTimeout(deadline);
    await debuggerSession?.call("Browser.close").catch(() => {});
    debuggerSession?.close(); stopBrowser(child);
    server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
    await rm(directory, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  }
});
