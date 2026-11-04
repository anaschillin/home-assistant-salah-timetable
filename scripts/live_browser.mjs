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
    assert.equal(await evaluate(expression(`const card=${findCard};return ![...card.shadowRoot.querySelectorAll('button')].some(item=>item.textContent==='Prayer reminders')`)), true, "Prayer reminders must be configured through the editor");
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
    // HA's footer-style desktop/tablet card editor can leave preview=false.
    // The custom card must recognise its edit wrapper and drop the photo
    // minimum regardless, otherwise HA's native Edit button sits below view.
    await until(expression(`const card=${findCard};return Boolean(card?.shadowRoot?.querySelector("ha-card"))`),
      "Real HA edit dashboard did not render its existing card");
    for (const width of [900, 1280]) {
      await call("Emulation.setDeviceMetricsOverride", {width, height: 900, deviceScaleFactor: 1, mobile: false});
      assert.equal(await evaluate(expression(`
        const card=${findCard};
        const wrapper=card?.closest?.("hui-card-options, hui-card-edit-mode");
        const surface=card?.shadowRoot?.querySelector("ha-card");
        if(!card||!surface)return false;
        const wasPreview=card.preview;
        // Exercise the actual wrapper even where this HA version passes preview.
        card.preview=false;
        const shortened=wrapper ?
          card.hasAttribute("dashboard-editing") &&
          getComputedStyle(surface).minHeight==="0px" : true;
        card.preview=wasPreview;
        return shortened;
      `)), true, `Real HA ${width}px card editor did not reduce canvas inside its edit wrapper`);
    }
    await call("Emulation.setDeviceMetricsOverride", {width: 900, height: 1100, deviceScaleFactor: 1, mobile: false});
    await until(expression("const button=deep().find(element=>element.localName==='ha-button'&&element.textContent.trim().toLowerCase()==='add card');if(!button)return false;button.click();return true"), "Real dashboard Add card button missing");
    await until(expression("const dialog=deep().find(element=>element.localName==='hui-dialog-create-card');const tab=dialog&&deep(dialog.shadowRoot).find(element=>element.localName==='ha-tab-group-tab'&&element.getAttribute('panel')==='card');if(!tab)return false;tab.click();return true"), "Real card picker tab missing");
    await until(expression("const picker=deep().find(element=>element.localName==='hui-card-picker');const option=picker&&deep(picker.shadowRoot).find(element=>element.classList.contains('overlay')&&element.config?.type==='custom:salah-timetable-card');if(!option)return false;option.click();return true"), "Salah Timetable missing from actual custom-card picker");
    await until(expression("const dialog=deep().find(element=>element.localName==='hui-dialog-edit-card');const editor=dialog&&deep(dialog.shadowRoot).find(element=>element.localName==='salah-timetable-card-editor');if(!editor?.shadowRoot?.querySelector('[data-option=detail_level]'))return false;window.salahEditor=editor;return true"), "Actual card editor controls did not render");
    assert.equal(await evaluate(`!window.salahEditor.shadowRoot.querySelector('input[type="text"], ha-textfield')`), true, "Graphical editor exposes a title field");
    await until("window.salahEditor.shadowRoot.querySelector('.reminder-setup')?.hidden===false", "Administrator editor is missing Prayer reminders");
    await setEditorOption("kiosk_mode", true);
    assert.equal(await evaluate("window.salahEditor.shadowRoot.querySelector('.reminder-setup').hidden"), true, "Kiosk editor must hide reminder setup");
    await setEditorOption("kiosk_mode", false);
    assert.equal(await evaluate("(()=>{const button=window.salahEditor.shadowRoot.querySelector('.reminder-setup');if(!button||button.hidden)return false;button.focus();button.click();return true})()"), true, "Administrator editor could not launch Prayer reminders");
    await until(expression("const wizard=deep().find(element=>element.localName==='salah-reminder-wizard');return wizard?.shadowRoot.querySelector('dialog')?.matches(':modal')&&['mosques','prayers'].includes(wizard._step)"), "Prayer reminder setup did not load from the installed integration");
    assert.equal(await evaluate(expression("const wizard=deep().find(element=>element.localName==='salah-reminder-wizard');const cancel=[...wizard.shadowRoot.querySelectorAll('button')].find(item=>item.textContent==='Cancel');if(!cancel)return false;cancel.click();return !wizard.isConnected")), true, "Prayer reminder setup did not close cleanly");
    assert.equal(await evaluate("window.salahEditor.shadowRoot.activeElement===window.salahEditor.shadowRoot.querySelector('.reminder-setup')"), true, "Closing reminders lost editor launch focus");
    console.log("Real HA administrator editor exposes Prayer reminders and loads its wizard");
    const detailSelector = "window.salahEditor.shadowRoot.querySelector('[data-option=detail_level]')";
    await evaluate(`${detailSelector}.focus()`);
    await setEditorOption("detail_level", "detailed");
    assert.equal(await evaluate(`window.salahEditor.shadowRoot.activeElement===${detailSelector}`), true, "Configuration echo lost keyboard focus");
    await call("Input.dispatchKeyEvent", {type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9});
    await call("Input.dispatchKeyEvent", {type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9});
    assert.equal(await evaluate(`window.salahEditor.shadowRoot.activeElement===${detailSelector}`), false, "Tab did not leave detail selector");
    const originalData = await evaluate(expression("const card=deep().find(element=>element.localName==='salah-timetable-card'&&element._config?.entity);const data=card._hass.states[card._config.entity].attributes;return {date:data.date,prayers:data.prayers,active:data.ramadan.active}"));
    assert.equal(originalData.active, true, "Smoke setup needs Ramadan active on the approved date");
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
    const editedCard = "deep().find(element=>element.localName==='salah-timetable-card'&&element._config?.hijri_adjustment===2)";
    await until(expression(`return Boolean(${editedCard})`), "Saved edited card did not appear on dashboard");
    await call("Page.reload", {ignoreCache: true});
    await until(expression(`const card=${editedCard};return Boolean(card?.shadowRoot?.querySelector('tbody'))`), "Saved card missing after page reload");
    const restored = await evaluate(expression(`const card=${editedCard};return {config:card._config,panels:card.shadowRoot.querySelectorAll('.panel:not(.hijri-month-info)').length,monthSubtitle:!!card.shadowRoot.querySelector('header .month-description'),duplicateMonthPanel:!!card.shadowRoot.querySelector('.hijri-month-info'),compact:!!card.shadowRoot.querySelector('.content.compact'),hijri:card.shadowRoot.querySelector('.hijri')?.textContent,gregorian:!!card.shadowRoot.querySelector('.gregorian'),data:{date:card._hass.states[card._config.entity].attributes.date,prayers:card._hass.states[card._config.entity].attributes.prayers,active:card._hass.states[card._config.entity].attributes.ramadan.active},times:[...card.shadowRoot.querySelectorAll('tbody td')].map(cell=>cell.textContent)}`));
    for (const [key, value] of Object.entries(selected)) assert.equal(restored.config[key], value, `Saved option did not survive reload: ${key}`);
    // A genuine UTC midnight rollover changes approved prayer timestamps;
    // only compare byte-for-byte while both snapshots refer to the same day.
    if (restored.data.date === originalData.date) {
      assert.deepEqual(restored.data, originalData, "Display controls changed prayer data or Ramadan activation");
    } else {
      const nextDay = new Date(Date.parse(`${originalData.date}T12:00:00Z`) + 86400000).toISOString().slice(0, 10);
      assert.equal(restored.data.date, nextDay, "Only a one-day rollover may change the smoke data");
      assert.equal(restored.data.active, true, "Ramadan fixture must remain active over midnight");
      assert.equal(restored.data.prayers?.length, originalData.prayers?.length, "Approved prayer fields disappeared during rollover");
    }
    assert.equal(restored.panels, 1); assert.equal(restored.monthSubtitle, true); assert.equal(restored.duplicateMonthPanel, false); assert.equal(restored.compact, false); assert.equal(restored.gregorian, false);
    assert.match(restored.hijri, /هجري \(محسوب\)/);
    assert.ok(restored.times.some(value => /(?:am|pm|ص|م)\s*$/i.test(value)), "Reloaded card does not use 12-hour times");
    await evaluate(expression(`const saved=${editedCard};window.salahAutoCard=deep().find(element=>element.localName==='salah-timetable-card'&&element._config?.entity&&element!==saved);if(!window.salahAutoCard)throw new Error('Original smoke card missing');window.salahAutoCard.setConfig({...window.salahAutoCard._config,language:'auto'});return true`));
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
    // PR #88 regression: real landscape tablet / desktop once put the long
    // month description on the same line as the Gregorian date.
    for (const width of [900, 1280, 1536]) {
      await call("Emulation.setDeviceMetricsOverride", {width, height: 1100, deviceScaleFactor: 1, mobile: false});
      await pause(100);
      assert.equal(await evaluate(`(()=>{
        const card=window.salahAutoCard, root=card.shadowRoot;
        const header=root.querySelector(".header"), hijri=root.querySelector(".hijri");
        const gregorian=root.querySelector(".gregorian"), month=root.querySelector(".month-description");
        if(!header||!hijri||!gregorian||!month) return false;
        const h=header.getBoundingClientRect(), d=month.getBoundingClientRect();
        const canvas=root.querySelector("ha-card"), content=root.querySelector(".content");
        const hostWidth=card.getBoundingClientRect().width;
        return getComputedStyle(header).display==="grid" &&
          d.top>=Math.max(hijri.getBoundingClientRect().bottom,gregorian.getBoundingClientRect().bottom)-1 &&
          d.width>=h.width-1 &&
          getComputedStyle(canvas).maxWidth==="none" &&
          Math.abs(canvas.getBoundingClientRect().width-hostWidth)<=2 &&
          getComputedStyle(content).maxWidth==="1160px" &&
          content.getBoundingClientRect().width<=1161 &&
          Math.abs(content.getBoundingClientRect().left+content.getBoundingClientRect().right-
            canvas.getBoundingClientRect().left-canvas.getBoundingClientRect().right)<=2 &&
          header.scrollWidth<=header.clientWidth+1;
      })()`), true, `Real HA header description shares date row or overflows at ${width}px`);
    }
    // Home Assistant keeps the dashboard in edit mode after saving a card.
    // First confirm that preview intentionally removes the full-height canvas,
    // so the native card Edit controls remain reachable without scrolling.
    await evaluate("window.salahAutoCard.setConfig({...window.salahAutoCard._config,show_mosque_background:true})");
    assert.equal(await evaluate(`(()=>{
      const card=window.salahAutoCard;
      const surface=card.shadowRoot.querySelector("ha-card");
      return card.preview === true &&
        card.hasAttribute("dashboard-editing") &&
        surface.classList.contains("has-mosque-background") &&
        getComputedStyle(surface).minHeight === "0px";
    })()`), true, "Real HA dashboard editing did not reduce the full-height photo canvas");
    // Leave edit mode through the real Home Assistant toolbar, rather than
    // forcing the custom card's preview property. Only then assert that
    // Yesterday/Tomorrow retain the full-viewport photo in normal viewing.
    await until(expression(`
      const exit=deep().find(element=>element.localName==="ha-button" &&
        element.classList.contains("exit-edit-mode"));
      if(!exit)return false;
      exit.click();
      return true;
    `), "Real HA dashboard exit-edit control missing");
    await until(expression(`
      const saved=window.salahAutoCard;
      const card=saved.isConnected ? saved : deep().find(element=>
        element.localName==="salah-timetable-card" &&
        element._config?.entity && element._config?.hijri_adjustment!==2);
      if(!card?.shadowRoot)return false;
      window.salahAutoCard=card;
      const surface=card.shadowRoot.querySelector("ha-card");
      return card.preview === false &&
        !card.hasAttribute("dashboard-editing") &&
        surface?.classList.contains("has-mosque-background") &&
        parseFloat(getComputedStyle(surface).minHeight)>0;
    `), "Real HA dashboard exit did not restore the full-height photo canvas");
    // The background minimum follows the real card position and the visible
    // screen at phone/tablet/desktop sizes; long content is never capped.
    for (const [width, height] of [[360, 780], [900, 760], [1280, 850], [360, 320]]) {
      await call("Emulation.setDeviceMetricsOverride", {
        width, height, deviceScaleFactor: 1, mobile: width === 360
      });
      await evaluate("window.scrollTo(0,0)");
      await until(expression(`
        const card=window.salahAutoCard, surface=card?.shadowRoot?.querySelector("ha-card");
        if (!surface)return false;
        const visual=window.visualViewport;
        const bottom=visual?.height ? visual.height+(visual.offsetTop||0) : innerHeight;
        const expected=Math.max(0,Math.floor(bottom-Math.max(0,card.getBoundingClientRect().top)-12));
        return Math.abs(parseFloat(getComputedStyle(surface).minHeight)-expected)<=1 &&
          surface.getBoundingClientRect().height>=expected-1 &&
          !card.hasAttribute("dashboard-editing");
      `), `Photo background did not fit available viewport at ${width}x${height}`);
      if (height === 320) {
        assert.equal(await evaluate(expression(`
          const card=window.salahAutoCard, surface=card.shadowRoot.querySelector("ha-card");
          return surface.getBoundingClientRect().height>
            parseFloat(getComputedStyle(surface).minHeight)+10;
        `)), true, "Long timetable content must extend beyond the small viewport");
      }
    }
    await call("Emulation.setDeviceMetricsOverride", {width: 900, height: 1100, deviceScaleFactor: 1, mobile: false});
    // The full-bleed photograph should reach the dashboard viewport bottom
    // even when Yesterday/Tomorrow omit both live countdowns. The timetable
    // itself stays compact at the top; only the photo canvas fills the view.
    assert.equal(await evaluate(`(()=>{
      const card=window.salahAutoCard;
      card.setConfig({...card._config,show_mosque_background:true,show_salah_countdown:true,show_jamaat_countdown:true});
      card._selectedDay=0;card._render();
      const today=card.shadowRoot.querySelector("ha-card");
      const todayPhoto=getComputedStyle(today,"::before");
      const before={width:parseFloat(todayPhoto.width),height:parseFloat(todayPhoto.height)};
      let ok=true;
      for(const index of [0,2,1]){
        card.shadowRoot.querySelectorAll(".date-tab")[index].click();
        const next=card.shadowRoot.querySelector("ha-card");
        const min=parseFloat(getComputedStyle(next).minHeight);
        const img=getComputedStyle(next,"::before");
        const table=next.querySelector(".timetable-shell").getBoundingClientRect();
        ok &&= min>0 && next.getBoundingClientRect().height>=min-1 &&
          Math.abs(parseFloat(img.width)-before.width)<2 &&
          Math.abs(parseFloat(img.height)-before.height)<2 &&
          table.bottom<=next.getBoundingClientRect().bottom+1 &&
          (index===1||!next.querySelector(".prayer-panel"));
      }
      return ok && card._selectedDay===0;
    })()`),true,"Real HA photo canvas cropped below short Yesterday/Tomorrow contents");
    // Real Home Assistant cards can change width slightly as the dashboard's
    // vertical scrollbar appears/disappears between Today and adjacent days.
    // Assert that neither pseudo-image layer scales in that situation.
    assert.equal(await evaluate(`(()=>{
      const card=window.salahAutoCard;
      card.setConfig({...card._config,show_mosque_background:true,show_salah_countdown:true,show_jamaat_countdown:true});
      card._selectedDay=0;
      card._render();
      const originalCanvas=card.shadowRoot.querySelector("ha-card");
      const baseImage=getComputedStyle(originalCanvas,"::before");
      const before={height:parseFloat(baseImage.height),width:parseFloat(baseImage.width)};
      const hostWidth=card.getBoundingClientRect().width;
      if(!Number.isFinite(before.width)||!Number.isFinite(before.height)||!hostWidth)return false;
      card.shadowRoot.querySelectorAll(".date-tab")[0].click();
      const yesterday=card.shadowRoot.querySelector("ha-card");
      const photoFrame=yesterday.style.getPropertyValue("--mosque-photo-frame-width");
      card.style.width=(hostWidth-12)+"px";
      card.shadowRoot.querySelectorAll(".date-tab")[2].click();
      const tomorrow=card.shadowRoot.querySelector("ha-card");
      const resizedImage=getComputedStyle(tomorrow,"::before");
      const retained=Boolean(photoFrame) &&
        tomorrow.style.getPropertyValue("--mosque-photo-frame-width")===photoFrame &&
        Math.abs(parseFloat(resizedImage.height)-before.height)<2 &&
        Math.abs(parseFloat(resizedImage.width)-before.width)<2;
      card.style.width="";
      card.shadowRoot.querySelectorAll(".date-tab")[1].click();
      return retained && card._selectedDay===0;
    })()`),true,"Real HA day navigation changed mosque photo crop after a scrollbar-sized width change");
    console.log("Real card picker, all graphical options, language/bilingual reload, Arabic/English HA locale, keyboard focus, themes and 200% text passed");
    return {viewports: [320, 360, 400, 900], languages: ["en", "ar"], bilingual_modes: [false, true], automatic_locale: ["en", "ar", "en"], configuration_reload: true, prayer_reminders: true, picker: true, editor: true, keyboard: true, themes: ["light", "dark"], root_text_scale: "200%"};
  } finally {
    if (originalLocale && socket?.readyState === WebSocket.OPEN) {
      await evaluate(`document.documentElement.style.fontSize='';document.querySelector('home-assistant')?.dispatchEvent(new CustomEvent('hass-language-select',{detail:${JSON.stringify(originalLocale.language)},bubbles:true,composed:true}))`).catch(() => {});
    }
    clearTimeout(deadline); signal.removeEventListener("abort", stop); socket?.close(); stop();
    await pause(100); await rm(profile, {recursive: true, force: true});
  }
}
