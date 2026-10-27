import {eventProgress, formatHijriDate, highlightedPrayer, prayerIsPast, countdown, discoverEntity, discoverTimetableEntities, elapsed, formatDate, formatTime, isTimetableState, jamaatPanel, nextRamadanEvent, nextSalah, normalizeConfig, timestamp} from "./card-utils.js?v=0.9.1";
import {localizedNumber, prayerLabels, resolveUi, tr} from "./card-i18n.js?v=0.9.1";

// Keep HA bookkeeping and unrelated entity updates out of the render decision.
const RENDER_ATTRIBUTES = [
  "mosque_name", "date", "time_zone", "prayers", "day_prayers", "beginning_events", "jamaat_events",
  "next_salah", "next_jamaat", "previous_jamaat", "context_jamaat", "context_mode",
  "ramadan", "sehri_events", "iftar_events", "next_sehri", "next_iftar",
  "show_hijri_date", "second_khutbah",
];
const PRAYERS = new Set(["fajr", "sunrise", "dhuhr", "jumuah", "asr", "maghrib", "isha"]);

const CSS = `\n.date-tabs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;padding:4px;background:var(--secondary-background-color);border-radius:12px;margin:0 0 16px}.date-tab{border:0;border-radius:9px;padding:10px 5px;font:inherit;font-weight:600;background:transparent;color:var(--secondary-text-color);cursor:pointer}.date-tab[aria-pressed="true"]{background:var(--primary-color);color:var(--text-primary-color,#fff)}.date-tab:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}.selected-date{font-size:.9rem;font-weight:600;color:var(--secondary-text-color);margin-bottom:12px}\n\n.mosque-tabs{display:flex;gap:6px;overflow-x:auto;margin:0 0 16px;padding:4px;border-radius:12px;background:var(--secondary-background-color)}.mosque-tab{flex:1 0 auto;border:0;border-radius:9px;padding:10px 14px;font:inherit;font-weight:600;background:transparent;color:var(--secondary-text-color);cursor:pointer}.mosque-tab[aria-pressed="true"]{background:var(--primary-color);color:var(--text-primary-color,#fff)}.mosque-tab:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}\n\n.prayer-panel{gap:8px}.prayer-panel .event{min-height:1.7em}.prayer-panel .count{margin:4px 0 8px}.prayer-times{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:auto;padding-top:12px;border-top:1px solid var(--divider-color)}.prayer-time{min-width:0}.prayer-time .label{margin:0 0 5px}.prayer-time .absolute{font-size:1.1rem;font-weight:700;color:var(--primary-text-color);margin:0}.prayer-panel[data-panel="jamaat"]{justify-content:space-between}.fajr-sunrise{margin-top:5px}\n
:host{display:block;container-type:inline-size;color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,inherit)}
ha-card{display:block;overflow:hidden;background:var(--ha-card-background,var(--card-background-color));border-radius:var(--ha-card-border-radius,12px)}
.content{padding:20px}.header{display:flex;gap:12px;align-items:baseline;justify-content:space-between;flex-wrap:wrap}h2{font-size:1.35rem;margin:0;overflow-wrap:anywhere}.date{color:var(--secondary-text-color);font-size:.9rem}
.panels{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:18px 0}.panel{border-radius:10px;padding:14px;background:var(--secondary-background-color);min-width:0}.label{color:var(--secondary-text-color);font-size:.83rem;margin-bottom:5px}.event{font-weight:600;font-size:1.05rem}.count{font-variant-numeric:tabular-nums;font-size:clamp(1.6rem,6cqi,2.2rem);color:var(--primary-color);margin-top:7px;overflow-wrap:anywhere}.absolute{color:var(--secondary-text-color);font-size:.85rem;margin-top:5px}
.table-scroll{max-width:100%;overflow-x:auto}thead th{overflow-wrap:anywhere}table{width:100%;border-collapse:collapse;font-size:.97rem}th,td{padding:10px 6px;border-bottom:1px solid var(--divider-color);text-align:end;font-variant-numeric:tabular-nums}th:first-child,td:first-child{text-align:start}th{color:var(--secondary-text-color);font-size:.83rem;font-weight:500}tr:last-child td,tr:last-child th{border-bottom:0}.ramadan{border-top:1px solid var(--divider-color);margin-top:14px;padding-top:14px}.ramadan h3{font-size:1rem;margin:0 0 12px}.ramadan-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.ramadan .count{font-size:1.1rem}.note{color:var(--secondary-text-color);font-size:.83rem;margin:12px 0 0}.empty{padding:22px;color:var(--secondary-text-color);line-height:1.5}.disconnected{color:var(--error-color);font-size:.85rem;margin:8px 0}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:420px){.content{padding:14px}.panels{gap:8px}.panel{padding:10px}.count{font-size:1.6rem}.ramadan-grid{grid-template-columns:1fr 1fr}.ramadan-grid>:last-child{grid-column:1/-1}th,td{padding:9px 3px;font-size:.9rem}}
.progress-help{font-size:.72rem;color:var(--secondary-text-color);margin-top:5px}.scroll-help{display:none;font-size:.75rem}
.event,.absolute,.date,.label{overflow-wrap:anywhere}bdi{unicode-bidi:isolate}.prayer-labels{display:inline-flex;flex-wrap:wrap;gap:.3em;align-items:baseline}.prayer-labels bdi{overflow-wrap:anywhere}.label-separator{font-weight:400;color:var(--secondary-text-color)}
progress::-webkit-progress-bar{background:var(--divider-color)}progress::-webkit-progress-value{background:var(--primary-color)}progress::-moz-progress-bar{background:var(--primary-color)}
progress{display:block;width:100%;height:4px;margin-top:12px;border:0;accent-color:var(--primary-color)}
.next-prayer{background:color-mix(in srgb,var(--primary-color) 12%,transparent)}.next-prayer th,.next-prayer td{font-weight:700;font-size:1.05em}.past-prayer{color:var(--secondary-text-color)}
.congregation-time{white-space:nowrap}.hijri{flex-basis:100%}.compact{padding:12px}.compact th,.compact td{padding-top:6px;padding-bottom:6px}.compact .panel{padding:10px}.compact .count{font-size:1.6rem}
table{table-layout:fixed;min-width:22rem}th:first-child{width:30%}.panels:has(>:only-child){grid-template-columns:1fr}
@container(max-width:26rem){.scroll-help{display:block}.panels{grid-template-columns:1fr}.count{font-size:1.7rem}.ramadan-grid{grid-template-columns:1fr 1fr}.ramadan-grid>:last-child{grid-column:1/-1}}

/* HaCasa-inspired translucent surfaces, without external assets or dependencies. */
ha-card{position:relative;isolation:isolate;background:var(--ha-card-background,var(--card-background-color));}
ha-card::before{content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;background:radial-gradient(ellipse at 95% 0%,color-mix(in srgb,var(--primary-color) 12%,transparent),transparent 55%)}
.panel{background:color-mix(in srgb,var(--secondary-background-color) 82%,transparent);box-shadow:0 5px 18px rgba(0,0,0,.055);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
.panel[data-panel="salah"]{background:color-mix(in srgb,var(--primary-color) 13%,var(--ha-card-background,var(--card-background-color)))}
.table-scroll{background:color-mix(in srgb,var(--ha-card-background,var(--card-background-color)) 92%,transparent)}
@media(prefers-contrast:more){.panel,.panel[data-panel="salah"],.table-scroll{background:var(--card-background-color);border:2px solid var(--primary-text-color);box-shadow:none}}
@media(prefers-reduced-transparency:reduce){.panel,.table-scroll{backdrop-filter:none;-webkit-backdrop-filter:none;background:var(--secondary-background-color)}}
/* Modern dashboard presentation: retain HA theme variables and accessible table semantics. */
ha-card{border:1px solid var(--divider-color);box-shadow:0 8px 28px rgba(0,0,0,.07)}
.content{padding:clamp(14px,3cqi,24px)}
.header{align-items:flex-start;gap:6px 16px;margin-bottom:18px}
.header h2{font-size:clamp(1.25rem,3cqi,1.65rem);font-weight:700;letter-spacing:-.025em;flex-basis:100%}
.date{font-size:.82rem}.hijri{flex-basis:auto;font-weight:600;color:var(--primary-text-color)}
.panels{gap:12px;margin:0 0 22px}
.panel{padding:clamp(14px,2.6cqi,20px);border:1px solid var(--divider-color);border-radius:16px;background:var(--secondary-background-color);display:flex;flex-direction:column;gap:4px}
.panel[data-panel="salah"]{background:color-mix(in srgb,var(--primary-color) 9%,var(--ha-card-background,var(--card-background-color)));border-color:color-mix(in srgb,var(--primary-color) 22%,var(--divider-color))}
.panel .label{font-size:.73rem;letter-spacing:.075em;text-transform:uppercase;font-weight:700}
.panel .event{font-size:1.2rem}.panel .count{font-size:clamp(1.65rem,5.5cqi,2.65rem);font-weight:750;letter-spacing:-.045em;margin:4px 0}
.panel .absolute{font-size:.88rem}.panel progress{height:6px;border-radius:99px;overflow:hidden;margin-top:10px}
.progress-help{font-size:.72rem}
.table-scroll{border:1px solid var(--divider-color);border-radius:14px;overflow-x:auto}
table{min-width:0;table-layout:auto}thead{background:var(--secondary-background-color)}
th,td{padding:12px 10px}thead th{font-size:.73rem;letter-spacing:.04em;text-transform:uppercase}
tbody tr:not(:last-child){border-bottom:1px solid var(--divider-color)}
tbody tr th,tbody tr td{border-bottom:0}
.next-prayer{background:color-mix(in srgb,var(--primary-color) 13%,transparent);box-shadow:inset 3px 0 var(--primary-color)}
.next-prayer th,.next-prayer td{font-weight:700}.past-prayer{opacity:.66}
.ramadan{margin-top:20px}.ramadan-grid>div{background:var(--secondary-background-color);border:1px solid var(--divider-color);padding:14px;border-radius:12px}
.compact{padding:12px}.compact .panel{padding:12px}.compact .panel .count{font-size:1.65rem}
@container(max-width:28rem){.panels{grid-template-columns:1fr}.table-scroll{border:0;border-radius:0}table{width:100%;min-width:0;font-size:.86rem}th,td{padding:9px 4px}th:first-child{width:auto}.panel .count{font-size:2rem}.ramadan-grid{grid-template-columns:1fr 1fr}}
@media(prefers-reduced-motion:no-preference){.panel,.next-prayer{transition:background-color .2s ease,border-color .2s ease}}
`;

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function direction(element, ui) {
  element.setAttribute("lang", ui.language);
  element.setAttribute("dir", ui.dir);
  return element;
}

