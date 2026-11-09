import test from "node:test";
import assert from "node:assert/strict";

class Element {
  constructor(tagName = "custom-element") { this.tagName = tagName; this.children = []; this.listeners = new Map(); this._text = ""; this.attributes = {}; this.classes = new Set(); this.classList = {add: name => this.classes.add(name), contains: name => this.classes.has(name)}; this.style = {values: {}, setProperty(name, value) { this.values[name] = value; }}; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(""); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this._text = ""; this.children = children; }
  setAttribute(name, value) { this.attributes[name] = value; }
  hasAttribute(name) { return Object.hasOwn(this.attributes, name); }
  removeAttribute(name) { delete this.attributes[name]; }
  attachShadow() { this.shadowRoot = new Element("shadow-root"); return this.shadowRoot; }
  addEventListener(name, callback) { if (!this.listeners.has(name)) this.listeners.set(name, []); this.listeners.get(name).push(callback); }
  dispatchEvent(event) { if (!event.target) Object.defineProperty(event, "target", {value: this}); for (const callback of this.listeners.get(event.type) || []) callback(event); return true; }
}
const registry = new Map(); const timers = new Map(); let timerId = 0;
globalThis.HTMLElement = Element;
globalThis.customElements = {get: name => registry.get(name), define: (name, type) => registry.set(name, type)};
globalThis.document = {createElement: name => registry.has(name) ? new (registry.get(name))() : new Element(name), createElementNS: (_ns, name) => new Element(name)};
globalThis.window = {setInterval: callback => { timers.set(++timerId, callback); return timerId; }, clearInterval: id => timers.delete(id), customCards: []};
const {SalahTimetableCard, SalahTimetableCardEditor} = await import("../../custom_components/salah_timetable/frontend/salah-timetable-card.js");
const {tr} = await import("../../custom_components/salah_timetable/frontend/card-i18n.js");
const {formatDate, formatHijriDate, hijriMonthInfo, normalizeConfig} = await import("../../custom_components/salah_timetable/frontend/card-utils.js");
function find(root, tag) { return [root, ...root.children.flatMap(child => find(child, tag))].filter(node => node.tagName === tag); }
const attributes = {
  mosque_name: "Example Mosque", date: "2026-10-21", time_zone: "Europe/London",
  prayers: [{key: "fajr", name: "Fajr", begin: "2026-10-21T04:45:00Z", jamaat: ["2026-10-21T05:15:00Z"]}],
  next_salah: {timestamp: "2026-10-21T04:45:00Z", prayer: "fajr"},
  next_jamaat: {timestamp: "2026-10-21T05:15:00Z", prayer: "fajr"},
  previous_jamaat: {timestamp: "2026-10-20T19:00:00Z", prayer: "isha"},
  context_mode: "previous", ramadan: {active: false},
};
function hass(data = attributes) { return {states: {"sensor.mosque_prayer_timetable": {state: "2026-10-21", attributes: data}}, locale: {language: "en-GB"}, config: {time_zone: "Europe/London"}, connection: {connected: true}, callService() { throw new Error("A card must never write countdown states"); }}; }

test("bundled card and graphical editor register once", () => {
  assert.equal(registry.get("salah-timetable-card"), SalahTimetableCard);
  assert.equal(registry.get("salah-timetable-card-editor"), SalahTimetableCardEditor);
  assert.equal(window.customCards.length, 11);
  assert.equal(SalahTimetableCard.getConfigElement() instanceof SalahTimetableCardEditor, true);
  assert.equal(SalahTimetableCard.getStubConfig(hass()).entity, "sensor.mosque_prayer_timetable");
});

test("adjacent days keep the painted photograph frame when viewport sizing settles", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_mosque_background: true});
  card.hass = hass();
  const surface = find(card.shadowRoot, "ha-card")[0];
  // The minimal unit DOM implements tree traversal, not querySelector.
  card.shadowRoot.querySelector = selector => selector === "ha-card" ? surface : null;
  surface.getBoundingClientRect = () => ({width: 344, height: 1480});
  const previousStyle = globalThis.getComputedStyle;
  try {
    globalThis.getComputedStyle = () => ({height: "1496px"});
    card._rememberBackgroundFrame();
    assert.deepEqual(card._backgroundFrame, {
      entity: "sensor.mosque_prayer_timetable", width: 344, height: 1500
    }, "Preserve the actual painted image even when the card rectangle is shorter");
    globalThis.getComputedStyle = () => ({height: "1400px"});
    card._rememberBackgroundFrame();
    assert.equal(card._backgroundFrame.height, 1480,
      "Never crop a larger card simply because its image layer is shorter");
    globalThis.getComputedStyle = () => ({height: "auto"});
    card._rememberBackgroundFrame();
    assert.equal(card._backgroundFrame.height, 1480,
      "Fall back to the measured card height if the pseudo-element is unavailable");
  } finally {
    globalThis.getComputedStyle = previousStyle;
  }
});

test("viewport sizing follows the rendered card top and available mobile screen", () => {
  const oldViewport = window.visualViewport;
  const oldHeight = window.innerHeight;
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_mosque_background: true});
  card.hass = hass();
  let top = 92;
  card.getBoundingClientRect = () => ({top, width: 360});
  try {
    window.visualViewport = {height: 700, offsetTop: 0};
    window.innerHeight = 850;
    card._measureViewportHeight();
    assert.equal(card.style.values["--salah-viewport-card-height"], "596px",
      "Use the visual viewport minus actual card top and a 12px bottom gap");
    top = 160;
    window.visualViewport.height = 640;
    card._measureViewportHeight();
    assert.equal(card.style.values["--salah-viewport-card-height"], "468px",
      "Recompute when the mobile toolbar or card position changes");
    top = 800;
    card._measureViewportHeight();
    assert.equal(card.style.values["--salah-viewport-card-height"], "0px",
      "Cards below the visible screen keep their natural content height");
    top = -100;
    card._measureViewportHeight();
    assert.equal(card.style.values["--salah-viewport-card-height"], "628px",
      "A scrolled card cannot force a minimum taller than the viewport");
    window.visualViewport = null;
    top = 92;
    card._measureViewportHeight();
    assert.equal(card.style.values["--salah-viewport-card-height"], "746px",
      "Fall back to innerHeight where visualViewport is unavailable");
    // Kiosk reserves the Home Assistant shell's footer margin so a single
    // full-screen card does not induce a tiny document scrollbar.
    card.setConfig({entity: "sensor.mosque_prayer_timetable", kiosk_mode: true});
    window.visualViewport = {height: 700, offsetTop: 0};
    card._measureViewportHeight();
    assert.equal(card.style.values["--salah-viewport-card-height"], "576px",
      "Kiosk leaves 32px of breathing room instead of the default 12px");
    card.preview = true;
    card._measureViewportHeight();
    assert.equal(card.style.values["--salah-viewport-card-height"], "596px",
      "Editing preview retains ordinary height measurement");
    card.getBoundingClientRect = () => ({top: 92, width: 0});
    card._measureViewportHeight();
    assert.equal(card.style.values["--salah-viewport-card-height"], "596px",
      "Ignore hidden or unmeasurable cards");
  } finally {
    window.visualViewport = oldViewport;
    window.innerHeight = oldHeight;
  }
});

test("desktop/tablet HA editing wrappers shrink photo without preview=true", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_mosque_background: true});
  card.hass = hass();
  let wrapper = null;
  card.closest = selector =>
    selector === "hui-card-options, hui-card-edit-mode" ? wrapper : null;
  assert.equal(card.preview, false);
  assert.equal(card.hasAttribute("dashboard-editing"), false);
  for (const kind of ["hui-card-options", "hui-card-edit-mode"]) {
    wrapper = {tagName: kind};
    // HA renders cards in these edit wrappers even with preview=false.
    card._syncDashboardEditing();
    assert.equal(card.hasAttribute("dashboard-editing"), true, kind);
    card.preview = false;
    assert.equal(card.hasAttribute("dashboard-editing"), true,
      `${kind} must override preview=false`);
  }
  wrapper = null;
  card._syncDashboardEditing();
  assert.equal(card.hasAttribute("dashboard-editing"), false,
    "Returning to normal dashboard view restores the full canvas");
  card.preview = true;
  assert.equal(card.hasAttribute("dashboard-editing"), true,
    "A standalone card-editor preview still shortens the canvas");
  card.preview = false;
  assert.equal(card.hasAttribute("dashboard-editing"), false);
});

test("HA dashboard preview shrinks only editing canvas, and restores viewing mode", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_mosque_background: true});
  card.hass = hass();
  assert.equal(card.preview, false);
  assert.equal(card.attributes["dashboard-editing"], undefined);
  card.preview = true;
  assert.equal(card.preview, true);
  assert.equal(card.attributes["dashboard-editing"], "");
  card.editMode = false;
  assert.equal(card.preview, false);
  assert.equal(card.attributes["dashboard-editing"], undefined);
  card.editMode = true;
  assert.equal(card.attributes["dashboard-editing"], "");
  card.preview = false;
  assert.equal(card.attributes["dashboard-editing"], undefined);
});

test("mosque header and both live countdowns share one summary card", () => {
  const config = {entity: "sensor.mosque_prayer_timetable"};
  const card = new SalahTimetableCard();
  card.setConfig(config); card.hass = hass();
  const shell = () => find(card.shadowRoot, "div").find(element => element.className === "summary-shell");
  const contents = () => shell().children;
  assert.ok(shell(), "Shared card must exist");
  assert.equal(contents()[0].tagName, "header");
  assert.equal(contents()[1].className, "panels");
  assert.equal(contents()[1].children.length, 2);
  assert.equal(contents()[1].children[0].attributes["data-panel"], "salah");
  assert.equal(contents()[1].children[1].attributes["data-panel"], "jamaat");
  assert.match(contents()[0].textContent, /Example Mosque/);
  assert.equal(find(card.shadowRoot, "table").length, 1);
  assert.ok(!contents().includes(find(card.shadowRoot, "table")[0]), "Timetable stays outside the summary");

  for (const [salah, jamaat] of [[true, false], [false, true], [false, false]]) {
    card.setConfig({...config, show_salah_countdown: salah, show_jamaat_countdown: jamaat});
    assert.equal(find(card.shadowRoot, "div").filter(element => element.className === "summary-shell").length, 1);
    const groups = contents().filter(element => element.className?.split(" ").includes("panels"));
    assert.equal(groups.length, salah || jamaat ? 1 : 0);
    if (groups.length) assert.equal(groups[0].children.length, Number(salah) + Number(jamaat));
  }
  card.setConfig(config);
  const footer = find(card.shadowRoot, "nav").find(element => element.className === "date-tabs");
  footer.children[0].dispatchEvent(new Event("click"));
  assert.equal(contents().length, 1, "Browsing an adjacent date keeps the mosque heading, not live countdowns");
});

test("card renders local times, missing states and theme-responsive layout", () => {
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable"}); card.hass = hass(); card._render(Date.parse("2026-10-21T04:40:00Z"));
  assert.match(card.shadowRoot.textContent, /Example Mosque/); assert.match(card.shadowRoot.textContent, /05:45/); assert.match(card.shadowRoot.textContent, /00:05:00/);
  assert.match(find(card.shadowRoot, "style")[0].textContent, /--primary-text-color/); assert.match(find(card.shadowRoot, "style")[0].textContent, /max-width:420px/);
  card.hass = {states: {}}; assert.match(card.shadowRoot.textContent, /entity was not found/);
  card.hass = {states: {"sensor.mosque_prayer_timetable": {state: "unavailable", attributes}}}; assert.match(card.shadowRoot.textContent, /Timetable unavailable/);
});

test("dashboard shows published sunrise as Fajr end and second Khutbah separately", () => {
  const friday = {...attributes, date: "2026-10-23",
    prayers: [{key: "fajr", name: "Fajr", begin: "2026-10-23T04:45:00Z", end: "2026-10-23T06:20:00Z", jamaat: ["2026-10-23T05:15:00Z"]},
      {key: "dhuhr", name: "Dhuhr", begin: "2026-10-23T11:45:00Z", jamaat: ["2026-10-23T12:30:00Z"]}],
    second_khutbah: "2026-10-23T15:30:00+01:00",
    show_hijri_date: true,
  };
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level: "detailed"}); card.hass = hass(friday);
  card._render(Date.parse("2026-10-23T04:00:00Z"));
  const rows = find(card.shadowRoot, "tr");
  assert.match(rows[1].textContent, /Ends at sunrise: 07:20/);
  assert.match(card.shadowRoot.textContent, /Second Jumu’ah khutbah: 15:30 \(published; not Jamaat\)/);
  assert.match(rows[2].textContent, /12:45/);
  assert.match(rows[2].textContent, /13:30/);
  const thursday = {...friday, date: "2026-10-22"};
  card.hass = hass(thursday); card._render(Date.parse("2026-10-22T04:00:00Z"));
  assert.doesNotMatch(card.shadowRoot.textContent, /Second Jumu’ah khutbah/);
});

test("mosque-wide Hijri preference overrides card visibility and remains configurable", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable"});
  card.hass = hass({...attributes, show_hijri_date: false});
  assert.doesNotMatch(find(card.shadowRoot, "header")[0].textContent, /Hijri/);
  card.hass = hass({...attributes, show_hijri_date: true});
  assert.match(find(card.shadowRoot, "header")[0].textContent, /Hijri/);
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_hijri_date: false});
  assert.doesNotMatch(find(card.shadowRoot, "header")[0].textContent, /Hijri/);
});

