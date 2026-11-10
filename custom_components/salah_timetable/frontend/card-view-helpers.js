/** Presentation helpers shared by the timetable card, its layouts and widgets.
 * Keep DOM construction independent of Home Assistant card lifecycle state.
 */
import {node} from "./card-shared.js?v=3.6.1";
import {publishedTimes, displayPrayerKey, prayerIsPast, elapsed, formatDate, formatTime, timestamp} from "./card-utils.js?v=3.6.1";
import {localizedNumber, prayerLabels, tr} from "./card-i18n.js?v=3.6.1";

const PRAYERS = new Set(["fajr", "sunrise", "dhuhr", "jumuah", "asr", "maghrib", "isha"]);




export function backgroundCredit(background) {
  const credit = node("small", undefined, "background-credit");
  const link = node("a", `Photo: ${background.photographer} · ${background.name}`);
  link.href = background.source_url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  credit.append(link);
  return credit;
}


export function isolated(text, dir = "ltr", lang) {
  const result = node("bdi", text);
  result.setAttribute("dir", dir);
  if (lang) result.setAttribute("lang", lang);
  return result;
}

export function formattedNode(tag, text, className) {
  const result = node(tag, undefined, className);
  result.append(isolated(text));
  return result;
}

// Keep a parameter's direction independent of the translated surrounding sentence.
export function translatedRun(tag, ui, key, parameter, value, className) {
  const result = node(tag, undefined, className);
  const [before, after = ""] = tr(ui, key, {[parameter]: "\uFFFC"}).split("\uFFFC");
  if (before) result.append(node("span", before));
  result.run = isolated(value);
  result.append(result.run);
  if (after) result.append(node("span", after));
  return result;
}

export function prayerNode(key, ui, bilingual, fallback) {
  const result = node("span", undefined, "prayer-labels");
  if (!PRAYERS.has(key) && fallback) {
    result.append(isolated(fallback, "auto"));
    return result;
  }
  for (const [index, label] of prayerLabels(key, ui, bilingual).entries()) {
    if (index) result.append(node("span", "/", "label-separator"));
    result.append(isolated(label.text, label.dir, label.lang));
  }
  return result;
}

export function eventPrayerKey(event) {
  const field = String(event?.field || "").replace(/_(?:begin|jamaat)$/, "");
  return PRAYERS.has(event?.prayer) ? event.prayer : PRAYERS.has(field) ? field : event?.prayer || field;
}


export function clockNode(text, ui, elapsedClock = false) {
  const result = elapsedClock ? translatedRun("div", ui, "status.elapsed", "time", text, "count") : formattedNode("div", text, "count");
  if (!result.run) result.run = result.children[0];
  return result;
}

// Subtle inline SVG silhouettes; purely decorative and independent of mosque data.
export function panelSilhouette(kind) {
  const holder = node("span", undefined, "panel-silhouette");
  holder.setAttribute("aria-hidden", "true");
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 64 64");
  svg.setAttribute("focusable", "false");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", kind === "salah"
    ? "M30 7V3h4v4l4 6H26l4-6Zm-8 11h20v5H22v-5Zm3 7h14v28H25V25Zm5 6v12h4V31h-4ZM20 54h24v5H20v-5ZM17 60h30v3H17v-3Z"
    : "M30 5V2h4v3l4 3-4 3v3h-4v-3l-4-3 4-3ZM32 15c-12 7-20 16-20 29v9h40v-9c0-13-8-22-20-29ZM8 54h48v6H8v-6ZM5 61h54v3H5v-3Z");
  svg.append(path);
  holder.append(svg);
  return holder;
}

/** Compare upcoming Salah against the mosque's civil date, not the browser UTC date. */
export function kioskSalahDayLabel(event, now, zone, ui) {
  const target = timestamp(event?.timestamp);
  if (target === null) return null;
  const localDay = instant => {
    const parts = new Intl.DateTimeFormat("en", {
      timeZone: zone, calendar: "gregory",
      year: "numeric", month: "2-digit", day: "2-digit",
    }).formatToParts(instant);
    const part = kind => parts.find(value => value.type === kind)?.value;
    const year = part("year"), month = part("month"), day = part("day");
    return year && month && day ? `${year}-${month}-${day}` : null;
  };
  try {
    const today = localDay(now), upcoming = localDay(target);
    if (!today || !upcoming || upcoming <= today) return null;
    const interval = (Date.parse(`${upcoming}T00:00:00Z`) - Date.parse(`${today}T00:00:00Z`)) / 86400000;
    return interval === 1 ? tr(ui, "card.tomorrow") : formatDate(upcoming, ui);
  } catch { return null; }
}

