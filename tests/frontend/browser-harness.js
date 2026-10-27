/** Real-browser fixture: native shadow DOM/CSS with small HA control stand-ins. */
import {SalahTimetableCard, SalahTimetableCardEditor} from "/custom_components/salah_timetable/frontend/salah-timetable-card.js?v=0.9.3";
import {resolveUi, tr} from "/custom_components/salah_timetable/frontend/card-i18n.js?v=0.9.3";

class Selector extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode: "open"}); this.select = document.createElement("select"); this.shadowRoot.append(this.select);
    this.select.addEventListener("change", () => this.dispatchEvent(new CustomEvent("value-changed", {detail: {value: this.value}, bubbles: true, composed: true})));
  }
  set hass(value) { this._hass = value; this._options(); }
  set selector(value) { this._selector = value; this._options(); }
  get value() { return this.select.value; }
  set value(value) { this._value = value; this.select.value = value; }
  _options() {
    const options = this._selector?.select?.options || (this._selector?.entity ? Object.keys(this._hass?.states || {}).map(value => ({value, label: value})) : []);
    this.select.replaceChildren(...options.map(value => { const option = document.createElement("option"); option.value = value.value; option.textContent = value.label; return option; }));
    this.select.value = this._value || "";
  }
}
if (!customElements.get("ha-selector")) customElements.define("ha-selector", Selector);

const query = new URLSearchParams(location.search);
const language = query.get("language") === "ar" ? "ar" : "en";
const bilingual = query.get("bilingual") === "true";
const width = window.innerWidth;
const checks = [];
function check(name, assertion) { if (!assertion) throw new Error(name); checks.push(name); }
function visibility(card) {
  const root = card.shadowRoot;
  const nodes = {
    show_hijri_date: root.querySelector(".hijri"),
    show_gregorian_date: root.querySelector(".gregorian"),
    show_salah_countdown: root.querySelector('[data-panel="salah"]'),
    show_jamaat_countdown: root.querySelector('[data-panel="jamaat"]'),
    show_ramadan_details: root.querySelector(".ramadan"),
    show_sehri_countdown: root.querySelector('[data-ramadan="sehri"] .count'),
    show_iftar_countdown: root.querySelector('[data-ramadan="iftar"] .count'),
    show_timezone_note: root.querySelector('[data-role="timezone-note"]'),
  };
  return Object.fromEntries(Object.entries(nodes).map(([key, node]) => [key, Boolean(node?.getClientRects().length)]));
}
function fits(card) {
  const root = card.shadowRoot;
  return card.getBoundingClientRect().width <= width + 1 && document.documentElement.scrollWidth <= width + 1 &&
    [".content", ".header", ".panels", ".ramadan", ".ramadan-grid", "h2", ".panel"].every(selector => [...root.querySelectorAll(selector)].every(element => element.scrollWidth <= element.clientWidth + 1));
}
const time = (hour, minute = 0) => `2026-10-21T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00Z`;
const event = (timestamp, prayer) => ({timestamp, prayer, field: `${prayer}_jamaat`});
const prayers = [
  {key: "fajr", name: "Fajr", begin: time(4, 45), end: time(6, 30), jamaat: [time(5, 15)]},
  {key: "dhuhr", name: "Dhuhr", begin: time(11), jamaat: [time(11, 30)]},
  {key: "asr", name: "Asr", begin: time(14), jamaat: [time(14, 30)]},
  {key: "maghrib", name: "Maghrib", begin: time(16, 30), jamaat: [time(16, 33)]},
  {key: "isha", name: "Isha", begin: time(18), jamaat: [time(18, 30)]},
];
const data = {
  mosque_name: "Example Mosque", date: "2026-10-21", time_zone: "Europe/London", prayers, show_hijri_date: true,
  next_salah: {timestamp: time(4, 45), prayer: "fajr", field: "fajr_begin"},
  next_jamaat: event(time(5, 15), "fajr"), previous_jamaat: event("2026-10-20T18:30:00Z", "isha"), context_mode: "previous",
  beginning_events: prayers.map(prayer => ({timestamp: prayer.begin, prayer: prayer.key, field: `${prayer.key}_begin`})),
  jamaat_events: prayers.flatMap(prayer => prayer.jamaat.map(timestamp => event(timestamp, prayer.key))),
  ramadan: {active: true, sehri: time(4, 40), iftar: time(16, 30), taraweeh: null, taraweeh_text: "After Isha Jamaat"},
};
let serviceCalls = 0;
const hass = {states: {"sensor.example_prayer_timetable": {state: data.date, attributes: data}}, locale: {language: "en-GB"}, config: {time_zone: data.time_zone}, connection: {connected: true}, callService() { serviceCalls++; }};
const config = {entity: "sensor.example_prayer_timetable", detail_level: "detailed", language, bilingual_prayer_labels: bilingual};
const ui = resolveUi(config, hass);
const digits = value => new Intl.NumberFormat(ui.locale, {useGrouping: false, minimumIntegerDigits: 2}).format(value);
const zero = `${digits(0)}:${digits(0)}:${digits(0)}`;