for (const [language, locale, month, gregorianMonth] of [["en", "en-GB", "Ramadan", "February"], ["ar", "ar-EG", "رمضان", "فبراير"]]) test(`Hijri-first header and independent date controls in ${language}`, () => {
  const card = new SalahTimetableCard();
  const data = {...attributes, date: "2026-02-18", show_hijri_date: true};
  const localizedHass = {...hass(data), locale: {language: locale}};
  card.setConfig({entity: "sensor.mosque_prayer_timetable", language, bilingual_prayer_labels: true});
  card.hass = localizedHass;
  const header = find(card.shadowRoot, "header")[0];
  assert.equal(header.children[1].className, "date hijri");
  assert.ok(header.children[1].textContent.includes(month));
  assert.ok(header.children[1].textContent.includes(tr(language, "card.hijri_calculated")));
  assert.equal(header.children[2].className, "date gregorian");
  assert.ok(header.children[2].textContent.includes(gregorianMonth));
  assert.equal(header.children[3].className, "month-description");
  assert.ok(header.children[3].textContent.length > 0);
  for (const show_hijri_date of [true, false]) for (const show_gregorian_date of [true, false]) {
    card.setConfig({entity: "sensor.mosque_prayer_timetable", language, show_hijri_date, show_gregorian_date});
    const currentHeader = find(card.shadowRoot, "header")[0];
    assert.equal(currentHeader.children.length, 1 + Number(show_hijri_date) * 2 + Number(show_gregorian_date));
    assert.equal(currentHeader.children.some(element => element.className === "date hijri"), show_hijri_date);
    assert.equal(currentHeader.children.some(element => element.className === "date gregorian"), show_gregorian_date);
    assert.equal(currentHeader.children.some(element => element.className === "month-description"), show_hijri_date);
    assert.equal(find(card.shadowRoot, "table").length, 1);
  }
  card.setConfig({entity: "sensor.mosque_prayer_timetable", language, show_hijri_date: true, show_gregorian_date: false});
  card.hass = {...localizedHass, states: {"sensor.mosque_prayer_timetable": {state: data.date, attributes: {...data, show_hijri_date: false}}}};
  assert.equal(find(card.shadowRoot, "header")[0].children.length, 1);
  const editor = SalahTimetableCard.getConfigElement();
  editor.hass = localizedHass;
  editor.setConfig({entity: "sensor.mosque_prayer_timetable", language, show_gregorian_date: false});
  assert.equal(editor._extraControls.show_gregorian_date.control.checked, false);
  assert.equal(editor._extraControls.show_gregorian_date.label.textContent, tr(language, "editor.show_gregorian_date"));
  assert.equal(editor._extraControls.show_hijri_date.control.checked, true);
});

test("Friday Dhuhr congregation is labelled Jumuah", () => {
  const friday = {
    ...attributes,
    date: "2026-10-23",
    prayers: [{
      key: "dhuhr",
      name: "Dhuhr",
      begin: "2026-10-23T11:55:00Z",
      jamaat: ["2026-10-23T12:25:00Z"],
    }],
    jamaat_events: [{
      timestamp: "2026-10-23T12:25:00Z",
      prayer: "jumuah",
      field: "jumuah",
    }],
  };

  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable"});
  card.hass = hass(friday);
  card._render(Date.parse("2026-10-23T11:00:00Z"));

  const rows = find(card.shadowRoot, "tr");
  const jumuah = rows.find(row => row.children[0]?.textContent.includes("Jumu"));
  assert.ok(jumuah, "Friday prayer row should be labelled Jumu'ah");
  assert.match(jumuah.textContent, /Jumu/);
  assert.match(jumuah.textContent, /13:25/);
});

test("Friday Jumu'ah labels cover countdowns, timetable, kiosk and adjacent dates", () => {
  const day = "2026-11-06";
  const row = {key: "dhuhr", name: "Dhuhr", begin: day + "T11:55:00Z",
    jamaat: [day + "T12:20:00Z", day + "T12:35:00Z", day + "T13:25:00Z"]};
  const thursdayRow = {key: "dhuhr", name: "Dhuhr", begin: "2026-11-05T11:55:00Z",
    jamaat: ["2026-11-05T12:20:00Z"]};
  const saturdayRow = {key: "dhuhr", name: "Dhuhr", begin: "2026-11-07T11:55:00Z",
    jamaat: ["2026-11-07T12:20:00Z"]};
  const friday = {...attributes, date: day, prayers: [row],
    day_prayers: {"2026-11-05": [thursdayRow], [day]: [row], "2026-11-07": [saturdayRow]},
    beginning_events: [{prayer: "dhuhr", timestamp: row.begin, field: "dhuhr_begin"}],
    jamaat_events: [
      {prayer: "dhuhr", timestamp: row.jamaat[0], field: "dhuhr_jamaat"},
      {prayer: "jumuah", timestamp: row.jamaat[1], field: "jumuah"},
      {prayer: "jumuah", timestamp: row.jamaat[2], field: "jumuah"},
    ],
    next_salah: {prayer: "dhuhr", timestamp: row.begin, field: "dhuhr_begin"}};
  const before = Date.parse(day + "T11:45:00Z");
  for (const detail_level of ["compact", "standard", "detailed"]) {
    const card = new SalahTimetableCard();
    card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level,
      bilingual_prayer_labels: true, show_mosque_background: false});
    card.hass = hass(friday);
    card._render(before);
    const panel = find(card.shadowRoot, "section").find(n => n.attributes["data-panel"] === "salah");
    assert.ok(panel, detail_level);
    assert.match(panel.children[1].textContent, /Jumu/);
    assert.match(panel.children[1].textContent, /الجمعة/);
    assert.doesNotMatch(panel.children[1].textContent, /Dhuhr/);
    assert.match(panel.textContent, /11:55/);
    assert.match(panel.textContent, /12:35/, "Show first Jumu'ah, not the ordinary Dhuhr congregation");
    if (detail_level !== "compact") {
      assert.ok(find(card.shadowRoot, "tr").some(r => r.children[0]?.textContent.includes("Jumu")));
    }
    card._render(Date.parse(day + "T13:30:00Z"));
    const previous = find(card.shadowRoot, "section").find(n => n.attributes["data-panel"] === "jamaat");
    assert.match(previous.children[1].textContent, /Jumu/, "Previous congregation retains Jumu'ah");
  }
  const kiosk = new SalahTimetableCard();
  kiosk.setConfig({entity: "sensor.mosque_prayer_timetable", kiosk_mode: true,
    show_mosque_background: false});
  kiosk.hass = hass(friday);
  const tileName = () => {
    const tile = find(kiosk.shadowRoot, "div").find(n => n.attributes["data-prayer"] === "dhuhr");
    return find(tile, "h3")[0].textContent;
  };
  kiosk._render(before);
  assert.match(tileName(), /Jumu/);
  kiosk._selectedDay = -1; kiosk._render(before);
  assert.match(tileName(), /Dhuhr/);
  kiosk._selectedDay = 1; kiosk._render(before);
  assert.match(tileName(), /Dhuhr/);

  const thursday = {...friday, date: "2026-11-05", prayers: [thursdayRow]};
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_mosque_background: false});
  card.hass = hass(thursday);
  card._render(Date.parse("2026-11-05T20:00:00Z"));
  const next = find(card.shadowRoot, "section").find(n => n.attributes["data-panel"] === "salah");
  assert.match(next.children[1].textContent, /Jumu/, "Tomorrow's Friday countdown is Jumu'ah");
  card._selectedDay = 1; card._render(Date.parse("2026-11-05T20:00:00Z"));
  assert.ok(find(card.shadowRoot, "tr").some(r => r.children[0]?.textContent.includes("Jumu")),
    "Tomorrow tab uses its own published Friday events");
});

test("weekday Dhuhr Jamaat is not labelled Jumuah", () => {
  const weekday = {
    ...attributes,
    date: "2026-10-22",
    prayers: [{
      key: "dhuhr",
      name: "Dhuhr",
      begin: "2026-10-22T11:55:00Z",
      jamaat: ["2026-10-22T12:25:00Z"],
    }],
    jamaat_events: [{
      timestamp: "2026-10-22T12:25:00Z",
      prayer: "dhuhr",
      field: "dhuhr_jamaat",
    }],
  };

  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable"});
  card.hass = hass(weekday);
  card._render(Date.parse("2026-10-22T11:00:00Z"));

  const dhuhr = find(card.shadowRoot, "tr")
    .find(row => row.textContent.includes("Dhuhr"));

  assert.ok(dhuhr);
  assert.match(dhuhr.textContent, /13:25/);
  assert.doesNotMatch(dhuhr.textContent, /Jumuah/);
});

test("card lifecycle ticks locally and releases its interval", () => {
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable"}); card.hass = hass();
  card.connectedCallback(); card.connectedCallback(); assert.equal(timers.size, 1);
  const stateBefore = JSON.stringify(card._hass.states); [...timers.values()][0](); assert.equal(JSON.stringify(card._hass.states), stateBefore);
  card.disconnectedCallback(); assert.equal(timers.size, 0);
});

test("Ramadan text and imported titles use text nodes, never markup", () => {
  const malicious = '<img src=x onerror="alert(1)">'; const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", title: malicious, detail_level: "detailed"});
  card.hass = hass({...attributes, ramadan: {active: true, sehri: "2026-10-21T04:40:00Z", iftar: "2026-10-21T17:00:00Z", taraweeh: null, taraweeh_text: "After Isha Jamaat"}});
  card._render(Date.parse("2026-10-21T04:30:00Z"));
  assert.equal(find(card.shadowRoot, "h2")[0].textContent, malicious); assert.equal(find(card.shadowRoot, "img").length, 0);
  assert.match(card.shadowRoot.textContent, /Ramadan/); assert.match(card.shadowRoot.textContent, /After Isha Jamaat/); assert.match(card.shadowRoot.textContent, /00:10:00/);
  assert.equal(card.getCardSize(), 7);
});

test("disconnected HA keeps visible source data with an explicit status", () => {
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable"}); const current = hass(); current.connection.connected = false; card.hass = current;
  assert.match(card.shadowRoot.textContent, /disconnected/); assert.match(card.shadowRoot.textContent, /Example Mosque/);
});

test("editor omits the title field and preserves an existing YAML title through config-changed", () => {
  const editor = new SalahTimetableCardEditor();
  editor.setConfig({entity: "sensor.mosque_prayer_timetable", mode: "context", title: "My Mosque"});
  editor.hass = hass();
  const emitted = [];
  editor.addEventListener("config-changed", event => emitted.push(event.detail.config));
  assert.equal(find(editor.shadowRoot, "ha-selector").length, 0);
  assert.equal(find(editor._controls.mosqueList, "input").length, 1);
  assert.ok(find(editor.shadowRoot, "input").every(input => input.type === "checkbox" || input.getAttribute?.("data-option") === "selection_group" || input.attributes["data-option"] === "selection_group"));
  assert.equal(find(editor.shadowRoot, "ha-textfield").length, 0);
  editor._extraControls.detail_level.control.value = "detailed";
  editor._extraControls.detail_level.control.dispatchEvent(new Event("change"));
  assert.deepEqual(emitted.at(-1), {...new SalahTimetableCardEditor()._config, type: "custom:salah-timetable-card", entity: "sensor.mosque_prayer_timetable", detail_level: "detailed", title: "My Mosque"});
  const reconstructed = new SalahTimetableCardEditor(); reconstructed.setConfig(emitted.at(-1)); reconstructed.hass = hass();
  assert.equal(reconstructed._extraControls.detail_level.control.value, "detailed");
  assert.equal(reconstructed._config.title, "My Mosque");
  const card = new SalahTimetableCard(); card.setConfig(emitted.at(-1)); card.hass = hass();
  assert.equal(find(card.shadowRoot, "h2")[0].textContent, "My Mosque");
});

test("editor discovers only timetable sensors, never individual prayer entities", () => {
  const editor = new SalahTimetableCardEditor();
  const current = hass();
  current.states["sensor.fajr"] = {state: "2026-10-21T04:45:00Z", attributes: {}};
  editor.hass = current;
  let emitted = false;
  editor.addEventListener("config-changed", () => { emitted = true; });
  assert.equal(find(editor.shadowRoot, "ha-selector").length, 0);
  assert.equal(find(editor._controls.mosqueList, "input").length, 1);
  assert.doesNotMatch(editor._controls.mosqueList.textContent, /sensor.fajr/);
  assert.equal(emitted, false);
});


test("editor preserves controls across config echoes and hass updates", () => {
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: "sensor.mosque_prayer_timetable"}); editor.hass = hass();
  const detail = editor._extraControls.detail_level.control;
  editor.addEventListener("config-changed", event => editor.setConfig(event.detail.config));
  detail.value = "compact"; detail.dispatchEvent(new Event("change"));
  editor.hass = hass({...attributes, mosque_name: "Renamed"});
  assert.equal(editor._extraControls.detail_level.control, detail);
  assert.equal(detail.value, "compact");
});

test("dashboard controls hide panels and details without hiding published prayer values", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level: "standard", show_salah_countdown: false, show_jamaat_countdown: false, show_hijri_date: false, show_timezone_note: false, show_ramadan_details: false, time_format: "12h"});
  card.hass = hass({...attributes, ramadan: {active: true}}); card._render(Date.parse("2026-10-21T04:40:00Z"));
  assert.equal(find(card.shadowRoot, "section").length, 0);
  assert.equal(find(card.shadowRoot, "div").filter(element => element.className === "month-description").length, 0);
  assert.equal(find(card.shadowRoot, "table").length, 1);
  assert.match(find(card.shadowRoot, "table")[0].textContent, /05:45\s*am/i);
  assert.equal(find(card.shadowRoot, "header")[0].textContent.includes("Hijri"), false);
  assert.equal(find(card.shadowRoot, "p").filter(element => !["note scroll-help", "note"].includes(element.className)).length, 0);
  assert.equal(find(card.shadowRoot, "tr")[1].attributes["aria-current"], "true");
});

