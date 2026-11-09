/** Minimal Home Assistant DOM and card fixtures shared by the Node card suites. */
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

export {test, assert, registry, timers, SalahTimetableCard, SalahTimetableCardEditor, tr, formatDate, formatHijriDate, hijriMonthInfo, normalizeConfig, find, attributes, hass};