try {
  const card = new SalahTimetableCard();
  const render = (patch = {}, now = time(4, 40)) => { card.setConfig({...config, ...patch}); card._render(Date.parse(now)); };
  card.setConfig(config); card.hass = hass; document.body.append(card); card._render(Date.parse(time(4, 40)));
  check("shadow DOM renders five prayer rows", card.shadowRoot.querySelectorAll("tbody tr").length === 5);
  const rules = card.shadowRoot.querySelector("style")?.sheet?.cssRules;
  check("bundled CSS module loads responsive rules", Boolean(rules?.length) && [...rules].some(rule => /max-width\s*:\s*28rem/.test(rule.conditionText || "")));
  const panelStyle = getComputedStyle(card.shadowRoot.querySelector(".panel"));
  const gridStyle = getComputedStyle(card.shadowRoot.querySelector(".panels"));
  check("theme panel layout and border radius survive CSS refactoring", panelStyle.display === "flex" && panelStyle.borderRadius === "16px" && gridStyle.display === "grid");
  check("container layout uses one column on mobile and two on tablet", gridStyle.gridTemplateColumns.split(" ").length === (width <= 400 ? 1 : 2));
  check("card language and direction match configuration", card.getAttribute("lang") === language && card.getAttribute("dir") === ui.dir);
  check("mosque timezone used for absolute times", card.shadowRoot.querySelector('[data-panel="salah"] .absolute').textContent === `${digits(5)}:${digits(45)}`);
  check("local beginning countdown", card.shadowRoot.querySelector('[data-panel="salah"] .count').textContent === `${digits(0)}:${digits(5)}:${digits(0)}`);
  check("Ramadan has textual Taraweeh fallback", card.shadowRoot.textContent.includes("After Isha Jamaat"));
  check("published Fajr end remains visible", card.shadowRoot.querySelector(".fajr-end bdi")?.textContent === `${digits(7)}:${digits(30)}`);
  const labelLanguages = [...card.shadowRoot.querySelectorAll("tbody th .prayer-labels")].map(label => [...label.querySelectorAll("bdi")].map(value => value.getAttribute("lang")));
  const expectedLanguages = bilingual ? [language, language === "en" ? "ar" : "en"] : [language];
  check("prayer labels use the selected languages", labelLanguages.length === 5 && labelLanguages.every(languages => JSON.stringify(languages) === JSON.stringify(expectedLanguages)));
  const numericNodes = [...card.shadowRoot.querySelectorAll("tbody td, .count, .absolute, [data-ramadan] .event")];
  check("numeric times use LTR isolation", numericNodes.length > 0 && numericNodes.every(element => element.querySelector('bdi[dir="ltr"]')) && [...card.shadowRoot.querySelectorAll('bdi[dir="ltr"]')].every(element => getComputedStyle(element).direction === "ltr"));
  card._render(Date.parse(time(4, 50)));
  check("pending Fajr Jamaat replaces the previous congregation", card.shadowRoot.querySelector('[data-panel="jamaat"] .label').textContent === tr(ui, "panel.next_jamaat"));
  check("upcoming Jamaat shows its countdown", card.shadowRoot.querySelector('[data-panel="jamaat"] .count')?.textContent === `${digits(0)}:${digits(25)}:${digits(0)}`);
  card._render(Date.parse(time(5, 15)));
  check("exact Jamaat becomes previous event", card.shadowRoot.querySelector('[data-panel="jamaat"] .label').textContent === tr(ui, "panel.previous_jamaat"));
  check("previous Jamaat displays published times", Boolean(card.shadowRoot.querySelector('[data-panel="jamaat"] .prayer-times bdi')));
  check("previous Jamaat shows live elapsed time", card.shadowRoot.querySelector('[data-panel="jamaat"] .count')?.textContent.includes(tr(ui, "status.elapsed").split("{time}")[0]) && card.shadowRoot.querySelector('[data-panel="jamaat"] .count')?.textContent.includes(":"));
  render({title: '<img src="x" onerror="window.injected=true">'});
  check("title uses literal text rather than executable markup", card.shadowRoot.querySelector("h2").textContent.startsWith("<img") && !card.shadowRoot.querySelector("img") && !window.injected);
  render({title: "مسجد الرحمة · Long mixed mosque title ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 · المسجد الكبير"});
  check("long mixed-direction title fits without overflow", fits(card) && card.shadowRoot.querySelector("h2").getAttribute("dir") === "auto");
  render();
  check("Gregorian and calculated Hijri dates are visible", card.shadowRoot.querySelector(".gregorian")?.textContent && card.shadowRoot.querySelector(".hijri")?.textContent.includes(tr(ui, "card.hijri_calculated")));
  check("Hijri date appears before the independent Gregorian date", card.shadowRoot.querySelector("header").children[1] === card.shadowRoot.querySelector(".hijri") && card.shadowRoot.querySelector("header").children[2] === card.shadowRoot.querySelector(".gregorian"));
  render({show_gregorian_date: false});
  check("Gregorian can be hidden while Hijri remains visible", !card.shadowRoot.querySelector(".gregorian") && Boolean(card.shadowRoot.querySelector(".hijri")));
  render({show_hijri_date: false});
  check("Hijri can be hidden while Gregorian remains visible", !card.shadowRoot.querySelector(".hijri") && Boolean(card.shadowRoot.querySelector(".gregorian")));
  render();
  card.hass = {...hass, states: {...hass.states, [config.entity]: {state: data.date, attributes: {...data, show_hijri_date: false}}}};
  check("mosque-configured Hijri visibility remains authoritative", !card.shadowRoot.querySelector(".hijri") && Boolean(card.shadowRoot.querySelector(".gregorian")));
  card.hass = {...hass, states: {...hass.states, [config.entity]: {state: "2026-10-23", attributes: {...data, date: "2026-10-23", second_khutbah: "2026-10-23T12:20:00Z"}}}};
  check("Friday published second Khutbah remains isolated", Boolean(card.shadowRoot.querySelector('.khutbah bdi[dir="ltr"]')));
  card.hass = hass; card._render(Date.parse(time(4, 40)));
  check("upcoming row has accessible emphasis", card.shadowRoot.querySelector("tbody tr").getAttribute("aria-current") === "true");
  render({}, time(8));
  check("previous Jamaat follows completed Fajr", card.shadowRoot.querySelector('[data-panel="jamaat"] .label').textContent === tr(ui, "panel.previous_jamaat"));
  check("Next Salah countdown and Previous Jamaat elapsed clock are both visible", card.shadowRoot.querySelectorAll(".prayer-panel .count").length === 2 && Boolean(card.shadowRoot.querySelector('[data-panel="jamaat"] .count')));
  render({detail_level: "standard", time_format: "12h", show_salah_countdown: false});
  check("single visible panel fills width", card.shadowRoot.querySelectorAll(".prayer-panel").length === 1 && Boolean(card.shadowRoot.querySelector(".hijri-month-info")));
  check("12-hour absolute times", /(?:am|pm|ص|م)\s*$/i.test(card.shadowRoot.querySelector("tbody td > bdi").textContent));
  render({}, time(4, 41));
  const scrollRegion = card.shadowRoot.querySelector(".table-scroll"); scrollRegion.focus();
  const stableTable = card.shadowRoot.querySelector("table");
  const prayerCell = stableTable.querySelector("tbody th");
  const range = document.createRange(); range.selectNodeContents(prayerCell);
  const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
  const selectedText = selection.toString();
  card._tick(Date.parse(time(4, 41)) + 1000);
  check("ordinary ticks retain table nodes and text selection", card.shadowRoot.querySelector("table") === stableTable && selection.toString() === selectedText);
  selection.removeAllRanges();
  check("countdown tick preserves table keyboard focus", card.shadowRoot.activeElement === card.shadowRoot.querySelector(".table-scroll"));
  check("card fits its viewport", fits(card));
  document.documentElement.style.fontSize = "200%";
  const fitsScaledText = card.getBoundingClientRect().width <= width + 1 && document.documentElement.scrollWidth <= width + 1 && card.shadowRoot.querySelector(".content").clientWidth > 0 && [...card.shadowRoot.querySelectorAll(".panel, h2")].every(element => element.getBoundingClientRect().width <= card.shadowRoot.querySelector(".content").clientWidth + 1);
  const scaledRegion = card.shadowRoot.querySelector(".table-scroll");
  const overflowing = scaledRegion.scrollWidth > scaledRegion.clientWidth + 1;
  check("overflow has visible scrolling guidance", !overflowing || getComputedStyle(card.shadowRoot.querySelector(".scroll-help")).display !== "none");
  scaledRegion.scrollLeft = ui.dir === "rtl" ? -50 : 50;
  check("overflow region can scroll without widening the card", !overflowing || Math.abs(scaledRegion.scrollLeft) > 0);
  check("RTL overflow uses Chromium negative scrollLeft", ui.dir !== "rtl" || !overflowing || scaledRegion.scrollLeft < 0);
  const savedScroll = scaledRegion.scrollLeft;
  card._tick(Date.parse(time(4, 41)) + 2000);
  check("countdown tick preserves horizontal scroll position", scaledRegion.scrollLeft === savedScroll);
  document.documentElement.style.fontSize = "";
  check("card contains 200% text without overflowing", fitsScaledText);
  const columns = getComputedStyle(card.shadowRoot.querySelector(".ramadan-grid")).gridTemplateColumns.split(" ").length;
  check("responsive Ramadan grid", columns === (width <= 420 ? 2 : 3));
  document.documentElement.style.setProperty("--primary-text-color", "rgb(250, 250, 250)");
  check("dark theme follows HA variables", getComputedStyle(card).color === "rgb(250, 250, 250)");
  document.documentElement.style.setProperty("--primary-text-color", "rgb(20, 20, 20)");
  check("light theme follows HA variables", getComputedStyle(card).color === "rgb(20, 20, 20)");

  const editor = new SalahTimetableCardEditor(); editor.setConfig(config); editor.hass = hass; document.body.append(editor);
  let lastConfig;
  editor.addEventListener("config-changed", event => { lastConfig = event.detail.config; editor.setConfig(event.detail.config); card.setConfig(event.detail.config); card._render(Date.parse(time(4, 40))); });
  const input = editor.shadowRoot.querySelector("input#mosque-title");
  input.focus(); input.value = "My Mosque"; input.dispatchEvent(new Event("input", {bubbles: true, composed: true}));
  check("graphical title editor emits configuration", lastConfig?.title === "My Mosque");
  check("configuration echo preserves focused input", editor.shadowRoot.querySelector("input#mosque-title") === input && editor.shadowRoot.activeElement === input);
  editor.hass = {...hass, states: {...hass.states}};
  check("hass state updates preserve focused input", editor.shadowRoot.querySelector("input#mosque-title") === input && editor.shadowRoot.activeElement === input);
  check("obsolete Jamaat mode editor removed", !editor.shadowRoot.textContent.includes("Jamaat panel"));
  const update = (key, value) => {
    const control = editor.shadowRoot.querySelector(`[data-option="${key}"]`);
    if (typeof value === "boolean") control.checked = value; else control.value = String(value);
    control.dispatchEvent(new Event("change", {bubbles: true}));
    check(`editor ${key}=${value} updates configuration`, lastConfig[key] === value);
  };
  for (const value of ["ar", "en", "auto", language]) {
    update("language", value);
    const expected = value === "ar" ? "rtl" : "ltr";
    check(`editor language=${value} updates direction`, editor.getAttribute("dir") === expected && card.getAttribute("dir") === expected);
    check(`editor language=${value} preserves focused title`, editor.shadowRoot.querySelector("input#mosque-title") === input && editor.shadowRoot.activeElement === input);
  }
  for (const value of [false, true, bilingual]) update("bilingual_prayer_labels", value);
  check("graphical language and bilingual controls round trip", lastConfig.language === language && lastConfig.bilingual_prayer_labels === bilingual);
  for (const [key, values] of Object.entries({detail_level: ["compact", "standard", "detailed"], time_format: ["12h", "24h"], hijri_adjustment: [-3, 3, 0]})) for (const value of values) update(key, value);
  const visibilityOptions = Object.keys(visibility(card));
  for (const key of visibilityOptions) for (const value of [false, true]) {
    update(key, value);
    const expected = Object.fromEntries(visibilityOptions.map(option => [option, true]));
    expected[key] = value;
    if (key === "show_ramadan_details") expected.show_sehri_countdown = expected.show_iftar_countdown = value;
    check(`editor ${key}=${value} changes the expected visible content`, Object.entries(visibility(card)).every(([option, visible]) => visible === expected[option]));
  }
  const restored = new SalahTimetableCardEditor(); restored.setConfig(JSON.parse(JSON.stringify(lastConfig))); restored.hass = hass;
  check("restored graphical configuration", restored.shadowRoot.querySelector("input#mosque-title").value === "My Mosque" && restored.shadowRoot.querySelector('[data-option="detail_level"]').value === lastConfig.detail_level);
  check("all graphical options survive configuration reload", [...restored.shadowRoot.querySelectorAll("[data-option]")].every(control => {
    const key = control.getAttribute("data-option"); return control.type === "checkbox" ? control.checked === lastConfig[key] : control.value === String(lastConfig[key]);
  }));
  check("countdowns never write HA service or state", serviceCalls === 0);
  check("real browser resource registration", customElements.get("salah-timetable-card") === SalahTimetableCard && window.customCards.some(item => item.type === "salah-timetable-card"));
  card.remove(); check("disconnected card clears local timer", card._timer === null);
  // Keep a static native-DOM preview for optional CDP screenshots.
  document.body.prepend(card); card.disconnectedCallback(); card._render(Date.parse(time(4, 40))); card.shadowRoot.querySelector(".table-scroll").scrollLeft = 0;
  parent.postMessage({kind: "salah-browser-result", status: "passed", width, language, bilingual, checks}, location.origin);
} catch (error) {
  parent.postMessage({kind: "salah-browser-result", status: "failed", width, language, bilingual, checks, error: error.stack || String(error)}, location.origin);
}