test("Hijri month explanation is a single subtitle beneath the date, with visibility controls", () => {
  const card = new SalahTimetableCard();
  const config = {entity: "sensor.mosque_prayer_timetable"};
  card.setConfig(config);
  card.hass = hass();
  const subtitle = () => find(card.shadowRoot, "div").filter(element => element.className === "month-description");
  const header = () => find(card.shadowRoot, "header")[0];
  assert.equal(subtitle().length, 1);
  assert.equal(header().children.at(-1), subtitle()[0]);
  assert.match(subtitle()[0].textContent, /fifth month/i);
  assert.equal(find(card.shadowRoot, "section").filter(element => element.className === "panel hijri-month-info").length, 0);
  card.setConfig({...config, show_hijri_month_info: false});
  assert.equal(subtitle().length, 0);
  card.setConfig({...config, show_hijri_date: false});
  assert.equal(subtitle().length, 0, "Do not show an orphan month description when Hijri date is hidden");
  card.setConfig({...config, detail_level: "compact"});
  assert.equal(subtitle().length, 0, "Compact mode also hides the Hijri heading");
  card.setConfig(config);
  card.hass = hass({...attributes, show_hijri_date: false});
  assert.equal(subtitle().length, 0, "Mosque-wide Hijri preference remains authoritative");
  assert.equal(find(card.shadowRoot, "table").length, 1);
});

test("Ramadan countdown switches retain published times and Taraweeh", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level: "detailed", show_sehri_countdown: false, show_iftar_countdown: false});
  card.hass = hass({...attributes, ramadan: {active: true, sehri: "2026-10-21T04:30:00Z", iftar: "2026-10-21T17:30:00Z", taraweeh_text: "After Isha Jamaat"}});
  card._render(Date.parse("2026-10-21T04:00:00Z"));
  const section = find(card.shadowRoot, "section").at(-1);
  assert.match(section.textContent, /05:30/); assert.match(section.textContent, /18:30/);
  assert.match(section.textContent, /After Isha Jamaat/);
  assert.equal(find(section, "div").filter(element => element.className === "count").length, 0);
});

test("retired background opacity is discarded from old Lovelace configs without affecting mosque choice", () => {
  const old = {entity: "sensor.mosque_prayer_timetable", mosque_background_opacity: 17, mosque_background: "masjid-al-haram"};
  const card = new SalahTimetableCard();
  card.setConfig(old);
  card.hass = hass();
  assert.equal(Object.hasOwn(card._config, "mosque_background_opacity"), false);
  assert.equal(card._config.mosque_background, "masjid-al-haram");
  assert.equal(find(card.shadowRoot, "ha-card")[0].style.values["--mosque-overlay"], undefined);
  const editor = new SalahTimetableCardEditor();
  editor.setConfig(old);
  editor.hass = hass();
  assert.equal(Object.hasOwn(editor._extraControls, "mosque_background_opacity"), false);
  assert.equal(editor._config.mosque_background, "masjid-al-haram");
  assert.equal(editor._config.mosque_background_opacity, undefined);
});

test("new editor controls round trip and retain nodes through HA config echoes", () => {
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: "sensor.mosque_prayer_timetable"}); editor.hass = hass();
  const changes = []; editor.addEventListener("config-changed", event => { changes.push(event.detail.config); editor.setConfig(event.detail.config); });
  for (const [key, entry] of Object.entries(editor._extraControls)) {
    const control = entry.control;
    if (control.disabled) continue; // Dependent and future options do not emit changes.
    if (entry.checkbox) control.checked = false;
    else control.value = ({language: "ar", detail_level: "compact", time_format: "12h", hijri_adjustment: "-2", hijri_day_boundary: "maghrib", mosque_background: "masjid-al-haram"})[key];
    control.dispatchEvent(new Event("change")); editor.hass = hass();
    assert.equal(editor._extraControls[key].control, control);
    assert.equal(changes.at(-1)[key], entry.checkbox ? false : key === "hijri_adjustment" ? Number(control.value) : control.value);
  }
});

test("editor uses Home Assistant switches in collapsible, accessible groups", () => {
  const editor = new SalahTimetableCardEditor(); editor.hass = hass();
  const dates = editor._sections.dates; const prayers = editor._sections.countdowns;
  const control = editor._extraControls.show_gregorian_date.control;
  assert.equal(dates.toggle.attributes["aria-expanded"], "true");
  assert.equal(dates.body.hidden, false);
  assert.equal(prayers.body.hidden, true);
  assert.equal(control.tagName, "ha-switch");
  assert.equal(control.attributes["aria-label"], tr("en", "editor.show_gregorian_date"));
  assert.match(editor._extraControls.show_gregorian_date.hint.textContent, /civil date/);
  assert.equal(find(editor.shadowRoot, "ha-switch").length, Object.values(editor._extraControls).filter(item => item.checkbox).length + 1, "Advanced adds one mosque synchronisation switch");
  prayers.toggle.dispatchEvent(new Event("click"));
  assert.equal(dates.body.hidden, true);
  assert.equal(prayers.toggle.attributes["aria-expanded"], "true");
  assert.equal(prayers.body.hidden, false);
  prayers.toggle.dispatchEvent(new Event("click"));
  assert.equal(prayers.body.hidden, true);
  editor.hass = hass();
  assert.equal(editor._extraControls.show_gregorian_date.control, control);
});

test("disabled dependent switches retain their saved preferences", () => {
  const editor = new SalahTimetableCardEditor(); editor.hass = hass();
  const updates = [];
  editor.addEventListener("config-changed", event => { updates.push(event.detail.config); editor.setConfig(event.detail.config); });
  const setSwitch = (key, checked) => {
    const control = editor._extraControls[key].control;
    control.checked = checked; control.dispatchEvent(new Event("change"));
  };
  setSwitch("show_hijri_date", false);
  const month = editor._extraControls.show_hijri_month_info.control;
  assert.equal(month.disabled, true);
  const count = updates.length;
  setSwitch("show_hijri_month_info", false);
  assert.equal(updates.length, count);
  assert.equal(editor._config.show_hijri_month_info, true);
  setSwitch("show_hijri_date", true);
  assert.equal(month.disabled, false);
  assert.equal(month.checked, true);
  setSwitch("show_ramadan_details", false);
  assert.equal(editor._extraControls.show_sehri_countdown.control.disabled, true);
  assert.equal(editor._extraControls.show_iftar_countdown.control.disabled, true);
  assert.equal(editor._config.show_iftar_countdown, true);
  setSwitch("show_ramadan_details", true);
  assert.equal(editor._extraControls.show_sehri_countdown.control.disabled, false);
  const detail = editor._extraControls.detail_level.control;
  detail.value = "compact"; detail.dispatchEvent(new Event("change"));
  assert.equal(editor._extraControls.show_night_calculations.control.disabled, true);
  detail.value = "standard"; detail.dispatchEvent(new Event("change"));
  assert.equal(editor._extraControls.show_night_calculations.control.disabled, false);
});

test("single background dropdown preserves legacy options when switched off", () => {
  const editor = new SalahTimetableCardEditor();
  editor.setConfig({entity: "sensor.mosque_prayer_timetable", mosque_background: "masjid-al-haram"});
  editor.hass = hass();
  const control = editor._extraControls.mosque_background.control;
  assert.equal(Object.hasOwn(editor._extraControls, "show_mosque_background"), false);
  const updates = [];
  editor.addEventListener("config-changed", event => { updates.push(event.detail.config); editor.setConfig(event.detail.config); });
  control.value = "none"; control.dispatchEvent(new Event("change"));
  assert.equal(updates.at(-1).show_mosque_background, false);
  assert.equal(updates.at(-1).mosque_background, "masjid-al-haram");
  assert.equal(control.value, "none");
  control.value = "daily"; control.dispatchEvent(new Event("change"));
  assert.equal(updates.at(-1).show_mosque_background, true);
  assert.equal(updates.at(-1).mosque_background, "daily");
  assert.equal(editor._extraControls.mosque_background.control, control);
});

test("all main countdown visibility combinations keep the timetable and both dates", () => {
  for (const detail_level of ["standard", "detailed"]) for (const salah of [true, false]) for (const jamaat of [true, false]) {
    const card = new SalahTimetableCard();
    card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level, show_salah_countdown: salah, show_jamaat_countdown: jamaat});
    card.hass = hass(); card._render(Date.parse("2026-10-21T04:40:00Z"));
    assert.equal(find(card.shadowRoot, "section").length, Number(salah) + Number(jamaat));
    assert.equal(find(card.shadowRoot, "div").filter(element => element.className === "month-description").length, 1);
    assert.equal(find(card.shadowRoot, "table").length, 1);
    assert.match(find(card.shadowRoot, "header")[0].textContent, /Hijri \(calculated\)/);
  }
});


test("the sole visible countdown is centred across normal and kiosk modes", () => {
  for (const [detail_level, kiosk_mode] of [
    ["compact", false], ["standard", false], ["detailed", false],
    ["compact", true], ["standard", true], ["detailed", true],
  ]) {
    for (const [salah, jamaat] of [[true, true], [true, false], [false, true], [false, false]]) {
      const card = new SalahTimetableCard();
      card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level, kiosk_mode,
        show_salah_countdown: salah, show_jamaat_countdown: jamaat});
      card.hass = hass();
      card._render(Date.parse("2026-10-21T04:40:00Z"));
      const summary = classNodes(card.shadowRoot, "summary-shell")[0];
      const visible = find(summary, "section").filter(panel => panel.className === "panel prayer-panel");
      const panels = find(summary, "div").filter(element => element.className?.split(" ").includes("panels"));
      const count = Number(salah) + Number(jamaat);
      assert.equal(visible.length, count, `${detail_level}/kiosk=${kiosk_mode}: panel count`);
      assert.equal(panels.length, count ? 1 : 0, "No empty grid when both cards are hidden");
      if (count) {
        assert.equal(panels[0].className, count === 1 ? "panels single-panel" : "panels");
      }
      if (count === 1) {
        assert.equal(visible[0].attributes["data-panel"], salah ? "salah" : "jamaat");
        assert.ok(visible[0].textContent.includes(salah ? "Next Salah" : "Previous Jamaat"));
      }
    }
  }
});

test("ordinary ticks update clocks and progress without rebuilding the table", () => {
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable"}); card.hass = hass();
  card._render(Date.parse("2026-10-21T04:40:00Z"));
  const table = find(card.shadowRoot, "table")[0]; const style = find(card.shadowRoot, "style")[0];
  const clocks = find(card.shadowRoot, "div").filter(element => element.className === "count");
  card._tick(Date.parse("2026-10-21T04:40:01Z"));
  assert.equal(find(card.shadowRoot, "table")[0], table); assert.equal(find(card.shadowRoot, "style")[0], style);
  assert.equal(find(card.shadowRoot, "div").find(element => element.className === "count"), clocks[0]);
  assert.equal(clocks[0].textContent, "00:04:59");
  card._tick(Date.parse("2026-10-21T05:15:00Z"));
  assert.notEqual(find(card.shadowRoot, "table")[0], table);
  assert.equal(find(card.shadowRoot, "tr")[1].className, "past-prayer");
});

test("equivalent timetable and unrelated HA updates retain nodes and ticking clocks", t => {
  const now = Date.parse("2026-10-21T04:40:00Z"); t.mock.method(Date, "now", () => now);
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable"}); card.hass = hass();
  const table = find(card.shadowRoot, "table")[0]; const style = find(card.shadowRoot, "style")[0];
  const clock = find(card.shadowRoot, "div").find(element => element.className === "count");
  const update = hass({...structuredClone(attributes), friendly_name: "New HA name", icon: "mdi:mosque"});
  update.states["sensor.other"] = {state: "on"};
  update.states["sensor.mosque_prayer_timetable"].last_updated = "2026-10-21T04:40:01Z";
  card.hass = update;
  assert.equal(card._hass, update);
  assert.equal(find(card.shadowRoot, "table")[0], table); assert.equal(find(card.shadowRoot, "style")[0], style);
  card._tick(now + 1000);
  assert.equal(find(card.shadowRoot, "div").find(element => element.className === "count"), clock);
  assert.equal(clock.textContent, "00:04:59");
});

test("timetable edits rebuild visible data even when HA reuses its objects", t => {
  t.mock.method(Date, "now", () => Date.parse("2026-10-21T04:40:00Z"));
  const current = hass(structuredClone(attributes)); const data = current.states["sensor.mosque_prayer_timetable"].attributes;
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level: "detailed"}); card.hass = current;
  const edits = [
    [() => { data.mosque_name = "Renamed Mosque"; }, () => assert.equal(find(card.shadowRoot, "h2")[0].textContent, "Renamed Mosque")],
    [() => { data.date = "2026-10-22"; }, () => assert.match(find(card.shadowRoot, "header")[0].textContent, /22 October/)],
    [() => { data.prayers[0].jamaat[0] = "2026-10-21T05:25:00Z"; }, () => assert.match(find(card.shadowRoot, "tbody")[0].textContent, /06:25/)],
    [() => { data.ramadan = {active: true, taraweeh_text: "After Isha Jamaat"}; }, () => assert.match(card.shadowRoot.textContent, /After Isha Jamaat/)],
  ];
  for (const [edit, verify] of edits) {
    const table = find(card.shadowRoot, "table")[0]; edit(); card.hass = current;
    assert.notEqual(find(card.shadowRoot, "table")[0], table); verify();
  }
});

