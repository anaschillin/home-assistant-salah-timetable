import test from "node:test";
import assert from "node:assert/strict";

class Element {
  constructor(tagName = "custom-element") {
    this.tagName = tagName;
    this.children = [];
    this.listeners = new Map();
    this.dataset = {};
    this.attributes = {};
    this._text = "";
    this.isConnected = true;
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(""); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this._text = ""; this.children = children; }
  setAttribute(key, value) { this.attributes[key] = value; }
  attachShadow() { this.shadowRoot = new Element("shadow-root"); return this.shadowRoot; }
  addEventListener(type, handler) { if (!this.listeners.has(type)) this.listeners.set(type, []); this.listeners.get(type).push(handler); }
  dispatchEvent(event) { for (const callback of this.listeners.get(event.type) || []) callback(event); }
  showModal() { this.open = true; }
  close() { this.open = false; }
  remove() { this.isConnected = false; }
  focus() { document.activeElement = this; }
  querySelector(selector) { return descendants(this).find(item => selector.startsWith("[data-key=") && item.dataset.key === selector.slice(11, -2)); }
}
const registry = new Map();
globalThis.HTMLElement = Element;
globalThis.customElements = {get: name => registry.get(name), define: (name, type) => registry.set(name, type)};
globalThis.document = {body: new Element("body"), activeElement: null, createElement: name => registry.has(name) ? new (registry.get(name))() : new Element(name)};
const {SalahReminderWizard, openReminderWizard} = await import("../../custom_components/salah_timetable/frontend/reminder-wizard.js");
const descendants = element => [element, ...element.children.flatMap(descendants)];
const nodes = wizard => descendants(wizard.shadowRoot);
const button = (wizard, label) => nodes(wizard).find(node => node.tagName === "button" && node.textContent === label);
const input = (wizard, key) => nodes(wizard).find(node => node.tagName === "input" && node.dataset.key === key);
const click = (wizard, label) => {
  const element = button(wizard, label);
  assert.ok(element, `Missing button ${label}`);
  assert.equal(element.disabled, false);
  element.dispatchEvent(new Event("click"));
};
const choose = (wizard, key, checked = true) => {
  const element = input(wizard, key); assert.ok(element, `Missing checkbox ${key}`);
  element.checked = checked; element.dispatchEvent(new Event("change"));
};
const type = (wizard, key, value) => {
  const element = input(wizard, key); assert.ok(element, `Missing input ${key}`);
  element.value = value; element.dispatchEvent(new Event("input"));
};
const fields = [{value: "fajr_begin", label: "Fajr beginning"}, {value: "fajr_jamaat", label: "Fajr Jamaat"}, {value: "jumuah", label: "Jumu’ah Jamaat"}];
const mosque = id => ({id, name: `Masjid ${id}`, time_zone: "Europe/London", fields, ready: true});
const options = count => ({mosques: Array.from({length: count}, (_, index) => mosque(String(index + 1))), notification_actions: [{value: "notify.mobile_app_phone", label: "Phone Companion app"}], notification_entities: [{value: "notify.tablet", label: "Tablet"}]});
function mockHass(count = 1) {
  const writes = [], previews = [];
  const hass = {
    states: {"media_player.hall": {attributes: {friendly_name: "Hall speaker"}}},
    async callWS(payload) {
      if (payload.type === "salah_timetable/reminder_options") return options(count);
      previews.push(payload); return {config: {alias: payload.name, triggers: [], actions: []}};
    },
    async callApi(...args) { writes.push(args); return {result: "ok"}; },
  };
  return {hass, writes, previews};
}
async function create(count = 1) {
  const mock = mockHass(count), wizard = new SalahReminderWizard();
  await wizard.start(mock.hass);
  return {...mock, wizard};
}
function toReview(wizard) {
  choose(wizard, "field:fajr_begin"); click(wizard, "Next");
  type(wizard, "begin_minutes", "12"); click(wizard, "Next");
  choose(wizard, "notification_actions:notify.mobile_app_phone"); click(wizard, "Next");
  assert.equal(wizard._step, "review");
}
const settle = () => new Promise(resolve => setImmediate(resolve));

