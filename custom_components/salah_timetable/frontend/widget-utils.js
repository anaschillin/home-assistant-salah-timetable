/** Finite widget configuration and approved timetable comparison helpers. */
export const SECTIONS = Object.freeze([
  {id: "mosque_selector", show: "show_mosque_selector", width: "full"},
  {id: "dates", show: "show_dates", width: "full"},
  {id: "clock", show: "show_clock", width: "full"},
  {id: "salah", show: "show_salah_countdown", width: "half"},
  {id: "jamaat", show: "show_jamaat_countdown", width: "half"},
  {id: "timetable", show: "show_timetable", width: "full"},
  {id: "ramadan", show: "show_ramadan_details", width: "full"},
  {id: "night_calculations", show: "show_night_calculations", width: "full"},
  {id: "jamaat_changes", show: "show_jamaat_changes", width: "full"},
  {id: "timetable_health", show: "show_timetable_health", width: "full"},
].map(section => Object.freeze(section)));
export const SECTION_IDS = Object.freeze(SECTIONS.map(section => section.id));
export const widgetType = id => `custom:salah-widget-${id.replaceAll("_", "-")}`;
export const WIDGET_TYPES = Object.freeze(Object.fromEntries(SECTION_IDS.map(id => [widgetType(id), id])));

export function widgetSection(configOrType) {
  const type = typeof configOrType === "string" ? configOrType : configOrType?.type;
  return Object.prototype.hasOwnProperty.call(WIDGET_TYPES, type) ? WIDGET_TYPES[type] : null;
}

function arrangementError() {
  const error = new Error("Arrangement requires unique known section IDs and full or half widths.");
  error.translationKey = "config.arrangement";
  error.params = {};
  return error;
}

export function normalizeArrangement(value) {
  if (value === undefined) return undefined;
  if (!value || typeof value !== "object" || Array.isArray(value) || !Array.isArray(value.sections)) throw arrangementError();
  const seen = new Set();
  const sections = value.sections.map(section => {
    if (!section || typeof section !== "object" || Array.isArray(section) ||
        !SECTION_IDS.includes(section.id) || seen.has(section.id) || !["full", "half"].includes(section.width)) throw arrangementError();
    seen.add(section.id);
    return {id: section.id, width: section.width};
  });
  for (const section of SECTIONS) if (!seen.has(section.id)) sections.push({id: section.id, width: section.width});
  return {sections};
}

/** Section presence is separate from data applicability (for example Ramadan). */
export function sectionVisible(config, id) {
  const single = widgetSection(config);
  if (single) return single === id;
  const definition = SECTIONS.find(section => section.id === id);
  if (!definition || config?.[definition.show] !== true) return false;
  if (config.arrangement) return true;
  if (config.detail_level === "compact" && ["dates", "timetable", "night_calculations"].includes(id)) return config.kiosk_mode === true && id !== "night_calculations";
  return true;
}

export const PRESETS = Object.freeze({
  countdown: ["mosque_selector", "dates", "salah", "jamaat", "jamaat_changes"],
  balanced: ["mosque_selector", "dates", "salah", "jamaat", "timetable", "jamaat_changes", "timetable_health", "ramadan"],
  timetable_first: ["mosque_selector", "dates", "timetable", "salah", "jamaat", "jamaat_changes", "timetable_health", "ramadan"],
  ramadan: ["mosque_selector", "dates", "ramadan", "salah", "jamaat", "night_calculations", "timetable", "jamaat_changes", "timetable_health"],
  wall: ["mosque_selector", "clock", "dates", "salah", "jamaat", "timetable", "jamaat_changes", "timetable_health", "ramadan"],
});

export function applyPreset(config, name) {
  const order = PRESETS[name];
  if (!order) throw new Error("Unknown layout preset");
  const result = {...config};
  for (const section of SECTIONS) result[section.show] = order.includes(section.id);
  result.arrangement = normalizeArrangement({sections: order.map(id => ({id, width: SECTIONS.find(section => section.id === id).width}))});
  if (name === "wall") result.kiosk_mode = true;
  return result;
}

