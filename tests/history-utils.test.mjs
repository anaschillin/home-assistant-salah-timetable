import test from "node:test";
import assert from "node:assert/strict";
import {HISTORY_DEFAULTS, historyOptions, selectHistory} from "../custom_components/salah_timetable/frontend/history-utils.js";

test("month information is on by default; history is opt-in", () => {
  assert.equal(HISTORY_DEFAULTS.show_hijri_month_info, true);
  assert.equal(HISTORY_DEFAULTS.show_historical_day_events, false);
  assert.equal(historyOptions({show_hijri_month_info: false}).show_hijri_month_info, false);
});

test("month-only events never become exact-day anniversaries", () => {
  const events = [
    {id: "month", month: 5, day: null, date_precision: "month", editorial_status: "approved"},
    {id: "day", month: 5, day: 10, date_precision: "day", editorial_status: "approved"},
    {id: "draft", month: 5, day: 10, date_precision: "day", editorial_status: "research_draft"},
  ];
  const result = selectHistory({month: 5, day: 10, monthInfo: [{month: 5, name_en: "Jumada al-Ula"}], events,
    config: {show_historical_day_events: true, show_historical_month_highlights: true}});
  assert.deepEqual(result.dayEvents.map(e => e.id), ["day"]);
  assert.deepEqual(result.monthHighlights.map(e => e.id), ["month"]);
  assert.equal(result.monthInfo.name_en, "Jumada al-Ula");
});

test("disputed dates require explicit opt-in", () => {
  const events = [{id: "disputed", month: 3, day: 12, date_precision: "day", date_status: "disputed", editorial_status: "approved"}];
  const base = {month: 3, day: 12, events, config: {show_historical_day_events: true}};
  assert.equal(selectHistory(base).dayEvents.length, 0);
  assert.equal(selectHistory({...base, config: {...base.config, show_disputed_historical_dates: true}}).dayEvents.length, 1);
});
