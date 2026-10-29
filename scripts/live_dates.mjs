/** Build real HA smoke data that survives UTC midnight and year changes. */
export function smokeDateWindow(at = new Date()) {
  const today = at.toISOString().slice(0, 10);
  const next = new Date(Date.parse(`${today}T12:00:00Z`) + 86400000).toISOString().slice(0, 10);
  const sameYear = next.slice(0, 4) === today.slice(0, 4);
  return {today, next, days: sameYear ? [today, next] : [today], nextYearDays: sameYear ? [] : [next]};
}
