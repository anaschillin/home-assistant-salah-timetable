import test from "node:test";
import assert from "node:assert/strict";

class Element {
  constructor(tagName = "custom-element") { this.tagName = tagName; this.children = []; this.listeners = new Map(); this._text = ""; this.attributes = {}; this.classes = new Set(); this.classList = {add: name => this.classes.add(name), contains: name => this.classes.has(name)}; this.style = {values: {}, setProperty(name, value) { this.values[name] = value; }}; }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(""); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this._text = ""; this.children = children; }
  setAttribute(name, value) { this.attributes[name] = value; }
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
const {formatDate, formatHijriDate, hijriMonthInfo} = await import("../../custom_components/salah_timetable/frontend/card-utils.js");
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
  assert.equal(window.customCards.length, 1);
  assert.equal(SalahTimetableCard.getConfigElement() instanceof SalahTimetableCardEditor, true);
  assert.equal(SalahTimetableCard.getStubConfig(hass()).entity, "sensor.mosque_prayer_timetable");
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
    const groups = contents().filter(element => element.className === "panels");
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
  const dhuhr = rows.find(row => row.textContent.includes("Dhuhr"));

  assert.ok(dhuhr, "Dhuhr row should exist");
  assert.match(dhuhr.textContent, /Jumu[’\']?ah\s+13:25/);
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

test("editor round trips entity, detail level and title through config-changed", () => {
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: "", mode: "context"}); editor.hass = hass(); const emitted = [];
  editor.addEventListener("config-changed", event => emitted.push(event.detail.config));
  const [entity] = find(editor.shadowRoot, "ha-selector");
  assert.deepEqual(entity.selector.select.options.map(option => option.value), ["sensor.mosque_prayer_timetable"]);
  entity.dispatchEvent(new CustomEvent("value-changed", {detail: {value: "sensor.mosque_prayer_timetable"}}));
  editor._extraControls.detail_level.control.value = "detailed"; editor._extraControls.detail_level.control.dispatchEvent(new Event("change"));
  const title = find(editor.shadowRoot, "input")[0]; title.value = "My Mosque"; title.dispatchEvent(new Event("input"));
  assert.deepEqual(emitted.at(-1), {...new SalahTimetableCardEditor()._config, type: "custom:salah-timetable-card", entity: "sensor.mosque_prayer_timetable", detail_level: "detailed", title: "My Mosque"});
  const reconstructed = new SalahTimetableCardEditor(); reconstructed.setConfig(emitted.at(-1)); reconstructed.hass = hass();
  assert.equal(reconstructed._extraControls.detail_level.control.value, "detailed"); assert.equal(find(reconstructed.shadowRoot, "input")[0].value, "My Mosque");
});

test("editor rejects an individual prayer entity rather than emitting a broken card", () => {
  const editor = new SalahTimetableCardEditor(); editor.hass = {states: {"sensor.fajr": {attributes: {}}}}; let emitted = false; editor.addEventListener("config-changed", () => { emitted = true; });
  find(editor.shadowRoot, "ha-selector")[0].dispatchEvent(new CustomEvent("value-changed", {detail: {value: "sensor.fajr"}}));
  assert.equal(emitted, false); assert.match(editor.shadowRoot.textContent, /rather than an individual prayer sensor/);
});


test("editor preserves controls across config echoes and hass updates", () => {
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: "sensor.mosque_prayer_timetable"}); editor.hass = hass();
  const input = find(editor.shadowRoot, "input")[0];
  editor.addEventListener("config-changed", event => editor.setConfig(event.detail.config));
  input.value = "A longer mosque title"; input.dispatchEvent(new Event("input"));
  editor.hass = hass({...attributes, mosque_name: "Renamed"});
  assert.equal(find(editor.shadowRoot, "input")[0], input);
  assert.equal(input.value, "A longer mosque title");
});


