/** Pure timestamp and display logic shared by the bundled card and its tests. */
import {localizedNumber, prayerLabels, tr} from "./card-i18n.js?v=0.9.1";

export const MODES = Object.freeze(["context", "previous", "upcoming"]);
const PRAYERS = Object.freeze(["fajr", "dhuhr", "jumuah", "asr", "maghrib", "isha"]);

export function timestamp(value) {
  if (typeof value !== "string" || !/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function duration(milliseconds, ui = "en") {
  if (!Number.isFinite(milliseconds)) return tr(ui, "status.unavailable");
  let seconds = Math.max(0, Math.floor(Math.abs(milliseconds) / 1000));
  const days = Math.floor(seconds / 86400); seconds %= 86400;
  const hours = Math.floor(seconds / 3600); seconds %= 3600;
  const minutes = Math.floor(seconds / 60); seconds %= 60;
  const clock = [hours, minutes, seconds].map(value => localizedNumber(value, ui, {minimumIntegerDigits: 2})).join(":");
  return days ? tr(ui, "duration.days", {days: localizedNumber(days, ui), clock}) : clock;
}

export function countdown(value, now = Date.now(), ui = "en") {
  const target = timestamp(value);
  if (target === null) return tr(ui, "status.unavailable");
  if (target < now) return tr(ui, "status.passed");
  return duration(target - now, ui);
}

export function elapsed(value, now = Date.now(), ui = "en") {
  const target = timestamp(value);
  return target === null || target > now ? tr(ui, "status.unavailable") : duration(now - target, ui);
}

export function prayerName(event, ui = "en") {
  if (!event) return tr(ui, "status.unavailable");
  const key = PRAYERS.includes(event.prayer) ? event.prayer : String(event.field || "").replace(/_(?:begin|jamaat)$/, "");
  return prayerLabels(PRAYERS.includes(key) ? key : "prayer", ui)[0].text;
}

function displayLocale(localeOrUi) {
  return localeOrUi && typeof localeOrUi === "object" ? localeOrUi.locale : localeOrUi;
}

export function formatTime(value, timeZone = "UTC", locale, timeFormat = "24h") {
  const instant = timestamp(value);
  if (instant === null) return "—";
  try {
    return new Intl.DateTimeFormat(displayLocale(locale), {calendar: "gregory", hour: "2-digit", minute: "2-digit", hourCycle: timeFormat === "12h" ? "h12" : "h23", timeZone}).format(instant);
  } catch { return "—"; }
}

/** Validate a published Gregorian date without formatting or calendar conversion. */
function dateInstant(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const instant = Date.parse(`${value}T12:00:00Z`);
  return Number.isFinite(instant) && new Date(instant).toISOString().slice(0, 10) === value ? instant : null;
}

export function formatDate(value, locale) {
  const instant = dateInstant(value);
  if (instant === null) return tr(locale, "status.date_unavailable");
  try { return new Intl.DateTimeFormat(displayLocale(locale), {calendar: "gregory", dateStyle: "full", timeZone: "UTC"}).format(instant); } catch { return value; }
}

function configError(key, params = {}) {
  const translationKey = `config.${key}`;
  const error = new Error(tr("en", translationKey, params));
  error.translationKey = translationKey;
  error.params = params;
  return error;
}

export function normalizeConfig(config) {
  if (!config || typeof config !== "object" || Array.isArray(config)) throw configError("required");
  // Legacy mode is ignored: the card always displays the previous Jamaat.
  if (config.entity && (typeof config.entity !== "string" || !/^sensor\.[a-z0-9_]+$/.test(config.entity))) throw configError("entity");
  if (config.title !== undefined && (typeof config.title !== "string" || config.title.length > 100)) throw configError("title");
  const defaults = {detail_level: config.detail_level || (config.layout === "compact" ? "compact" : "standard"), layout: "expanded", time_format: "24h", hijri_adjustment: 0, language: "auto", bilingual_prayer_labels: false, show_hijri_date: true, show_gregorian_date: true, show_salah_countdown: true, show_jamaat_countdown: true, show_ramadan_details: true, show_sehri_countdown: true, show_iftar_countdown: true, show_timezone_note: true};
  const result = {...defaults, ...config};
  if (!["compact", "standard", "detailed"].includes(result.detail_level)) throw configError("detail_level");
  if (!["12h", "24h"].includes(result.time_format)) throw configError("time_format");
  if (!Number.isInteger(result.hijri_adjustment) || Math.abs(result.hijri_adjustment) > 3) throw configError("hijri_adjustment");
  if (!["auto", "en", "ar"].includes(result.language)) throw configError("language");
  for (const key of Object.keys(defaults).filter(key => key.startsWith("show_") || key === "bilingual_prayer_labels")) if (typeof result[key] !== "boolean") throw configError("boolean", {option: key});
  const {mode: _legacyMode, ...withoutMode} = result;
  return {...withoutMode, type: "custom:salah-timetable-card", entity: config.entity || ""};
}

export function isTimetableState(state) {
  return Boolean(state && Array.isArray(state.attributes?.prayers) && typeof state.attributes?.mosque_name === "string");
}

export function discoverTimetableEntities(hass) {
  // Each mosque exposes its own dashboard sensor. Do not use the integration-wide
  // entity selector, which also lists individual prayer and status sensors.
  return Object.entries(hass?.states || {})
    .filter(([entity, state]) => entity.startsWith("sensor.") && isTimetableState(state))
    .map(([entity, state]) => ({entity, name: state.attributes.mosque_name}))
    .sort((left, right) => left.name.localeCompare(right.name) || left.entity.localeCompare(right.entity));
}

export function discoverEntity(hass) {
  return discoverTimetableEntities(hass)[0]?.entity || "";
}

function eventOf(event) {
  return event && timestamp(event.timestamp) !== null ? event : null;
}

function pair(prayer) { return prayer === "jumuah" ? "dhuhr" : prayer; }

function sameDay(first, second, timeZone = "UTC") {
  try {
    const formatter = new Intl.DateTimeFormat("en-CA", {year: "numeric", month: "2-digit", day: "2-digit", timeZone});
    return formatter.format(timestamp(first)) === formatter.format(timestamp(second));
  } catch { return false; }
}

function events(attributes, congregation) {
  const candidates = [];
  for (const row of Array.isArray(attributes?.prayers) ? attributes.prayers : []) {
    if (!row || typeof row !== "object") continue;
    const times = congregation ? (Array.isArray(row.jamaat) ? row.jamaat : []) : [row.begin];
    for (const value of times) {
      if (timestamp(value) !== null) candidates.push({timestamp: value, prayer: row.key, field: `${row.key}_${congregation ? "jamaat" : "begin"}`});
    }
  }
  const publishedEvents = congregation ? attributes?.jamaat_events : attributes?.beginning_events;
  for (const event of Array.isArray(publishedEvents) ? publishedEvents : []) if (eventOf(event)) candidates.push(event);
  const extra = congregation ? [attributes?.next_jamaat, attributes?.previous_jamaat, attributes?.context_jamaat] : [attributes?.next_salah];
  for (const event of extra) if (eventOf(event)) candidates.push(event);
  const unique = new Map();
  for (const event of candidates) unique.set(`${event.timestamp}|${pair(event.prayer)}`, event);
  return [...unique.values()].sort((a, b) => timestamp(a.timestamp) - timestamp(b.timestamp));
}

export function nextSalah(attributes, now = Date.now()) {
  return events(attributes, false).find(event => timestamp(event.timestamp) > now) || null;
}

export function jamaatPanel(attributes, mode = "context", now = Date.now()) {
  const congregations = events(attributes, true);
  const previous = congregations.filter(event => timestamp(event.timestamp) <= now).at(-1) || null;
  const upcoming = congregations.find(event => timestamp(event.timestamp) > now) || null;
  if (mode === "previous") return {mode: "previous", event: previous};
  if (mode === "upcoming") return {mode: "upcoming", event: upcoming};
  const lastBeginning = events(attributes, false).filter(event => timestamp(event.timestamp) <= now).at(-1);
  // The backend provides the current context, including previous-day beginnings.
  // Recompute from today's published events so second-level ticks cross boundaries
  // correctly even if the next HA update has not arrived yet.
  const currentCongregation = lastBeginning && congregations.find(event => timestamp(event.timestamp) > now && pair(lastBeginning.prayer) === pair(event.prayer) && sameDay(lastBeginning.timestamp, event.timestamp, attributes?.time_zone || "UTC"));
  if (currentCongregation) return {mode: "upcoming", event: currentCongregation};
  if (!lastBeginning && attributes?.context_mode === "upcoming") {
    const current = eventOf(attributes.context_jamaat);
    if (current && timestamp(current.timestamp) > now) return {mode: "upcoming", event: current};
  }
  return {mode: "previous", event: previous};
}


export function nextRamadanEvent(attributes, kind, now = Date.now()) {
  const timeline = kind === "sehri" ? attributes?.sehri_events : attributes?.iftar_events;
  const future = (Array.isArray(timeline) ? timeline : []).filter(event => eventOf(event) && timestamp(event.timestamp) > now).sort((first, second) => timestamp(first.timestamp) - timestamp(second.timestamp))[0];
  return future?.timestamp || attributes?.[`next_${kind}`]?.timestamp || attributes?.ramadan?.[kind] || null;
}

/** Calculated display date only; never used for Ramadan activation. */
export function formatHijriDate(value, adjustment = 0, locale) {
  const instant = dateInstant(value);
  if (instant === null) return tr(locale, "status.hijri_unavailable");
  try {
    const formatter = new Intl.DateTimeFormat(`${displayLocale(locale)}-u-ca-islamic-umalqura`, {day: "numeric", month: "long", year: "numeric", timeZone: "UTC"});
    if (formatter.resolvedOptions().calendar !== "islamic-umalqura") return tr(locale, "status.hijri_unavailable");
    return formatter.format(instant + adjustment * 86400000);
  } catch { return tr(locale, "status.hijri_unavailable"); }
}

export function eventProgress(attributes, congregation, event, now = Date.now()) {
  const end = timestamp(event?.timestamp);
  if (end === null || end <= now) return null;
  const previous = events(attributes, congregation).filter(item => timestamp(item.timestamp) < end).at(-1);
  const start = timestamp(previous?.timestamp);
  if (start === null || start > now) return null;
  return Math.min(100, Math.max(0, (now - start) / (end - start) * 100));
}

/** One current row, anchored to today's published events. */
export function highlightedPrayer(attributes, now = Date.now()) {
  const rows = (attributes?.prayers || []).filter(row => row && typeof row === "object");
  const begun = rows.filter(row => timestamp(row.begin) !== null && timestamp(row.begin) <= now)
    .sort((a, b) => timestamp(a.begin) - timestamp(b.begin)).at(-1);
  if (begun) {
    const published = (Array.isArray(begun.jamaat) ? begun.jamaat : []).map(timestamp).filter(value => value !== null);
    // A missing congregation has no implied end. Keep this row until another
    // published beginning supersedes it, including after the final daily prayer.
    if (!published.length || published.some(value => value > now)) return begun.key;
  }
  const future = rows.filter(row => timestamp(row.begin) !== null && timestamp(row.begin) > now)
    .sort((a, b) => timestamp(a.begin) - timestamp(b.begin))[0];
  if (future) return future.key;
  return null;
}

export function prayerIsPast(row, now = Date.now()) {
  const times = [row.begin, ...(Array.isArray(row.jamaat) ? row.jamaat : [])].map(timestamp).filter(value => value !== null);
  return times.length > 0 && Math.max(...times) <= now;
}