test("new future prayer and Ramadan publications refresh today's countdown", t => {
  t.mock.method(Date, "now", () => Date.parse("2026-10-21T04:40:00Z"));
  const current = hass({...structuredClone(attributes), prayers: [], ramadan: {active: true, sehri: "2026-10-21T04:50:00Z"}});
  const data = current.states["sensor.mosque_prayer_timetable"].attributes;
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level: "detailed"}); card.hass = current;
  const clocks = () => find(card.shadowRoot, "div").filter(element => element.className === "count");
  data.next_salah = {timestamp: "2026-10-21T05:00:00Z", prayer: "fajr"}; card.hass = current;
  assert.equal(clocks()[0].textContent, "00:20:00");
  data.sehri_events = [{timestamp: "2026-10-21T04:45:00Z"}]; card.hass = current;
  assert.equal(clocks()[2].textContent, "00:05:00");
  data.next_iftar = {timestamp: "2026-10-21T17:00:00Z"}; card.hass = current;
  assert.equal(clocks()[3].textContent, "12:20:00");
});

test("HA locale, effective timezone and connection changes refresh the display", t => {
  t.mock.method(Date, "now", () => Date.parse("2026-10-21T04:40:00Z"));
  const current = hass({...structuredClone(attributes), time_zone: null});
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable"}); card.hass = current;
  current.config.time_zone = "UTC"; card.hass = current;
  assert.match(find(card.shadowRoot, "tbody")[0].textContent, /04:45/);
  current.locale.language = "fr"; card.hass = current;
  assert.match(find(card.shadowRoot, "header")[0].textContent, /mercredi/);
  delete current.locale; current.language = "en-GB"; card.hass = current;
  assert.match(find(card.shadowRoot, "header")[0].textContent, /Wednesday/);
  current.connection.connected = false; card.hass = current;
  assert.match(card.shadowRoot.textContent, /Home Assistant disconnected/);
  current.connection.connected = true; card.hass = current;
  assert.doesNotMatch(card.shadowRoot.textContent, /Home Assistant disconnected/);
  current.states["sensor.mosque_prayer_timetable"].attributes.time_zone = "Europe/London"; card.hass = current;
  const table = find(card.shadowRoot, "table")[0]; current.config.time_zone = "Europe/Paris"; card.hass = current;
  assert.equal(find(card.shadowRoot, "table")[0], table, "The mosque timezone takes precedence over HA's timezone");
});

test("availability recovery and entity configuration changes invalidate the rendered data", t => {
  t.mock.method(Date, "now", () => Date.parse("2026-10-21T04:40:00Z"));
  const current = hass(structuredClone(attributes)); const state = current.states["sensor.mosque_prayer_timetable"];
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable"}); card.hass = current;
  for (const value of ["unavailable", "unknown"]) {
    state.state = value; card.hass = current;
    assert.match(card.shadowRoot.textContent, /Timetable unavailable/);
  }
  delete current.states["sensor.mosque_prayer_timetable"]; card.hass = current;
  assert.match(card.shadowRoot.textContent, /entity was not found/);
  state.state = "2026-10-21"; current.states["sensor.mosque_prayer_timetable"] = state; card.hass = current;
  assert.equal(find(card.shadowRoot, "table").length, 1);
  state.attributes.prayers = null; card.hass = current;
  assert.match(card.shadowRoot.textContent, /Timetable unavailable/);
  state.attributes.prayers = structuredClone(attributes.prayers); card.hass = current;
  assert.equal(find(card.shadowRoot, "table").length, 1);
  current.states["sensor.other_mosque"] = {...state, attributes: {...state.attributes, mosque_name: "Other Mosque"}};
  card.setConfig({entity: "sensor.other_mosque", title: "Selected Mosque"});
  assert.equal(find(card.shadowRoot, "select").find(element => element.className === "mosque-select").value, "sensor.other_mosque");
  assert.ok(find(card.shadowRoot, "h2")[0].textContent.includes("Selected Mosque"));
  const table = find(card.shadowRoot, "table")[0]; card.hass = current;
  assert.equal(find(card.shadowRoot, "table")[0], table);
  current.states["sensor.other_mosque"].attributes.prayers = []; card.hass = current;
  assert.equal(find(card.shadowRoot, "tbody")[0].children.length, 0);
});

test("ordinary ticks advance the next Salah and Ramadan clocks without rebuilding the timetable", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level: "detailed"});
  card.hass = hass({...attributes, ramadan: {active: true, sehri: "2026-10-21T04:30:00Z", iftar: "2026-10-21T17:00:00Z"}});
  card._render(Date.parse("2026-10-21T04:20:00Z"));
  const table = find(card.shadowRoot, "table")[0];
  const clocks = find(card.shadowRoot, "div").filter(element => element.className === "count");
  const before = clocks[0].textContent;
  card._tick(Date.parse("2026-10-21T04:20:01Z"));
  assert.equal(find(card.shadowRoot, "table")[0], table);
  assert.notEqual(clocks[0].textContent, before);
  assert.equal(clocks[2].textContent, "00:09:59");
});

function withLanguage(language, data = attributes) {
  const current = hass(data); current.locale.language = language; return current;
}
function classNodes(root, className) { return find(root, "div").filter(element => element.className === className); }


test("automatic Arabic localizes labels, published names, dates and isolated digits", () => {
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable"});
  card.hass = withLanguage("ar-SA-u-nu-arab", {...attributes, prayers: [{...attributes.prayers[0], name: "Backend English Fajr"}]});
  card._render(Date.parse("2026-10-21T04:40:00Z"));
  assert.equal(card.attributes.dir, "rtl"); assert.equal(card.attributes.lang, "ar");
  assert.equal(find(card.shadowRoot, "ha-card")[0].attributes.dir, "rtl");
  const table = find(card.shadowRoot, "table")[0];
  assert.match(table.textContent, /الفجر/); assert.match(table.textContent, /دخول الوقت/); assert.doesNotMatch(table.textContent, /Backend English Fajr/);
  assert.match(classNodes(card.shadowRoot, "count")[0].textContent, /٠٠:٠٥:٠٠/);
  for (const cell of find(table, "td")) assert.ok(find(cell, "bdi").some(run => run.attributes.dir === "ltr"));
  for (const clock of classNodes(card.shadowRoot, "count")) assert.equal(find(clock, "bdi")[0].attributes.dir, "ltr");
  assert.match(find(card.shadowRoot, "header")[0].textContent, /هجري \(محسوب\)/);
  const region = classNodes(card.shadowRoot, "table-scroll")[0];
  assert.equal(region.attributes["aria-label"], tr("ar", "table.region"));
  const timezone = find(card.shadowRoot, "p").find(element => element.attributes["data-role"] === "timezone-note");
  assert.equal(find(timezone, "bdi")[0].textContent, "Europe/London");
  assert.match(find(card.shadowRoot, "style")[0].textContent, /text-align:\s*start/);
  assert.match(find(card.shadowRoot, "style")[0].textContent, /text-align:\s*end/);
});

test("explicit language overrides HA and unsupported label languages retain local date formatting", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", language: "en"}); card.hass = withLanguage("ar-SA");
  card._render(Date.parse("2026-10-21T04:40:00Z"));
  assert.equal(card.attributes.dir, "ltr"); assert.equal(card.attributes.lang, "en");
  assert.match(find(card.shadowRoot, "table")[0].textContent, /Fajr/); assert.match(classNodes(card.shadowRoot, "count")[0].textContent, /00:05:00/);
  card.setConfig({...card._config, language: "ar"});
  assert.equal(card.attributes.dir, "rtl"); assert.match(find(card.shadowRoot, "table")[0].textContent, /الفجر/);
  card.setConfig({...card._config, language: "auto"}); card.hass = withLanguage("fr-FR");
  assert.equal(card.attributes.lang, "en"); assert.match(find(card.shadowRoot, "table")[0].textContent, /Beginning/);
  assert.match(find(card.shadowRoot, "header")[0].textContent, /mercredi/);
  card.hass = withLanguage("not_a_locale");
  assert.equal(card.attributes.lang, "en"); assert.match(find(card.shadowRoot, "header")[0].textContent, /Wednesday/);
});

test("bilingual names isolate both languages while custom published content stays literal", () => {
  const malicious = '<img src=x onerror="alert(1)">';
  const data = {...attributes, mosque_name: malicious, prayers: [...attributes.prayers, {key: "custom", name: malicious, begin: null, jamaat: []}], ramadan: {active: true, taraweeh_text: malicious}};
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable", language: "ar", bilingual_prayer_labels: true}); card.hass = hass(data);
  card._render(Date.parse("2026-10-21T04:40:00Z"));
  const table = find(card.shadowRoot, "table")[0];
  const labels = find(table, "span").find(element => element.className === "prayer-labels");
  assert.deepEqual(find(labels, "bdi").map(run => [run.textContent, run.attributes.lang, run.attributes.dir]), [["الفجر", "ar", "rtl"], ["Fajr", "en", "ltr"]]);
  const custom = find(table, "th").find(element => element.textContent === malicious);
  assert.ok(custom); assert.equal(find(custom, "bdi")[0].attributes.dir, "auto");
  assert.equal(find(card.shadowRoot, "h2")[0].textContent, malicious);
  assert.match(card.shadowRoot.textContent, /<img src=x/); assert.equal(find(card.shadowRoot, "img").length, 0);
  card.setConfig({...card._config, language: "en"});
  const englishLabels = find(find(card.shadowRoot, "table")[0], "span").find(element => element.className === "prayer-labels");
  assert.deepEqual(find(englishLabels, "bdi").map(run => run.attributes.lang), ["en", "ar"]);
});

test("Arabic empty, unavailable, disconnected and Ramadan states use the catalog", () => {
  const card = new SalahTimetableCard(); card.setConfig({language: "ar"});
  assert.equal(find(card.shadowRoot, "ha-card")[0].textContent, tr("ar", "card.choose_entity"));
  card.setConfig({entity: "sensor.mosque_prayer_timetable", language: "ar"}); card.hass = {states: {}};
  assert.equal(find(card.shadowRoot, "ha-card")[0].textContent, tr("ar", "card.entity_missing"));
  card.hass = {states: {"sensor.mosque_prayer_timetable": {state: "unavailable", attributes}}};
  assert.equal(find(card.shadowRoot, "ha-card")[0].textContent, tr("ar", "card.unavailable"));
  const current = withLanguage("ar", {...attributes, prayers: [], next_salah: null, next_jamaat: null, previous_jamaat: null, ramadan: {active: true}}); current.connection.connected = false;
  card.setConfig({entity: "sensor.mosque_prayer_timetable", language: "ar", detail_level: "detailed"}); card.hass = current; card._render(Date.parse("2026-10-21T04:40:00Z"));
  for (const key of ["card.disconnected", "status.unavailable", "ramadan.title", "ramadan.sehri_ends", "ramadan.iftar", "ramadan.taraweeh", "ramadan.no_time"]) assert.ok(card.shadowRoot.textContent.includes(tr("ar", key)), key);
  assert.equal(card.shadowRoot.textContent.includes(tr("ar", "panel.no_event")), false, "empty prayer panels use the unavailable state rather than the removed no-event label");
});

test("Arabic ticks retain table and numeric runs while crossing a passed boundary refreshes selection", () => {
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable", language: "ar", detail_level: "detailed"});
  card.hass = withLanguage("ar-SA-u-nu-arab", {...attributes, ramadan: {active: true, sehri: "2026-10-21T04:40:02Z", iftar: "2026-10-21T17:00:00Z"}});
  card._render(Date.parse("2026-10-21T04:40:00Z"));
  const table = find(card.shadowRoot, "table")[0]; const clocks = classNodes(card.shadowRoot, "count"); const run = find(clocks[0], "bdi")[0];
  card._tick(Date.parse("2026-10-21T04:40:01Z"));
  assert.equal(find(card.shadowRoot, "table")[0], table); assert.equal(classNodes(card.shadowRoot, "count")[0], clocks[0]); assert.equal(find(clocks[0], "bdi")[0], run);
  assert.equal(clocks[0].textContent, "٠٠:٠٤:٥٩"); assert.equal(clocks[2].textContent, "٠٠:٠٠:٠١");
  card._tick(Date.parse("2026-10-21T04:40:03Z"));
  assert.notEqual(find(card.shadowRoot, "table")[0], table);
  const sehri = classNodes(card.shadowRoot, "ramadan-grid")[0].children.find(element => element.attributes["data-ramadan"] === "sehri");
  assert.match(sehri.textContent, new RegExp(tr("ar", "status.passed")));
});

test("editor language changes localize existing controls", () => {
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: "sensor.mosque_prayer_timetable"}); editor.hass = hass();
  const language = editor._extraControls.language.control; const bilingual = editor._extraControls.bilingual_prayer_labels.control;
  editor.hass = withLanguage("ar-SA");
  assert.equal(editor.attributes.dir, "rtl"); assert.equal(editor.attributes.lang, "ar");
  assert.equal(find(editor.shadowRoot, "ha-selector").length, 0, "No duplicate sensor selector");
  assert.deepEqual(editor._extraControls.detail_level.control.children.map(option => option.value), ["compact", "standard", "detailed"]);
  assert.equal(language.attributes["aria-label"], tr("ar", "editor.language"));
  assert.deepEqual(language.children.map(option => option.value), ["auto", "en", "ar"]);
  const changes = []; editor.addEventListener("config-changed", event => { changes.push(event.detail.config); editor.setConfig(event.detail.config); });
  language.value = "en"; language.dispatchEvent(new Event("change"));
  bilingual.checked = true; bilingual.dispatchEvent(new Event("change"));
  assert.equal(editor.attributes.dir, "ltr"); assert.equal(language.attributes["aria-label"], tr("en", "editor.language"));
  assert.equal(editor._extraControls.language.control, language); assert.equal(editor._extraControls.bilingual_prayer_labels.control, bilingual);
  assert.equal(changes.at(-1).language, "en"); assert.equal(changes.at(-1).bilingual_prayer_labels, true);
  assert.equal(Object.hasOwn(changes.at(-1), "اللغة"), false);
});

