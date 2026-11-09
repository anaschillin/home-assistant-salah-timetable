import test from "node:test";
import assert from "node:assert/strict";
import {joinSelectionGroup, selectionScope} from "../../custom_components/salah_timetable/frontend/widget-selection.js";

const card = scope => ({parentElement: scope});
const view = () => ({localName: "hui-view"});

test("first member seeds a group and late members adopt without rebroadcast loops", () => {
  const scope = view(), first = [], second = [];
  const a = joinSelectionGroup(card(scope), "home", "sensor.a", entity => first.push(entity));
  const b = joinSelectionGroup(card(scope), "home", "sensor.b", entity => second.push(entity));
  assert.equal(a.entity, "sensor.a"); assert.equal(b.entity, "sensor.a");
  assert.deepEqual(first, ["sensor.a"]); assert.deepEqual(second, ["sensor.a"]);
  b.publish("sensor.b");
  assert.deepEqual(first, ["sensor.a", "sensor.b"]); assert.deepEqual(second, ["sensor.a", "sensor.b"]);
  a.publish("sensor.b");
  assert.equal(first.length, 2); assert.equal(second.length, 2);
  a.leave(); b.leave();
});

test("groups, dashboard views and document scopes remain independent", () => {
  const scope = view(), other = view(), values = [];
  const a = joinSelectionGroup(card(scope), "home", "sensor.a", () => {});
  const b = joinSelectionGroup(card(scope), "holiday", "sensor.b", value => values.push(value));
  const c = joinSelectionGroup(card(other), "home", "sensor.c", value => values.push(value));
  a.publish("sensor.changed");
  assert.deepEqual(values, ["sensor.b", "sensor.c"]);
  assert.equal(b.entity, "sensor.b"); assert.equal(c.entity, "sensor.c");
  a.leave(); b.leave(); c.leave();
});

test("leaving is idempotent and the final removal discards temporary selection", () => {
  const scope = view(), values = [];
  const a = joinSelectionGroup(card(scope), "home", "sensor.a", () => {});
  const b = joinSelectionGroup(card(scope), "home", "sensor.b", entity => values.push(entity));
  a.leave(); a.leave(); a.publish("sensor.ignored");
  b.publish("sensor.b");
  assert.deepEqual(values, ["sensor.a", "sensor.b"]);
  b.leave();
  const fresh = joinSelectionGroup(card(scope), "home", "sensor.fresh", () => {});
  assert.equal(fresh.entity, "sensor.fresh");
  fresh.leave();
});

test("composed-tree traversal scopes cards across shadow roots to their view", () => {
  const scope = view();
  const shadowHost = {parentElement: scope};
  const inside = {getRootNode: () => ({host: shadowHost})};
  assert.equal(selectionScope(inside), scope);
  const document = {};
  assert.equal(selectionScope({ownerDocument: document}), document);
  assert.throws(() => joinSelectionGroup(card(scope), "  ", "sensor.a", () => {}));
});

test("selector receivers may publish the received selection without an echo", () => {
  const scope = view(), values = [];
  let b;
  const a = joinSelectionGroup(card(scope), "home", "sensor.a", () => {});
  b = joinSelectionGroup(card(scope), "home", "sensor.b", entity => { values.push(entity); b?.publish(entity); });
  a.publish("sensor.c");
  assert.deepEqual(values, ["sensor.a", "sensor.c"]);
  a.leave(); b.leave();
});
