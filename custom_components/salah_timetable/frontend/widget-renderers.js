/** Small read-only sections shared by composite and standalone cards. */
import {formatDate, formatTime} from "./card-utils.js?v=3.1.1";
import {localizedNumber, prayerLabels, tr} from "./card-i18n.js?v=3.1.1";
import {jamaatChanges} from "./widget-utils.js?v=3.1.1";
import {widgetTr} from "./widget-i18n.js?v=3.1.1";

function element(tag, text, className) {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  if (className) result.className = className;
  return result;
}
function panel(id, ui) {
  const result = element("section", undefined, `widget-panel widget-${id === "jamaat_changes" ? "changes" : "health"}`);
  result.setAttribute("data-section", id);
  result.append(element("h3", widgetTr(ui, `section.${id}`), "widget-heading"));
  return result;
}
function note(result, text, className = "widget-status", status = null) {
  const message = element("p", text, className);
  if (status) message.setAttribute("data-status", status);
  result.append(message);
}
function prayerName(key, ui) { return prayerLabels(key, ui, false)[0]?.text || key; }
function fieldName(field, ui) {
  const translated = widgetTr(ui, `field.${field}`);
  if (translated !== `field.${field}`) return translated;
  const key = String(field).replace(/_(begin|jamaat)$/, "");
  const suffix = String(field).endsWith("_begin") ? tr(ui, "table.beginning") : String(field).endsWith("_jamaat") ? tr(ui, "table.jamaat") : "";
  return `${prayerName(key, ui)}${suffix ? ` · ${suffix}` : ""}`;
}
function timeList(values, data, ui, config) {
  return values.length ? values.map(value => formatTime(value, data.time_zone || "UTC", ui, config.time_format)).join(" · ") : widgetTr(ui, "changes.no_published_time");
}
export function buildJamaatChanges(data, ui, config, connected = true) {
  const result = panel("jamaat_changes", ui);
  if (!connected) { note(result, widgetTr(ui, "changes.unavailable")); return result; }
  const summary = jamaatChanges(data);
  if (summary.status === "unavailable") { note(result, widgetTr(ui, "changes.unavailable")); return result; }
  note(result, `${formatDate(summary.today, ui)} → ${formatDate(summary.tomorrow, ui)}`, "note");
  for (const change of summary.changes.filter(item => item.status !== "unchanged")) {
    const row = element("div", undefined, "widget-change-row");
    row.setAttribute("data-field", change.field);
    row.append(element("strong", prayerName(change.prayer, ui)));
    const times = element("div", undefined, "widget-change-times");
    for (const [day, values] of [["today", change.today], ["tomorrow", change.tomorrow]]) {
      const cell = element("div");
      cell.append(element("span", widgetTr(ui, `changes.${day}`), "label"));
      const value = element("bdi", timeList(values, data, ui, config)); value.setAttribute("dir", "ltr");
      cell.append(value); times.append(cell);
    }
    row.append(times);
    if (Number.isFinite(change.delta_minutes) && change.delta_minutes !== 0) {
      row.append(element("span", widgetTr(ui, change.delta_minutes < 0 ? "changes.earlier" : "changes.later", {minutes: localizedNumber(Math.abs(change.delta_minutes), ui)}), "widget-status"));
    }
    result.append(row);
  }
  if (summary.status === "unchanged") note(result, widgetTr(ui, "changes.no_changes"));
  if (summary.status === "incomplete") note(result, widgetTr(ui, "changes.incomplete"), "widget-status", "incomplete");
  return result;
}
export function buildTimetableHealth(data, ui, config, hass) {
  const result = panel("timetable_health", ui);
  const health = data.timetable_health;
  if (hass?.connection?.connected === false || !health?.coverage || !health?.completeness || !health?.source) {
    note(result, widgetTr(ui, "health.unavailable")); return result;
  }
  const {coverage, completeness, source} = health;
  note(result, widgetTr(ui, "health.as_of", {date: formatDate(data.date, ui)}), "note");
  if (coverage.status === "not_configured") note(result, widgetTr(ui, "health.no_approved_timetable"));
  else {
    note(result, widgetTr(ui, `health.status.${coverage.status}`), "widget-status", ["missing_today", "missing_tomorrow"].includes(coverage.status) ? "unavailable" : coverage.status === "expiring" ? "incomplete" : "covered");
    if (coverage.available_through) note(result, widgetTr(ui, "health.through", {date: formatDate(coverage.available_through, ui)}));
    else note(result, widgetTr(ui, "health.partial"));
    note(result, widgetTr(ui, "health.days_remaining", {days: localizedNumber(coverage.days_remaining || 0, ui)}));
    for (const [day, fields] of [["today", completeness.missing_today], ["tomorrow", completeness.missing_tomorrow]]) {
      if (Array.isArray(fields) && fields.length) note(result, widgetTr(ui, `health.missing_${day}`, {fields: fields.map(field => fieldName(field, ui)).join(", ")}));
    }
    if (completeness.status === "complete" && coverage.today_available && coverage.tomorrow_available && !completeness.missing_today?.length && !completeness.missing_tomorrow?.length) note(result, widgetTr(ui, "health.complete"));
    if (coverage.unresolved_date || completeness.unresolved_date) note(result, widgetTr(ui, "health.unresolved"));
  }
  if (source.pending_review) note(result, widgetTr(ui, "health.pending_review"), "widget-status pending-review");
  if (source.error_count > 0) note(result, widgetTr(ui, "health.source_errors", {count: localizedNumber(source.error_count, ui)}));
  if (source.status === "not_configured") note(result, widgetTr(ui, "health.source_not_configured"), "note");
  if (source.last_checked) note(result, widgetTr(ui, "health.last_checked", {time: formatTime(source.last_checked, data.time_zone || "UTC", ui, config.time_format)}), "note");
  if (hass?.user?.is_admin && typeof data.config_entry_id === "string") {
    const link = element("a", widgetTr(ui, source.pending_review ? "health.review_pending" : "health.open_setup"), "widget-action");
    link.href = `/config/integrations/integration/salah_timetable?config_entry=${encodeURIComponent(data.config_entry_id)}`;
    result.append(link);
  }
  return result;
}
