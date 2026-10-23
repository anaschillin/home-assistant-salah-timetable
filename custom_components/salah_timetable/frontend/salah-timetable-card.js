import {countdown, discoverEntity, elapsed, formatDate, formatTime, isTimetableState, jamaatPanel, nextRamadanEvent, nextSalah, normalizeConfig, prayerName} from "./card-utils.js?v=0.5.3";

const CSS = `
:host{display:block;color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,inherit)}
ha-card{display:block;overflow:hidden;background:var(--ha-card-background,var(--card-background-color));border-radius:var(--ha-card-border-radius,12px)}
.content{padding:20px}.header{display:flex;gap:12px;align-items:baseline;justify-content:space-between;flex-wrap:wrap}h2{font-size:1.35rem;margin:0;overflow-wrap:anywhere}.date{color:var(--secondary-text-color);font-size:.9rem}
.panels{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:18px 0}.panel{border-radius:10px;padding:14px;background:var(--secondary-background-color);min-width:0}.label{color:var(--secondary-text-color);font-size:.83rem;margin-bottom:5px}.event{font-weight:600;font-size:1.05rem}.count{font-variant-numeric:tabular-nums;font-size:1.5rem;color:var(--primary-color);margin-top:7px;overflow-wrap:anywhere}.absolute{color:var(--secondary-text-color);font-size:.85rem;margin-top:5px}
.table-scroll{max-width:100%;overflow-x:auto}thead th{overflow-wrap:anywhere}table{width:100%;border-collapse:collapse;font-size:.97rem}th,td{padding:10px 6px;border-bottom:1px solid var(--divider-color);text-align:right;font-variant-numeric:tabular-nums}th:first-child,td:first-child{text-align:left}th{color:var(--secondary-text-color);font-size:.83rem;font-weight:500}tr:last-child td,tr:last-child th{border-bottom:0}.ramadan{border-top:1px solid var(--divider-color);margin-top:14px;padding-top:14px}.ramadan h3{font-size:1rem;margin:0 0 12px}.ramadan-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.ramadan .count{font-size:1.1rem}.note{color:var(--secondary-text-color);font-size:.83rem;margin:12px 0 0}.empty{padding:22px;color:var(--secondary-text-color);line-height:1.5}.disconnected{color:var(--error-color);font-size:.85rem;margin:8px 0}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:420px){.content{padding:14px}.panels{gap:8px}.panel{padding:10px}.count{font-size:1.25rem}.ramadan-grid{grid-template-columns:1fr 1fr}.ramadan-grid>:last-child{grid-column:1/-1}th,td{padding:9px 3px;font-size:.9rem}}
`;

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function panel(label, event, clock, zone, locale) {
  const result = node("section", undefined, "panel");
  result.append(node("div", label, "label"), node("div", prayerName(event), "event"), node("div", clock, "count"));
  result.append(node("div", event ? formatTime(event.timestamp, zone, locale) : "No published event", "absolute"));
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
  set hass(value) { this._hass = value; this._render(); }
  getCardSize() { return this._state()?.attributes?.ramadan?.active ? 7 : 5; }
  getGridOptions() { return {columns: 12, rows: this.getCardSize(), min_columns: 6, min_rows: 4}; }

  connectedCallback() {
    if (this._timer === null) this._timer = window.setInterval(() => this._render(), 1000);
    this._render();
  }
  disconnectedCallback() {
    if (this._timer !== null) window.clearInterval(this._timer);
    this._timer = null;
  }
  _state() { return this._hass?.states?.[this._config.entity]; }

  _render(now = Date.now()) {
    if (!this.shadowRoot) return;
    const style = node("style", CSS);
    const card = node("ha-card");
    const state = this._state();
    if (!this._config.entity || !state || ["unavailable", "unknown"].includes(state.state) || !isTimetableState(state)) {
      const message = !this._config.entity ? "Choose a mosque Prayer timetable sensor in the card editor." : !state ? "Timetable entity was not found. Check the selected mosque." : "Timetable unavailable. Check the mosque integration and imported dates.";
      card.append(node("div", message, "empty"));
      this.shadowRoot.replaceChildren(style, card);
      return;
    }
    const data = state.attributes;
    const zone = data.time_zone || this._hass?.config?.time_zone || "UTC";
    const locale = this._hass?.locale?.language || this._hass?.language;
    const content = node("div", undefined, "content");
    const header = node("header", undefined, "header");
    header.append(node("h2", this._config.title || data.mosque_name), node("div", formatDate(data.date || state.state, locale), "date"));
    content.append(header);
    if (this._hass?.connection?.connected === false) content.append(node("p", "Home Assistant disconnected — showing the last received timetable.", "disconnected"));
    const next = nextSalah(data, now);
    const congregation = jamaatPanel(data, this._config.mode, now);
    const panels = node("div", undefined, "panels");
    panels.append(panel("Next Salah beginning", next, countdown(next?.timestamp, now), zone, locale));
    panels.append(panel(congregation.mode === "upcoming" ? "Upcoming Jamaat" : "Previous Jamaat", congregation.event, congregation.mode === "upcoming" ? countdown(congregation.event?.timestamp, now) : congregation.event ? `${elapsed(congregation.event.timestamp, now)} elapsed` : "Unavailable", zone, locale));
    content.append(panels);
    const table = node("table");
    table.append(node("caption", "Published prayer beginning and congregation times", "sr-only"));
    const head = node("thead"); const headRow = node("tr");
    for (const label of ["Prayer", "Beginning", "Jamaat"]) { const th = node("th", label); th.scope = "col"; headRow.append(th); }
    head.append(headRow); table.append(head);
    const body = node("tbody");
    for (const prayer of data.prayers) {
      if (!prayer || typeof prayer !== "object") continue;
      const row = node("tr"); const name = node("th", prayer.name || prayerName({prayer: prayer.key})); name.scope = "row";
      const congregations = Array.isArray(prayer.jamaat) ? prayer.jamaat : [];
      row.append(name, node("td", formatTime(prayer.begin, zone, locale)), node("td", congregations.length ? congregations.map(value => formatTime(value, zone, locale)).join(" / ") : "—"));
      body.append(row);
    }
    table.append(body);
    const tableRegion = node("div", undefined, "table-scroll");
    tableRegion.tabIndex = 0;
    tableRegion.setAttribute("role", "region");
    tableRegion.setAttribute("aria-label", "Prayer beginning and Jamaat times");
    tableRegion.append(table); content.append(tableRegion);
    if (data.ramadan?.active) {
      const ramadan = node("section", undefined, "ramadan"); ramadan.append(node("h3", "Ramadan"));
      const grid = node("div", undefined, "ramadan-grid");
      for (const [label, value] of [["Sehri ends", nextRamadanEvent(data, "sehri", now)], ["Iftar", nextRamadanEvent(data, "iftar", now)]]) {
        const box = node("div"); box.append(node("div", label, "label"), node("div", formatTime(value, zone, locale), "event"), node("div", countdown(value, now), "count")); grid.append(box);
      }
      const taraweeh = node("div"); taraweeh.append(node("div", "Taraweeh", "label"), node("div", data.ramadan.taraweeh ? formatTime(data.ramadan.taraweeh, zone, locale) : data.ramadan.taraweeh_text || "No published time", "event")); grid.append(taraweeh);
      ramadan.append(grid); content.append(ramadan);
    }
    content.append(node("p", `Times shown in ${zone}. Missing times are not estimated.`, "note"));
    card.append(content); this.shadowRoot.replaceChildren(style, card);
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
    const style = node("style", ":host{display:block}.form{display:grid;gap:16px;padding:12px 0}.help{color:var(--secondary-text-color);font-size:.9rem}.error{color:var(--error-color)}.title-field{display:grid;gap:7px}.title-field label{font:inherit;color:var(--primary-text-color)}.title-field input{box-sizing:border-box;width:100%;padding:12px;border:1px solid var(--divider-color);border-radius:4px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit}.title-field input:focus{outline:2px solid var(--primary-color);outline-offset:1px}");
    const form = node("div", undefined, "form");
    const entity = node("ha-selector"); entity.hass = this._hass; entity.label = "Mosque Prayer timetable sensor"; entity.selector = {entity: {filter: [{domain: "sensor", integration: "salah_timetable"}]}}; entity.value = this._config.entity;
    const error = node("div", "", "error"); error.setAttribute("role", "alert");
    entity.addEventListener("value-changed", event => {
      const value = event.detail?.value;
      if (value && !isTimetableState(this._hass?.states?.[value])) { error.textContent = "Choose the Prayer timetable sensor, rather than an individual prayer sensor."; return; }
      error.textContent = ""; this._changed({entity: value || ""});
    });
    const mode = node("ha-selector"); mode.hass = this._hass; mode.label = "Jamaat panel"; mode.selector = {select: {options: [{value: "context", label: "Context aware"}, {value: "previous", label: "Previous Jamaat"}, {value: "upcoming", label: "Upcoming Jamaat"}]}}; mode.value = this._config.mode;
    mode.addEventListener("value-changed", event => this._changed({mode: event.detail?.value || "context"}));
    const titleField = node("div", undefined, "title-field");
    const titleLabel = node("label", "Title (optional)"); titleLabel.htmlFor = "mosque-title";
    const title = node("input"); title.id = "mosque-title"; title.type = "text"; title.value = this._config.title || ""; title.maxLength = 100;
    titleField.append(titleLabel, title);
    title.addEventListener("input", event => this._changed({title: event.target.value}));
    this._controls = {entity, mode, title};
    form.append(entity, error, mode, titleField, node("div", "Choose the mosque’s Prayer timetable entity. Countdowns run in this card; no per-second sensor updates or Card Mod are required.", "help"));
    this.shadowRoot.replaceChildren(style, form);
  }
}

if (!customElements.get("salah-timetable-card")) customElements.define("salah-timetable-card", SalahTimetableCard);
if (!customElements.get("salah-timetable-card-editor")) customElements.define("salah-timetable-card-editor", SalahTimetableCardEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === "salah-timetable-card")) window.customCards.push({type: "salah-timetable-card", name: "Salah Timetable", description: "Mosque prayer times, contextual Jamaat and Ramadan countdowns", preview: true});