function isolated(text, dir = "ltr", lang) {
  const result = node("bdi", text);
  result.setAttribute("dir", dir);
  if (lang) result.setAttribute("lang", lang);
  return result;
}

function formattedNode(tag, text, className) {
  const result = node(tag, undefined, className);
  result.append(isolated(text));
  return result;
}

// Keep a parameter's direction independent of the translated surrounding sentence.
function translatedRun(tag, ui, key, parameter, value, className) {
  const result = node(tag, undefined, className);
  const [before, after = ""] = tr(ui, key, {[parameter]: "\uFFFC"}).split("\uFFFC");
  if (before) result.append(node("span", before));
  result.run = isolated(value);
  result.append(result.run);
  if (after) result.append(node("span", after));
  return result;
}

function prayerNode(key, ui, bilingual, fallback) {
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

function eventPrayerKey(event) {
  const field = String(event?.field || "").replace(/_(?:begin|jamaat)$/, "");
  return PRAYERS.has(event?.prayer) ? event.prayer : PRAYERS.has(field) ? field : event?.prayer || field;
}

function normalizeForUi(config, hass) {
  try { return normalizeConfig(config); }
  catch (error) {
    if (!error.translationKey) throw error;
    throw new Error(tr(resolveUi(config, hass), error.translationKey, error.params));
  }
}

function clockNode(text, ui, elapsedClock = false) {
  const result = elapsedClock ? translatedRun("div", ui, "status.elapsed", "time", text, "count") : formattedNode("div", text, "count");
  if (!result.run) result.run = result.children[0];
  return result;
}

function publishedTimes(data, event) {
  const key = eventPrayerKey(event);
  const rows = Object.values(data?.day_prayers || {}).flat();
  const row = rows.find(item => item?.key === (key === "jumuah" ? "dhuhr" : key) && (item?.jamaat || []).includes(event?.timestamp)) || (data?.prayers || []).find(item => item?.key === (key === "jumuah" ? "dhuhr" : key));
  const jamaats = Array.isArray(row?.jamaat) ? row.jamaat : [];
  const matching = jamaats.find(value => timestamp(value) === timestamp(event?.timestamp));
  return {begin: row?.begin || null, jamaat: key === "jumuah" ? (matching || event?.timestamp || null) : (matching || jamaats[0] || null), end: key === "fajr" ? row?.end : null};
}

// Shared structure and styles for the upcoming Salah and previous Jamaat.
function prayerPanel(kind, event, data, zone, ui, config, clock) {
  const result = node("section", undefined, "panel prayer-panel");
  result.setAttribute("data-panel", kind);
  const label = node("div", tr(ui, kind === "salah" ? "panel.next_salah" : "panel.previous_jamaat"), "label");
  const name = node("div", undefined, "event");
  if (event) name.append(prayerNode(eventPrayerKey(event), ui, config.bilingual_prayer_labels, event.name));
  else name.textContent = tr(ui, "status.unavailable");
  result.append(label, name);
  if (kind === "salah") {
    result.clock = clockNode(clock, ui);
    result.append(result.clock);
  }
  const times = publishedTimes(data, event);
  const grid = node("div", undefined, "prayer-times");
  for (const [key, value] of [["table.beginning", times.begin], ["table.jamaat", times.jamaat]]) {
    const cell = node("div", undefined, "prayer-time");
    cell.append(node("div", tr(ui, key), "label"), formattedNode("div", formatTime(value, zone, ui, config.time_format), "absolute"));
    grid.append(cell);
  }
  result.append(grid);
  if (kind === "salah" && config.detail_level === "detailed" && times.end) result.append(translatedRun("div", ui, "table.fajr_end", "time", formatTime(times.end, zone, ui, config.time_format), "note fajr-sunrise"));
  return result;
}

export class SalahTimetableCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this._config = normalizeConfig({});
    this._timer = null;
    this._selectedMosque = null;
    this._selectedDay = 0;
  }

  static getConfigElement() { return document.createElement("salah-timetable-card-editor"); }
  static getStubConfig(hass) { return normalizeConfig({entity: discoverEntity(hass)}); }
  setConfig(config) { this._config = normalizeForUi(config, this._hass); this._render(); }
  set hass(value) {
    this._hass = value;
    if (this._hassRenderKey() !== this._renderedHassKey) this._render();
  }
  getCardSize() { return (this._config.detail_level === "compact" ? 3 : 5) + (this._config.detail_level === "detailed" && this._state()?.attributes?.ramadan?.active && this._config.show_ramadan_details ? 2 : 0); }
  getGridOptions() { return {columns: 12, rows: this.getCardSize(), min_columns: 6, min_rows: 4}; }

  connectedCallback() {
    if (this._timer === null) this._timer = window.setInterval(() => this._tick(), 1000);
    this._render();
  }
  disconnectedCallback() {
    if (this._timer !== null) window.clearInterval(this._timer);
    this._timer = null;
  }
  _mosques() { return discoverTimetableEntities(this._hass); }
  _activeEntity() {
    const mosques = this._mosques();
    if (this._selectedMosque && mosques.some(item => item.entity === this._selectedMosque)) return this._selectedMosque;
    return this._config.entity || mosques[0]?.entity || "";
  }
  _state() { return this._hass?.states?.[this._activeEntity()]; }

  _hassRenderKey() {
    const state = this._state();
    const data = state?.attributes;
    const ui = resolveUi(this._config, this._hass);
    return JSON.stringify([
      this._activeEntity(), this._mosques().map(item => [item.entity, item.name]), Boolean(state), state?.state,
      ...RENDER_ATTRIBUTES.map(key => data?.[key]),
      data?.time_zone || this._hass?.config?.time_zone || "UTC",
      ui.language, ui.locale, ui.dir,
      this._hass?.connection?.connected === false,
    ]);
  }

  _selection(data, now) {
    const next = nextSalah(data, now);
    const congregation = jamaatPanel(data, "previous", now);
    return JSON.stringify([next, congregation, highlightedPrayer(data, now),
      data.prayers.map(row => row && prayerIsPast(row, now)),
      ...["sehri", "iftar"].map(kind => {
        const value = nextRamadanEvent(data, kind, now);
        const instant = timestamp(value);
        return [value, instant !== null && instant < now];
      })]);
  }

  _tick(now = Date.now()) {
    const live = this._live;
    if (!live) return;
    if (this._selection(live.data, now) !== live.selection) { this._render(now); return; }
    for (const update of live.updates) update(now);
  }

  _render(now = Date.now()) {
    if (!this.shadowRoot) return;
    const ui = resolveUi(this._config, this._hass);
    direction(this, ui);
    this._renderedHassKey = this._hassRenderKey();
    this._live = null;
    const updates = [];
    const style = node("style", CSS);
    const card = direction(node("ha-card"), ui);
    const state = this._state();
    if (!this._activeEntity() || !state || ["unavailable", "unknown"].includes(state.state) || !isTimetableState(state)) {
      const key = !this._activeEntity() ? "card.choose_entity" : !state ? "card.entity_missing" : "card.unavailable";
      card.append(node("div", tr(ui, key), "empty"));
      this.shadowRoot.replaceChildren(style, card);
      return;
    }
    const previousRegion = this.shadowRoot.querySelector?.(".table-scroll");
    const regionFocused = Boolean(previousRegion && this.shadowRoot.activeElement === previousRegion);
    const scrollLeft = previousRegion?.scrollLeft || 0;
    const data = state.attributes;
    const zone = data.time_zone || this._hass?.config?.time_zone || "UTC";
    const content = node("div", undefined, `content ${this._config.detail_level === "compact" ? "compact" : "expanded"}`);
    const timeFormat = this._config.time_format;
    const header = node("header", undefined, "header");
    const title = node("h2", this._config.title || data.mosque_name); title.setAttribute("dir", "auto");
    header.append(title);
    if (this._config.detail_level !== "compact" && this._config.show_hijri_date && data.show_hijri_date !== false) header.append(node("div", `${formatHijriDate(data.date || state.state, this._config.hijri_adjustment, ui)} · ${tr(ui, "card.hijri_calculated")}`, "date hijri"));
    if (this._config.detail_level !== "compact" && this._config.show_gregorian_date) header.append(node("div", formatDate(data.date || state.state, ui), "date gregorian"));
    content.append(header);
    const mosques = this._mosques();
    if (mosques.length > 1) {
      const tabs = node("nav", undefined, "mosque-tabs");
      tabs.setAttribute("aria-label", "Mosques");
      for (const mosque of mosques) {
        const button = node("button", mosque.name || mosque.entity, "mosque-tab");
        button.type = "button";
        button.setAttribute("aria-pressed", String(mosque.entity === this._activeEntity()));
        button.addEventListener("click", () => {
          if (mosque.entity === this._activeEntity()) return;
          this._selectedMosque = mosque.entity;
          this._render();
        });
        tabs.append(button);
      }
      content.append(tabs);
    }
    const dateTabs = node("nav", undefined, "date-tabs");
    dateTabs.setAttribute("aria-label", tr(ui, "card.day_navigation"));
    for (const [offset, key] of [[-1, "yesterday"], [0, "today"], [1, "tomorrow"]]) {
      const button = node("button", tr(ui, `card.${key}`), "date-tab");
      button.type = "button";
      button.setAttribute("aria-pressed", String(this._selectedDay === offset));
      button.addEventListener("click", () => { if (this._selectedDay !== offset) { this._selectedDay = offset; this._render(); } });
      dateTabs.append(button);
    }
    content.append(dateTabs);
    const baseDate = Date.parse(`${data.date || state.state}T12:00:00Z`);
    const selectedDate = Number.isFinite(baseDate) ? new Date(baseDate + this._selectedDay * 86400000).toISOString().slice(0, 10) : "";
    const selectedPrayers = this._selectedDay === 0 ? data.prayers : data.day_prayers?.[selectedDate];
    if (this._selectedDay !== 0) {
      content.append(node("div", formatDate(selectedDate, ui), "selected-date"));
      if (!selectedPrayers) {
        content.append(node("div", tr(ui, "card.day_unavailable"), "empty"));
        card.append(content); this.shadowRoot.replaceChildren(style, card);
        return;
      }
    }
    if (this._hass?.connection?.connected === false) content.append(node("p", tr(ui, "card.disconnected"), "disconnected"));
    const next = nextSalah(data, now);
    const previous = jamaatPanel(data, "previous", now).event;
    const panels = node("div", undefined, "panels");
    if (this._selectedDay === 0 && this._config.show_salah_countdown) {
      const box = prayerPanel("salah", next, data, zone, ui, this._config, countdown(next?.timestamp, now, ui));
      updates.push(instant => { box.clock.run.textContent = countdown(next?.timestamp, instant, ui); });
      panels.append(box);
    }
    if (this._selectedDay === 0 && this._config.show_jamaat_countdown) panels.append(prayerPanel("jamaat", previous, data, zone, ui, this._config));
    if (panels.children.length) content.append(panels);
    const highlighted = highlightedPrayer(data, now);
    let tableRegion;
    if (this._selectedDay !== 0 || this._config.detail_level !== "compact") {
    const table = node("table");
    table.append(node("caption", tr(ui, "table.caption"), "sr-only"));
    const head = node("thead"); const headRow = node("tr");
    for (const key of ["table.prayer", "table.beginning", "table.jamaat"]) { const th = node("th", tr(ui, key)); th.scope = "col"; headRow.append(th); }
    head.append(headRow); table.append(head);
    const body = node("tbody");
    for (const prayer of selectedPrayers) {
      if (!prayer || typeof prayer !== "object") continue;
      const row = node("tr", undefined, this._selectedDay === 0 ? (prayer.key === highlighted ? "next-prayer" : prayerIsPast(prayer, now) ? "past-prayer" : "") : "");
      if (this._selectedDay === 0 && prayer.key === highlighted) row.setAttribute("aria-current", "true");
      const name = node("th"); name.scope = "row";
      name.append(prayerNode(prayer.key, ui, this._config.bilingual_prayer_labels, prayer.name));
      const congregations = Array.isArray(prayer.jamaat) ? prayer.jamaat : [];
      const congregationCell = node("td");
      for (const value of congregations) {
        const isJumuah = prayer.key === "dhuhr" && Array.isArray(data.jamaat_events) && data.jamaat_events.some(event => event.prayer === "jumuah" && Date.parse(event.timestamp) === Date.parse(value));
        const congregationTime = node("div", undefined, "congregation-time");
        if (isJumuah) congregationTime.append(prayerNode("jumuah", ui, this._config.bilingual_prayer_labels), node("span", " "));
        congregationTime.append(isolated(formatTime(value, zone, ui, timeFormat)));
        congregationCell.append(congregationTime);
      }
      if (!congregations.length) congregationCell.append(isolated("—"));
      const beginningCell = formattedNode("td", formatTime(prayer.begin, zone, ui, timeFormat));
      if (this._config.detail_level === "detailed" && prayer.key === "fajr") beginningCell.append(translatedRun("div", ui, "table.fajr_end", "time", formatTime(prayer.end, zone, ui, timeFormat), "note fajr-end"));
      row.append(name, beginningCell, congregationCell);
      body.append(row);
    }
    table.append(body);
    tableRegion = node("div", undefined, "table-scroll");
    tableRegion.tabIndex = 0;
    tableRegion.setAttribute("role", "region");
    tableRegion.setAttribute("aria-label", tr(ui, "table.region"));
    const scrollHelp = node("p", tr(ui, "table.scroll_help"), "note scroll-help");
    tableRegion.append(table); content.append(tableRegion, scrollHelp);
    }
    if (this._selectedDay === 0 && this._config.detail_level === "detailed" && timestamp(data.second_khutbah) !== null && typeof data.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(data.date) && new Date(`${data.date}T12:00:00Z`).getUTCDay() === 5) {
      content.append(translatedRun("p", ui, "card.second_khutbah", "time", formatTime(data.second_khutbah, zone, ui, timeFormat), "note khutbah"));
    }
    if (this._selectedDay === 0 && this._config.detail_level === "detailed" && data.ramadan?.active && this._config.show_ramadan_details) {
      const ramadan = node("section", undefined, "ramadan"); ramadan.append(node("h3", tr(ui, "ramadan.title")));
      const grid = node("div", undefined, "ramadan-grid");
      for (const kind of ["sehri", "iftar"]) {
        const value = nextRamadanEvent(data, kind, now);
        const box = node("div"); box.setAttribute("data-ramadan", kind);
        box.append(node("div", tr(ui, kind === "sehri" ? "ramadan.sehri_ends" : "ramadan.iftar"), "label"), formattedNode("div", formatTime(value, zone, ui, timeFormat), "event"));
        if (this._config[`show_${kind}_countdown`]) {
          const clock = clockNode(countdown(value, now, ui), ui); box.append(clock);
          updates.push(instant => { clock.run.textContent = countdown(value, instant, ui); });
        }
        grid.append(box);
      }
      const taraweeh = node("div");
      const taraweehValue = data.ramadan.taraweeh ? formattedNode("div", formatTime(data.ramadan.taraweeh, zone, ui, timeFormat), "event") : node("div", data.ramadan.taraweeh_text || tr(ui, "ramadan.no_time"), "event");
      if (!data.ramadan.taraweeh && data.ramadan.taraweeh_text) taraweehValue.setAttribute("dir", "auto");
      taraweeh.append(node("div", tr(ui, "ramadan.taraweeh"), "label"), taraweehValue); grid.append(taraweeh);
      ramadan.append(grid); content.append(ramadan);
    }
    if (this._selectedDay === 0 && this._config.show_timezone_note) {
      const note = translatedRun("p", ui, "card.timezone_note", "zone", zone, "note");
      note.setAttribute("data-role", "timezone-note"); content.append(note);
    }
    card.append(content); this.shadowRoot.replaceChildren(style, card);
    if (tableRegion) {
      tableRegion.scrollLeft = scrollLeft;
      if (regionFocused) tableRegion.focus({preventScroll: true});
    }
    this._live = {data, updates, selection: this._selection(data, now)};
  }
}

