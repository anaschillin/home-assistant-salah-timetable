/** Pure timestamp and display logic shared by the bundled card and its tests. */
import {localizedNumber, prayerLabels, tr} from "./card-i18n.js?v=0.9.3";

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
  const defaults = {detail_level: config.detail_level || (config.layout === "compact" ? "compact" : "standard"), layout: "expanded", time_format: "24h", hijri_adjustment: 0, language: "auto", bilingual_prayer_labels: false, show_hijri_date: true, show_gregorian_date: true, show_salah_countdown: true, show_jamaat_countdown: true, show_ramadan_details: true, show_sehri_countdown: true, show_iftar_countdown: true, show_timezone_note: true, show_hijri_month_info: true, show_historical_day_events: false, show_historical_month_highlights: false, show_historical_sources: false, show_disputed_historical_dates: false};
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

/** Resolve the displayed clock times from the event's actual dated row. */
export function publishedTimes(attributes, event, congregation = false) {
  const instant = timestamp(event?.timestamp);
  if (instant === null) return {begin: null, jamaat: null, end: null};
  const key = PRAYERS.includes(event.prayer) ? event.prayer : String(event.field || "").replace(/_(?:begin|jamaat)$/, "");
  const rows = [
    ...Object.values(attributes?.day_prayers || {}).flat(),
    ...(Array.isArray(attributes?.prayers) ? attributes.prayers : []),
  ];
  const row = rows.find(item => item && item.key === pair(key) && (timestamp(item.begin) === instant ||
    (Array.isArray(item.jamaat) && item.jamaat.some(value => timestamp(value) === instant))));
  const jamaats = Array.isArray(row?.jamaat) ? row.jamaat : [];
  // A published event is sufficient to display its own time, but other times
  // must come from the matching dated row (never today's row as a fallback).
  return {
    begin: row?.begin || (congregation ? null : event.timestamp),
    jamaat: congregation ? event.timestamp : (jamaats[0] || null),
    end: row && key === "fajr" ? row.end || null : null,
  };
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

/** Read numeric Umm al-Qura fields; some WebViews mislabel named months and eras. */
function hijriParts(value, adjustment = 0) {
  const instant = dateInstant(value);
  if (instant === null || !Number.isInteger(adjustment) || Math.abs(adjustment) > 3) return null;
  try {
    const formatter = new Intl.DateTimeFormat("en-u-nu-latn", {calendar: "islamic-umalqura", day: "numeric", month: "numeric", year: "numeric", timeZone: "UTC"});
    if (formatter.resolvedOptions().calendar !== "islamic-umalqura") return null;
    const parts = formatter.formatToParts(instant + adjustment * 86400000);
    const number = field => Number(parts.find(part => part.type === field)?.value);
    const day = number("day"), month = number("month"), year = number("year");
    return day >= 1 && day <= 30 && month >= 1 && month <= 12 && Number.isInteger(year) && year > 0 ? {day, month, year} : null;
  } catch { return null; }
}

/** Calculated display date only; never used for Ramadan activation. */
export function formatHijriDate(value, adjustment = 0, locale) {
  const unavailable = tr(locale, "status.hijri_unavailable");
  try {
    const requestedLocale = displayLocale(locale);
    if (requestedLocale) new Intl.DateTimeFormat(requestedLocale);
  } catch { return unavailable; }
  const parts = hijriParts(value, adjustment);
  if (!parts) return unavailable;
  const language = typeof locale === "string" ? locale : locale?.language || locale?.locale || "en";
  const arabic = /^ar(?:-|$)/i.test(language);
  const name = HIJRI_MONTH_INFO[parts.month - 1][arabic ? 1 : 0];
  return `${localizedNumber(parts.day, locale)} ${name} ${localizedNumber(parts.year, locale)} ${arabic ? "هـ" : "AH"}`;
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

export const HIJRI_MONTH_INFO = Object.freeze([["Muharram","المحرّم","The first Hijri month and one of four sacred months."],["Safar","صفر","The second month. Islam does not regard Safar as inherently unlucky."],["Rabi al-Awwal","ربيع الأول","The third month. The precise date of the Prophet's ﷺ birth is disputed."],["Rabi al-Thani","ربيع الآخر","The fourth month of the lunar Hijri calendar."],["Jumada al-Ula","جمادى الأولى","The fifth month. The expedition of Mu'tah is recorded in this month."],["Jumada al-Akhirah","جمادى الآخرة","The sixth month of the lunar Hijri calendar."],["Rajab","رجب","One of the four sacred months. The date of Isra and Mi'raj is not established."],["Sha'ban","شعبان","The month before Ramadan; the Prophet ﷺ frequently observed voluntary fasts in it."],["Ramadan","رمضان","The month of obligatory fasting and the revelation of the Qur'an."],["Shawwal","شوّال","Eid al-Fitr marks the beginning of Shawwal."],["Dhu al-Qa'dah","ذو القعدة","One of the four sacred months."],["Dhu al-Hijjah","ذو الحجة","A sacred month containing Hajj, the Day of Arafah and Eid al-Adha."]]);
export function hijriMonthInfo(value, adjustment = 0) {
  const parts = hijriParts(value, adjustment);
  if (!parts) return null;
  const {month} = parts;
  return {month, name_en: HIJRI_MONTH_INFO[month - 1][0], name_ar: HIJRI_MONTH_INFO[month - 1][1], summary_en: HIJRI_MONTH_INFO[month - 1][2]};
}
