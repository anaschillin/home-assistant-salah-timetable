import test from 'node:test';
import assert from 'node:assert/strict';
import {waitForRunning, waitForEntry} from '../../scripts/live_readiness.mjs';

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