export function resetArrangement(config) {
  const {arrangement: _arrangement, ...result} = config;
  Object.assign(result, {
    show_mosque_selector: true,
    show_dates: config.detail_level !== "compact" || config.kiosk_mode === true,
    show_clock: config.kiosk_mode === true,
    show_salah_countdown: true,
    show_jamaat_countdown: true,
    show_timetable: config.detail_level !== "compact" || config.kiosk_mode === true,
    show_ramadan_details: true,
    show_night_calculations: false,
    show_jamaat_changes: false,
    show_timetable_health: false,
  });
  return result;
}

const JAMAAT_FIELDS = Object.freeze(["fajr_jamaat", "dhuhr_jamaat", "jumuah", "asr_jamaat", "maghrib_jamaat", "isha_jamaat"]);

function dateInstant(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const instant = Date.parse(`${value}T12:00:00Z`);
  return Number.isFinite(instant) && new Date(instant).toISOString().slice(0, 10) === value ? instant : null;
}

/** Compare local published clocks, never the 23/24/25 hours between dates. */
export function jamaatChanges(attributes) {
  const instant = dateInstant(attributes?.date);
  const empty = {status: "unavailable", today: attributes?.date || null, tomorrow: null, changes: []};
  if (instant === null || attributes.date === "9999-12-31") return empty;
  const today = attributes.date;
  const tomorrow = new Date(instant + 86400000).toISOString().slice(0, 10);
  const result = {...empty, today, tomorrow};
  if (!Array.isArray(attributes?.day_prayers?.[today]) || !Array.isArray(attributes?.day_prayers?.[tomorrow]) || !Array.isArray(attributes.jamaat_events)) return result;
  let formatter;
  try {
    formatter = new Intl.DateTimeFormat("en-GB-u-nu-latn", {calendar: "gregory", timeZone: attributes.time_zone || "UTC", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23"});
  } catch { return result; }
  const fields = new Map(JAMAAT_FIELDS.map(field => [field, {[today]: [], [tomorrow]: []}]));
  for (const event of attributes.jamaat_events) {
    if (!fields.has(event?.field) || typeof event.timestamp !== "string" || !/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(event.timestamp)) continue;
    const stamp = Date.parse(event.timestamp);
    if (!Number.isFinite(stamp)) continue;
    const parts = Object.fromEntries(formatter.formatToParts(stamp).map(part => [part.type, part.value]));
    const date = `${parts.year}-${parts.month}-${parts.day}`;
    if (date !== today && date !== tomorrow) continue;
    const values = fields.get(event.field)[date];
    // Duplicate timeline entries do not create extra published congregations.
    const minute = Number(parts.hour) * 60 + Number(parts.minute);
    if (!values.some(value => value.minute === minute)) values.push({timestamp: event.timestamp, minute});
  }
  const required = attributes?.timetable_health?.completeness?.required_fields;
  const expected = Array.isArray(required) ? required.filter(field => JAMAAT_FIELDS.includes(field)) : JAMAAT_FIELDS.filter(field => field !== "jumuah");
  let incomplete = false;
  let changed = false;
  for (const field of JAMAAT_FIELDS) {
    const grouped = fields.get(field);
    const left = grouped[today].sort((a, b) => a.minute - b.minute);
    const right = grouped[tomorrow].sort((a, b) => a.minute - b.minute);
    if (!left.length && !right.length && !expected.includes(field)) continue;
    const available = left.length > 0 && right.length > 0;
    const equal = available && left.length === right.length && left.every((value, index) => value.minute === right[index].minute);
    // A missing required value is an incomplete comparison, not proof of a change.
    if (!available && expected.includes(field)) incomplete = true;
    const entry = {
      field,
      prayer: field === "jumuah" ? "jumuah" : field.replace(/_jamaat$/, ""),
      today: left.map(value => value.timestamp),
      tomorrow: right.map(value => value.timestamp),
      delta_minutes: available && left.length === 1 && right.length === 1 ? right[0].minute - left[0].minute : null,
      status: available ? equal ? "unchanged" : "changed" : "unavailable",
    };
    if (entry.status === "changed") changed = true;
    // An unmatched session is not proof that another session moved or was cancelled.
    if (!available && (left.length || right.length)) incomplete = true;
    result.changes.push(entry);
  }
  result.status = incomplete ? "incomplete" : changed ? "changed" : result.changes.length ? "unchanged" : "unavailable";
  return result;
}
