import test from 'node:test';
import assert from 'node:assert/strict';
import {waitForRunning, waitForEntry, pollUntil} from '../../scripts/live_readiness.mjs';

async function poll(action, predicate, message) {
  for (let attempt = 0; attempt < 4; attempt++) {
    const result = await action();
    if (predicate(result)) return result;
  }
  throw new Error(message);
}

test('startup waits beyond reachable HTTP until HA is RUNNING', async () => {
  const states = ['NOT_RUNNING', 'STARTING', 'RUNNING'];
  await waitForRunning(async () => ({state: states.shift()}), poll);
  assert.equal(states.length, 0);
});

test('restart waits for the specific mosque, ignoring other loaded entries', async () => {
  const states = [undefined, 'setup_in_progress', 'loaded'];
  await waitForEntry(async () => {
    const state = states.shift();
    return [{entry_id: 'other', state: 'loaded'}, ...(state ? [{entry_id: 'target', state}] : [])];
  }, poll, 'target');
  assert.equal(states.length, 0);
});

for (const state of ['setup_error', 'migration_error', 'failed_unload']) {
  test(`reports terminal ${state} before asserting timetable persistence`, async () => {
    await assert.rejects(waitForEntry(async () => [{entry_id: 'target', state}], poll, 'target'),
      new RegExp(`Mosque setup failed: ${state}`));
  });
}

test('startup timeout is distinct from a timetable mismatch', async () => {
  await assert.rejects(waitForRunning(async () => ({state: 'STARTING'}), poll), /did not reach RUNNING/);
  await assert.rejects(waitForEntry(async () => [], poll, 'target'), /did not finish loading/);
});


for (const status of [401, 403, 404, 400, 500]) {
  test(`readiness surfaces HTTP ${status} without retrying`, async () => {
    let attempts = 0;
    await assert.rejects(pollUntil(async () => { attempts++; throw Object.assign(new Error("HTTP failure"), {status}); }, Boolean, "timeout", {pause: async () => {}}), /HTTP failure/);
    assert.equal(attempts, 1);
  });
}

test("readiness retries refused connections and gateway startup errors", async () => {
  const errors = [Object.assign(new Error("fetch failed"), {cause: {code: "ECONNREFUSED"}}), Object.assign(new Error("starting"), {status: 503})];
  let attempts = 0;
  assert.equal(await pollUntil(async () => { attempts++; if (errors.length) throw errors.shift(); return true; }, Boolean, "timeout", {pause: async () => {}}), true);
  assert.equal(attempts, 3);
});

test("readiness never retries invalid JSON, assertions or cancellation", async () => {
  for (const error of [new SyntaxError("bad response"), new Error("bad schema")]) {
    await assert.rejects(pollUntil(async () => { throw error; }, Boolean, "timeout", {pause: async () => assert.fail("must not pause")}), error);
  }
  const abort = new AbortController(); abort.abort(new Error("cancelled"));
  await assert.rejects(pollUntil(async () => assert.fail("must not request"), Boolean, "timeout", {signal: abort.signal, pause: async () => {}}), /cancelled/);
});

test("readiness retries transient request timeouts without masking permanent failures", async () => {
  const timeout = Object.assign(new Error("The operation timed out"), {name: "TimeoutError"});
  let attempts = 0;
  const result = await pollUntil(async () => {
    attempts++;
    if (attempts === 1) throw timeout;
    return ["onboarding"];
  }, Array.isArray, "HA did not start", {attempts: 3, pause: async () => {}});
  assert.deepEqual(result, ["onboarding"]);
  assert.equal(attempts, 2);
});