test("single-masjid setup skips selection and conditionally shows minutes, retaining Back choices", async () => {
  const {wizard, writes} = await create();
  assert.equal(wizard._step, "prayers");
  click(wizard, "Next"); assert.match(wizard.shadowRoot.textContent, /Select at least one beginning/);
  choose(wizard, "field:fajr_begin"); click(wizard, "Next");
  assert.ok(input(wizard, "begin_minutes")); assert.equal(input(wizard, "jamaat_minutes"), undefined);
  type(wizard, "begin_minutes", "11.5"); click(wizard, "Next");
  assert.match(wizard.shadowRoot.textContent, /whole minutes/);
  type(wizard, "begin_minutes", "11"); click(wizard, "Next");
  assert.equal(wizard._step, "delivery");
  click(wizard, "Back"); assert.equal(Number(input(wizard, "begin_minutes").value), 11);
  click(wizard, "Back"); assert.equal(input(wizard, "field:fajr_begin").checked, true);
  assert.equal(writes.length, 0);
});

test("multi-masjid setup carries prayers, supports per-masjid adjustments and separate offsets", async () => {
  const {wizard, writes} = await create(2);
  click(wizard, "Next"); assert.match(wizard.shadowRoot.textContent, /at least one masjid/);
  choose(wizard, "mosque:1"); choose(wizard, "mosque:2"); click(wizard, "Next");
  choose(wizard, "field:fajr_begin"); choose(wizard, "field:fajr_jamaat");
  click(wizard, "Apply these prayers to all selected masjids"); click(wizard, "Next");
  assert.match(wizard.shadowRoot.textContent, /Masjid 2/);
  assert.equal(input(wizard, "field:fajr_begin").checked, true);
  choose(wizard, "field:fajr_begin", false); choose(wizard, "field:jumuah"); click(wizard, "Next");
  type(wizard, "begin_minutes", "5"); type(wizard, "jamaat_minutes", "15"); click(wizard, "Next");
  assert.equal(input(wizard, "begin_minutes"), undefined);
  type(wizard, "jamaat_minutes", "20"); click(wizard, "Next");
  choose(wizard, "notification_entities:notify.tablet"); click(wizard, "Next");
  assert.match(wizard.shadowRoot.textContent, /5 minutes before/);
  assert.match(wizard.shadowRoot.textContent, /15 minutes before/);
  assert.match(wizard.shadowRoot.textContent, /20 minutes before/);
  assert.match(wizard.shadowRoot.textContent, /all published congregations/);
  assert.match(wizard.shadowRoot.textContent, /Tablet/);
  assert.equal(writes.length, 0);
  const payload = wizard._payload();
  assert.deepEqual(payload.mosques.map(item => [item.id, item.fields]), [["1", ["fajr_begin", "fajr_jamaat"]], ["2", ["fajr_jamaat", "jumuah"]]]);
  assert.deepEqual(payload.delivery.notification_entities, ["notify.tablet"]);
});

