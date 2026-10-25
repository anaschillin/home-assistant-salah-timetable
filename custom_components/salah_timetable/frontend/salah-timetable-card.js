import {eventProgress, formatHijriDate, highlightedPrayer, prayerIsPast, countdown, discoverEntity, elapsed, formatDate, formatTime, isTimetableState, jamaatPanel, nextRamadanEvent, nextSalah, normalizeConfig, prayerName, timestamp} from "./card-utils.js?v=0.8.0";

// Keep HA bookkeeping and unrelated entity updates out of the render decision.
const RENDER_ATTRIBUTES = [
  "mosque_name", "date", "time_zone", "prayers", "beginning_events", "jamaat_events",
  "next_salah", "next_jamaat", "previous_jamaat", "context_jamaat", "context_mode",
  "ramadan", "sehri_events", "iftar_events", "next_sehri", "next_iftar",
  "show_hijri_date", "second_khutbah",
];

const CSS = `
:host{display:block;container-type:inline-size;color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,inherit)}
ha-card{display:block;overflow:hidden;background:var(--ha-card-background,var(--card-background-color));border-radius:var(--ha-card-border-radius,12px)}
.content{padding:20px}.header{display:flex;gap:12px;align-items:baseline;justify-content:space-between;flex-wrap:wrap}h2{font-size:1.35rem;margin:0;overflow-wrap:anywhere}.date{color:var(--secondary-text-color);font-size:.9rem}
.panels{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:18px 0}.panel{border-radius:10px;padding:14px;background:var(--secondary-background-color);min-width:0}.label{color:var(--secondary-text-color);font-size:.83rem;margin-bottom:5px}.event{font-weight:600;font-size:1.05rem}.count{font-variant-numeric:tabular-nums;font-size:clamp(1.6rem,6cqi,2.2rem);color:var(--primary-color);margin-top:7px;overflow-wrap:anywhere}.absolute{color:var(--secondary-text-color);font-size:.85rem;margin-top:5px}
.table-scroll{max-width:100%;overflow-x:auto}thead th{overflow-wrap:anywhere}table{width:100%;border-collapse:collapse;font-size:.97rem}th,td{padding:10px 6px;border-bottom:1px solid var(--divider-color);text-align:right;font-variant-numeric:tabular-nums}th:first-child,td:first-child{text-align:left}th{color:var(--secondary-text-color);font-size:.83rem;font-weight:500}tr:last-child td,tr:last-child th{border-bottom:0}.ramadan{border-top:1px solid var(--divider-color);margin-top:14px;padding-top:14px}.ramadan h3{font-size:1rem;margin:0 0 12px}.ramadan-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.ramadan .count{font-size:1.1rem}.note{color:var(--secondary-text-color);font-size:.83rem;margin:12px 0 0}.empty{padding:22px;color:var(--secondary-text-color);line-height:1.5}.disconnected{color:var(--error-color);font-size:.85rem;margin:8px 0}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:420px){.content{padding:14px}.panels{gap:8px}.panel{padding:10px}.count{font-size:1.6rem}.ramadan-grid{grid-template-columns:1fr 1fr}.ramadan-grid>:last-child{grid-column:1/-1}th,td{padding:9px 3px;font-size:.9rem}}

.progress-help{font-size:.72rem;color:var(--secondary-text-color);margin-top:5px}.scroll-help{display:none;font-size:.75rem}
.event,.absolute,.date,.label{overflow-wrap:anywhere}
progress::-webkit-progress-bar{background:var(--divider-color)}progress::-webkit-progress-value{background:var(--primary-color)}progress::-moz-progress-bar{background:var(--primary-color)}
progress{display:block;width:100%;height:4px;margin-top:12px;border:0;accent-color:var(--primary-color)}
.next-prayer{background:color-mix(in srgb,var(--primary-color) 12%,transparent)}.next-prayer th,.next-prayer td{font-weight:700;font-size:1.05em}.past-prayer{color:var(--secondary-text-color)}
.congregation-time{white-space:nowrap}.hijri{flex-basis:100%}.compact{padding:12px}.compact th,.compact td{padding-top:6px;padding-bottom:6px}.compact .panel{padding:10px}.compact .count{font-size:1.6rem}
table{table-layout:fixed;min-width:22rem}th:first-child{width:30%}.panels:has(>:only-child){grid-template-columns:1fr}
@container(max-width:26rem){.scroll-help{display:block}.panels{grid-template-columns:1fr}.count{font-size:1.7rem}.ramadan-grid{grid-template-columns:1fr 1fr}.ramadan-grid>:last-child{grid-column:1/-1}}

`;

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function congregationProgressLabel(label) {
  return label === "Next Salah Begins" ? "Since previous Salah beginning" : "Since previous Jamaat";
}

