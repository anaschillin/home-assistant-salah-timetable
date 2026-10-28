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
const unsafeJsCharMap = {"<":"\\u003C",">":"\\u003E","/":"\\u002F","\\":"\\\\","\b":"\\b","\f":"\\f","\n":"\\n","\r":"\\r","\t":"\\t","\0":"\\0","\u2028":"\\u2028","\u2029":"\\u2029"};
const safeJsLiteral = value => JSON.stringify(value).replace(/[<>\/\\\b\f\n\r\t\0\u2028\u2029]/g, character => unsafeJsCharMap[character] ?? character);

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
  const deadline = setTimeout(stop, 180000); signal.addEventListener("abort", stop, {once: true});
  let socket; let sequence = 0; const pending = new Map();
  let originalLocale;
  function call(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++sequence;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Browser command timed out: ${method}`)); }, 8000);
      pending.set(id, {resolve, reject, timer}); socket.send(JSON.stringify({id, method, params}));
    });
  }
  async function evaluate(expression) {
    const value = await call("Runtime.evaluate", {expression, returnByValue: true, awaitPromise: true});
    if (value.exceptionDetails) throw new Error("Browser evaluation failed: " + value.exceptionDetails.text + (value.exceptionDetails.exception?.description ? "\n" + value.exceptionDetails.exception.description : ""));
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
  const previewCard = "(()=>{const dialog=deep().find(element=>element.localName==='hui-dialog-edit-card');return dialog&&deep(dialog.shadowRoot).find(element=>element.localName==='salah-timetable-card')})()";
  async function setEditorOption(key, value) {
    await evaluate(`(()=>{const control=window.salahEditor.shadowRoot.querySelector('[data-option="'+${safeJsLiteral(String(key))}+'"]');if(!control)throw new Error('Missing editor control: '+${safeJsLiteral(String(key))});${typeof value === "boolean" ? `control.checked=${value};` : `control.value=${safeJsLiteral(String(value))};`}control.dispatchEvent(new Event('change',{bubbles:true}));return true})()`);
    await until(`window.salahEditor._config[${safeJsLiteral(key)}]===${safeJsLiteral(value)}`, `Editor option did not update: ${key}`);
  }
  try {
    const port = await waitForDebuggerPort(child, profile, {timeoutMs: 30000, stderr: () => stderr});
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
    originalLocale = await evaluate("({...document.querySelector('home-assistant').hass.locale})");
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
    await until(expression("const dialog=deep().find(element=>element.localName==='hui-dialog-edit-card');const editor=dialog&&deep(dialog.shadowRoot).find(element=>element.localName==='salah-timetable-card-editor');if(!editor?.shadowRoot?.querySelector('#mosque-title'))return false;window.salahEditor=editor;return Boolean(editor.shadowRoot.querySelector('[data-option=detail_level]'))"), "Actual card editor controls did not render");
    await setEditorOption("detail_level", "detailed");
    await until("window.salahEditor._config.detail_level==='detailed'", "Actual detail level did not update configuration");
    await evaluate("window.salahEditor.shadowRoot.querySelector('#mosque-title').focus()");
    await call("Input.insertText", {text: "Keyboard smoke title"});
    await until("window.salahEditor._config.title==='Keyboard smoke title'", "Keyboard title input did not update configuration");
    assert.equal(await evaluate("window.salahEditor.shadowRoot.activeElement===window.salahEditor.shadowRoot.querySelector('#mosque-title')"), true, "Configuration echo lost keyboard focus");
    await call("Input.dispatchKeyEvent", {type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9});
    await call("Input.dispatchKeyEvent", {type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9});
    assert.equal(await evaluate("window.salahEditor.shadowRoot.activeElement===window.salahEditor.shadowRoot.querySelector('#mosque-title')"), false, "Tab did not leave title field");
    const originalData = await evaluate(expression("const card=deep().find(element=>element.localName==='salah-timetable-card'&&element._config?.entity);const data=card._hass.states[card._config.entity].attributes;return {prayers:data.prayers,active:data.ramadan.active}"));
    for (const language of ["en", "ar"]) for (const bilingual of [false, true]) {
      await setEditorOption("language", language);
      await setEditorOption("bilingual_prayer_labels", bilingual);
      await until(expression(`const card=${previewCard};const label=card?.shadowRoot.querySelector('tbody th .prayer-labels');const names=label&&[...label.querySelectorAll('bdi')];return card?.getAttribute('lang')===${safeJsLiteral(language)}&&card.getAttribute('dir')===${safeJsLiteral(language === "ar" ? "rtl" : "ltr")}&&window.salahEditor.getAttribute('dir')===card.getAttribute('dir')&&names?.length===${bilingual ? 2 : 1}&&names[0].getAttribute('lang')===${safeJsLiteral(language)}${bilingual ? `&&names[1].getAttribute('lang')===${safeJsLiteral(language === "ar" ? "en" : "ar")}` : ""}`), `Actual language/bilingual controls did not update preview: ${language}/${bilingual}`);
      await until(expression(`const root=${previewCard}?.shadowRoot;return root?.querySelector('header').children[1]===root?.querySelector('.hijri')&&root?.querySelector('header').children[2]===root?.querySelector('.gregorian')`), `Hijri-first header missing: ${language}/${bilingual}`);
      await setEditorOption("show_gregorian_date", false);
      await until(expression(`const root=${previewCard}?.shadowRoot;return !!root?.querySelector('.hijri')&&!root?.querySelector('.gregorian')`), `Gregorian visibility affected Hijri date: ${language}/${bilingual}`);
      await setEditorOption("show_gregorian_date", true);
    }
    await setEditorOption("language", "auto");
    await until(expression(`const card=${previewCard};return card?._config.language==='auto'&&card.getAttribute('lang')==='en'`), "Actual automatic-language control did not follow the English HA locale");
    const selected = {language: "ar", bilingual_prayer_labels: true, detail_level: "standard", time_format: "12h", hijri_adjustment: 2, show_hijri_date: true, show_gregorian_date: false, show_salah_countdown: false, show_jamaat_countdown: true, show_ramadan_details: true, show_sehri_countdown: false, show_iftar_countdown: false, show_timezone_note: false};
    for (const [key, target] of Object.entries(selected)) for (const value of typeof target === "boolean" ? [!target, target] : [target]) {
      await setEditorOption(key, value);
      if (typeof value === "boolean" && key !== "bilingual_prayer_labels") await until(expression(`
        const dialog=deep().find(element=>element.localName==='hui-dialog-edit-card');
        const card=dialog&&deep(dialog.shadowRoot).find(element=>element.localName==='salah-timetable-card');
        if(!card?.shadowRoot||card._config[${safeJsLiteral(key)}]!==${value})return false;
        const root=card.shadowRoot;
        const nodes={
          show_hijri_date:root.querySelector('.hijri'),
          show_gregorian_date:root.querySelector('.gregorian'),
          show_salah_countdown:root.querySelector('[data-panel="salah"]'),
          show_jamaat_countdown:root.querySelector('[data-panel="jamaat"]'),
          show_ramadan_details:root.querySelector('.ramadan'),
          show_sehri_countdown:root.querySelector('[data-ramadan="sehri"] .count'),
          show_iftar_countdown:root.querySelector('[data-ramadan="iftar"] .count'),
          show_timezone_note:root.querySelector('[data-role="timezone-note"]')
        };
        return Boolean(nodes[${safeJsLiteral(key)}]?.getClientRects().length)===${value};
      `), `Editor option did not change preview visibility: ${key}=${value}`);
    }
    await until(expression("const dialog=deep().find(element=>element.localName==='hui-dialog-edit-card');const save=dialog&&deep(dialog.shadowRoot).find(element=>element.localName==='ha-button'&&element.getAttribute('slot')==='primaryAction');if(!save)return false;save.click();return true"), "Real card editor Save button missing");
    await until(expression("return deep().filter(element=>element.localName==='salah-timetable-card').some(card=>card.shadowRoot.textContent.includes('Keyboard smoke title'))"), "Saved edited card did not appear on dashboard");
    await call("Page.reload", {ignoreCache: true});
    await until(expression("return deep().filter(element=>element.localName==='salah-timetable-card').some(card=>card.shadowRoot?.textContent.includes('Keyboard smoke title'))"), "Saved card missing after page reload");
    const restored = await evaluate(expression("const card=deep().find(element=>element.localName==='salah-timetable-card'&&element._config?.title==='Keyboard smoke title');return card?{config:card._config,panels:card.shadowRoot.querySelectorAll('.panel:not(.hijri-month-info)').length,monthSubtitle:!!card.shadowRoot.querySelector('header .month-description'),duplicateMonthPanel:!!card.shadowRoot.querySelector('.hijri-month-info'),compact:!!card.shadowRoot.querySelector('.content.compact'),hijri:card.shadowRoot.querySelector('.hijri')?.textContent,gregorian:!!card.shadowRoot.querySelector('.gregorian'),data:{prayers:card._hass.states[card._config.entity].attributes.prayers,active:card._hass.states[card._config.entity].attributes.ramadan.active},times:[...card.shadowRoot.querySelectorAll('tbody td')].map(cell=>cell.textContent)}:null"));
    for (const [key, value] of Object.entries(selected)) assert.equal(restored.config[key], value, `Saved option did not survive reload: ${key}`);
    assert.deepEqual(restored.data, originalData, "Display controls changed prayer data or Ramadan activation");
    assert.equal(restored.panels, 1); assert.equal(restored.monthSubtitle, true); assert.equal(restored.duplicateMonthPanel, false); assert.equal(restored.compact, false); assert.equal(restored.gregorian, false);
    assert.match(restored.hijri, /هجري \(محسوب\)/);
    assert.ok(restored.times.some(value => /(?:am|pm|ص|م)\s*$/i.test(value)), "Reloaded card does not use 12-hour times");
    await evaluate(expression("window.salahAutoCard=deep().find(element=>element.localName==='salah-timetable-card'&&element._config?.entity&&element._config.title!=='Keyboard smoke title');if(!window.salahAutoCard)throw new Error('Original smoke card missing');window.salahAutoCard.setConfig({...window.salahAutoCard._config,language:'auto'});return true"));
    // The live smoke owns an ephemeral HA instance and temporary browser profile.
    // HA2026.10 uses a language string as event detail and saves user preferences.
    // Exercise that normal UI event in this disposable instance, then restore it.
    for (const language of ["en", "ar", "en"]) {
      await evaluate(`document.querySelector('home-assistant').dispatchEvent(new CustomEvent('hass-language-select',{detail:${JSON.stringify(language)},bubbles:true,composed:true}))`);
      await until(`document.querySelector('home-assistant').hass.locale.language.startsWith(${JSON.stringify(language)})&&window.salahAutoCard.getAttribute('lang')===${JSON.stringify(language)}`, `Automatic language did not follow real HA locale: ${language}`);
      for (const bilingual of [false, true]) {
        await evaluate(`window.salahAutoCard.setConfig({...window.salahAutoCard._config,bilingual_prayer_labels:${bilingual}})`);
        assert.equal(await evaluate(`(()=>{const root=window.salahAutoCard.shadowRoot;const labels=[...root.querySelectorAll('tbody th .prayer-labels')];return labels.length>0&&labels.every(label=>label.querySelectorAll('bdi').length===${bilingual ? 2 : 1})&&root.querySelector('thead th').textContent===${safeJsLiteral(language === "ar" ? "الصلاة" : "Prayer")}&&window.salahAutoCard.getAttribute('dir')===${safeJsLiteral(language === "ar" ? "rtl" : "ltr")}})()`), true, `Automatic-language labels did not update: ${language}/${bilingual}`);
        for (const width of [320, 360, 400, 900]) {
          await call("Emulation.setDeviceMetricsOverride", {width, height: 1100, deviceScaleFactor: 1, mobile: width === 360});
          await evaluate("document.documentElement.style.fontSize='200%'"); await pause(100);
          assert.equal(await evaluate(`(()=>{const card=window.salahAutoCard;const root=card.shadowRoot;const content=root.querySelector('.content');const region=root.querySelector('.table-scroll');const overflow=region.scrollWidth>region.clientWidth+1;region.scrollLeft=${language === "ar" ? -50 : 50};return content.scrollWidth<=content.clientWidth+1&&card.getBoundingClientRect().left>=-1&&card.getBoundingClientRect().right<=innerWidth+1&&(!overflow||${language === "ar" ? "region.scrollLeft<0" : "region.scrollLeft>0"})&&[...root.querySelectorAll('tbody td,.count,.absolute')].every(element=>element.querySelector('bdi[dir="ltr"]'))})()`), true, `Real HA ${language}/${bilingual} card overflows or loses LTR time isolation at ${width}px/200%`);
          await evaluate("document.documentElement.style.fontSize=''");
          if (output) { await mkdir(output, {recursive: true}); const image = await call("Page.captureScreenshot", {format: "png"}); await writeFile(join(output, `ha-${language}${bilingual ? "-bilingual" : ""}-${width}.png`), Buffer.from(image.data, "base64")); }
        }
      }
    }
    console.log("Real card picker, all graphical options, language/bilingual reload, Arabic/English HA locale, keyboard focus, themes and 200% text passed");
    return {viewports: [320, 360, 400, 900], languages: ["en", "ar"], bilingual_modes: [false, true], automatic_locale: ["en", "ar", "en"], configuration_reload: true, picker: true, editor: true, keyboard: true, themes: ["light", "dark"], root_text_scale: "200%"};
  } finally {
    if (originalLocale && socket?.readyState === WebSocket.OPEN) {
      await evaluate(`document.documentElement.style.fontSize='';document.querySelector('home-assistant')?.dispatchEvent(new CustomEvent('hass-language-select',{detail:${JSON.stringify(originalLocale.language)},bubbles:true,composed:true}))`).catch(() => {});
    }
    clearTimeout(deadline); signal.removeEventListener("abort", stop); socket?.close(); stop();
    await pause(100); await rm(profile, {recursive: true, force: true});
  }
}
