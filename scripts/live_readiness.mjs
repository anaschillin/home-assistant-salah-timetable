/** Readiness gates for the disposable HA acceptance runner. */
export async function waitForRunning(request, until) {
  return until(() => request('/api/config'), value => value.state === 'RUNNING',
    'Home Assistant did not reach RUNNING', 120);
}

export async function waitForEntry(request, until, entryId) {
  const terminal = new Set(['setup_error', 'migration_error', 'failed_unload']);
  let observed = 'absent';
  const result = await until(async () => {
    const entries = await request('/api/config/config_entries/entry?domain=salah_timetable');
    const entry = entries.find(item => item.entry_id === entryId);
    observed = entry?.state ?? 'absent';
    return {state: observed};
  }, value => value.state === 'loaded' || terminal.has(value.state),
  'Mosque did not finish loading after startup', 120);
  if (result.state !== 'loaded') throw new Error(`Mosque setup failed: ${observed}`);
}

/** Retry startup transport failures, not auth errors or incompatible API replies. */
export function transientReadinessError(error) {
  if (error?.status !== undefined) return [502, 503, 504].includes(error.status);
  const code = error?.cause?.code ?? error?.code;
  return ["ECONNREFUSED", "ECONNRESET", "EPIPE", "UND_ERR_SOCKET", "UND_ERR_CONNECT_TIMEOUT"].includes(code) || error?.name === "TimeoutError";
}

export async function pollUntil(action, predicate, message, {attempts = 90, pause, signal} = {}) {
  let lastTransientError;
  for (let attempt = 0; attempt < attempts; attempt++) {
    signal?.throwIfAborted();
    try {
      const result = await action();
      if (predicate(result)) return result;
    } catch (error) {
      if (signal?.aborted || !transientReadinessError(error)) throw error;
      lastTransientError = error;
    }
    if (attempt + 1 < attempts) await pause(1000);
  }
  throw new Error(`${message} after ${attempts} probes${lastTransientError ? `; last transport error: ${lastTransientError.message}` : ""}`);
}
