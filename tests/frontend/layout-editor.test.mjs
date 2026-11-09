import test from "node:test";
import assert from "node:assert/strict";
import {buildLayoutEditor} from "../../custom_components/salah_timetable/frontend/layout-editor.js";

class Element {
  constructor(tagName) {
    this.tagName = tagName;
    this.children = [];
    this.attributes = {};
    this.listeners = new Map();
    this.style = {};
    this._text = "";
  }
  append(...children) {
    for (const child of children) {
      if (child.parentNode) child.parentNode.children = child.parentNode.children.filter(item => item !== child);
      child.parentNode = this;
      this.children.push(child);
    }
  }
  replaceChildren(...children) {
    for (const child of this.children) child.parentNode = null;
    this.children = [];
    this.append(...children);
  }
  set textContent(value) { this._text = value; this.replaceChildren(); }
  get textContent() { return this._text + this.children.map(child => child.textContent).join(""); }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key]; }
  addEventListener(name, callback) {
    if (!this.listeners.has(name)) this.listeners.set(name, []);
    this.listeners.get(name).push(callback);
  }
  closest(selector) {
    if (selector === "[data-layout-section]" && this.attributes["data-layout-section"]) return this;
    return this.parentNode?.closest(selector);
  }
  getRootNode() { return document; }
  focus() { document.activeElement = this; }
}

class Preview extends Element {
  constructor() { super("salah-timetable-card"); this.configCalls = []; }
  setConfig(config) { this.configCalls.push({config, preview: this.preview}); }
}

let observed = [];
globalThis.document = {createElement: tag => tag === "salah-timetable-card" ? new Preview() : new Element(tag)};
globalThis.ResizeObserver = class {
  constructor(callback) { this.callback = callback; observed.push(this); }
  observe() {}
  disconnect() { this.disconnected = true; }
};

const ui = {language: "en", dir: "ltr"};
const config = () => ({
  type: "custom:salah-timetable-card", entity: "sensor.mosque", title: "My wall card",
  selection_group: "household", detail_level: "compact", kiosk_mode: false,
  show_mosque_selector: true, show_dates: true, show_clock: false,
  show_salah_countdown: true, show_jamaat_countdown: true, show_timetable: true,
  show_ramadan_details: true, show_night_calculations: false,
  show_jamaat_changes: false, show_timetable_health: false,
  show_gregorian_date: false,
});
function find(root, attribute, value) {
  if (Object.hasOwn(root.attributes, attribute) && (value === undefined || root.attributes[attribute] === value)) return root;
  for (const child of root.children) {
    const found = find(child, attribute, value);
    if (found) return found;
  }
}
function control(root, id, action) { return find(find(root, "data-layout-section", id), "data-layout-action", action); }
function fire(element, type, extra = {}) {
  const event = {type, target: element, preventDefault() {}, ...extra};
  for (const callback of element.listeners.get(type) || []) callback(event);
}
function mount(initial = config()) {
  const changes = [];
  const hass = {states: {}};
  const root = buildLayoutEditor({config: initial, hass, ui, onChange: next => changes.push(next)});
  return {root, changes, hass};
}

test("first arrangement edit preserves Compact's effective visibility and saved preferences", () => {
  const original = config();
  const {root, changes} = mount(original);
  try {
    assert.equal(control(root, "dates", "visible").checked, false);
    const width = control(root, "salah", "width");
    width.value = "full";
    fire(width, "change");
    assert.equal(changes[0].arrangement.sections.find(section => section.id === "salah").width, "full");
    assert.equal(changes[0].show_dates, false);
    assert.equal(changes[0].show_timetable, false);
    assert.equal(changes[0].title, original.title);
    assert.equal(changes[0].selection_group, "household");
    assert.equal(changes[0].show_gregorian_date, false);
    assert.equal(original.arrangement, undefined, "Never mutate the config supplied by HA");
    assert.equal(original.show_dates, true);
    const visible = control(root, "dates", "visible");
    visible.checked = true;
    fire(visible, "change");
    assert.equal(changes[1].show_dates, true, "Explicit visibility lifts the Compact gate");
  } finally { root.dispose(); }
});

