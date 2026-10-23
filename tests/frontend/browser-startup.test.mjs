import test from "node:test";
import assert from "node:assert/strict";
import {EventEmitter} from "node:events";
import {mkdtemp, rm, writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {setTimeout as pause} from "node:timers/promises";
import {waitForDebuggerPort} from "./browser-startup.mjs";

async function fixture(t) {
  const directory = await mkdtemp(join(tmpdir(), "salah-debugger-test-"));
  t.after(() => rm(directory, {recursive: true, force: true}));
  const child = Object.assign(new EventEmitter(), {exitCode: null, signalCode: null});
  return {directory, child, portFile: join(directory, "DevToolsActivePort")};
}

test("debugger readiness waits for delayed and partially written port files", async t => {
  const {directory, child, portFile} = await fixture(t);
  const discovery = waitForDebuggerPort(child, directory, {timeoutMs: 3000, pollMs: 5});
  const writer = (async () => {
    await pause(20);
    await writeFile(portFile, "");
    await pause(20);
    await writeFile(portFile, "432");
    await pause(20);
    await writeFile(portFile, "43210\n/devtools/browser/test\n");
  })();
  const [port] = await Promise.all([discovery, writer]);
  assert.equal(port, "43210");
  assert.equal(child.listenerCount("error"), 0);
});

test("a private Chromium profile can announce its loopback debugger on stderr", async t => {
  const {directory, child} = await fixture(t);
  const port = await waitForDebuggerPort(child, directory, {
    stderr: () => "D-Bus warning\nDevTools listening on ws://127.0.0.1:54321/devtools/browser/id\n",
  });
  assert.equal(port, "54321");
});

test("invalid ports and non-loopback announcements never count as readiness", async t => {
  const {directory, child, portFile} = await fixture(t);
  await writeFile(portFile, "70000\n");
  await assert.rejects(waitForDebuggerPort(child, directory, {
    timeoutMs: 30, pollMs: 5,
    stderr: () => "DevTools listening on ws://example.org:12345/devtools/browser/id",
  }), /did not start its debugger within 30ms/);
  assert.equal(child.listenerCount("error"), 0);
});

for (const [property, value, reason] of [
  ["exitCode", 2, "exit 2"],
  ["signalCode", "SIGTRAP", "SIGTRAP"],
]) test(`startup reports ${reason} immediately`, async t => {
  const {directory, child} = await fixture(t);
  child[property] = value;
  await assert.rejects(waitForDebuggerPort(child, directory), error => {
    assert.ok(error.message.includes(reason));
    return true;
  });
  assert.equal(child.listenerCount("error"), 0);
});

test("a spawn error is reported without waiting for the startup deadline", async t => {
  const {directory, child} = await fixture(t);
  queueMicrotask(() => child.emit("error", new Error("spawn missing-browser ENOENT")));
  await assert.rejects(waitForDebuggerPort(child, directory, {pollMs: 1}), /could not start: spawn missing-browser ENOENT/);
  assert.equal(child.listenerCount("error"), 0);
});

test("startup timeout retains stderr diagnostics", async t => {
  const {directory, child} = await fixture(t);
  await assert.rejects(waitForDebuggerPort(child, directory, {
    timeoutMs: 30, pollMs: 5, stderr: () => "D-Bus: Unknown address type",
  }), /within 30ms: D-Bus: Unknown address type/);
});
