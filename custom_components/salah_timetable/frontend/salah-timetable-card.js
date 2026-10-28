import {MOSQUE_BACKGROUNDS, chooseMosqueBackground} from "./mosque-backgrounds.js?v=0.9.11";
import {CARD_CSS, EDITOR_CSS} from "./card-styles.js?v=0.9.11";
import {eventProgress, publishedTimes, hijriMonthInfo, formatHijriDate, highlightedPrayer, prayerIsPast, countdown, discoverEntity, discoverTimetableEntities, elapsed, formatDate, formatTime, isTimetableState, jamaatPanel, nextRamadanEvent, nextSalah, normalizeConfig, timestamp} from "./card-utils.js?v=0.9.11";
import {localizedNumber, prayerLabels, resolveUi, tr} from "./card-i18n.js?v=0.9.11";

// Keep HA bookkeeping and unrelated entity updates out of the render decision.
const RENDER_ATTRIBUTES = [
  "mosque_name", "date", "time_zone", "prayers", "day_prayers", "beginning_events", "jamaat_events",
  "next_salah", "next_jamaat", "previous_jamaat", "context_jamaat", "context_mode",
  "ramadan", "sehri_events", "iftar_events", "next_sehri", "next_iftar",
  "show_hijri_date", "second_khutbah",
];
const PRAYERS = new Set(["fajr", "sunrise", "dhuhr", "jumuah", "asr", "maghrib", "isha"]);



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

