import test from "node:test";
import assert from "node:assert/strict";

class Element {
  constructor(tagName = "custom-element") { this.tagName = tagName; this.children = []; this.listeners = new Map(); this._text = ""; this.attributes = {}; }
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
globalThis.document = {createElement: name => registry.has(name) ? new (registry.get(name))() : new Element(name)};
globalThis.window = {setInterval: callback => { timers.set(++timerId, callback); return timerId; }, clearInterval: id => timers.delete(id), customCards: []};
const {SalahTimetableCard, SalahTimetableCardEditor} = await import("../../custom_components/salah_timetable/frontend/salah-timetable-card.js");
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

test("card renders local times, missing states and theme-responsive layout", () => {
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable"}); card.hass = hass(); card._render(Date.parse("2026-10-21T04:40:00Z"));
  assert.match(card.shadowRoot.textContent, /Example Mosque/); assert.match(card.shadowRoot.textContent, /05:45/); assert.match(card.shadowRoot.textContent, /00:05:00/);
  assert.match(find(card.shadowRoot, "style")[0].textContent, /--primary-text-color/); assert.match(find(card.shadowRoot, "style")[0].textContent, /max-width:420px/);
  card.hass = {states: {}}; assert.match(card.shadowRoot.textContent, /entity was not found/);
  card.hass = {states: {"sensor.mosque_prayer_timetable": {state: "unavailable", attributes}}}; assert.match(card.shadowRoot.textContent, /Timetable unavailable/);
});

test("card lifecycle ticks locally and releases its interval", () => {
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable"}); card.hass = hass();
  card.connectedCallback(); card.connectedCallback(); assert.equal(timers.size, 1);
  const stateBefore = JSON.stringify(card._hass.states); [...timers.values()][0](); assert.equal(JSON.stringify(card._hass.states), stateBefore);
  card.disconnectedCallback(); assert.equal(timers.size, 0);
});

test("Ramadan text and imported titles use text nodes, never markup", () => {
  const malicious = '<img src=x onerror="alert(1)">'; const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", title: malicious});
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

test("editor round trips entity, mode and title through config-changed", () => {
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: "", mode: "context"}); editor.hass = hass(); const emitted = [];
  editor.addEventListener("config-changed", event => emitted.push(event.detail.config));
  const [entity, mode] = find(editor.shadowRoot, "ha-selector");
  assert.equal(entity.selector.entity.filter[0].integration, "salah_timetable");
  entity.dispatchEvent(new CustomEvent("value-changed", {detail: {value: "sensor.mosque_prayer_timetable"}}));
  mode.dispatchEvent(new CustomEvent("value-changed", {detail: {value: "upcoming"}}));
  const title = find(editor.shadowRoot, "input")[0]; title.value = "My Mosque"; title.dispatchEvent(new Event("input"));
  assert.deepEqual(emitted.at(-1), {type: "custom:salah-timetable-card", entity: "sensor.mosque_prayer_timetable", mode: "upcoming", title: "My Mosque"});
  const reconstructed = new SalahTimetableCardEditor(); reconstructed.setConfig(emitted.at(-1)); reconstructed.hass = hass();
  assert.equal(find(reconstructed.shadowRoot, "ha-selector")[1].value, "upcoming"); assert.equal(find(reconstructed.shadowRoot, "input")[0].value, "My Mosque");
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