function panel(label, event, clock, zone, locale, timeFormat, progress) {
  const result = node("section", undefined, "panel");
  result.clock = node("div", clock, "count");
  result.append(node("div", label, "label"), node("div", prayerName(event), "event"), result.clock);
  result.append(node("div", event ? formatTime(event.timestamp, zone, locale, timeFormat) : "No published event", "absolute"));
  if (progress !== null && progress !== undefined) {
    const bar = node("progress"); bar.max = 100; bar.value = progress;
    bar.setAttribute("aria-label", `${label}: progress between published events`);
    result.progressBar = bar;
    const description = congregationProgressLabel(label);
    bar.title = description;
    result.append(bar, node("div", description, "progress-help"));
  }
  return result;
}

export class SalahTimetableCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this._config = normalizeConfig({});
    this._timer = null;
  }

  static getConfigElement() { return document.createElement("salah-timetable-card-editor"); }
  static getStubConfig(hass) { return normalizeConfig({entity: discoverEntity(hass)}); }
  setConfig(config) { this._config = normalizeConfig(config); this._render(); }
  set hass(value) {
    this._hass = value;
    if (this._hassRenderKey() !== this._renderedHassKey) this._render();
  }
  getCardSize() { return (this._config.layout === "compact" ? 4 : 5) + (this._state()?.attributes?.ramadan?.active && this._config.show_ramadan_details ? 2 : 0); }
  getGridOptions() { return {columns: 12, rows: this.getCardSize(), min_columns: 6, min_rows: 4}; }

  connectedCallback() {
    if (this._timer === null) this._timer = window.setInterval(() => this._tick(), 1000);
    this._render();
  }
  disconnectedCallback() {
    if (this._timer !== null) window.clearInterval(this._timer);
    this._timer = null;
  }
  _state() { return this._hass?.states?.[this._config.entity]; }

  _hassRenderKey() {
    const state = this._state();
    const data = state?.attributes;
    return JSON.stringify([
      Boolean(state), state?.state,
      ...RENDER_ATTRIBUTES.map(key => data?.[key]),
      data?.time_zone || this._hass?.config?.time_zone || "UTC",
      this._hass?.locale?.language || this._hass?.language,
      this._hass?.connection?.connected === false,
    ]);
  }

  _selection(data, now) {
    const next = nextSalah(data, now);
    const congregation = jamaatPanel(data, this._config.mode, now);
    return JSON.stringify([next, congregation, highlightedPrayer(data, now),
      data.prayers.map(row => row && prayerIsPast(row, now)),
      ...["sehri", "iftar"].map(kind => { const value = nextRamadanEvent(data, kind, now); return [value, countdown(value, now) === "Passed"]; })]);
  }

  _tick(now = Date.now()) {
    const live = this._live;
    if (!live) return;
    if (this._selection(live.data, now) !== live.selection) { this._render(now); return; }
    for (const update of live.updates) update(now);
  }

  _render(now = Date.now()) {
    if (!this.shadowRoot) return;
    this._renderedHassKey = this._hassRenderKey();
    this._live = null;
    const updates = [];
    const style = node("style", CSS);
    const card = node("ha-card");
    const state = this._state();
    if (!this._config.entity || !state || ["unavailable", "unknown"].includes(state.state) || !isTimetableState(state)) {
      const message = !this._config.entity ? "Choose a mosque Prayer timetable sensor in the card editor." : !state ? "Timetable entity was not found. Check the selected mosque." : "Timetable unavailable. Check the mosque integration and imported dates.";
      card.append(node("div", message, "empty"));
      this.shadowRoot.replaceChildren(style, card);
      return;
    }
    const previousRegion = this.shadowRoot.querySelector?.(".table-scroll");
    const regionFocused = Boolean(previousRegion && this.shadowRoot.activeElement === previousRegion);
    const scrollLeft = previousRegion?.scrollLeft || 0;
    const data = state.attributes;
    const zone = data.time_zone || this._hass?.config?.time_zone || "UTC";
    const locale = this._hass?.locale?.language || this._hass?.language;
    const content = node("div", undefined, `content ${this._config.layout}`);
    const timeFormat = this._config.time_format;
    const header = node("header", undefined, "header");
    header.append(node("h2", this._config.title || data.mosque_name), node("div", formatDate(data.date || state.state, locale), "date"));
    if (this._config.show_hijri_date && data.show_hijri_date !== false) header.append(node("div", `${formatHijriDate(data.date || state.state, this._config.hijri_adjustment, locale)} · Hijri (calculated)`, "date hijri"));
    content.append(header);
    if (this._hass?.connection?.connected === false) content.append(node("p", "Home Assistant disconnected — showing the last received timetable.", "disconnected"));
    const next = nextSalah(data, now);
    const congregation = jamaatPanel(data, this._config.mode, now);
    const panels = node("div", undefined, "panels");
    if (this._config.show_salah_countdown) {
      const box = panel("Next Salah Begins", next, countdown(next?.timestamp, now), zone, locale, timeFormat, eventProgress(data, false, next, now));
      updates.push(instant => {
        box.clock.textContent = countdown(next?.timestamp, instant);
        if (box.progressBar) box.progressBar.value = eventProgress(data, false, next, instant);
      });
      panels.append(box);
    }
    if (this._config.show_jamaat_countdown) {
      const clock = instant => congregation.mode === "upcoming" ? countdown(congregation.event?.timestamp, instant) : congregation.event ? `${elapsed(congregation.event.timestamp, instant)} elapsed` : "Unavailable";
      const box = panel(congregation.mode === "upcoming" ? "Next Jamaat" : "Previous Jamaat", congregation.event, clock(now), zone, locale, timeFormat, congregation.mode === "upcoming" ? eventProgress(data, true, congregation.event, now) : null);
      updates.push(instant => {
        box.clock.textContent = clock(instant);
        if (box.progressBar) box.progressBar.value = eventProgress(data, true, congregation.event, instant);
      });
      panels.append(box);
    }
    if (panels.children.length) content.append(panels);
    const highlighted = highlightedPrayer(data, now);
    const table = node("table");
    table.append(node("caption", "Published prayer beginning and congregation times", "sr-only"));
    const head = node("thead"); const headRow = node("tr");
    for (const label of ["Prayer", "Beginning", "Jamaat"]) { const th = node("th", label); th.scope = "col"; headRow.append(th); }
    head.append(headRow); table.append(head);
    const body = node("tbody");
    for (const prayer of data.prayers) {
      if (!prayer || typeof prayer !== "object") continue;
      const row = node("tr", undefined, prayer.key === highlighted ? "next-prayer" : prayerIsPast(prayer, now) ? "past-prayer" : "");
      if (prayer.key === highlighted) row.setAttribute("aria-current", "true");
      const name = node("th", prayer.name || prayerName({prayer: prayer.key})); name.scope = "row";
      const congregations = Array.isArray(prayer.jamaat) ? prayer.jamaat : [];

      const congregationCell = node("td");
      for (const value of congregations) {
        const isJumuah = prayer.key === "dhuhr" && Array.isArray(data.jamaat_events) && data.jamaat_events.some(event => event.prayer === "jumuah" && Date.parse(event.timestamp) === Date.parse(value));
        congregationCell.append(node("div", `${isJumuah ? "Jumuah " : ""}${formatTime(value, zone, locale, timeFormat)}`, "congregation-time"));
      }
      if (!congregations.length) congregationCell.textContent = "—";
      const beginningCell = node("td", formatTime(prayer.begin, zone, locale, timeFormat));
       if (prayer.key === "fajr") beginningCell.append(node("div", `Ends at sunrise: ${formatTime(prayer.end, zone, locale, timeFormat)}`, "note fajr-end"));
       row.append(name, beginningCell, congregationCell);
      body.append(row);
    }
    table.append(body);
    const tableRegion = node("div", undefined, "table-scroll");
    tableRegion.tabIndex = 0;
    tableRegion.setAttribute("role", "region");
    tableRegion.setAttribute("aria-label", "Prayer beginning and Jamaat times");
    const scrollHelp = node("p", "Swipe or scroll horizontally for all prayer times. Keyboard: focus the table and use the arrow keys.", "note scroll-help");
    tableRegion.append(table); content.append(tableRegion, scrollHelp);
    if (timestamp(data.second_khutbah) !== null && typeof data.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(data.date) && new Date(data.date + "T12:00:00Z").getUTCDay() === 5) {
      content.append(node("p", `Second Jumu’ah khutbah: ${formatTime(data.second_khutbah, zone, locale, timeFormat)} (published; not Jamaat)`, "note khutbah"));
    }
    if (data.ramadan?.active && this._config.show_ramadan_details) {
      const ramadan = node("section", undefined, "ramadan"); ramadan.append(node("h3", "Ramadan"));
      const grid = node("div", undefined, "ramadan-grid");
      for (const [label, value] of [["Sehri ends", nextRamadanEvent(data, "sehri", now)], ["Iftar", nextRamadanEvent(data, "iftar", now)]]) {
        const box = node("div"); box.append(node("div", label, "label"), node("div", formatTime(value, zone, locale, timeFormat), "event"));
        if (this._config[label === "Sehri ends" ? "show_sehri_countdown" : "show_iftar_countdown"]) {
          const clock = node("div", countdown(value, now), "count"); box.append(clock);
          updates.push(instant => { clock.textContent = countdown(value, instant); });
        }
        grid.append(box);
      }
      const taraweeh = node("div"); taraweeh.append(node("div", "Taraweeh", "label"), node("div", data.ramadan.taraweeh ? formatTime(data.ramadan.taraweeh, zone, locale, timeFormat) : data.ramadan.taraweeh_text || "No published time", "event")); grid.append(taraweeh);
      ramadan.append(grid); content.append(ramadan);
    }
    if (this._config.show_timezone_note) content.append(node("p", `Times shown in ${zone}. Missing times are not estimated.`, "note"));
    card.append(content); this.shadowRoot.replaceChildren(style, card);
    tableRegion.scrollLeft = scrollLeft;
    if (regionFocused) tableRegion.focus({preventScroll: true});
    this._live = {data, updates, selection: this._selection(data, now)};
  }
}

