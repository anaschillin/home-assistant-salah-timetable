/** Real HA card-picker/editor browser check used by the opt-in live smoke. */
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {constants} from "node:fs";
import {access, mkdir, mkdtemp, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {waitForDebuggerPort} from "../tests/frontend/browser-startup.mjs";

const pause = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
const deep = "function deep(root=document){let result=[];for(const element of root.querySelectorAll('*')){result.push(element);if(element.shadowRoot)result.push(...deep(element.shadowRoot));}return result}";

export async function runBrowserSmoke({base, tokens, output, signal}) {
  let browser;
  for (const path of [process.env.CHROME_BIN, "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome", "/opt/google/chrome/chrome"].filter(Boolean)) {
    try { await access(path, constants.X_OK); browser = path; break; } catch { /* Try another installed browser. */ }
  }
  assert.ok(browser, "Chromium/Chrome is required; set CHROME_BIN to its executable");
  const profile = await mkdtemp(join(tmpdir(), "salah-ha-browser-"));
  const child = spawn(browser, ["--headless", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-background-networking", "--no-first-run", `--user-data-dir=${profile}`, "--remote-debugging-port=0", "about:blank"], {detached: process.platform !== "win32", stdio: ["ignore", "ignore", "pipe"]});
  let stderr = ""; child.stderr.on("data", value => { stderr = (stderr + value).slice(-2000); });
  const stop = () => { try { process.kill(process.platform === "win32" ? child.pid : -child.pid, "SIGKILL"); } catch { /* Already stopped. */ } };
  const deadline = setTimeout(stop, 120000); signal.addEventListener("abort", stop, {once: true});
  let socket; let sequence = 0; const pending = new Map();
  function call(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++sequence;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Browser command timed out: ${method}`)); }, 8000);
      pending.set(id, {resolve, reject, timer}); socket.send(JSON.stringify({id, method, params}));
    });
  }
  async function evaluate(expression) {
    const value = await call("Runtime.evaluate", {expression, returnByValue: true, awaitPromise: true});
    if (value.exceptionDetails) throw new Error("Browser evaluation failed: " + value.exceptionDetails.text);
    return value.result?.value;
  }
  async function until(expression, message, attempts = 100) {
    for (let attempt = 0; attempt < attempts; attempt++) {
      signal.throwIfAborted();
      const value = await evaluate(expression);
      if (value) return value;
      await pause(300);
    }
    throw new Error(message);
  }
  const expression = body => `(()=>{${deep};${body}})()`;
  const findCard = "deep().find(element=>element.localName==='salah-timetable-card')";
  try {
    const port = await waitForDebuggerPort(child, profile, {stderr: () => stderr});
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`, {signal: AbortSignal.timeout(5000)})).json();
    socket = new WebSocket(targets.find(target => target.type === "page").webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, {once: true}); socket.addEventListener("error", reject, {once: true}); });
    socket.addEventListener("message", event => {
      const value = JSON.parse(event.data); const task = pending.get(value.id);
      if (task) { pending.delete(value.id); clearTimeout(task.timer); value.error ? task.reject(new Error(JSON.stringify(value.error))) : task.resolve(value.result); }
    });
    socket.addEventListener("close", () => { for (const task of pending.values()) { clearTimeout(task.timer); task.reject(new Error("Browser debugger disconnected")); } pending.clear(); });
    await call("Page.enable");
    await call("Page.addScriptToEvaluateOnNewDocument", {source: `if(location.origin===${JSON.stringify(base)})localStorage.setItem('hassTokens',${JSON.stringify(JSON.stringify(tokens))});`});
    await call("Emulation.setDeviceMetricsOverride", {width: 900, height: 1100, deviceScaleFactor: 1, mobile: false});
    await call("Page.navigate", {url: `${base}/salah-smoke/smoke`});
    await until(expression(`const card=${findCard};return card?.shadowRoot?.textContent?.includes('Smoke Mosque')`), "Bundled card did not render in real HA");
    console.log("Real HA frontend loaded the bundled card");
    for (const width of [320, 360, 400, 900]) {
      await call("Emulation.setDeviceMetricsOverride", {width, height: 1100, deviceScaleFactor: 1, mobile: width === 360}); await pause(250);
      assert.equal(await evaluate(expression(`const card=${findCard};const content=card.shadowRoot.querySelector('.content');return content.scrollWidth<=content.clientWidth+1&&card.getBoundingClientRect().right<=innerWidth+1`)), true, `Card overflows at ${width}px`);
      if (output) { await mkdir(output, {recursive: true}); await pause(500); const image = await call("Page.captureScreenshot", {format: "png"}); await writeFile(join(output, `ha-${width}.png`), Buffer.from(image.data, "base64")); }
    }
    const before = await evaluate(expression(`return getComputedStyle(${findCard}).color`));
    await evaluate("document.querySelector('home-assistant').dispatchEvent(new CustomEvent('settheme',{detail:{theme:'default',dark:true},bubbles:true,composed:true}))");
    await until("document.querySelector('home-assistant').hass.themes.darkMode===true", "HA dark preference did not apply");
    assert.notEqual(await evaluate(expression(`return getComputedStyle(${findCard}).color`)), before, "Card text did not follow real HA dark theme");
    await evaluate("document.querySelector('home-assistant').dispatchEvent(new CustomEvent('settheme',{detail:{theme:'default',dark:false},bubbles:true,composed:true}))");
    await until("document.querySelector('home-assistant').hass.themes.darkMode===false", "HA light preference did not apply");
    await call("Emulation.setDeviceMetricsOverride", {width: 360, height: 1100, deviceScaleFactor: 1, mobile: true});
    await evaluate("document.documentElement.style.fontSize='200%'"); await pause(200);
    assert.equal(await evaluate(expression(`const card=${findCard};const content=card.shadowRoot.querySelector('.content');return content.scrollWidth<=content.clientWidth+1`)), true, "Card overflows at 200% root text scale");
    await evaluate("document.documentElement.style.fontSize=''");
    await call("Emulation.setDeviceMetricsOverride", {width: 900, height: 1100, deviceScaleFactor: 1, mobile: false});
    await call("Page.navigate", {url: `${base}/salah-smoke/smoke?edit=1`});
    await until(expression("const button=deep().find(element=>element.localName==='ha-button'&&element.textContent.trim().toLowerCase()==='add card');if(!button)return false;button.click();return true"), "Real dashboard Add card button missing");
    await until(expression("const dialog=deep().find(element=>element.localName==='hui-dialog-create-card');const tab=dialog&&deep(dialog.shadowRoot).find(element=>element.localName==='ha-tab-group-tab'&&element.getAttribute('panel')==='card');if(!tab)return false;tab.click();return true"), "Real card picker tab missing");
    await until(expression("const picker=deep().find(element=>element.localName==='hui-card-picker');const option=picker&&deep(picker.shadowRoot).find(element=>element.classList.contains('overlay')&&element.config?.type==='custom:salah-timetable-card');if(!option)return false;option.click();return true"), "Salah Timetable missing from actual custom-card picker");
    await until(expression("const dialog=deep().find(element=>element.localName==='hui-dialog-edit-card');const editor=dialog&&deep(dialog.shadowRoot).find(element=>element.localName==='salah-timetable-card-editor');if(!editor?.shadowRoot?.querySelector('#mosque-title'))return false;window.salahEditor=editor;return deep(editor.shadowRoot).some(element=>element.localName==='ha-radio-option'&&element.value==='upcoming')"), "Actual card editor controls did not render");
    await evaluate(expression("deep(window.salahEditor.shadowRoot).find(element=>element.localName==='ha-radio-option'&&element.value==='upcoming').click();return true"));
    await until("window.salahEditor._config.mode==='upcoming'", "Actual mode radio did not update configuration");
    await evaluate("window.salahEditor.shadowRoot.querySelector('#mosque-title').focus()");
    await call("Input.insertText", {text: "Keyboard smoke title"});
    await until("window.salahEditor._config.title==='Keyboard smoke title'", "Keyboard title input did not update configuration");
    assert.equal(await evaluate("window.salahEditor.shadowRoot.activeElement===window.salahEditor.shadowRoot.querySelector('#mosque-title')"), true, "Configuration echo lost keyboard focus");
    await call("Input.dispatchKeyEvent", {type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9});
    await call("Input.dispatchKeyEvent", {type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9});
    assert.equal(await evaluate("window.salahEditor.shadowRoot.activeElement===window.salahEditor.shadowRoot.querySelector('#mosque-title')"), false, "Tab did not leave title field");
    const originalData = await evaluate(expression("const card=deep().find(element=>element.localName==='salah-timetable-card'&&element._config?.entity);const data=card._hass.states[card._config.entity].attributes;return {prayers:data.prayers,active:data.ramadan.active}"));
    const selected = {layout: "compact", time_format: "12h", hijri_adjustment: 2, show_hijri_date: true, show_salah_countdown: false, show_jamaat_countdown: true, show_ramadan_details: true, show_sehri_countdown: false, show_iftar_countdown: false, show_timezone_note: false};
    for (const [key, target] of Object.entries(selected)) for (const value of typeof target === "boolean" ? [!target, target] : [target]) {
      await evaluate(`(()=>{const control=window.salahEditor.shadowRoot.querySelector('[data-option="${key}"]');if(!control)throw new Error('Missing editor control');${typeof value === "boolean" ? `control.checked=${value};` : `control.value=${JSON.stringify(String(value))};`}control.dispatchEvent(new Event('change',{bubbles:true}));return true})()`);
      await until(`window.salahEditor._config[${JSON.stringify(key)}]===${JSON.stringify(value)}`, `Editor option did not update: ${key}`);
    }
    await until(expression("const dialog=deep().find(element=>element.localName==='hui-dialog-edit-card');const save=dialog&&deep(dialog.shadowRoot).find(element=>element.localName==='ha-button'&&element.getAttribute('slot')==='primaryAction');if(!save)return false;save.click();return true"), "Real card editor Save button missing");
    await until(expression("return deep().filter(element=>element.localName==='salah-timetable-card').some(card=>card.shadowRoot.textContent.includes('Keyboard smoke title'))"), "Saved edited card did not appear on dashboard");
    await call("Page.reload", {ignoreCache: true});
    await until(expression("return deep().filter(element=>element.localName==='salah-timetable-card').some(card=>card.shadowRoot?.textContent.includes('Keyboard smoke title'))"), "Saved card missing after page reload");
    const restored = await evaluate(expression("const card=deep().find(element=>element.localName==='salah-timetable-card'&&element._config?.title==='Keyboard smoke title');return card?{config:card._config,panels:card.shadowRoot.querySelectorAll('.panel').length,compact:!!card.shadowRoot.querySelector('.content.compact'),hijri:card.shadowRoot.querySelector('.hijri')?.textContent,data:{prayers:card._hass.states[card._config.entity].attributes.prayers,active:card._hass.states[card._config.entity].attributes.ramadan.active},times:[...card.shadowRoot.querySelectorAll('tbody td')].map(cell=>cell.textContent)}:null"));
    for (const [key, value] of Object.entries(selected)) assert.equal(restored.config[key], value, `Saved option did not survive reload: ${key}`);
    assert.deepEqual(restored.data, originalData, "Display controls changed prayer data or Ramadan activation");
    assert.equal(restored.panels, 1); assert.equal(restored.compact, true);
    assert.match(restored.hijri, /Hijri \(calculated\)/);
    assert.ok(restored.times.some(value => /[ap]m/i.test(value)), "Reloaded card does not use 12-hour times");
    console.log("Real card picker, mode radio, keyboard title, focus, themes and 200% text scale passed");
    return {viewports: [320, 360, 400, 900], configuration_reload: true, picker: true, editor: true, keyboard: true, themes: ["light", "dark"], root_text_scale: "200%"};
  } finally {
    clearTimeout(deadline); signal.removeEventListener("abort", stop); socket?.close(); stop();
    await pause(100); await rm(profile, {recursive: true, force: true});
  }
}
