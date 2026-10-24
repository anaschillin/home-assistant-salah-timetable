import test from "node:test";
import assert from "node:assert/strict";
import {dependencyEvidence} from "../../scripts/live_dependency.mjs";
const absent = {version: null, module_version: null};
const installed = {version: "6.21.1", module_version: "6.21.1"};

test("fresh dependency evidence requires absence before and the pinned import after", () => {
  const result = dependencyEvidence(absent, installed, "6.21.1", {requireFresh: true});
  assert.equal(result.fresh_install_verified, true);
  assert.equal(result.before_version, null);
  assert.equal(result.installed_module_version, "6.21.1");
});

for (const before of [installed, {version: "6.0.0", module_version: "6.0.0"}, {version: null, module_version: "6.21.1"}]) {
  test(`pre-existing ${JSON.stringify(before)} cannot be claimed as a fresh install`, () => {
    assert.equal(dependencyEvidence(before, installed, "6.21.1").fresh_install_verified, false);
    assert.throws(() => dependencyEvidence(before, installed, "6.21.1", {requireFresh: true}), /Fresh dependency/);
  });
}

test("preloading is explicitly separate from fresh installation", () => {
  assert.equal(dependencyEvidence(absent, installed, "6.21.1", {preloaded: true}).fresh_install_verified, false);
  assert.throws(() => dependencyEvidence(absent, installed, "6.21.1", {preloaded: true, requireFresh: true}), /Fresh dependency/);
});

test("wrong distribution metadata or imported code fails verification", () => {
  for (const after of [absent, {version: "6.0.0", module_version: "6.21.1"}, {version: "6.21.1", module_version: "6.0.0"}]) assert.throws(() => dependencyEvidence(absent, after, "6.21.1"), /does not match/);
});