test("editor validation errors follow the UI language without changing YAML values", () => {
  const editor = new SalahTimetableCardEditor(); editor.hass = withLanguage("ar");
  let emitted = false; editor.addEventListener("config-changed", () => { emitted = true; });
  assert.equal(find(editor.shadowRoot, "ha-selector").length, 0);
  assert.equal(emitted, false);
  editor.hass = hass();
  assert.equal(find(editor.shadowRoot, "ha-selector").length, 0);
  for (const Type of [SalahTimetableCard, SalahTimetableCardEditor]) {
    const element = new Type(); element.hass = withLanguage("ar");
    assert.throws(() => element.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level: "invalid"}), {message: tr("ar", "config.detail_level")});
    assert.throws(() => element.setConfig({language: "ar", title: "x".repeat(101)}), {message: tr("ar", "config.title")});
  }
});

test("localized Fajr end, Friday khutbah and mosque Hijri visibility preserve the merged features", () => {
  const friday = {...attributes, date: "2026-10-23", second_khutbah: "2026-10-23T13:00:00Z", show_hijri_date: false,
    prayers: [{key: "fajr", name: "Fajr", begin: "2026-10-23T04:45:00Z", end: "2026-10-23T06:30:00Z", jamaat: []}, {key: "dhuhr", name: "Dhuhr", begin: "2026-10-23T11:55:00Z", jamaat: ["2026-10-23T12:25:00Z"]}],
    jamaat_events: [{timestamp: "2026-10-23T12:25:00Z", prayer: "jumuah", field: "jumuah"}]};
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable", language: "ar", bilingual_prayer_labels: true, detail_level: "detailed"}); card.hass = withLanguage("ar-SA-u-nu-arab", friday);
  card._render(Date.parse("2026-10-23T11:00:00Z"));
  assert.doesNotMatch(find(card.shadowRoot, "header")[0].textContent, /هجري/);
  const end = classNodes(card.shadowRoot, "note fajr-end")[0]; assert.match(end.textContent, /الشروق/); assert.match(end.textContent, /٠٧:٣٠/); assert.equal(find(end, "bdi")[0].attributes.dir, "ltr");
  const khutbah = find(card.shadowRoot, "p").find(element => element.className === "note khutbah"); assert.match(khutbah.textContent, /خطبة الجمعة الثانية/); assert.equal(find(khutbah, "bdi")[0].attributes.dir, "ltr");
  const jumuah = find(card.shadowRoot, "tr").find(row => row.children[0]?.textContent.includes("الجمعة"));
  assert.ok(jumuah, "Friday heading is Jumu'ah in Arabic as well as English");
  assert.match(jumuah.textContent, /Jumu’ah/);
  const current = hass({...friday, show_hijri_date: true}); card.hass = current;
  assert.match(find(card.shadowRoot, "header")[0].textContent, /هجري \(محسوب\)/);
  current.states["sensor.mosque_prayer_timetable"].attributes.date = "2026-10-22"; card.hass = current;
  assert.equal(find(card.shadowRoot, "p").some(element => element.className === "note khutbah"), false);
});

test("two configured mosques are both selectable as independent dashboard cards", () => {
  const multi = hass();
  multi.states["sensor.second_mosque_prayer_timetable"] = {
    state: "2026-10-21", attributes: {...attributes, mosque_name: "Second Mosque"}
  };
  multi.states["sensor.second_mosque_fajr_beginning"] = {state: "2026-10-21T04:45:00Z", attributes: {}};
  const editor = new SalahTimetableCardEditor();
  editor.hass = multi;
  const rows = () => editor._controls.mosqueList.children;
  assert.equal(find(editor.shadowRoot, "ha-selector").length, 0);
  assert.equal(rows().length, 2);
  assert.match(rows()[0].textContent, /Example Mosque/);
  assert.match(rows()[1].textContent, /Second Mosque/);
  const emitted = [];
  editor.addEventListener("config-changed", event => { emitted.push(event.detail.config); editor.setConfig(event.detail.config); });
  find(rows()[1], "button").find(button => button.className === "mosque-move-up").dispatchEvent(new Event("click"));
  assert.equal(emitted.at(-1).entity, "sensor.second_mosque_prayer_timetable");
  const first = new SalahTimetableCard();
  first.setConfig({entity: "sensor.mosque_prayer_timetable"});
  first.hass = multi;
  const second = new SalahTimetableCard();
  second.setConfig(emitted.at(-1));
  second.hass = multi;
  assert.match(first.shadowRoot.textContent, /Example Mosque/);
  assert.match(second.shadowRoot.textContent, /Second Mosque/);
  assert.equal(window.customCards.filter(card => card.type === "salah-timetable-card").length, 1, "One composite card type serves every mosque");

  editor.hass = {states: {}};
  assert.deepEqual(
    rows().map(row => row.attributes["data-mosque-row"]),
    ["sensor.second_mosque_prayer_timetable", "sensor.mosque_prayer_timetable"],
    "Stored ordered mosque selections remain editable while unavailable"
  );
});

test("bundled background shows photographer credit and local URL", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable"});
  card.hass = hass();
  card._render(Date.parse("2026-10-21T04:40:00Z"));
  const surface = find(card.shadowRoot, "ha-card")[0];
  assert.equal(surface.classList.contains("has-mosque-background"), true);
  assert.match(surface.style.values["--mosque-background-image"], /^url\("\/salah_timetable\/backgrounds\//);
  const [link] = find(card.shadowRoot, "a");
  assert.ok(link.href.startsWith("https://unsplash.com/photos/"));
  assert.equal(link.rel, "noopener noreferrer");
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_mosque_background: false});
  assert.equal(find(card.shadowRoot, "a").length, 0);
});

test("coming-soon history settings cannot be enabled from the editor", () => {
  const editor = new SalahTimetableCardEditor(); editor.hass = hass();
  const keys = ["show_historical_day_events", "show_historical_month_highlights", "show_historical_sources", "show_disputed_historical_dates"];
  const changes = []; editor.addEventListener("config-changed", event => changes.push(event.detail.config));
  for (const key of keys) {
    const field = editor._extraControls[key].control;
    assert.equal(field.disabled, true, key);
    field.checked = true; field.dispatchEvent(new Event("change"));
  }
  assert.equal(changes.length, 0, "Disabled history controls never write unimplemented settings");
});

test("card filter allows separate fixed mosque cards and a selectable multi-mosque card", () => {
  const multi = hass();
  const a = "sensor.mosque_prayer_timetable", b = "sensor.second_mosque_prayer_timetable";
  multi.states[b] = {state: "2026-10-21", attributes: {...attributes, mosque_name: "Second Mosque"}};
  const editor = new SalahTimetableCardEditor();
  editor.setConfig({entity: a}); editor.hass = multi;
  const choices = () => find(editor._controls.mosqueList, "input");
  assert.equal(choices().length, 2);
  assert.deepEqual(choices().map(c => c.checked), [true, true], "Old cards default to all mosques");
  const changes = []; editor.addEventListener("config-changed", event => { changes.push(event.detail.config); editor.setConfig(event.detail.config); });
  choices()[1].checked = false; choices()[1].dispatchEvent(new Event("change"));
  assert.deepEqual(changes.at(-1).mosque_entities, [a]);
  assert.equal(choices()[0].disabled, true, "The last enabled mosque cannot be unchecked");
  const fixed = new SalahTimetableCard(); fixed.setConfig(changes.at(-1)); fixed.hass = multi;
  assert.equal(classNodes(fixed.shadowRoot, "mosque-select").length, 0);
  assert.match(find(fixed.shadowRoot, "h2")[0].textContent, /Example Mosque/);

  choices()[1].checked = true; choices()[1].dispatchEvent(new Event("change"));
  assert.deepEqual(changes.at(-1).mosque_entities, [a, b]);
  const switching = new SalahTimetableCard(); switching.setConfig(changes.at(-1)); switching.hass = multi;
  const chooser = find(switching.shadowRoot, "select").find(select => select.className === "mosque-select");
  assert.equal(chooser.children.length, 2);
  assert.equal(chooser.value, a);
  chooser.value = b;
  chooser.dispatchEvent(new Event("change"));
  assert.match(find(switching.shadowRoot, "h2")[0].textContent, /Second Mosque/);
  assert.equal(switching._activeEntity(), b);
  const secondFixed = new SalahTimetableCard(); secondFixed.setConfig({entity: b, mosque_entities: [b]}); secondFixed.hass = multi;
  assert.equal(classNodes(secondFixed.shadowRoot, "mosque-select").length, 0);
  assert.match(find(secondFixed.shadowRoot, "h2")[0].textContent, /Second Mosque/);
  assert.equal(fixed._activeEntity(), a, "Switching one card must not affect another");
});

test("day navigation updates Hijri, Gregorian and month information without duplicate selected date", () => {
  const card = new SalahTimetableCard();
  const base = "2026-10-28";
  const data = {...attributes, date: base, day_prayers: {"2026-10-27": attributes.prayers, "2026-10-29": attributes.prayers}};
  card.setConfig({entity: "sensor.mosque_prayer_timetable"});
  card.hass = hass(data);
  const dateTabs = () => find(card.shadowRoot, "nav").find(element => element.className === "date-tabs");
  const header = () => find(card.shadowRoot, "header")[0];
  for (const [offset, expected] of [[-1, "2026-10-27"], [1, "2026-10-29"], [0, base]]) {
    dateTabs().children[offset + 1].dispatchEvent(new Event("click"));
    const parts = header().children;
    assert.equal(parts[1].textContent, `${formatHijriDate(expected, 0, "en")} · Hijri (calculated)`);
    assert.equal(parts[2].textContent, formatDate(expected, {locale: "en-GB"}));
    assert.equal(parts[3].textContent, hijriMonthInfo(expected, 0).summary_en);
    assert.equal(find(card.shadowRoot, "div").filter(element => element.className === "selected-date").length, 0);
    assert.equal(card._selectedDay, offset);
    assert.equal(find(card.shadowRoot, "table").length, 1);
  }
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_gregorian_date: false});
  dateTabs().children[2].dispatchEvent(new Event("click"));
  assert.equal(find(card.shadowRoot, "div").filter(element => element.className === "selected-date").length, 1,
    "Adjacent-day timetable retains its date when Gregorian header is disabled");
});

test("mosque photo retains Today's canvas across tabs and invalidates on width change", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable"});
  card.hass = hass();
  card.shadowRoot.querySelector = selector => selector === "ha-card" ? find(card.shadowRoot, "ha-card")[0] : null;
  const first = find(card.shadowRoot, "ha-card")[0];
  first.getBoundingClientRect = () => ({width: 900, height: 720});
  const tabs = () => find(card.shadowRoot, "nav").find(element => element.className === "date-tabs");
  tabs().children[2].dispatchEvent(new Event("click"));
  assert.equal(card._selectedDay, 1);
  assert.deepEqual(card._backgroundFrame, {entity: "sensor.mosque_prayer_timetable", width: 900, height: 720});
  const tomorrow = find(card.shadowRoot, "ha-card")[0];
  assert.equal(tomorrow.style.values["--mosque-photo-frame-height"], "716px");
  assert.equal(tomorrow.style.values["--mosque-photo-frame-width"], "898px");
  // A small dashboard width change (e.g. disappearing scrollbar) is not a
  // meaningful device resize and must not re-crop the image.
  tomorrow.getBoundingClientRect = () => ({width: 886, height: 550});
  tabs().children[0].dispatchEvent(new Event("click"));
  const yesterday = find(card.shadowRoot, "ha-card")[0];
  assert.equal(yesterday.style.values["--mosque-photo-frame-height"], "716px");
  assert.equal(yesterday.style.values["--mosque-photo-frame-width"], "898px");
  // Conversely a substantial change should invalidate both photo dimensions.
  yesterday.getBoundingClientRect = () => ({width: 800, height: 550});
  tabs().children[1].dispatchEvent(new Event("click"));
  const resized = find(card.shadowRoot, "ha-card")[0];
  assert.equal(resized.style.values["--mosque-photo-frame-height"], undefined,
    "A genuinely resized card must not reuse an obsolete photo height");
  assert.equal(resized.style.values["--mosque-photo-frame-width"], undefined,
    "A genuinely resized card must not reuse an obsolete photo width");
});

test("compact timetable puts date controls after the table and preserves adjacent-date access", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_mosque_background: false});
  card.hass = hass();
  const shell = classNodes(card.shadowRoot, "timetable-shell")[0];
  assert.ok(shell);
  assert.equal(shell.children[0].className, "table-scroll");
  assert.equal(shell.children.at(-1).className, "date-tabs");
  const [yesterday, today] = shell.children.at(-1).children;
  assert.equal(today.attributes["aria-pressed"], "true");
  yesterday.dispatchEvent(new Event("click"));
  assert.equal(card._selectedDay, -1);
  assert.equal(find(card.shadowRoot, "table").length, 0, "Missing dates do not borrow today's timetable");
  assert.match(card.shadowRoot.textContent, /No approved timetable/);
  assert.equal(find(card.shadowRoot, "nav").filter(element => element.className === "date-tabs").length, 1, "Day controls survive an unavailable date");
  const nextToday = find(card.shadowRoot, "nav").find(element => element.className === "date-tabs").children[1];
  nextToday.dispatchEvent(new Event("click"));
  assert.equal(card._selectedDay, 0);
  assert.equal(find(card.shadowRoot, "table").length, 1);
  assert.equal(find(card.shadowRoot, "nav").find(element => element.className === "date-tabs").children[1].attributes["aria-pressed"], "true");
});