export class SalahTimetableCardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({mode: "open"}); this._config = normalizeConfig({}); }
  setConfig(config) {
    const next = normalizeConfig(config);
    const changed = JSON.stringify(next) !== JSON.stringify(this._config);
    this._config = next;
    if (changed || !this._controls) this._render();
  }
  set hass(value) { this._hass = value; this._render(); }
  _changed(patch) {
    this._config = normalizeConfig({...this._config, ...patch});
    this._updateControls();
    this.dispatchEvent(new CustomEvent("config-changed", {detail: {config: {...this._config}}, bubbles: true, composed: true}));
  }
  _updateControls() {
    if (!this._controls) return;
    for (const [key, {control, checkbox}] of Object.entries(this._extraControls || {})) {
      if (checkbox) control.checked = this._config[key];
      else if (control.value !== String(this._config[key])) control.value = String(this._config[key]);
    }
    const {entity, mode, title} = this._controls;
    entity.hass = this._hass;
    mode.hass = this._hass;
    if (entity.value !== this._config.entity) entity.value = this._config.entity;
    if (mode.value !== this._config.mode) mode.value = this._config.mode;
    if (title.value !== (this._config.title || "")) title.value = this._config.title || "";
  }
  _render() {
    if (!this.shadowRoot) return;
    if (this._controls) { this._updateControls(); return; }
    const style = node("style", ":host{display:block}.form{display:grid;gap:16px;padding:12px 0}.help{color:var(--secondary-text-color);font-size:.9rem}.error{color:var(--error-color)}.setting{display:flex;justify-content:space-between;gap:12px;align-items:center}.setting select{font:inherit;color:var(--primary-text-color);background:var(--card-background-color);padding:8px}.title-field{display:grid;gap:7px}.title-field label{font:inherit;color:var(--primary-text-color)}.title-field input{box-sizing:border-box;width:100%;padding:12px;border:1px solid var(--divider-color);border-radius:4px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit}.title-field input:focus{outline:2px solid var(--primary-color);outline-offset:1px}");
    const form = node("div", undefined, "form");
    const entity = node("ha-selector"); entity.hass = this._hass; entity.label = "Mosque Prayer timetable sensor"; entity.selector = {entity: {filter: [{domain: "sensor", integration: "salah_timetable"}]}}; entity.value = this._config.entity;
    const error = node("div", "", "error"); error.setAttribute("role", "alert");
    entity.addEventListener("value-changed", event => {
      const value = event.detail?.value;
      if (value && !isTimetableState(this._hass?.states?.[value])) { error.textContent = "Choose the Prayer timetable sensor, rather than an individual prayer sensor."; return; }
      error.textContent = ""; this._changed({entity: value || ""});
    });
    const mode = node("ha-selector"); mode.hass = this._hass; mode.label = "Jamaat panel"; mode.selector = {select: {options: [{value: "context", label: "Context aware"}, {value: "previous", label: "Previous Jamaat"}, {value: "upcoming", label: "Upcoming Jamaat"}]}}; mode.value = this._config.mode;
    mode.addEventListener("value-changed", event => this._changed({mode: event.detail?.value || "upcoming"}));
    const titleField = node("div", undefined, "title-field");
    const titleLabel = node("label", "Title (optional)"); titleLabel.htmlFor = "mosque-title";
    const title = node("input"); title.id = "mosque-title"; title.type = "text"; title.value = this._config.title || ""; title.maxLength = 100;
    titleField.append(titleLabel, title);
    title.addEventListener("input", event => this._changed({title: event.target.value}));
    this._controls = {entity, mode, title};
    this._extraControls = {};
    const settings = [
      ["layout", "Layout", ["expanded", "compact"]], ["time_format", "Time format", ["24h", "12h"]],
      ["hijri_adjustment", "Hijri date adjustment (days)", [-3, -2, -1, 0, 1, 2, 3]],
      ["show_hijri_date", "Show calculated Hijri date"], ["show_salah_countdown", "Show Salah countdown"], ["show_jamaat_countdown", "Show Jamaat countdown"],
      ["show_ramadan_details", "Show Ramadan details"], ["show_sehri_countdown", "Show Sehri countdown"], ["show_iftar_countdown", "Show Iftar countdown"], ["show_timezone_note", "Show timezone and help text"]
    ];
    const extras = [];
    for (const [key, label, choices] of settings) {
      const field = node("label", undefined, "setting"); field.append(node("span", label));
      const control = node(choices ? "select" : "input");
      if (choices) for (const choice of choices) { const option = node("option", String(choice)); option.value = String(choice); control.append(option); }
      else control.type = "checkbox";
      control.setAttribute("aria-label", label);
      control.setAttribute("data-option", key);
      control.addEventListener("change", () => this._changed({[key]: choices ? key === "hijri_adjustment" ? Number(control.value) : control.value : control.checked}));
      this._extraControls[key] = {control, checkbox: !choices}; field.append(control); extras.push(field);
    }
    form.append(entity, error, mode, titleField, ...extras, node("div", "Choose the mosque’s Prayer timetable entity. Countdowns run in this card; no per-second sensor updates or Card Mod are required. Hijri visibility is also controlled under mosque setup and Configure → Mosque settings; the card switch can hide it further. The calculated Hijri date adjustment affects display only, not Ramadan activation.", "help"));
    this._updateControls();
    this.shadowRoot.replaceChildren(style, form);
  }
}

if (!customElements.get("salah-timetable-card")) customElements.define("salah-timetable-card", SalahTimetableCard);
if (!customElements.get("salah-timetable-card-editor")) customElements.define("salah-timetable-card-editor", SalahTimetableCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === "salah-timetable-card")) window.customCards.push({type: "salah-timetable-card", name: "Salah Timetable", description: "Mosque prayer times, contextual Jamaat and Ramadan countdowns", preview: true});
