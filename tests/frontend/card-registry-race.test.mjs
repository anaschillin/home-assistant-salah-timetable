import test from "node:test";
import assert from "node:assert/strict";

const CARD_MODULE = "../../custom_components/salah_timetable/frontend/salah-timetable-card.js";
const TAGS = ["salah-timetable-card", "salah-timetable-card-editor"];

function createRegistry() {
  const elements = new Map();
  const listeners = new Map();
  const definitions = [];
  const registry = {
    get(tag) { return elements.get(tag); },
    define(tag, constructor) {
      if (elements.has(tag)) throw new Error(`duplicate custom-element: ${tag}`);
      elements.set(tag, constructor);
      definitions.push(tag);
      for (const resolve of listeners.get(tag) || []) resolve();
      listeners.delete(tag);
    },
    whenDefined(tag) {
      if (elements.has(tag)) return Promise.resolve();
      return new Promise(resolve => {
        const pending = listeners.get(tag) || [];
        pending.push(resolve);
        listeners.set(tag, pending);
      });
    },
    definitions,
  };
  return registry;
}

async function loadCardCase(name) {
  const queued = [];
  const native = createRegistry();
  globalThis.HTMLElement = class {};
  globalThis.customElements = native;
  globalThis.window = {customCards: []};
  const originalTimeout = globalThis.setTimeout;
  globalThis.setTimeout = callback => {
    queued.push(callback);
    return {unref() {}};
  };
  try {
    const constructors = await import(`${CARD_MODULE}?registry-race=${name}`);
    for (const tag of TAGS) assert.ok(native.get(tag), tag);
    assert.equal(window.customCards.length, 1);
    return {native, queued, constructors};
  } finally {
    globalThis.setTimeout = originalTimeout;
  }
}

test("registers card and editor again when HA swaps the custom element registry", async () => {
  const {native, queued, constructors} = await loadCardCase("late-shell");
  const polyfill = createRegistry();
  globalThis.customElements = polyfill;
  assert.equal(polyfill.get(TAGS[0]), undefined);

  native.define("home-assistant", class {});
  await Promise.resolve();
  await Promise.resolve();

  assert.equal(polyfill.get(TAGS[0]), constructors.SalahTimetableCard);
  assert.equal(polyfill.get(TAGS[1]), constructors.SalahTimetableCardEditor);

  for (const timer of queued) timer();
  assert.deepEqual(polyfill.definitions, TAGS, "Later checks never double-define tags");
});

test("fallback timer repairs registry swap even if Home Assistant was ready earlier", async () => {
  const {native, queued, constructors} = await loadCardCase("early-shell");
  native.define("home-assistant", class {});
  await Promise.resolve();
  await Promise.resolve();

  const polyfill = createRegistry();
  globalThis.customElements = polyfill;
  assert.equal(polyfill.get(TAGS[0]), undefined);
  queued[0]();
  assert.equal(polyfill.get(TAGS[0]), constructors.SalahTimetableCard);
  assert.equal(polyfill.get(TAGS[1]), constructors.SalahTimetableCardEditor);
  for (const check of queued.slice(1)) check();
  assert.deepEqual(polyfill.definitions, TAGS);
});

test("normal startup never triggers duplicate element definitions", async () => {
  const {native, queued} = await loadCardCase("normal");
  native.define("home-assistant", class {});
  await Promise.resolve();
  await Promise.resolve();
  queued.forEach(check => check());
  assert.equal(native.definitions.filter(tag => TAGS.includes(tag)).length, 2);
  assert.equal(window.customCards.length, 1);
});