test("editor title is a labelled native input without removed HA controls", () => {
  const editor = new SalahTimetableCardEditor(); editor.hass = hass();
  const input = find(editor.shadowRoot, "input")[0];
  const label = find(editor.shadowRoot, "label")[0];
  assert.equal(input.type, "text"); assert.equal(input.maxLength, 100);
  assert.equal(label.htmlFor, input.id); assert.equal(label.textContent, "Title (optional)");
  assert.equal(find(editor.shadowRoot, "ha-textfield").length, 0);
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
    if (entry.checkbox) control.checked = false;
    else control.value = ({language: "ar", detail_level: "compact", time_format: "12h", hijri_adjustment: "-2", hijri_day_boundary: "maghrib", mosque_background: "masjid-al-haram"})[key];
    control.dispatchEvent(new Event("change")); editor.hass = hass();
    assert.equal(editor._extraControls[key].control, control);
    assert.equal(changes.at(-1)[key], entry.checkbox ? false : key === "hijri_adjustment" ? Number(control.value) : control.value);
  }
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

test("editor language changes localize existing controls without replacing a focused title", () => {
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: "sensor.mosque_prayer_timetable", title: "My مسجد"}); editor.hass = hass();
  const title = editor._controls.title; const language = editor._extraControls.language.control; const bilingual = editor._extraControls.bilingual_prayer_labels.control;
  title.selectionStart = 1; title.selectionEnd = 5; editor.shadowRoot.activeElement = title;
  editor.hass = withLanguage("ar-SA");
  assert.equal(editor.attributes.dir, "rtl"); assert.equal(editor.attributes.lang, "ar");
  assert.equal(editor._controls.title, title); assert.equal(title.value, "My مسجد"); assert.equal(title.selectionStart, 1); assert.equal(title.selectionEnd, 5);
  assert.equal(editor._controls.titleLabel.textContent, tr("ar", "editor.title"));
  assert.equal(editor._controls.entity.label, tr("ar", "editor.entity"));
  assert.deepEqual(editor._extraControls.detail_level.control.children.map(option => option.value), ["compact", "standard", "detailed"]);
  assert.equal(language.attributes["aria-label"], tr("ar", "editor.language"));
  assert.deepEqual(language.children.map(option => option.value), ["auto", "en", "ar"]);
  const changes = []; editor.addEventListener("config-changed", event => { changes.push(event.detail.config); editor.setConfig(event.detail.config); });
  language.value = "en"; language.dispatchEvent(new Event("change"));
  bilingual.checked = true; bilingual.dispatchEvent(new Event("change"));
  assert.equal(editor.attributes.dir, "ltr"); assert.equal(editor._controls.titleLabel.textContent, "Title (optional)");
  assert.equal(editor._extraControls.language.control, language); assert.equal(editor._extraControls.bilingual_prayer_labels.control, bilingual);
  assert.equal(editor._controls.title, title); assert.equal(title.selectionStart, 1); assert.equal(title.selectionEnd, 5);
  assert.equal(changes.at(-1).language, "en"); assert.equal(changes.at(-1).bilingual_prayer_labels, true);
  assert.equal(Object.hasOwn(changes.at(-1), "اللغة"), false);
});

test("editor validation errors follow the UI language without changing YAML values", () => {
  const editor = new SalahTimetableCardEditor(); editor.hass = withLanguage("ar");
  let emitted = false; editor.addEventListener("config-changed", () => { emitted = true; });
  editor._controls.entity.dispatchEvent(new CustomEvent("value-changed", {detail: {value: "sensor.fajr"}}));
  assert.equal(emitted, false); assert.equal(editor._controls.error.textContent, tr("ar", "editor.invalid_entity"));
  const error = editor._controls.error; editor.hass = hass();
  assert.equal(editor._controls.error, error); assert.equal(error.textContent, tr("en", "editor.invalid_entity"));
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
  const dhuhr = find(card.shadowRoot, "tr").find(row => row.textContent.includes("الظهر")); assert.match(dhuhr.textContent, /الجمعة/); assert.match(dhuhr.textContent, /Jumu’ah/);
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
  const options = find(editor.shadowRoot, "ha-selector")[0].selector.select.options;
  assert.deepEqual(options.map(option => option.value), [
    "sensor.mosque_prayer_timetable", "sensor.second_mosque_prayer_timetable"
  ]);
  assert.match(options[0].label, /Example Mosque/);
  assert.match(options[1].label, /Second Mosque/);
  const emitted = [];
  editor.addEventListener("config-changed", event => emitted.push(event.detail.config));
  find(editor.shadowRoot, "ha-selector")[0].dispatchEvent(
    new CustomEvent("value-changed", {detail: {value: "sensor.second_mosque_prayer_timetable"}})
  );
  assert.equal(emitted.at(-1).entity, "sensor.second_mosque_prayer_timetable");
  const first = new SalahTimetableCard();
  first.setConfig({entity: "sensor.mosque_prayer_timetable"});
  first.hass = multi;
  const second = new SalahTimetableCard();
  second.setConfig(emitted.at(-1));
  second.hass = multi;
  assert.match(first.shadowRoot.textContent, /Example Mosque/);
  assert.match(second.shadowRoot.textContent, /Second Mosque/);
  assert.equal(window.customCards.length, 1, "One reusable card type serves every mosque");

  editor.hass = {states: {}};
  assert.deepEqual(
    find(editor.shadowRoot, "ha-selector")[0].selector.select.options.map(option => option.value),
    ["sensor.second_mosque_prayer_timetable"],
    "Stored card selections remain editable while their sensor is unavailable"
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
  editor._controls.entity.dispatchEvent(new CustomEvent("value-changed", {detail: {value: a}}));
  assert.deepEqual(editor._config.mosque_entities, [a]);
  const multi = hass(); multi.states[b] = {state: "2026-10-21", attributes: {...attributes, mosque_name: "Second Mosque"}};
  editor.hass = multi;
  editor._controls.entity.dispatchEvent(new CustomEvent("value-changed", {detail: {value: b}}));
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
