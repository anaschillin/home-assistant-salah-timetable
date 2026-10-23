/** Pure timestamp and display logic shared by the bundled card and its tests. */
export const MODES = Object.freeze(["context", "previous", "upcoming"]);
const NAMES = Object.freeze({fajr: "Fajr", dhuhr: "Dhuhr", jumuah: "Jumu’ah", asr: "Asr", maghrib: "Maghrib", isha: "Isha"});

export function timestamp(value) {
  if (typeof value !== "string" || !/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function duration(milliseconds) {
  if (!Number.isFinite(milliseconds)) return "Unavailable";
  let seconds = Math.max(0, Math.floor(Math.abs(milliseconds) / 1000));
  const days = Math.floor(seconds / 86400); seconds %= 86400;
  const hours = Math.floor(seconds / 3600); seconds %= 3600;
  const minutes = Math.floor(seconds / 60); seconds %= 60;
  const clock = [hours, minutes, seconds].map(value => String(value).padStart(2, "0")).join(":");
  return days ? `${days}d ${clock}` : clock;
}

export function countdown(value, now = Date.now()) {
  const target = timestamp(value);
  if (target === null) return "Unavailable";
  if (target < now) return "Passed";
  return duration(target - now);
}

export function elapsed(value, now = Date.now()) {
  const target = timestamp(value);
  return target === null || target > now ? "Unavailable" : duration(now - target);
}

export function prayerName(event) {
  return event ? NAMES[event.prayer] || NAMES[String(event.field || "").replace(/_(?:begin|jamaat)$/, "")] || "Prayer" : "Unavailable";
}

export function formatTime(value, timeZone = "UTC", locale) {
  const instant = timestamp(value);
  if (instant === null) return "—";
  try {
    return new Intl.DateTimeFormat(locale, {hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone}).format(instant);
  } catch { return "—"; }
}

export function formatDate(value, locale) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "Date unavailable";
  const instant = Date.parse(`${value}T12:00:00Z`);
  if (!Number.isFinite(instant)) return "Date unavailable";
  if (new Date(instant).toISOString().slice(0, 10) !== value) return "Date unavailable";
  try { return new Intl.DateTimeFormat(locale, {dateStyle: "full", timeZone: "UTC"}).format(instant); } catch { return value; }
}

export function normalizeConfig(config) {
  if (!config || typeof config !== "object" || Array.isArray(config)) throw new Error("A card configuration is required");
  const mode = config.mode || "context";
  if (!MODES.includes(mode)) throw new Error("Choose context, previous or upcoming Jamaat mode");
  if (config.entity && (typeof config.entity !== "string" || !/^sensor\.[a-z0-9_]+$/.test(config.entity))) throw new Error("Choose a timetable sensor");
  if (config.title !== undefined && (typeof config.title !== "string" || config.title.length > 100)) throw new Error("Title must be at most 100 characters");
  return {...config, type: "custom:salah-timetable-card", entity: config.entity || "", mode};
}

export function isTimetableState(state) {
  return Boolean(state && Array.isArray(state.attributes?.prayers) && typeof state.attributes?.mosque_name === "string");
}

export function discoverEntity(hass) {
  return Object.entries(hass?.states || {}).find(([, state]) => isTimetableState(state))?.[0] || "";
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