export class SalahTimetableCardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({mode: "open"}); this._config = normalizeConfig({}); }
  setConfig(config) {
    const next = normalizeForUi(config, this._hass);
    const changed = JSON.stringify(next) !== JSON.stringify(this._config);
    this._config = next;
    if (changed || !this._controls) this._render();
  }
  set hass(value) { this._hass = value; this._render(); }
  _changed(patch) {
    this._config = normalizeForUi({...this._config, ...patch}, this._hass);
    this._updateControls();
    this.dispatchEvent(new CustomEvent("config-changed", {detail: {config: {...this._config}}, bubbles: true, composed: true}));
  }
  _updateControls() {
    if (!this._controls) return;
    const ui = resolveUi(this._config, this._hass);
    direction(this, ui); direction(this._form, ui);
    for (const [key, {control, checkbox, label, options}] of Object.entries(this._extraControls || {})) {
      const text = tr(ui, `editor.${key}`);
      label.textContent = text; control.setAttribute("aria-label", text);
      for (const {option, value} of options || []) option.textContent = key === "hijri_adjustment" ? localizedNumber(value, ui, {signDisplay: "exceptZero"}) : tr(ui, `editor.${key}.${value}`);
      if (checkbox) control.checked = this._config[key];
      else if (control.value !== String(this._config[key])) control.value = String(this._config[key]);
    }
    const {entity, title, titleLabel, error, help} = this._controls;
    entity.hass = this._hass; entity.label = tr(ui, "editor.entity");
    const mosques = discoverTimetableEntities(this._hass);
    const options = mosques.map(({entity: value, name}) => ({value, label: `${name} (${value})`}));
    // Preserve a saved selection while Home Assistant is starting or the
    // selected mosque is temporarily unavailable.
    if (this._config.entity && !mosques.some(item => item.entity === this._config.entity)) {
      options.push({value: this._config.entity, label: this._config.entity});
    }
    entity.selector = {select: {options}};
    titleLabel.textContent = tr(ui, "editor.title");
    error.textContent = this._entityError ? tr(ui, "editor.invalid_entity") : "";
    help.textContent = tr(ui, "editor.help");
    if (entity.value !== this._config.entity) entity.value = this._config.entity;
    if (title.value !== (this._config.title || "")) title.value = this._config.title || "";
  }
  _render() {
    if (!this.shadowRoot) return;
    if (this._controls) { this._updateControls(); return; }
    const style = node("style", ":host{display:block}.form{display:grid;gap:16px;padding:12px 0}.help{color:var(--secondary-text-color);font-size:.9rem}.error{color:var(--error-color)}.setting{display:flex;justify-content:space-between;gap:12px;align-items:center}.setting select{font:inherit;color:var(--primary-text-color);background:var(--card-background-color);padding:8px;max-width:55%}.setting span{overflow-wrap:anywhere}.title-field{display:grid;gap:7px}.title-field label{font:inherit;color:var(--primary-text-color)}.title-field input{box-sizing:border-box;width:100%;padding:12px;border:1px solid var(--divider-color);border-radius:4px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit}.title-field input:focus{outline:2px solid var(--primary-color);outline-offset:1px}@media(max-width:420px){.setting{gap:8px}}");
    const form = node("div", undefined, "form"); this._form = form;
    const entity = node("ha-selector");
    const error = node("div", "", "error"); error.setAttribute("role", "alert");
    entity.addEventListener("value-changed", event => {
      const value = event.detail?.value;
      this._entityError = Boolean(value && !isTimetableState(this._hass?.states?.[value]));
      if (this._entityError) { this._updateControls(); return; }
      this._changed({entity: value || ""});
    });
    const titleField = node("div", undefined, "title-field");
    const titleLabel = node("label"); titleLabel.htmlFor = "mosque-title";
    const title = node("input"); title.id = "mosque-title"; title.type = "text"; title.value = this._config.title || ""; title.maxLength = 100; title.setAttribute("dir", "auto");
    titleField.append(titleLabel, title);
    title.addEventListener("input", event => this._changed({title: event.target.value}));
    const help = node("div", undefined, "help");
    this._controls = {entity, title, titleLabel, error, help};
    this._extraControls = {};
    const settings = [
      ["language", ["auto", "en", "ar"]], ["bilingual_prayer_labels"],
      ["detail_level", ["compact", "standard", "detailed"]], ["time_format", ["24h", "12h"]],
      ["hijri_adjustment", [-3, -2, -1, 0, 1, 2, 3]],
      ["show_hijri_date"], ["show_gregorian_date"], ["show_salah_countdown"], ["show_jamaat_countdown"],
      ["show_ramadan_details"], ["show_sehri_countdown"], ["show_iftar_countdown"], ["show_timezone_note"]
    ];
    const extras = [];
    for (const [key, choices] of settings) {
      const field = node("label", undefined, "setting"); const label = node("span"); field.append(label);
      const control = node(choices ? "select" : "input"); const options = [];
      if (choices) for (const value of choices) { const option = node("option"); option.value = String(value); control.append(option); options.push({option, value}); }
      else control.type = "checkbox";
      control.setAttribute("data-option", key);
      control.addEventListener("change", () => this._changed({[key]: choices ? key === "hijri_adjustment" ? Number(control.value) : control.value : control.checked}));
      this._extraControls[key] = {control, checkbox: !choices, label, options}; field.append(control); extras.push(field);
    }
    form.append(entity, error, titleField, ...extras, help);
    this._updateControls();
    this.shadowRoot.replaceChildren(style, form);
  }
}

if (!customElements.get("salah-timetable-card")) customElements.define("salah-timetable-card", SalahTimetableCard);
if (!customElements.get("salah-timetable-card-editor")) customElements.define("salah-timetable-card-editor", SalahTimetableCardEditor);
window.customCards = window.customCards || [];
const registrationUi = resolveUi({}, {language: globalThis.navigator?.language});
if (!window.customCards.some(card => card.type === "salah-timetable-card")) window.customCards.push({type: "salah-timetable-card", name: tr(registrationUi, "card.name"), description: tr(registrationUi, "card.description"), preview: true});