export function prayerTimeline(times, ui, now) {
  const beginning = timestamp(times.begin);
  const jamaat = timestamp(times.jamaat);
  if (beginning === null || jamaat === null || jamaat <= beginning) return null;

  const strip = node("div", undefined, "timeline-strip");
  const caption = node("span", undefined, "timeline-caption");
  for (const name of ["timeline-start", "timeline-line", null, "timeline-line", "timeline-end"]) {
    const part = name ? node("span", undefined, name) : caption;
    if (name) part.setAttribute("aria-hidden", "true");
    strip.append(part);
  }
  let lastProgress, lastKey, lastMinutes;
  const update = instant => {
    const progress = Math.max(0, Math.min(1, (instant - beginning) / (jamaat - beginning)));
    if (progress !== lastProgress) {
      // The caption splits the track into two equal segments.
      strip.style.setProperty("--timeline-first-fill", `${Math.min(progress * 200, 100)}%`);
      strip.style.setProperty("--timeline-second-fill", `${Math.max(progress * 200 - 100, 0)}%`);
      strip.className = progress === 1 ? "timeline-strip is-complete" : "timeline-strip";
      lastProgress = progress;
    }
    const key = instant < beginning ? "timeline.interval" : instant < jamaat ? "timeline.remaining" : "timeline.elapsed";
    const minutes = instant >= jamaat ? Math.floor((instant - jamaat) / 60000)
      : Math.ceil((jamaat - Math.max(instant, beginning)) / 60000);
    if (key !== lastKey || minutes !== lastMinutes) {
      caption.textContent = tr(ui, key, {minutes: localizedNumber(minutes, ui)});
      lastKey = key;
      lastMinutes = minutes;
    }
  };
  update(now);
  return {strip, update};
}

// Shared structure and styles for the upcoming Salah and contextual Jamaat.
export function prayerPanel(kind, event, data, zone, ui, config, clock, {mode = "previous", timelineNow} = {}) {
  const result = node("section", undefined, "panel prayer-panel");
  result.setAttribute("data-panel", kind);
  const label = node("div", tr(ui, kind === "salah" ? "panel.next_salah" : mode === "upcoming" ? "panel.next_jamaat" : "panel.previous_jamaat"), "label");
  result.label = label;
  const name = node("div", undefined, "event");
  if (event) name.append(prayerNode(displayPrayerKey(data, eventPrayerKey(event), event.timestamp),
    ui, config.bilingual_prayer_labels, event.name));
  else name.textContent = tr(ui, "status.unavailable");
  result.append(label, name);
  if (kind === "salah" || kind === "jamaat") {
    result.clock = clockNode(clock, ui, kind === "jamaat" && mode === "previous");
    result.append(result.clock);
  }
  const times = publishedTimes(data, event, kind === "jamaat");
  const grid = node("div", undefined, "prayer-times");
  if (timelineNow !== undefined) grid.setAttribute("data-time-format", config.time_format);
  for (const [key, value] of [["table.beginning", times.begin], ["table.jamaat", times.jamaat]]) {
    const cell = node("div", undefined, "prayer-time");
    cell.append(node("div", tr(ui, key), "label"), formattedNode("div", formatTime(value, zone, ui, config.time_format), "absolute"));
    grid.append(cell);
  }
  const timeline = timelineNow === undefined ? null : prayerTimeline(times, ui, timelineNow);
  if (timeline) {
    grid.append(timeline.strip);
    result.updateTimeline = timeline.update;
  }
  result.append(grid, panelSilhouette(kind));
  if (kind === "salah" && config.detail_level === "detailed" && times.end) result.append(translatedRun("div", ui, "table.fajr_end", "time", formatTime(times.end, zone, ui, config.time_format), "note fajr-sunrise"));
  return result;
}


