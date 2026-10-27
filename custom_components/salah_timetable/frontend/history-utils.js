/** Pure helpers for the optional Islamic History display. No network access. */
export const HISTORY_DEFAULTS = Object.freeze({
  show_hijri_month_info: true,
  show_historical_day_events: false,
  show_historical_month_highlights: false,
  show_historical_sources: false,
  show_disputed_historical_dates: false,
});

export function historyOptions(config = {}) {
  return Object.fromEntries(Object.entries(HISTORY_DEFAULTS).map(([key, defaultValue]) =>
    [key, typeof config[key] === "boolean" ? config[key] : defaultValue]));
}

/** Choose independently enabled content without promoting month-only events to days. */
export function selectHistory({month, day, monthInfo = [], events = [], config = {}}) {
  const options = historyOptions(config);
  if (!Number.isInteger(month) || month < 1 || month > 12 ||
      !Number.isInteger(day) || day < 1 || day > 30) return {monthInfo: null, dayEvents: [], monthHighlights: []};
  const eligible = (event) => event?.editorial_status === "approved" &&
    (options.show_disputed_historical_dates || event?.date_status !== "disputed");
  return {
    monthInfo: options.show_hijri_month_info ? monthInfo.find(item => item.month === month) ?? null : null,
    dayEvents: options.show_historical_day_events ? events.filter(event =>
      eligible(event) && event.month === month && event.day === day && event.date_precision === "day") : [],
    monthHighlights: options.show_historical_month_highlights ? events.filter(event =>
      eligible(event) && event.month === month && event.date_precision === "month" && event.day == null) : [],
  };
}