// Subtle inline SVG silhouettes; purely decorative and independent of mosque data.
function panelSilhouette(kind) {
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

// Shared structure and styles for the upcoming Salah and contextual Jamaat.
function prayerPanel(kind, event, data, zone, ui, config, clock, mode = "previous") {
  const result = node("section", undefined, "panel prayer-panel");
  result.setAttribute("data-panel", kind);
  const label = node("div", tr(ui, kind === "salah" ? "panel.next_salah" : mode === "upcoming" ? "panel.next_jamaat" : "panel.previous_jamaat"), "label");
  const name = node("div", undefined, "event");
  if (event) name.append(prayerNode(eventPrayerKey(event), ui, config.bilingual_prayer_labels, event.name));
  else name.textContent = tr(ui, "status.unavailable");
  result.append(label, name);
  if (kind === "salah" || kind === "jamaat") {
    result.clock = clockNode(clock, ui, kind === "jamaat" && mode === "previous");
    result.append(result.clock);
  }
  const times = publishedTimes(data, event, kind === "jamaat");
  const grid = node("div", undefined, "prayer-times");
  for (const [key, value] of [["table.beginning", times.begin], ["table.jamaat", times.jamaat]]) {
    const cell = node("div", undefined, "prayer-time");
    cell.append(node("div", tr(ui, key), "label"), formattedNode("div", formatTime(value, zone, ui, config.time_format), "absolute"));
    grid.append(cell);
  }
  result.append(grid, panelSilhouette(kind));
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
  getCardSize() { return (this._config.detail_level === "compact" ? 3 : 5) + (this._state()?.attributes?.ramadan?.active && this._config.show_ramadan_details ? 2 : 0); }
  getGridOptions() { return {columns: 12, rows: this.getCardSize(), min_columns: 6, min_rows: 4}; }

  connectedCallback() {
    if (this._timer === null) this._timer = window.setInterval(() => this._tick(), 1000);
    this._render();
  }
  disconnectedCallback() {
    if (this._timer !== null) window.clearInterval(this._timer);
    this._timer = null;
  }
  _mosques() {
    const available = discoverTimetableEntities(this._hass);
    if (!this._config.mosque_entities) return available;
    const enabled = new Set(this._config.mosque_entities);
    return available.filter(mosque => enabled.has(mosque.entity));
  }
  _activeEntity() {
    const mosques = this._mosques();
    if (this._selectedMosque && mosques.some(item => item.entity === this._selectedMosque)) return this._selectedMosque;
    if (this._config.entity && (!this._config.mosque_entities || this._config.mosque_entities.includes(this._config.entity))) return this._config.entity;
    return mosques[0]?.entity || this._config.mosque_entities?.[0] || "";
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
    const congregation = jamaatPanel(data, "context", now);
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
    const style = node("style", CARD_CSS);
    const card = direction(node("ha-card"), ui);
    const state = this._state();
    const background = this._config.show_mosque_background && chooseMosqueBackground(MOSQUE_BACKGROUNDS, this._config.mosque_background, (state?.attributes?.date || new Date(now).toISOString().slice(0, 10)));
    if (background) {
      card.classList.add("has-mosque-background");
      card.style.setProperty("--mosque-background-image", `url("${background.path}")`);
      card.style.setProperty("--mosque-overlay", `color-mix(in srgb, var(--ha-card-background,var(--card-background-color)) ${100 - this._config.mosque_background_opacity}%, transparent)`);
      card.style.setProperty("--mosque-background-position", background.position || "center");
    }
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
    const mosques = this._mosques();
    const title = node("h2");
    if (mosques.length > 1) {
      // The active mosque is displayed only in the header, never repeated in tabs.
      const chooser = node("select", undefined, "mosque-select");
      chooser.setAttribute("aria-label", tr(ui, "card.select_mosque"));
      chooser.setAttribute("dir", "auto");
      for (const mosque of mosques) {
        const name = mosque.entity === this._config.entity && this._config.title
          ? this._config.title : (mosque.name || mosque.entity);
        const option = node("option", name);
        option.value = mosque.entity;
        chooser.append(option);
      }
      chooser.value = this._activeEntity();
      chooser.addEventListener("change", () => {
        if (chooser.value === this._activeEntity()) return;
        this._selectedMosque = chooser.value;
        this._selectedDay = 0;
        this._render();
      });
      title.append(chooser);
    } else {
      title.textContent = this._config.title || data.mosque_name;
      title.setAttribute("dir", "auto");
    }
    header.append(title);
    if (this._config.detail_level !== "compact" && this._config.show_hijri_date && data.show_hijri_date !== false) header.append(node("div", `${formatHijriDate(data.date || state.state, this._config.hijri_adjustment, ui)} · ${tr(ui, "card.hijri_calculated")}`, "date hijri"));
    if (this._config.detail_level !== "compact" && this._config.show_gregorian_date) header.append(node("div", formatDate(data.date || state.state, ui), "date gregorian"));
    if (this._config.detail_level !== "compact" && this._config.show_hijri_date && data.show_hijri_date !== false && this._config.show_hijri_month_info) {
      // Show context only beneath a visible Hijri date; never repeat its month.
      // The header remains based on the mosque's current day during date navigation.
      const month = hijriMonthInfo(data.date || state.state, this._config.hijri_adjustment);
      if (month) header.append(node("div", month.summary_en, "month-description"));
    }
    // One cohesive glass surface for mosque identity and both live summaries.
    // Individual countdown components remain independent for timing and options.
    const summary = node("div", undefined, "summary-shell");
    summary.append(header);
    content.append(summary);
    const dateTabs = node("nav", undefined, "date-tabs");
    dateTabs.setAttribute("aria-label", tr(ui, "card.day_navigation"));
    for (const [offset, key] of [[-1, "yesterday"], [0, "today"], [1, "tomorrow"]]) {
      const button = node("button", tr(ui, `card.${key}`), "date-tab");
      button.type = "button";
      button.setAttribute("aria-pressed", String(this._selectedDay === offset));
      button.addEventListener("click", () => { if (this._selectedDay !== offset) { this._selectedDay = offset; this._render(); } });
      dateTabs.append(button);
    }
    const baseDate = Date.parse(`${data.date || state.state}T12:00:00Z`);
    const selectedDate = Number.isFinite(baseDate) ? new Date(baseDate + this._selectedDay * 86400000).toISOString().slice(0, 10) : "";
    const selectedPrayers = this._selectedDay === 0 ? data.prayers : data.day_prayers?.[selectedDate];
    const tableShell = node("div", undefined, "timetable-shell");
    if (this._selectedDay !== 0) tableShell.append(node("div", formatDate(selectedDate, ui), "selected-date"));
    if (this._hass?.connection?.connected === false) summary.append(node("p", tr(ui, "card.disconnected"), "disconnected"));
    const next = nextSalah(data, now);
    const congregation = jamaatPanel(data, "context", now);
    const panels = node("div", undefined, "panels");
    if (this._selectedDay === 0 && this._config.show_salah_countdown) {
      const box = prayerPanel("salah", next, data, zone, ui, this._config, countdown(next?.timestamp, now, ui));
      updates.push(instant => { box.clock.run.textContent = countdown(next?.timestamp, instant, ui); });
      panels.append(box);
    }
    if (this._selectedDay === 0 && this._config.show_jamaat_countdown) {
      const congregationClock = instant => congregation.mode === "upcoming"
        ? countdown(congregation.event?.timestamp, instant, ui)
        : elapsed(congregation.event?.timestamp, instant, ui);
      const box = prayerPanel("jamaat", congregation.event, data, zone, ui, this._config, congregationClock(now), congregation.mode);
      updates.push(instant => { box.clock.run.textContent = congregationClock(instant); });
      panels.append(box);
    }
    if (panels.children.length) summary.append(panels);
    const highlighted = highlightedPrayer(data, now);
    let tableRegion;
    if (Array.isArray(selectedPrayers) && (this._selectedDay !== 0 || this._config.detail_level !== "compact")) {
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
    tableRegion.append(table); tableShell.append(tableRegion, scrollHelp);
    }
    if (!selectedPrayers) tableShell.append(node("div", tr(ui, "card.day_unavailable"), "empty"));
    tableShell.append(dateTabs);
    content.append(tableShell);
    if (this._selectedDay === 0 && this._config.detail_level === "detailed" && timestamp(data.second_khutbah) !== null && typeof data.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(data.date) && new Date(`${data.date}T12:00:00Z`).getUTCDay() === 5) {
      content.append(translatedRun("p", ui, "card.second_khutbah", "time", formatTime(data.second_khutbah, zone, ui, timeFormat), "note khutbah"));
    }
    if (this._selectedDay === 0 && data.ramadan?.active && this._config.show_ramadan_details) {
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
    if (background) {
      const credit = node("small", undefined, "background-credit");
      const link = node("a", `Photo: ${background.photographer} · ${background.name}`);
      link.href = background.source_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      credit.append(link);
      content.append(credit);
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
      const historyLabels = {show_mosque_background: "Show mosque background", mosque_background: "Mosque background", mosque_background_opacity: "Background opacity (%)",show_hijri_month_info: "Show Hijri month information", show_historical_day_events: "Show historical day events (coming soon)", show_historical_month_highlights: "Show monthly history highlights (coming soon)", show_historical_sources: "Show history sources (coming soon)", show_disputed_historical_dates: "Include disputed dates (coming soon)"};
      const text = historyLabels[key] || tr(ui, `editor.${key}`);
      label.textContent = text; control.setAttribute("aria-label", text);
      for (const {option, value} of options || []) option.textContent = key === "hijri_adjustment" ? localizedNumber(value, ui, {signDisplay: "exceptZero"}) : key === "mosque_background_opacity" ? `${value}%` : key === "mosque_background" ? (MOSQUE_BACKGROUNDS.find(item => item.id === value)?.name || (value === "daily" ? "Rotate daily" : "None")) : tr(ui, `editor.${key}.${value}`);
      if (checkbox) control.checked = this._config[key];
      else if (control.value !== String(this._config[key])) control.value = String(this._config[key]);
      // These settings have no implemented behaviour yet; do not allow users
      // to enable an option that cannot display any history data.
      control.disabled = ["show_historical_day_events", "show_historical_month_highlights", "show_historical_sources", "show_disputed_historical_dates"].includes(key);
    }
    const {entity, title, titleLabel, error, help, mosqueGroup, mosqueHeading, mosqueList} = this._controls;
    entity.hass = this._hass; entity.label = tr(ui, "editor.entity");
    const mosques = discoverTimetableEntities(this._hass);
    const options = mosques.map(({entity: value, name}) => ({value, label: `${name} (${value})`}));
    // Preserve a saved selection while Home Assistant is starting or the
    // selected mosque is temporarily unavailable.
    if (this._config.entity && !mosques.some(item => item.entity === this._config.entity)) {
      options.push({value: this._config.entity, label: this._config.entity});
    }
    entity.selector = {select: {options}};
    mosqueHeading.textContent = tr(ui, "editor.mosques");
    const listed = options.map(option => ({entity: option.value, name: mosques.find(item => item.entity === option.value)?.name || option.value}));
    // Preserve any selected-but-temporarily-missing mosque during HA startup.
    for (const value of this._config.mosque_entities || []) {
      if (!listed.some(item => item.entity === value)) listed.push({entity: value, name: value});
    }
    mosqueGroup.hidden = listed.length < 2;
    mosqueList.replaceChildren();
    const enabled = new Set(this._config.mosque_entities || listed.map(item => item.entity));
    for (const mosque of listed) {
      const row = node("label", undefined, "mosque-choice");
      const checkbox = node("input"); checkbox.type = "checkbox";
      checkbox.checked = enabled.has(mosque.entity);
      checkbox.disabled = checkbox.checked && enabled.size === 1;
      checkbox.setAttribute("data-mosque-entity", mosque.entity);
      row.append(checkbox, node("span", mosque.name));
      checkbox.addEventListener("change", () => {
        const allowed = new Set(this._config.mosque_entities || listed.map(item => item.entity));
        if (checkbox.checked) allowed.add(mosque.entity);
        else allowed.delete(mosque.entity);
        if (!allowed.size) { this._updateControls(); return; }
        const entities = [...allowed];
        this._changed({mosque_entities: entities,
          entity: entities.includes(this._config.entity) ? this._config.entity : entities[0]});
      });
      mosqueList.append(row);
    }
    titleLabel.textContent = tr(ui, "editor.title");
    error.textContent = this._entityError ? tr(ui, "editor.invalid_entity") : "";
    help.textContent = tr(ui, "editor.help");
    if (entity.value !== this._config.entity) entity.value = this._config.entity;
    if (title.value !== (this._config.title || "")) title.value = this._config.title || "";
  }
  _render() {
    if (!this.shadowRoot) return;
    if (this._controls) { this._updateControls(); return; }
    const style = node("style", EDITOR_CSS);
    const form = node("div", undefined, "form"); this._form = form;
    const entity = node("ha-selector");
    const error = node("div", "", "error"); error.setAttribute("role", "alert");
    entity.addEventListener("value-changed", event => {
      const value = event.detail?.value;
      this._entityError = Boolean(value && !isTimetableState(this._hass?.states?.[value]));
      if (this._entityError) { this._updateControls(); return; }
      const patch = {entity: value || ""};
      if (value && this._config.mosque_entities && !this._config.mosque_entities.includes(value)) {
        patch.mosque_entities = [...this._config.mosque_entities, value];
      }
      this._changed(patch);
    });
    const titleField = node("div", undefined, "title-field");
    const titleLabel = node("label"); titleLabel.htmlFor = "mosque-title";
    const title = node("input"); title.id = "mosque-title"; title.type = "text"; title.value = this._config.title || ""; title.maxLength = 100; title.setAttribute("dir", "auto");
    titleField.append(titleLabel, title);
    title.addEventListener("input", event => this._changed({title: event.target.value}));
    const mosqueGroup = node("div", undefined, "mosque-options");
    const mosqueHeading = node("div", undefined, "mosque-options-heading");
    const mosqueList = node("div", undefined, "mosque-options-list");
    mosqueGroup.append(mosqueHeading, mosqueList);
    const help = node("div", undefined, "help");
    this._controls = {entity, title, titleLabel, error, help, mosqueGroup, mosqueHeading, mosqueList};
    this._extraControls = {};
    const settings = [
      ["language", ["auto", "en", "ar"]], ["bilingual_prayer_labels"],
      ["detail_level", ["compact", "standard", "detailed"]], ["time_format", ["24h", "12h"]],
      ["hijri_adjustment", [-3, -2, -1, 0, 1, 2, 3]],
      ["show_hijri_date"], ["show_gregorian_date"], ["show_salah_countdown"], ["show_jamaat_countdown"],
      ["show_hijri_month_info"], ["show_historical_day_events"], ["show_historical_month_highlights"], ["show_historical_sources"], ["show_disputed_historical_dates"],
      ["show_mosque_background"], ["mosque_background", ["daily", "none", ...MOSQUE_BACKGROUNDS.map(item => item.id)]], ["mosque_background_opacity", [0, 3, 5, 7, 10, 12, 15, 20]],
      ["show_ramadan_details"], ["show_sehri_countdown"], ["show_iftar_countdown"], ["show_timezone_note"]
    ];
    const extras = [];
    for (const [key, choices] of settings) {
      const field = node("label", undefined, "setting"); const label = node("span"); field.append(label);
      const control = node(choices ? "select" : "input"); const options = [];
      if (choices) for (const value of choices) { const option = node("option"); option.value = String(value); control.append(option); options.push({option, value}); }
      else control.type = "checkbox";
      control.setAttribute("data-option", key);
      control.addEventListener("change", () => {
        if (control.disabled) return;
        this._changed({[key]: choices ? ["hijri_adjustment", "mosque_background_opacity"].includes(key) ? Number(control.value) : control.value : control.checked});
      });
      this._extraControls[key] = {control, checkbox: !choices, label, options}; field.append(control); extras.push(field);
    }
    form.append(entity, error, titleField, mosqueGroup, ...extras, help);
    this._updateControls();
    this.shadowRoot.replaceChildren(style, form);
  }
}

if (!customElements.get("salah-timetable-card")) customElements.define("salah-timetable-card", SalahTimetableCard);
if (!customElements.get("salah-timetable-card-editor")) customElements.define("salah-timetable-card-editor", SalahTimetableCardEditor);
window.customCards = window.customCards || [];
const registrationUi = resolveUi({}, {language: globalThis.navigator?.language});
if (!window.customCards.some(card => card.type === "salah-timetable-card")) window.customCards.push({type: "salah-timetable-card", name: tr(registrationUi, "card.name"), description: tr(registrationUi, "card.description"), preview: true});