test("notification and sound delivery validate recording, volume and final combined payload", async () => {
  const {wizard, writes, previews} = await create();
  choose(wizard, "field:fajr_begin"); click(wizard, "Next"); click(wizard, "Next");
  click(wizard, "Next"); assert.match(wizard.shadowRoot.textContent, /Choose at least one notification/);
  assert.equal(input(wizard, "media_content_id"), undefined);
  choose(wizard, "media_player:media_player.hall");
  click(wizard, "Next"); assert.match(wizard.shadowRoot.textContent, /recording's media URL/);
  type(wizard, "media_content_id", "media-source://media_source/local/reminder.mp3");
  choose(wizard, "set_volume"); type(wizard, "volume", "1.5");
  click(wizard, "Next"); assert.match(wizard.shadowRoot.textContent, /volume from 0 to 1/);
  type(wizard, "volume", "0.3"); choose(wizard, "notification_actions:notify.mobile_app_phone");
  click(wizard, "Next"); assert.match(wizard.shadowRoot.textContent, /Hall speaker/);
  assert.match(wizard.shadowRoot.textContent, /without restoring/);
  assert.equal(writes.length, 0);
  click(wizard, "Finish"); await settle();
  assert.equal(writes.length, 1); assert.equal(previews.length, 1);
  assert.deepEqual(previews[0].delivery.media_players, ["media_player.hall"]);
  assert.equal(previews[0].delivery.volume, 0.3);
  assert.equal(previews[0].delivery.notification_actions[0], "notify.mobile_app_phone");
  assert.equal(wizard._step, "done");
  assert.equal(nodes(wizard).find(node => node.tagName === "a").href, `/config/automation/edit/${wizard._automationId}`);
});

test("Finish is locked during save and retries reuse the same automation ID", async () => {
  const {wizard, hass, writes} = await create();
  toReview(wizard);
  let release;
  hass.callApi = (...args) => { writes.push(args); return new Promise((resolve, reject) => { release = {resolve, reject}; }); };
  click(wizard, "Finish"); await settle();
  assert.equal(wizard._saving, true);
  assert.ok(nodes(wizard).filter(node => node.tagName === "button").every(node => node.disabled));
  wizard._next(); wizard.close();
  assert.equal(wizard.isConnected, true); assert.equal(writes.length, 1);
  release.reject(new Error("Disconnected")); await settle();
  assert.equal(wizard._step, "review"); assert.match(wizard.shadowRoot.textContent, /Could not save/);
  click(wizard, "Finish"); await settle();
  assert.equal(writes.length, 2); assert.equal(writes[0][1], writes[1][1]);
  release.resolve({result: "ok"}); await settle();
  assert.equal(wizard._step, "done");
});

test("loading and preview errors produce recoverable UI and no automation write", async () => {
  const {hass, writes} = mockHass();
  const wizard = new SalahReminderWizard();
  const original = hass.callWS;
  hass.callWS = async () => { throw new Error("Unauthorized"); };
  await wizard.start(hass); assert.equal(wizard._step, "load_error");
  assert.match(wizard.shadowRoot.textContent, /administrator access/);
  hass.callWS = original; click(wizard, "Retry"); await settle();
  toReview(wizard);
  hass.callWS = async () => { throw new Error("Masjid removed"); };
  click(wizard, "Finish"); await settle();
  assert.equal(writes.length, 0); assert.equal(wizard._saving, false);
  assert.equal(wizard._step, "review");
});

test("Cancel performs no writes and restores the launching control's focus", async () => {
  const launcher = new Element("button"); launcher.focus();
  const {hass, writes} = mockHass();
  const wizard = openReminderWizard(hass); await settle();
  click(wizard, "Cancel");
  assert.equal(wizard.isConnected, false); assert.equal(writes.length, 0);
  assert.equal(document.activeElement, launcher);
});

test("review renders masjid and recording text as text rather than markup", async () => {
  const {wizard} = await create();
  wizard._options.mosques[0].name = '<img src=x onerror="alert(1)">';
  toReview(wizard);
  assert.match(wizard.shadowRoot.textContent, /<img src=x/);
  assert.equal(nodes(wizard).some(node => node.tagName === "img"), false);
});


test("wizard IDs also work on local HTTP without crypto.randomUUID", async () => {
  const original = Object.getOwnPropertyDescriptor(globalThis.crypto.__proto__, "randomUUID");
  Object.defineProperty(globalThis.crypto, "randomUUID", {value: undefined, configurable: true});
  try {
    const first = await create(), second = await create();
    assert.match(first.wizard._automationId, /^salah_reminders_[a-f0-9]{32}$/);
    assert.notEqual(first.wizard._automationId, second.wizard._automationId);
    first.wizard.close(); second.wizard.close();
  } finally {
    delete globalThis.crypto.randomUUID;
    if (original) Object.defineProperty(globalThis.crypto.__proto__, "randomUUID", original);
  }
});

test("unused timing inputs cannot invalidate the final payload after going Back", async () => {
  const {wizard} = await create();
  choose(wizard, "field:fajr_begin"); choose(wizard, "field:fajr_jamaat"); click(wizard, "Next");
  type(wizard, "begin_minutes", ""); click(wizard, "Back");
  choose(wizard, "field:fajr_begin", false); click(wizard, "Next"); click(wizard, "Next");
  choose(wizard, "notification_entities:notify.tablet"); click(wizard, "Next");
  assert.equal(wizard._payload().mosques[0].begin_minutes, 10);
});

test("dialog startup failures clean up and reject the launch readiness promise", async () => {
  const original = Element.prototype.showModal;
  Element.prototype.showModal = () => { throw new Error("Dialog unavailable"); };
  try {
    const {hass} = mockHass();
    const wizard = openReminderWizard(hass);
    await assert.rejects(wizard.ready, /Dialog unavailable/);
    assert.equal(wizard.isConnected, false);
  } finally { Element.prototype.showModal = original; }
});