test("arrow and handle dragging produce the same arrangement and retain row focus", () => {
  const first = mount(), second = mount();
  try {
    const up = control(first.root, "dates", "up");
    up.focus();
    fire(up, "click");
    assert.equal(document.activeElement, control(first.root, "dates", "drag"),
      "A newly disabled boundary arrow hands focus to the same row's grip");
    const data = new Map();
    const dataTransfer = {setData: (key, value) => data.set(key, value)};
    fire(control(second.root, "dates", "drag"), "dragstart", {dataTransfer});
    fire(find(second.root, "data-layout-section", "mosque_selector"), "drop", {dataTransfer});
    assert.deepEqual(first.changes[0], second.changes[0]);
    assert.equal(data.get("application/x-salah-layout-section"), "dates");
    const before = second.changes.length;
    fire(find(second.root, "data-layout-section", "timetable"), "drop", {dataTransfer});
    assert.equal(second.changes.length, before, "Unrelated external drops do not reorder this editor");
  } finally { first.root.dispose(); second.root.dispose(); }
});

test("device previews render the actual card at isolated device widths", () => {
  const {root, changes, hass} = mount();
  try {
    const preview = find(root, "data-layout-preview-card");
    assert.equal(preview.tagName, "salah-timetable-card");
    assert.equal(preview.configCalls[0].preview, true);
    assert.equal(Object.hasOwn(preview.configCalls[0].config, "selection_group"), false);
    assert.equal(preview.configCalls[0].config.type, "custom:salah-timetable-card");
    assert.equal(preview.hass, hass);
    const frame = find(root, "data-layout-preview-frame");
    const content = frame.children[0];
    assert.equal(content.style.width, "360px");
    frame.clientWidth = 320;
    content.scrollHeight = 640;
    const device = find(root, "data-layout-device");
    device.value = "desktop";
    fire(device, "change");
    assert.equal(content.style.width, "1280px");
    assert.equal(content.style.transform, "scale(0.25)");
    assert.equal(frame.style.height, "160px");
    assert.equal(changes.length, 0, "Preview device changes never write the card config");
    assert.equal(preview.configCalls.length, 1, "Resizing keeps the existing preview instance");
  } finally { root.dispose(); }
});

test("presets and reset keep unrelated settings, and refresh preserves focused controls", () => {
  const {root, changes} = mount();
  try {
    const preset = find(root, "data-layout-preset");
    preset.value = "wall";
    fire(preset, "change");
    assert.equal(changes[0].kiosk_mode, true);
    assert.equal(changes[0].show_clock, true);
    assert.equal(changes[0].show_gregorian_date, false);
    const width = control(root, "salah", "width");
    width.focus();
    root.refresh({hass: {states: {}}, config: {...changes[0], title: "Updated"}});
    assert.equal(control(root, "salah", "width"), width);
    assert.equal(document.activeElement, width);
    fire(find(root, "data-layout-reset"), "click");
    assert.equal(changes[1].arrangement, undefined);
    assert.equal(changes[1].title, "Updated");
    assert.equal(changes[1].selection_group, "household");
    assert.equal(changes[1].kiosk_mode, true);
    assert.equal(changes[1].show_jamaat_changes, false);
  } finally { root.dispose(); }
});

test("disposing an editor stops its preview observer and further updates", () => {
  observed = [];
  const {root} = mount();
  const preview = find(root, "data-layout-preview-card");
  const calls = preview.configCalls.length;
  root.dispose();
  assert.equal(observed.length, 1);
  assert.equal(observed[0].disconnected, true);
  root.refresh({config: {...config(), title: "Detached"}});
  assert.equal(preview.configCalls.length, calls);
});
