/** Bounded Chrome debugger discovery, including Snap's private profile paths. */
import {readFile} from "node:fs/promises";
import {join} from "node:path";
import {performance} from "node:perf_hooks";
import {setTimeout as pause} from "node:timers/promises";

function validPort(value) {
  return /^[1-9]\d{0,4}$/.test(value) && Number(value) <= 65535;
}

export async function waitForDebuggerPort(child, directory, {
  timeoutMs = 15000,
  pollMs = 100,
  stderr = () => "",
} = {}) {
  let spawnError;
  const onError = error => { spawnError = error; };
  child.on("error", onError);
  const deadline = performance.now() + timeoutMs;
  try {
    while (performance.now() < deadline) {
      if (spawnError) throw new Error(`Browser could not start: ${spawnError.message}`);
      if (child.exitCode !== null || child.signalCode !== null) {
        throw new Error(`Browser exited during startup (${child.signalCode || `exit ${child.exitCode}`}): ${stderr()}`);
      }
      // Chrome also announces this endpoint on stderr. A confined Chromium can
      // expose the profile file in a private /tmp invisible to the parent.
      const announced = stderr().match(/DevTools listening on ws:\/\/(?:127\.0\.0\.1|localhost|\[::1\]):([1-9]\d{0,4})\/devtools\/browser\//)?.[1];
      if (announced && validPort(announced)) return announced;
      try {
        const contents = await readFile(join(directory, "DevToolsActivePort"), "utf8");
        // Do not accept a file while Chrome is still writing its first line.
        const port = contents.match(/^([1-9]\d{0,4})\r?\n/)?.[1];
        if (port && validPort(port)) return port;
      } catch (error) {
        if (error.code !== "ENOENT") throw error;
      }
      await pause(Math.min(pollMs, Math.max(0, deadline - performance.now())));
    }
    throw new Error(`Browser did not start its debugger within ${timeoutMs}ms: ${stderr()}`);
  } finally {
    child.removeListener("error", onError);
  }
}