/** Five published daily prayers in display order; no estimates or synthetic times. */
export function kioskPrayerStrip(rows, next, congregation, data, zone, ui, config, selectedDay, selectedDate, now) {
  const strip = node("section", undefined, "kiosk-strip");
  strip.setAttribute("aria-label", tr(ui, "table.caption"));
  const ordered = ["fajr", "dhuhr", "asr", "maghrib", "isha"]
    .map(key => Array.isArray(rows) ? rows.find(row => row?.key === key) : null)
    .filter(Boolean);
  if (!ordered.length) {
    strip.append(node("p", tr(ui, "card.day_unavailable"), "kiosk-strip-empty"));
    return strip;
  }
  const nextTime = timestamp(next?.timestamp);
  const nextKey = selectedDay === 0 && nextTime !== null
    ? ordered.find(row => timestamp(row.begin) === nextTime)?.key : null;
  const currentKey = selectedDay === 0
    ? ordered.filter(row => {
      const begin = timestamp(row.begin);
      return begin !== null && begin <= now;
    }).at(-1)?.key : null;
  const nextJamaatTime = selectedDay === 0 && congregation?.mode === "upcoming"
    ? timestamp(congregation.event?.timestamp) : null;
  const nextJamaatKey = nextJamaatTime === null ? null
    : ordered.find(row => Array.isArray(row.jamaat) &&
      row.jamaat.some(value => timestamp(value) === nextJamaatTime))?.key;

  for (const prayer of ordered) {
    const status = prayer.key === nextKey ? "is-next"
      : prayer.key === currentKey ? "is-current"
      : selectedDay === 0 && prayerIsPast(prayer, now) ? "is-past" : "";
    const isNextJamaat = prayer.key === nextJamaatKey;
    const tile = node("div", undefined, "kiosk-tile" + (status ? " " + status : "") +
      (isNextJamaat ? " is-next-jamaat" : ""));
    tile.setAttribute("data-prayer", prayer.key);
    if (isNextJamaat) {
      tile.setAttribute("data-next-jamaat", "true");
      tile.setAttribute("title", tr(ui, "panel.next_jamaat"));
    }
    if (status === "is-next") tile.setAttribute("aria-current", "true");
    const heading = node("h3", undefined, "kiosk-tile-name");
    heading.append(prayerNode(displayPrayerKey(data, prayer.key, selectedDate),
      ui, config.bilingual_prayer_labels, prayer.name));
    const times = node("div", undefined, "kiosk-tile-times");
    const beginning = node("div", undefined, "kiosk-tile-time");
    beginning.append(
      node("span", tr(ui, "table.beginning"), "kiosk-tile-label"),
      formattedNode("strong", formatTime(prayer.begin, zone, ui, config.time_format)),
    );
    times.append(beginning);
    const jamaat = node("div", undefined, "kiosk-tile-time");
    jamaat.append(node("span", tr(ui, "table.jamaat"), "kiosk-tile-label"));
    const congregations = Array.isArray(prayer.jamaat) && prayer.jamaat.length
      ? prayer.jamaat : [null];
    const jamaatValues = node("div", undefined, "kiosk-tile-jamaat-values");
    for (const [index, value] of congregations.entries()) {
      if (index) jamaatValues.append(node("span", " · ", "kiosk-tile-separator"));
      const isJumuah = prayer.key === "dhuhr" && Array.isArray(data.jamaat_events)
        && data.jamaat_events.some(event => event.prayer === "jumuah"
          && timestamp(event.timestamp) !== null
          && timestamp(event.timestamp) === timestamp(value));
      if (isJumuah) {
        const marker = node("span", undefined, "kiosk-tile-jumuah");
        marker.append(prayerNode("jumuah", ui, config.bilingual_prayer_labels));
        jamaatValues.append(marker);
      }
      jamaatValues.append(formattedNode("strong", formatTime(value, zone, ui, config.time_format)));
    }
    jamaat.append(jamaatValues);
    times.append(jamaat);
    tile.append(heading, times);
    strip.append(tile);
  }
  return strip;
}

export function mosqueClock(zone, ui, timeFormat, now, updates) {
  const kioskClock = node("div", undefined, "kiosk-clock");
  kioskClock.setAttribute("title", zone);
  const clockLabel = node("span", tr(ui, "card.current_time"), "kiosk-clock-label");
  const clockValue = node("time", undefined, "kiosk-clock-value");
  clockValue.setAttribute("dir", "ltr");
  const updateClock = instant => {
    const iso = new Date(instant).toISOString();
    const value = formatTime(iso, zone, ui, timeFormat);
    if (clockValue.textContent !== value) clockValue.textContent = value;
    clockValue.setAttribute("datetime", iso);
  };
  updateClock(now);
  updates.push(updateClock);
  kioskClock.append(clockLabel, clockValue);
  return kioskClock;
}
