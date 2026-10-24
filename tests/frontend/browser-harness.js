/** Real-browser fixture: native shadow DOM/CSS with small HA control stand-ins. */
import {SalahTimetableCard, SalahTimetableCardEditor} from "/custom_components/salah_timetable/frontend/salah-timetable-card.js";

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

const checks = [];
function check(name, assertion) { if (!assertion) throw new Error(name); checks.push(name); }
function visibility(card) {
  const root = card.shadowRoot;
  const panels = [...root.querySelectorAll(".panels > .panel")];
  const nodes = {
    show_hijri_date: root.querySelector(".hijri"),
    show_salah_countdown: panels.find(panel => panel.querySelector(".label").textContent === "Next Salah Begins"),
    show_jamaat_countdown: panels.find(panel => /^(Next|Previous) Jamaat$/.test(panel.querySelector(".label").textContent)),
    show_ramadan_details: root.querySelector(".ramadan"),
    show_sehri_countdown: root.querySelector(".ramadan-grid > :nth-child(1) .count"),
    show_iftar_countdown: root.querySelector(".ramadan-grid > :nth-child(2) .count"),
    show_timezone_note: root.querySelector(".content > .note:not(.scroll-help)"),
  };
  return Object.fromEntries(Object.entries(nodes).map(([key, node]) => [key, Boolean(node?.getClientRects().length)]));
}
const time = (hour, minute = 0) => `2026-10-21T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00Z`;
const event = (timestamp, prayer) => ({timestamp, prayer, field: `${prayer}_jamaat`});
const prayers = [
  {key: "fajr", name: "Fajr", begin: time(4, 45), jamaat: [time(5, 15)]},
  {key: "dhuhr", name: "Dhuhr", begin: time(11), jamaat: [time(11, 30)]},
  {key: "asr", name: "Asr", begin: time(14), jamaat: [time(14, 30)]},
  {key: "maghrib", name: "Maghrib", begin: time(16, 30), jamaat: [time(16, 33)]},
  {key: "isha", name: "Isha", begin: time(18), jamaat: [time(18, 30)]},
];
const data = {
  mosque_name: "Example Mosque", date: "2026-10-21", time_zone: "Europe/London", prayers,
  next_salah: {timestamp: time(4, 45), prayer: "fajr", field: "fajr_begin"},
  next_jamaat: event(time(5, 15), "fajr"), previous_jamaat: event("2026-10-20T18:30:00Z", "isha"), context_mode: "previous",
  beginning_events: prayers.map(prayer => ({timestamp: prayer.begin, prayer: prayer.key, field: `${prayer.key}_begin`})),
  jamaat_events: prayers.flatMap(prayer => prayer.jamaat.map(timestamp => event(timestamp, prayer.key))),
  ramadan: {active: true, sehri: time(4, 40), iftar: time(16, 30), taraweeh: null, taraweeh_text: "After Isha Jamaat"},
};
let serviceCalls = 0;
const hass = {states: {"sensor.example_prayer_timetable": {state: data.date, attributes: data}}, locale: {language: "en-GB"}, config: {time_zone: data.time_zone}, connection: {connected: true}, callService() { serviceCalls++; }};