test("minaret and dome silhouettes are decorative, month subtitle does not duplicate the heading", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable"});
  card.hass = hass();
  const icons = find(card.shadowRoot, "span").filter(element => element.className === "panel-silhouette");
  assert.equal(icons.length, 2);
  assert.deepEqual(icons.map(icon => icon.attributes["aria-hidden"]), ["true", "true"]);
  assert.equal(find(card.shadowRoot, "svg").length, 2);
  const month = find(card.shadowRoot, "div").find(element => element.className === "month-description");
  assert.ok(month);
  assert.match(month.textContent, /fifth month/i);
  assert.equal(find(card.shadowRoot, "details").length, 0);
  assert.equal(find(card.shadowRoot, "section").filter(element => element.className === "panel hijri-month-info").length, 0);
});

test("mosque selection preserves missing sensors, automatically includes new primary and validates filters", () => {
  const a = "sensor.mosque_prayer_timetable", b = "sensor.second_mosque_prayer_timetable";
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: a, mosque_entities: [a]}); editor.hass = hass();
  editor.addEventListener("config-changed", event => editor.setConfig(event.detail.config));
  assert.deepEqual(editor._config.mosque_entities, [a]);
  const multi = hass(); multi.states[b] = {state: "2026-10-21", attributes: {...attributes, mosque_name: "Second Mosque"}};
  editor.hass = multi;
  const choices = find(editor._controls.mosqueList, "input");
  choices[1].checked = true;
  choices[1].dispatchEvent(new Event("change"));
  assert.deepEqual(editor._config.mosque_entities, [a,b]);
  const missing = new SalahTimetableCard(); missing.setConfig({entity: b, mosque_entities: [b]}); missing.hass = hass();
  assert.equal(missing._activeEntity(), b);
  assert.match(missing.shadowRoot.textContent, /entity was not found/);
  editor.hass = hass(); 
  assert.equal(find(editor._controls.mosqueList, "input").length, 2, "Missing chosen mosque remains editable");
  for (const mosque_entities of [[], ["sensor.fajr", "sensor.fajr"], ["switch.bad"], "oops"]) {
    assert.throws(() => new SalahTimetableCard().setConfig({entity: a, mosque_entities}));
  }
});


test("monthly view queries only the selected mosque and displays missing days", async () => {
  const card = new SalahTimetableCard();
  const api = hass();
  const requests = [];
  api.callWS = async message => {
    requests.push(message);
    if (message.type === "salah_timetable/month") return {rows: [
      {date: "2026-10-21", published: true, times: {fajr_begin: ["05:45"], fajr_jamaat: ["06:15"]}},
      {date: "2026-10-22", published: false, times: {}},
    ]};
    if (message.type === "salah_timetable/sources") return {sources: [
      {source_id: "approved", first_date: "2026-01-01", last_date: "2026-12-31", rows: 365, format: "csv", check_status: "approved"},
    ]};
    throw new Error("Unexpected request");
  };
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_month_view: true});
  card.hass = api;
  assert.equal(find(card.shadowRoot, "section").filter(el => el.className === "monthly-shell").length, 0);
  const toggle = find(card.shadowRoot, "button").find(el => el.className === "month-toggle");
  toggle.dispatchEvent(new Event("click"));
  await Promise.resolve();
  assert.equal(requests[0].type, "salah_timetable/month");
  assert.equal(requests[0].entity_id, "sensor.mosque_prayer_timetable");
  assert.equal(requests[0].year, 2026);
  assert.match(card.shadowRoot.textContent, /05:45/);
  assert.match(card.shadowRoot.textContent, /2026/);
  const source = find(card.shadowRoot, "button").find(el => el.attributes["aria-label"] === "Source details");
  source.dispatchEvent(new Event("click"));
  await Promise.resolve();
  assert.equal(requests.at(-1).type, "salah_timetable/sources");
  assert.match(card.shadowRoot.textContent, /approved: 2026-01-01/);
  find(card.shadowRoot, "button").find(el => el.className === "month-toggle").dispatchEvent(new Event("click"));
  assert.equal(card._monthView, false);
});

test("month view defaults off and validates a strict boolean", () => {
  assert.equal(normalizeConfig({}).show_month_view, false);
  assert.equal(normalizeConfig({show_month_view: true}).show_month_view, true);
  assert.throws(() => normalizeConfig({show_month_view: "yes"}));
});


test("kiosk 3.0 renders the three-zone display from published prayers and respects options", () => {
  const card = new SalahTimetableCard();
  const entity = "sensor.mosque_prayer_timetable";
  const date = "2026-10-21";
  const instant = (hour, minute) => date + "T" + String(hour).padStart(2, "0") +
    ":" + String(minute).padStart(2, "0") + ":00Z";
  const rows = [
    ["fajr", 4, 45, 5, 15], ["dhuhr", 11, 45, 13, 0],
    ["asr", 14, 10, 14, 45], ["maghrib", 16, 29, 16, 32],
    ["isha", 18, 26, 20, 0],
  ].map(([key, h, m, jh, jm]) => ({key, name: key,
    begin: instant(h, m), jamaat: [instant(jh, jm)]}));
  const data = {...attributes, date, prayers: rows, show_hijri_date: true,
    day_prayers: {"2026-10-20": rows, "2026-10-22": rows},
    beginning_events: rows.map(row => ({prayer: row.key, timestamp: row.begin})),
    jamaat_events: rows.map(row => ({prayer: row.key, timestamp: row.jamaat[0]}))};
  const start = Date.parse(instant(4, 40));
  card.setConfig({entity, kiosk_mode: true, detail_level: "compact",
    show_month_view: true, show_timezone_note: true,
    show_hijri_date: true, show_gregorian_date: true, show_hijri_month_info: true});
  card.hass = hass(data);
  card._render(start);
  const header = find(card.shadowRoot, "header")[0];
  const identity = find(header, "div").find(element => element.className === "kiosk-identity");
  const toolbar = find(card.shadowRoot, "div").find(element => element.className === "kiosk-toolbar");
  const dates = find(header, "div").find(element => element.className === "kiosk-dates");
  const clock = find(header, "time")[0];
  const strip = find(card.shadowRoot, "section").find(element => element.className === "kiosk-strip");
  const footer = find(card.shadowRoot, "footer")[0];
  assert.ok(identity);
  assert.match(identity.textContent, /Example Mosque/);
  assert.match(identity.textContent, /Europe\/London/);
  assert.ok(dates);
  assert.equal(clock.textContent, "05:40");
  assert.ok(find(dates, "div").some(element => element.className === "date hijri"));
  assert.ok(find(dates, "div").some(element => element.className === "date gregorian"));
  assert.ok(find(dates, "div").some(element => element.className === "month-description"));
  assert.ok(header.children.findIndex(child => child.className === "kiosk-clock") <
    header.children.indexOf(dates));
  assert.ok(strip);
  assert.equal(strip.children.length, 5, "Five prayer tiles use only published source rows");
  assert.deepEqual(strip.children.map(tile => tile.attributes["data-prayer"]),
    ["fajr", "dhuhr", "asr", "maghrib", "isha"]);
  assert.match(strip.textContent, /05:45/);
  assert.match(strip.textContent, /21:00/, "Published 20:00 UTC is 21:00 in Europe/London during BST");
  assert.ok(strip.children[0].className.includes("is-next"));
  assert.equal(find(card.shadowRoot, "table").length, 0, "Kiosk has no duplicate scrolling timetable");

  const tabs = find(card.shadowRoot, "nav").find(element => element.className === "date-tabs");
  assert.equal(footer.children[1], tabs);
  assert.equal(footer.children[2], toolbar);
  const summary = find(card.shadowRoot, "div").find(element => element.className === "summary-shell");
  const fullscreen = summary.children.find(child => child.className === "kiosk-fullscreen");
  assert.ok(fullscreen, "Fullscreen icon is a direct child of the glass summary");
  assert.equal(fullscreen.textContent, "", "Only the icon is visible, not button text");
  assert.equal(fullscreen.children[0].tagName, "ha-icon");
  assert.equal(fullscreen.children[0].attributes.icon, "mdi:fullscreen");
  assert.equal(fullscreen.attributes["aria-label"], "Enter fullscreen");
  assert.equal(fullscreen.attributes["aria-pressed"], "false");
  assert.ok(!toolbar.children.some(child => child.className === "kiosk-fullscreen"),
    "The previous footer fullscreen button is removed");
  assert.ok(toolbar.children.some(child => child.className === "card-actions-menu"),
    "Compact monthly actions stay in More disclosure");
  card._tick(start + 60000);
  assert.equal(find(card.shadowRoot, "time")[0], clock);
  assert.equal(clock.textContent, "05:41");

  card._render(Date.parse(instant(16, 15)));
  const nextStrip = find(card.shadowRoot, "section").find(element => element.className === "kiosk-strip");
  assert.ok(nextStrip.children[3].className.includes("is-next"), "Next published beginning is Maghrib");
  assert.ok(nextStrip.children[2].className.includes("is-current"), "Latest begun Salah is Asr");
  const changedTabs = find(card.shadowRoot, "nav").find(element => element.className === "date-tabs");
  changedTabs.children[2].dispatchEvent(new Event("click"));
  const tomorrowFooter = find(card.shadowRoot, "footer")[0];
  assert.ok(tomorrowFooter.children.some(child => child.className === "date-tabs"),
    "Adjacent dates retain bottom controls");
  assert.equal(find(card.shadowRoot, "section").find(element => element.className === "kiosk-strip").children.length, 5);
  find(card.shadowRoot, "nav").find(element => element.className === "date-tabs")
    .children[1].dispatchEvent(new Event("click"));

  card.setConfig({entity, kiosk_mode: true, detail_level: "compact", time_format: "12h",
    show_hijri_date: false, show_gregorian_date: false, show_timezone_note: false});
  card._render(start);
  assert.equal(find(card.shadowRoot, "div").filter(element => element.className === "kiosk-dates").length, 0);
  assert.equal(find(card.shadowRoot, "small").filter(element => element.className === "kiosk-timezone").length, 0);
  assert.match(find(card.shadowRoot, "time")[0].textContent, /05:40\s*am/i);
  assert.equal(find(card.shadowRoot, "div").filter(element => element.className === "kiosk-footer-note").length, 0);

  card.setConfig({entity, kiosk_mode: true, detail_level: "compact",
    show_hijri_date: true, show_gregorian_date: true});
  card.hass = hass({...data, show_hijri_date: false});
  card._render(start);
  const mosqueDates = find(card.shadowRoot, "div").find(element => element.className === "kiosk-dates");
  assert.ok(find(mosqueDates, "div").some(element => element.className === "date gregorian"));
  assert.ok(!find(mosqueDates, "div").some(element => element.className === "date hijri"));

  card.setConfig({entity, detail_level: "standard"});
  assert.equal(find(card.shadowRoot, "time").length, 0, "Non-kiosk has no live wall clock");
  assert.equal(find(card.shadowRoot, "section").filter(element => element.className === "kiosk-strip").length, 0);
  assert.equal(find(card.shadowRoot, "table").length, 1, "Normal timetable remains unchanged");
});

test("kiosk fullscreen icon enters, exits and follows external Escape", () => {
  const card = new SalahTimetableCard();
  const entity = "sensor.mosque_prayer_timetable";
  card.setConfig({entity, kiosk_mode: true, show_month_view: true});
  card.hass = hass();
  const summary = find(card.shadowRoot, "div").find(element => element.className === "summary-shell");
  const fullscreen = summary.children.find(child => child.className === "kiosk-fullscreen");
  const surface = find(card.shadowRoot, "ha-card")[0];
  const oldFullscreen = document.fullscreenElement;
  const oldExit = document.exitFullscreen;
  let enters = 0, exits = 0;
  card.shadowRoot.querySelector = selector => selector === "ha-card" ? surface : null;
  surface.requestFullscreen = () => {
    enters++;
    document.fullscreenElement = surface;
    card._onFullscreenChange();
    return Promise.resolve();
  };
  document.exitFullscreen = () => {
    exits++;
    document.fullscreenElement = null;
    card._onFullscreenChange();
    return Promise.resolve();
  };
  try {
    assert.equal(fullscreen.attributes["aria-label"], "Enter fullscreen");
    assert.equal(fullscreen.children[0].attributes.icon, "mdi:fullscreen");
    fullscreen.dispatchEvent(new Event("click"));
    assert.equal(enters, 1, "First tap requests fullscreen on this card only");
    assert.equal(document.fullscreenElement, surface);
    assert.equal(fullscreen.attributes["aria-label"], "Exit fullscreen");
    assert.equal(fullscreen.attributes["aria-pressed"], "true");
    assert.equal(fullscreen.children[0].attributes.icon, "mdi:fullscreen-exit");

    fullscreen.dispatchEvent(new Event("click"));
    assert.equal(exits, 1, "Second tap exits fullscreen to the previous view");
    assert.equal(document.fullscreenElement, null);
    assert.equal(fullscreen.attributes["aria-label"], "Enter fullscreen");
    assert.equal(fullscreen.attributes["aria-pressed"], "false");
    assert.equal(fullscreen.children[0].attributes.icon, "mdi:fullscreen");

    fullscreen.dispatchEvent(new Event("click"));
    document.fullscreenElement = null;
    card._onFullscreenChange();
    assert.equal(fullscreen.attributes["aria-label"], "Enter fullscreen",
      "Esc and external fullscreen exits must restore the expand icon");
    assert.equal(fullscreen.children[0].attributes.icon, "mdi:fullscreen");
  } finally {
    if (oldFullscreen === undefined) delete document.fullscreenElement;
    else document.fullscreenElement = oldFullscreen;
    if (oldExit === undefined) delete document.exitFullscreen;
    else document.exitFullscreen = oldExit;
  }
});

