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