try {
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.example_prayer_timetable", mode: "context"}); card.hass = hass; document.body.append(card); card._render(Date.parse(time(4, 40)));
  check("shadow DOM renders five prayer rows", card.shadowRoot.querySelectorAll("tbody tr").length === 5);
  check("mosque timezone used for absolute times", card.shadowRoot.textContent.includes("05:45"));
  check("local beginning countdown", card.shadowRoot.querySelector(".count").textContent === "00:05:00");
  check("Ramadan has textual Taraweeh fallback", card.shadowRoot.textContent.includes("After Isha Jamaat"));
  card._render(Date.parse(time(4, 50)));
  check("context changes at prayer beginning", card.shadowRoot.querySelectorAll(".panel .label")[1].textContent === "Next Jamaat");
  card._render(Date.parse(time(5, 15)));
  check("exact Jamaat becomes previous event", card.shadowRoot.querySelectorAll(".panel .label")[1].textContent === "Previous Jamaat");
  check("exact Jamaat elapsed zero", card.shadowRoot.querySelectorAll(".panel .count")[1].textContent === "00:00:00 elapsed");
  card.setConfig({entity: "sensor.example_prayer_timetable", title: '<img src="x" onerror="window.injected=true">'}); card._render(Date.parse(time(4, 40)));
  check("title uses literal text rather than executable markup", card.shadowRoot.querySelector("h2").textContent.startsWith("<img") && !card.shadowRoot.querySelector("img") && !window.injected);
  card.setConfig({entity: "sensor.example_prayer_timetable"}); card._render(Date.parse(time(4, 40)));
  check("Gregorian and calculated Hijri dates are visible", card.shadowRoot.querySelector(".hijri").textContent.includes("Hijri (calculated)"));
  check("upcoming row has accessible emphasis", card.shadowRoot.querySelector("tbody tr").getAttribute("aria-current") === "true");
  card._render(Date.parse(time(8)));
  check("future countdowns show bounded progress", [...card.shadowRoot.querySelectorAll("progress")].every(bar => bar.value >= 0 && bar.value <= 100) && card.shadowRoot.querySelectorAll("progress").length === 2);
  card.setConfig({entity: "sensor.example_prayer_timetable", layout: "compact", time_format: "12h", show_salah_countdown: false}); card._render(Date.parse(time(4, 40)));
  check("single visible panel fills width", card.shadowRoot.querySelectorAll(".panel").length === 1);
  check("12-hour absolute times", /am/i.test(card.shadowRoot.querySelector("tbody").textContent));
  card.setConfig({entity: "sensor.example_prayer_timetable"}); card._render(Date.parse(time(4, 40)));
  card._render(Date.parse(time(4, 41)));
  const scrollRegion = card.shadowRoot.querySelector(".table-scroll"); scrollRegion.focus();
  const stableTable = card.shadowRoot.querySelector("table");
  const range = document.createRange(); range.selectNodeContents(stableTable.querySelector("tbody th"));
  const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
  card._tick(Date.parse(time(4, 41)) + 1000);
  check("ordinary ticks retain table nodes and text selection", card.shadowRoot.querySelector("table") === stableTable && selection.toString() === "Fajr");
  selection.removeAllRanges();
  check("countdown tick preserves table keyboard focus", card.shadowRoot.activeElement === card.shadowRoot.querySelector(".table-scroll"));
  const width = window.innerWidth;
  check("card fits its viewport", card.getBoundingClientRect().width <= width && document.documentElement.scrollWidth <= width);
  document.documentElement.style.fontSize = "200%";
  const scaledContent = card.shadowRoot.querySelector(".content");
  const fitsScaledText = scaledContent.scrollWidth <= scaledContent.clientWidth + 1;
  const scaledRegion = card.shadowRoot.querySelector(".table-scroll");
  const overflowing = scaledRegion.scrollWidth > scaledRegion.clientWidth + 1;
  check("overflow has visible scrolling guidance", !overflowing || getComputedStyle(card.shadowRoot.querySelector(".scroll-help")).display !== "none");
  scaledRegion.scrollLeft = 50;
  check("overflow region can scroll without widening the card", !overflowing || scaledRegion.scrollLeft > 0);
  document.documentElement.style.fontSize = "";
  check("card contains 200% text without overflowing", fitsScaledText);
  const columns = getComputedStyle(card.shadowRoot.querySelector(".ramadan-grid")).gridTemplateColumns.split(" ").length;
  check("responsive Ramadan grid", columns === (width <= 420 ? 2 : 3));
  document.documentElement.style.setProperty("--primary-text-color", "rgb(250, 250, 250)");
  check("dark theme follows HA variables", getComputedStyle(card).color === "rgb(250, 250, 250)");
  document.documentElement.style.setProperty("--primary-text-color", "rgb(20, 20, 20)");
  check("light theme follows HA variables", getComputedStyle(card).color === "rgb(20, 20, 20)");

  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: "sensor.example_prayer_timetable", mode: "context"}); editor.hass = hass; document.body.append(editor);
  let lastConfig;
  editor.addEventListener("config-changed", event => { lastConfig = event.detail.config; editor.setConfig(event.detail.config); card.setConfig(event.detail.config); card._render(Date.parse(time(4, 40))); });
  const input = editor.shadowRoot.querySelector("input#mosque-title");
  input.focus(); input.value = "My Mosque"; input.dispatchEvent(new Event("input", {bubbles: true, composed: true}));
  check("graphical title editor emits configuration", lastConfig?.title === "My Mosque");
  check("configuration echo preserves focused input", editor.shadowRoot.querySelector("input#mosque-title") === input && editor.shadowRoot.activeElement === input);
  editor.hass = {...hass, states: {...hass.states}};
  check("hass state updates preserve focused input", editor.shadowRoot.querySelector("input#mosque-title") === input && editor.shadowRoot.activeElement === input);
  const mode = editor.shadowRoot.querySelectorAll("ha-selector")[1]; mode.value = "upcoming"; mode.select.dispatchEvent(new Event("change"));
  check("graphical mode editor round trip", lastConfig.mode === "upcoming" && mode.value === "upcoming");
  const visibilityOptions = Object.keys(visibility(card));
  for (const key of visibilityOptions) {
    const control = editor.shadowRoot.querySelector(`[data-option="${key}"]`);
    for (const value of [false, true]) {
      control.click();
      const expected = Object.fromEntries(visibilityOptions.map(option => [option, true]));
      expected[key] = value;
      if (key === "show_ramadan_details") expected.show_sehri_countdown = expected.show_iftar_countdown = value;
      check(`editor ${key}=${value} changes the expected visible content`, lastConfig[key] === value && Object.entries(visibility(card)).every(([option, visible]) => visible === expected[option]));
    }
  }
  const restored = new SalahTimetableCardEditor(); restored.setConfig(lastConfig); restored.hass = hass;
  check("restored graphical configuration", restored.shadowRoot.querySelector("input#mosque-title").value === "My Mosque" && restored.shadowRoot.querySelectorAll("ha-selector")[1].value === "upcoming");
  check("countdowns never write HA service or state", serviceCalls === 0);
  check("real browser resource registration", customElements.get("salah-timetable-card") === SalahTimetableCard && window.customCards.some(item => item.type === "salah-timetable-card"));
  card.remove(); check("disconnected card clears local timer", card._timer === null);
  // Keep a static native-DOM preview for optional CDP screenshots.
  document.body.prepend(card); card.disconnectedCallback(); card._render(Date.parse(time(4, 40))); card.shadowRoot.querySelector(".table-scroll").scrollLeft = 0;
  parent.postMessage({kind: "salah-browser-result", status: "passed", width, checks}, location.origin);
} catch (error) {
  parent.postMessage({kind: "salah-browser-result", status: "failed", width: window.innerWidth, checks, error: error.stack || String(error)}, location.origin);
}