test("kiosk distinguishes tomorrow's Salah and the next published Jamaat", () => {
  const entity = "sensor.mosque_prayer_timetable";
  const card = new SalahTimetableCard();
  const start = Date.parse("2026-10-21T18:28:00Z");
  const rows = [
    ["fajr", "04:45", "05:15"], ["dhuhr", "11:45", "13:00"],
    ["asr", "14:10", "14:45"], ["maghrib", "16:29", "16:32"],
    ["isha", "18:26", "20:00"],
  ].map(([key, begin, jamaat]) => ({
    key, name: key,
    begin: `2026-10-21T${begin}:00Z`,
    jamaat: [`2026-10-21T${jamaat}:00Z`],
  }));
  const data = {
    ...attributes, date: "2026-10-21", time_zone: "Europe/London",
    prayers: rows,
    beginning_events: rows.map(row => ({timestamp: row.begin, prayer: row.key})),
    jamaat_events: rows.map(row => ({timestamp: row.jamaat[0], prayer: row.key})),
    next_salah: {timestamp: "2026-10-22T04:45:00Z", prayer: "fajr"},
  };
  card.setConfig({entity, kiosk_mode: true});
  card.hass = hass(data);
  card._render(start);
  const day = find(card.shadowRoot, "span").find(element => element.className === "kiosk-next-day");
  assert.equal(day?.textContent, "Tomorrow", "Next Salah's day is relative to the mosque timezone");
  assert.equal(day?.attributes["data-role"], "next-salah-day");
  const isha = find(card.shadowRoot, "div").find(element => element.attributes["data-prayer"] === "isha");
  assert.ok(isha?.className.includes("is-next-jamaat"), "Upcoming Isha Jamaat gets a subtle tile outline");
  assert.equal(isha?.attributes["data-next-jamaat"], "true");
  assert.ok(!isha.className.includes("is-next "), "Tomorrow's Fajr should not highlight today's Isha as next beginning");
  assert.equal(find(card.shadowRoot, "div").filter(element => element.attributes["data-next-jamaat"] === "true").length, 1);

  // A UTC date can still be tomorrow in Europe/London (BST).
  card.hass = hass({...data, next_salah: {timestamp: "2026-10-21T23:10:00Z", prayer: "fajr"}});
  card._render(start);
  assert.equal(find(card.shadowRoot, "span").find(element => element.className === "kiosk-next-day")?.textContent, "Tomorrow");
  card.hass = hass({...data, time_zone: "UTC", next_salah: {timestamp: "2026-10-21T23:10:00Z", prayer: "fajr"}});
  card._render(start);
  assert.equal(find(card.shadowRoot, "span").filter(element => element.className === "kiosk-next-day").length, 0,
    "Same UTC day must not be mislabelled Tomorrow");

  // Previous Jamaat is not an upcoming congregation and should not highlight a tile.
  card.hass = hass({...data, next_salah: {timestamp: "2026-10-22T04:45:00Z", prayer: "fajr"}});
  card._render(Date.parse("2026-10-21T20:10:00Z"));
  assert.equal(find(card.shadowRoot, "div").filter(element => element.attributes["data-next-jamaat"] === "true").length, 0);
  card.setConfig({entity});
  assert.equal(find(card.shadowRoot, "span").filter(element => element.className === "kiosk-next-day").length, 0,
    "Normal dashboard modes are unchanged");
});

test("reminder setup lives in the editor and follows administrator and kiosk changes", () => {
  const card = new SalahTimetableCard();
  const editor = new SalahTimetableCardEditor();
  const state = hass();
  card.setConfig({entity: "sensor.mosque_prayer_timetable"});
  card.hass = {...state, user: {is_admin: true}};
  assert.equal(find(card.shadowRoot, "button").filter(button => button.textContent === "Prayer reminders").length, 0);
  editor.setConfig({entity: "sensor.mosque_prayer_timetable"});
  const action = () => find(editor.shadowRoot, "button").find(button => button.className === "reminder-setup");
  assert.equal(action().hidden, true);
  editor.hass = {...state, user: {is_admin: true}};
  assert.equal(action().hidden, false);
  const form = find(editor.shadowRoot, "div").find(element => element.className === "form");
  assert.equal(form.children[form.children.indexOf(action()) - 1], editor._extraControls.detail_level.field);
  editor.hass = {...state, user: {is_admin: false}};
  assert.equal(action().hidden, true);
  editor.hass = {...state, user: {is_admin: true}, states: {}};
  assert.equal(action().hidden, false);
  editor.setConfig({entity: "sensor.mosque_prayer_timetable", kiosk_mode: true});
  assert.equal(action().hidden, true);
});

test("monthly action is labelled beside the mosque name in Standard and Detailed; Compact uses More", () => {
  const card = new SalahTimetableCard(); card.hass = hass();
  for (const detail_level of ["compact", "standard", "detailed"]) {
    card.setConfig({entity: "sensor.mosque_prayer_timetable", show_month_view: true, detail_level});
    const header = find(card.shadowRoot, "header")[0];
    const action = find(card.shadowRoot, "button").find(button => button.className === "month-toggle");
    assert.ok(action);
    assert.equal(action.attributes["aria-label"], "Monthly timetable");
    assert.equal(action.title, "Monthly timetable");
    assert.equal(action.attributes["aria-expanded"], "false");
    assert.equal(find(action, "ha-icon")[0].attributes.icon, "mdi:calendar-month");
    assert.ok(find(header, "button").includes(action), "The action stays in the header for every mode");
    assert.ok(find(action, "span").some(span => span.textContent === "Monthly timetable"),
      "The labelled action is visible in both Compact More and full-sized toolbars");
    assert.equal(find(card.shadowRoot, "details").some(item => item.className === "card-actions-menu"), detail_level === "compact");
    assert.equal(find(card.shadowRoot, "nav").some(item => item.className === "card-action-strip"), detail_level !== "compact");
    assert.equal(find(card.shadowRoot, "nav").some(item => item.className === "card-actions-footer"), false);
  }
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_month_view: false});
  assert.equal(find(card.shadowRoot, "button").some(button => button.className === "month-toggle"), false);
});


test("ordered mosque list uses a dedicated drag handle and arrow fallback", () => {
  const a = "sensor.mosque_prayer_timetable", b = "sensor.second_mosque_prayer_timetable";
  const multi = hass();
  multi.states[b] = {state: "2026-10-21", attributes: {...attributes, mosque_name: "Second Mosque"}};
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: a, mosque_entities: [a, b]}); editor.hass = multi;
  editor.addEventListener("config-changed", event => editor.setConfig(event.detail.config));
  const rows = () => editor._controls.mosqueList.children;
  assert.equal(find(editor.shadowRoot, "ha-selector").length, 0);
  assert.equal(rows()[0].draggable, undefined, "The row itself must not initiate dragging");
  const handles = () => find(editor._controls.mosqueList, "button").filter(item => item.className === "mosque-grip");
  assert.equal(handles().length, 2);
  assert.equal(handles()[0].draggable, true);
  assert.equal(find(handles()[0], "ha-icon")[0].attributes.icon, "mdi:drag-vertical");
  assert.match(rows()[0].textContent, /Shown first/);
  const moved = find(rows()[1], "button").find(item => item.className === "mosque-move-up");
  moved.dispatchEvent(new Event("click"));
  assert.deepEqual(editor._config.mosque_entities, [b, a]);
  assert.equal(editor._config.entity, b);
  assert.match(rows()[0].textContent, /Shown first/);
  const card = new SalahTimetableCard(); card.setConfig({entity: a, mosque_entities: [b, a]}); card.hass = multi;
  assert.equal(card._activeEntity(), b, "Ordered first mosque wins over legacy entity");
  const data = new Map();
  const transfer = {setData(type, value) { data.set(type, value); }, getData(type) { return data.get(type); }};
  handles()[1].dispatchEvent({type: "dragstart", dataTransfer: transfer});
  rows()[0].dispatchEvent({type: "drop", preventDefault() {}, dataTransfer: transfer});
  assert.deepEqual(editor._config.mosque_entities, [a, b]);
  const checkboxes = find(editor._controls.mosqueList, "input");
  checkboxes[1].checked = false;
  checkboxes[1].dispatchEvent(new Event("change"));
  assert.equal(handles()[1].disabled, true);
  assert.equal(find(rows()[1], "button").find(item => item.className === "mosque-move-up").disabled, true);
});

function widgetAttributes() {
  return {...attributes,
    day_prayers: {"2026-10-21": attributes.prayers, "2026-10-22": attributes.prayers},
    jamaat_events: [
      {field: "fajr_jamaat", prayer: "fajr", timestamp: "2026-10-21T05:15:00Z"},
      {field: "fajr_jamaat", prayer: "fajr", timestamp: "2026-10-22T05:00:00Z"},
    ],
    config_entry_id: "example-entry",
    timetable_health: {
      coverage: {status: "expiring", available_through: "2026-10-22", days_remaining: 1, today_available: true, tomorrow_available: true},
      completeness: {status: "complete", required_fields: ["fajr_begin"], missing_today: [], missing_tomorrow: []},
      source: {status: "not_configured", pending_review: true, error_count: 0},
    },
  };
}
test("new widgets stay opt-in and share read-only sections with standalone cards", () => {
  const data = widgetAttributes();
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable"}); card.hass = hass(data);
  assert.ok(!card.shadowRoot.textContent.includes("15 min earlier"));
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_jamaat_changes: true, show_timetable_health: true});
  const sections = find(card.shadowRoot, "section");
  assert.ok(sections.some(section => section.attributes["data-section"] === "jamaat_changes"));
  assert.ok(sections.some(section => section.attributes["data-section"] === "timetable_health"));
  assert.ok(card.shadowRoot.textContent.includes("15 min earlier"));
  const Changes = registry.get("salah-widget-jamaat-changes");
  const widget = new Changes(); widget.setConfig({entity: "sensor.mosque_prayer_timetable"}); widget.hass = hass(data);
  assert.equal(widget._config.type, "custom:salah-widget-jamaat-changes");
  assert.equal(widget._config.show_mosque_background, false);
  assert.ok(widget.shadowRoot.textContent.includes("15 min earlier"));
  assert.equal(find(widget.shadowRoot, "table").length, 0);
});
test("health refreshes on pending changes and only administrators get setup navigation", () => {
  const Health = registry.get("salah-widget-timetable-health");
  const widget = new Health(); widget.setConfig({entity: "sensor.mosque_prayer_timetable"});
  const data = widgetAttributes(); const state = hass(data);
  widget.hass = state;
  assert.equal(find(widget.shadowRoot, "a").length, 0);
  widget.hass = {...state, user: {is_admin: true}};
  assert.ok(find(widget.shadowRoot, "a")[0].href.endsWith("?config_entry=example-entry"));
  data.timetable_health.source.pending_review = false;
  widget.hass = {...state, user: {is_admin: true}};
  assert.equal(find(widget.shadowRoot, "a")[0].textContent, "Open mosque setup");
  widget.hass = {...state, connection: {connected: false}};
  assert.equal(find(widget.shadowRoot, "a").length, 0);
  assert.ok(widget.shadowRoot.textContent.includes("unavailable"));
});
test("grouped widgets synchronize mosque and reject an excluded selection without fallback", () => {
  const data = widgetAttributes();
  const state = hass(data);
  state.states["sensor.other_prayer_timetable"] = {state: data.date, attributes: {...data, mosque_name: "Other mosque"}};
  const Selector = registry.get("salah-widget-mosque-selector");
  const selector = new Selector(); selector.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "example"}); selector.hass = state; selector.connectedCallback();
  const Health = registry.get("salah-widget-timetable-health");
  const health = new Health(); health.setConfig({entity: "sensor.mosque_prayer_timetable", mosque_entities: ["sensor.mosque_prayer_timetable"], selection_group: "example"}); health.hass = state; health.connectedCallback();
  selector._selectMosque("sensor.other_prayer_timetable");
  assert.equal(health._activeEntity(), "sensor.other_prayer_timetable");
  assert.ok(health.shadowRoot.textContent.includes("not enabled"));
  assert.ok(!health.shadowRoot.textContent.includes("approved through"));
  health.preview = true;
  selector._selectMosque("sensor.mosque_prayer_timetable");
  assert.equal(health._group, null, "Preview leaves live group");
  health.disconnectedCallback(); selector.disconnectedCallback();
  assert.equal(timers.size, 0);
});
test("standalone editor exposes its own settings without an ineffective hide toggle", () => {
  const editor = new SalahTimetableCardEditor();
  editor.setConfig({type: "custom:salah-widget-jamaat-changes", entity: "sensor.mosque_prayer_timetable"}); editor.hass = hass();
  const options = find(editor.shadowRoot, "ha-switch").map(item => item.attributes["data-option"]);
  assert.ok(!options.includes("show_jamaat_changes"));
  assert.ok(!options.includes("show_hijri_date"));
  assert.ok(find(editor.shadowRoot, "input").some(item => item.attributes["data-option"] === "selection_group"));
});

test("today's complete status does not claim tomorrow's missing fields are complete", () => {
  const Health = registry.get("salah-widget-timetable-health");
  const widget = new Health(); widget.setConfig({entity: "sensor.mosque_prayer_timetable"});
  const data = widgetAttributes(); data.timetable_health.completeness.missing_tomorrow = ["fajr_begin"];
  widget.hass = hass(data);
  assert.ok(!widget.shadowRoot.textContent.includes("complete for today and tomorrow"));
  assert.ok(widget.shadowRoot.textContent.includes("Missing tomorrow"));
});


test("standalone cards retain photographer attribution when backgrounds are explicitly enabled", () => {
  const Health = registry.get("salah-widget-timetable-health");
  const widget = new Health();
  widget.setConfig({entity: "sensor.mosque_prayer_timetable", show_mosque_background: true}); widget.hass = hass(widgetAttributes());
  assert.ok(find(widget.shadowRoot, "small").some(item => item.className === "background-credit"));
  assert.ok(find(widget.shadowRoot, "a").some(item => item.textContent.startsWith("Photo:")));
});


function arrangedSections(card) {
  return find(card.shadowRoot, "section").filter(item => item.className === "arrangement-section");
}
test("custom arrangements order shared sections and show an explicitly enabled Compact timetable", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level: "compact", show_timetable: true, show_dates: true,
    arrangement: {sections: [{id: "timetable", width: "full"}, {id: "jamaat", width: "half"}, {id: "salah", width: "half"}]}});
  card.hass = hass(widgetAttributes());
  const sections = arrangedSections(card);
  assert.deepEqual(sections.slice(0, 3).map(item => item.attributes["data-section"]), ["timetable", "jamaat", "salah"]);
  assert.equal(sections[1].attributes["data-width"], "half");
  assert.equal(find(card.shadowRoot, "table").length, 1);
  assert.ok(sections.some(item => item.attributes["data-section"] === "dates"));
  assert.equal(find(card.shadowRoot, "nav").filter(item => item.className === "date-tabs").length, 1);
});
test("all ten standalone sections register with correct stub types and relevant independent content", () => {
  const ids = ["mosque-selector", "dates", "clock", "salah", "jamaat", "timetable", "ramadan", "night-calculations", "jamaat-changes", "timetable-health"];
  const data = widgetAttributes();
  data.ramadan = {active: true, sehri: "2026-10-21T04:45:00Z", iftar: "2026-10-21T17:00:00Z"};
  data.night_calculations = {midpoint: "2026-10-21T23:00:00Z", last_third: "2026-10-22T01:00:00Z"};
  for (const id of ids) {
    const Widget = registry.get(`salah-widget-${id}`);
    assert.ok(Widget, id);
    assert.equal(Widget.getStubConfig(hass()).type, `custom:salah-widget-${id}`);
    const card = new Widget(); card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level: "compact"}); card.hass = hass(data);
    card._render(Date.parse("2026-10-21T03:00:00Z"));
    if (!["mosque-selector", "jamaat-changes", "timetable-health"].includes(id)) assert.deepEqual(arrangedSections(card).map(item => item.attributes["data-section"]), [id.replaceAll("-", "_")]);
    assert.equal(find(card.shadowRoot, "table").length, id === "timetable" ? 1 : 0);
  }
});
test("standalone clock uses the host tick and conditional widgets explain inactive data", () => {
  const Clock = registry.get("salah-widget-clock");
  const clock = new Clock(); clock.setConfig({entity: "sensor.mosque_prayer_timetable"}); clock.hass = hass();
  clock._render(Date.parse("2026-10-21T03:00:00Z"));
  const time = find(clock.shadowRoot, "time")[0];
  assert.equal(time.textContent, "04:00");
  clock._tick(Date.parse("2026-10-21T03:01:00Z"));
  assert.equal(time.textContent, "04:01");
  for (const [id, message] of [["ramadan", "Ramadan"], ["night-calculations", "night"]]) {
    const Widget = registry.get(`salah-widget-${id}`); const card = new Widget();
    card.setConfig({entity: "sensor.mosque_prayer_timetable"}); card.hass = hass();
    assert.ok(card.shadowRoot.textContent.includes(message));
    assert.equal(arrangedSections(card).length, 1);
  }
});
test("custom kiosk keeps fullscreen fixed and puts day navigation inside the movable timetable", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", kiosk_mode: true, arrangement: {sections: [{id: "clock", width: "full"}, {id: "timetable", width: "full"}]}});
  card.hass = hass(widgetAttributes());
  const sections = arrangedSections(card);
  assert.equal(sections[0].attributes["data-section"], "clock");
  const table = sections.find(item => item.attributes["data-section"] === "timetable");
  assert.ok(find(table, "nav").some(item => item.className.includes("date-tabs")));
  assert.equal(find(card.shadowRoot, "button").filter(item => item.className === "kiosk-fullscreen").length, 1);
  assert.ok(find(card.shadowRoot, "div").some(item => item.className === "arrangement-toolbar"));
});
test("main editor offers a live isolated Layout tab and Reset removes saved placement", () => {
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "house"}); editor.hass = hass();
  const tab = find(editor.shadowRoot, "button").find(item => item.attributes["data-editor-tab"] === "layout");
  tab.dispatchEvent(new Event("click"));
  assert.ok(editor._layoutRoot);
  const preview = find(editor._layoutRoot, "custom-element").find(item => item instanceof SalahTimetableCard);
  assert.ok(preview?.preview);
  assert.equal(preview._config.selection_group, "");
  const preset = find(editor._layoutRoot, "select").find(item => item.attributes["data-layout-preset"] !== undefined);
  preset.value = "balanced"; preset.dispatchEvent(new Event("change"));
  assert.ok(editor._config.arrangement);
  const reset = find(editor._layoutRoot, "button").find(item => item.attributes["data-layout-reset"] !== undefined);
  reset.dispatchEvent(new Event("click"));
  assert.equal(editor._config.arrangement, undefined);
  assert.equal(editor._config.selection_group, "house");
  editor.disconnectedCallback();
  assert.equal(editor._layoutRoot, null);
});


test("hiding the timetable cancels adjacent-day and monthly browsing so live panels remain reachable", () => {
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable", show_month_view: true}); card.hass = hass(widgetAttributes());
  card._selectedDay = 1; card._monthView = true; card._monthState = {loading: true};
  const request = card._monthRequest;
  card.setConfig({...card._config, show_timetable: false, arrangement: {sections: [{id: "salah", width: "full"}]}});
  assert.equal(card._selectedDay, 0);
  assert.equal(card._monthView, false);
  assert.equal(card._monthState, null);
  assert.ok(card._monthRequest > request);
  assert.ok(arrangedSections(card).some(item => item.attributes["data-section"] === "salah"));
});
test("standalone widgets and custom arrangements use automatic Sections dashboard height", () => {
  const Health = registry.get("salah-widget-timetable-health");
  const widget = new Health(); widget.setConfig({entity: "sensor.mosque_prayer_timetable"});
  assert.equal(widget.getGridOptions().rows, "auto");
  assert.equal(widget.getGridOptions().min_rows, 1);
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable"});
  assert.equal(typeof card.getGridOptions().rows, "number");
  card.setConfig({...card._config, arrangement: {sections: []}});
  assert.equal(card.getGridOptions().rows, "auto");
});
test("custom widget identity uses a saved title only for the primary mosque", () => {
  const primary = "sensor.mosque_prayer_timetable", other = "sensor.other_prayer_timetable";
  const state = hass(widgetAttributes());
  state.states[other] = {state: attributes.date, attributes: {...widgetAttributes(), mosque_name: "Other mosque"}};
  for (const type of ["custom:salah-widget-salah", "custom:salah-timetable-card"]) {
    const Card = type.endsWith("widget-salah") ? registry.get("salah-widget-salah") : SalahTimetableCard;
    const card = new Card();
    card.setConfig({type, entity: primary, title: "Home", show_mosque_selector: false, arrangement: {sections: []}});
    card.hass = state;
    const identity = () => {
      const label = find(card.shadowRoot, "div").find(item => item.className === "widget-mosque-name");
      if (label) return label.textContent;
      const chooser = find(card.shadowRoot, "select").find(item => item.className === "mosque-select");
      if (chooser) return find(chooser, "option").find(item => item.value === chooser.value)?.textContent;
      return find(card.shadowRoot, "h2")[0]?.textContent;
    };
    assert.equal(identity(), "Home");
    card._selectMosque(other); card._render();
    assert.equal(identity(), "Other mosque");
  }
});
test("Jamaat-change widgets honor bilingual prayer labels and direction metadata", () => {
  const Changes = registry.get("salah-widget-jamaat-changes");
  const card = new Changes(); card.setConfig({entity: "sensor.mosque_prayer_timetable", language: "en"});
  card.hass = hass(widgetAttributes());
  assert.ok(!card.shadowRoot.textContent.includes("الفجر"));
  card.setConfig({...card._config, bilingual_prayer_labels: true});
  assert.ok(card.shadowRoot.textContent.includes("Fajr / الفجر"));
  assert.ok(find(card.shadowRoot, "span").some(item => item.attributes.lang === "ar" && item.attributes.dir === "rtl"));
});
test("arrangement validation uses localized messages and tab navigation has one keyboard stop", () => {
  for (const language of ["en", "ar"]) {
    const card = new SalahTimetableCard();
    for (const invalid of [{arrangement: {sections: [{id: "unknown", width: "full"}]}}, {selection_group: 42}, {type: "custom:unknown"}]) {
      assert.throws(() => card.setConfig({...invalid, language}), error => !error.message.startsWith("config.") && (language === "en" || /[\u0600-\u06ff]/.test(error.message)));
    }
  }
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: "sensor.mosque_prayer_timetable"}); editor.hass = hass();
  assert.ok(editor._sections.history.body.children.some(item => item.className === "editor-soon-note"));
  let focused = null;
  for (const [id, button] of Object.entries(editor._tabButtons)) button.focus = () => { focused = id; };
  assert.equal(editor._tabButtons.settings.tabIndex, 0);
  assert.equal(editor._tabButtons.layout.tabIndex, -1);
  const right = new Event("keydown", {cancelable: true}); Object.defineProperty(right, "key", {value: "ArrowRight"});
  editor._tabButtons.settings.dispatchEvent(right);
  assert.equal(editor._activeTab, "layout"); assert.equal(focused, "layout");
  assert.equal(editor._tabButtons.settings.tabIndex, -1);
  assert.equal(editor._tabButtons.layout.tabIndex, 0);
  const home = new Event("keydown", {cancelable: true}); Object.defineProperty(home, "key", {value: "Home"});
  editor._tabButtons.layout.dispatchEvent(home);
  assert.equal(editor._activeTab, "settings"); assert.equal(focused, "settings");
  editor.disconnectedCallback();
});

test("linked standalone widgets share mosque choice without repeated dropdowns", () => {
  const state = hass(widgetAttributes());
  state.states["sensor.other_prayer_timetable"] = {state: attributes.date, attributes: {...widgetAttributes(), mosque_name: "Other mosque"}};
  const Health = registry.get("salah-widget-timetable-health");
  const Selector = registry.get("salah-widget-mosque-selector");
  const linked = new Health();
  linked.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "home"});
  linked.hass = state;
  assert.equal(find(linked.shadowRoot, "select").length, 0);
  assert.ok(find(linked.shadowRoot, "h2").some(item => item.textContent === "Example Mosque"));
  assert.equal(linked.hasAttribute("data-standalone"), true);
  const separate = new Health();
  separate.setConfig({entity: "sensor.mosque_prayer_timetable"});
  separate.hass = state;
  assert.ok(find(separate.shadowRoot, "select").length > 0);
  const central = new Selector();
  central.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "home"});
  central.hass = state;
  assert.ok(find(central.shadowRoot, "select").length > 0);
  const main = new SalahTimetableCard();
  main.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "home"});
  main.hass = state;
  assert.ok(find(main.shadowRoot, "select").length > 0);
});

test("Advanced makes mosque synchronisation opt-in and retains existing groups", () => {
  const editor = new SalahTimetableCardEditor();
  editor.setConfig({entity: "sensor.mosque_prayer_timetable"}); editor.hass = hass();
  assert.ok(find(editor._sections.advanced.body, "ha-switch").includes(editor._groupSyncControl));
  assert.ok(find(editor._sections.advanced.body, "input").includes(editor._groupControl));
  assert.equal(editor._groupSyncControl.checked, false);
  assert.equal(editor._groupNameField.hidden, true);
  editor._groupSyncControl.checked = true;
  editor._groupSyncControl.dispatchEvent(new Event("change"));
  assert.equal(editor._config.selection_group, "home");
  assert.equal(editor._groupNameField.hidden, false);
  editor._groupControl.value = "kitchen"; editor._groupControl.dispatchEvent(new Event("change"));
  assert.equal(editor._config.selection_group, "kitchen");
  editor._groupSyncControl.checked = false; editor._groupSyncControl.dispatchEvent(new Event("change"));
  assert.equal(editor._config.selection_group, "");
  editor.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "legacy-linked"});
  assert.equal(editor._groupSyncControl.checked, true);
  assert.equal(editor._groupControl.value, "legacy-linked");
});

test("all other standalone sections retain a chooser only when independent", () => {
  const state = hass(widgetAttributes());
  state.states["sensor.other_prayer_timetable"] = {state: attributes.date, attributes: {...widgetAttributes(), mosque_name: "Other mosque"}};
  for (const id of ["dates", "clock", "salah", "jamaat", "timetable", "ramadan", "night-calculations"]) {
    const Card = registry.get(`salah-widget-${id}`);
    const unlinked = new Card();
    unlinked.setConfig({entity: "sensor.mosque_prayer_timetable"});
    unlinked.hass = state;
    assert.ok(find(unlinked.shadowRoot, "select").length > 0, `${id} allows independent choice`);
    const linked = new Card();
    linked.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "home"});
    linked.hass = state;
    assert.equal(find(linked.shadowRoot, "select").length, 0, `${id} follows linked choice`);
  }
});
