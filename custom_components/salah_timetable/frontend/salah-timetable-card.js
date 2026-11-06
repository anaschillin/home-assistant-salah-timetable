import {openReminderWizard} from "./reminder-wizard.js?v=3.1.0";
import {MOSQUE_BACKGROUNDS, chooseMosqueBackground} from "./mosque-backgrounds.js?v=3.1.0";
import {CARD_CSS, EDITOR_CSS} from "./card-styles.js?v=3.1.0";
import {eventProgress, publishedTimes, hijriMonthInfo, formatHijriDate, hijriDisplayDate, highlightedPrayer, prayerIsPast, countdown, discoverEntity, discoverTimetableEntities, elapsed, formatDate, formatTime, isTimetableState, jamaatPanel, nextRamadanEvent, nextSalah, normalizeConfig, timestamp} from "./card-utils.js?v=3.1.0";
import {localizedNumber, prayerLabels, resolveUi, tr} from "./card-i18n.js?v=3.1.0";

// Keep HA bookkeeping and unrelated entity updates out of the render decision.
const RENDER_ATTRIBUTES = [
  "mosque_name", "date", "time_zone", "prayers", "day_prayers", "beginning_events", "jamaat_events",
  "next_salah", "next_jamaat", "previous_jamaat", "context_jamaat", "context_mode",
  "ramadan", "sehri_events", "iftar_events", "next_sehri", "next_iftar",
  "show_hijri_date", "second_khutbah", "night_calculations",
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

/** Compare upcoming Salah against the mosque's civil date, not the browser UTC date. */
function kioskSalahDayLabel(event, now, zone, ui) {
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

// Shared structure and styles for the upcoming Salah and contextual Jamaat.
function prayerPanel(kind, event, data, zone, ui, config, clock, mode = "previous") {
  const result = node("section", undefined, "panel prayer-panel");
  result.setAttribute("data-panel", kind);
  const label = node("div", tr(ui, kind === "salah" ? "panel.next_salah" : mode === "upcoming" ? "panel.next_jamaat" : "panel.previous_jamaat"), "label");
  result.label = label;
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


/** Five published daily prayers in display order; no estimates or synthetic times. */
function kioskPrayerStrip(rows, next, congregation, data, zone, ui, config, selectedDay, now) {
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
    heading.append(prayerNode(prayer.key, ui, config.bilingual_prayer_labels, prayer.name));
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

export class SalahTimetableCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this._config = normalizeConfig({});
    this._timer = null;
    this._selectedMosque = null;
    this._selectedDay = 0;
    this._backgroundFrame = null;
    this._viewportFrame = null;
    this._viewportObserver = null;
    this._viewportHeight = null;
    this._onViewportResize = () => this._scheduleViewportHeight();
    this._onFullscreenChange = () => {
      this._syncFullscreenButton();
      this._scheduleViewportHeight();
    };
    this._fullscreenButton = null;
    this._monthView = false;
    this._monthState = null;
    this._sourceState = null;
    this._monthRequest = 0;
  }

  static getConfigElement() { return document.createElement("salah-timetable-card-editor"); }
  static getStubConfig(hass) { return normalizeConfig({entity: discoverEntity(hass)}); }
  setConfig(config) {
    const next = normalizeForUi(config, this._hass);
    // Reordered mosque lists establish a new first (default) mosque.
    if (this._config?.entity !== next.entity) this._selectedMosque = null;
    this._config = next;
    this._render();
  }
  set hass(value) {
    this._hass = value;
    if (this._hassRenderKey() !== this._renderedHassKey) this._render();
  }
  // Lovelace passes preview=true for some editor paths, but existing
  // dashboards also wrap ordinary cards in hui-card-options (Edit button below
  // the card) or hui-card-edit-mode (overlay). Those wrappers do not reliably
  // forward preview to the custom element. Detect the editor's DOM context
  // rather than relying on preview alone.
  _syncDashboardEditing() {
    const editing = this.preview ||
      Boolean(this.closest?.("hui-card-options, hui-card-edit-mode"));
    if (editing === Boolean(this.hasAttribute?.("dashboard-editing"))) return;
    if (editing) this.setAttribute("dashboard-editing", "");
    else this.removeAttribute("dashboard-editing");
  }
  set preview(value) {
    this._preview = Boolean(value);
    this._syncDashboardEditing();
    this._scheduleViewportHeight();
  }
  get preview() { return this._preview || false; }
  // HA still assigns editMode for compatibility with older custom cards.
  set editMode(value) { this.preview = value; }
  get editMode() { return this.preview; }
  getCardSize() { return (this._config.kiosk_mode ? 7 : this._config.detail_level === "compact" ? 3 : 5) + (this._state()?.attributes?.ramadan?.active && this._config.show_ramadan_details ? 2 : 0); }
  getGridOptions() { return {columns: 12, rows: this.getCardSize(), min_columns: 6, min_rows: 4}; }

  connectedCallback() {
    if (this._timer === null) this._timer = window.setInterval(() => this._tick(), 1000);
    window.addEventListener?.("resize", this._onViewportResize);
    window.visualViewport?.addEventListener?.("resize", this._onViewportResize);
    document.addEventListener?.("fullscreenchange", this._onFullscreenChange);
    if (typeof ResizeObserver !== "undefined") {
      this._viewportObserver = new ResizeObserver(this._onViewportResize);
      this._viewportObserver.observe(this);
    }
    this._syncDashboardEditing();
    this._render();
    this._scheduleViewportHeight();
  }
  disconnectedCallback() {
    if (this._timer !== null) window.clearInterval(this._timer);
    this._timer = null;
    window.removeEventListener?.("resize", this._onViewportResize);
    window.visualViewport?.removeEventListener?.("resize", this._onViewportResize);
    document.removeEventListener?.("fullscreenchange", this._onFullscreenChange);
    this._viewportObserver?.disconnect();
    this._viewportObserver = null;
    if (this._viewportFrame !== null) window.cancelAnimationFrame?.(this._viewportFrame);
    this._viewportFrame = null;
  }
  _isKioskFullscreen() {
    const surface = this.shadowRoot?.querySelector?.("ha-card");
    // The Fullscreen API retargets document.fullscreenElement at shadow roots.
    // ShadowRoot.fullscreenElement identifies the actual fullscreen card.
    return Boolean(surface && (
      this.shadowRoot.fullscreenElement === surface ||
      document.fullscreenElement === surface ||
      document.fullscreenElement === this
    ));
  }
  _syncFullscreenButton() {
    const button = this._fullscreenButton;
    if (!button) return;
    const expanded = this._isKioskFullscreen();
    const label = expanded ? button._exitFullscreenLabel : button._enterFullscreenLabel;
    button.setAttribute("aria-label", label);
    button.setAttribute("title", label);
    button.setAttribute("aria-pressed", String(expanded));
    button.children[0]?.setAttribute("icon",
      expanded ? "mdi:fullscreen-exit" : "mdi:fullscreen");
  }
  _scheduleViewportHeight() {
    this._syncDashboardEditing();
    if (this._viewportFrame !== null || typeof window.requestAnimationFrame !== "function" ||
        this.isConnected === false) return;
    this._viewportFrame = window.requestAnimationFrame(() => {
      this._viewportFrame = null;
      this._measureViewportHeight();
    });
  }
  _measureViewportHeight() {
    // Measure from the card's real viewport position, not a guessed HA header
    // height. visualViewport accounts for mobile browser toolbar resizing.
    if (typeof this.getBoundingClientRect !== "function") return;
    const rect = this.getBoundingClientRect();
    const visual = window.visualViewport;
    const bottom = Number.isFinite(visual?.height) && visual.height > 0
      ? visual.height + (visual.offsetTop || 0) : window.innerHeight;
    if (!Number.isFinite(rect.top) || !(rect.width > 0) ||
        !Number.isFinite(bottom) || bottom <= 0) return;
    // Do not let a scrolled-out card grow beyond one screen. Reserve a little
    // bottom breathing room for HA's dashboard margins and mobile safe area.
    // HA may add a bottom margin beneath a full-screen dashboard card. In
    // kiosk mode leave room for that shell margin instead of inducing a tiny
    // document scrollbar; genuinely taller mobile content still scrolls.
    const reserve = this._config.kiosk_mode && !this.hasAttribute("dashboard-editing") ? 32 : 12;
    const visibleHeight = Math.max(0, Math.floor(bottom - Math.max(0, rect.top) - reserve));
    const value = `${visibleHeight}px`;
    if (this._viewportHeight === value) return;
    this._viewportHeight = value;
    this.style.setProperty("--salah-viewport-card-height", value);
    // The cached photograph frame must match the new canvas before the
    // Yesterday/Tomorrow navigation takes its first size snapshot.
    if (this._selectedDay === 0 && this._config.show_mosque_background && !this.preview) {
      this._rememberBackgroundFrame();
    }
  }
  _mosques() {
    const available = discoverTimetableEntities(this._hass);
    if (!this._config.mosque_entities) return available;
    // The saved list is ordered; alphabetic discovery must not override it.
    const byEntity = new Map(available.map(mosque => [mosque.entity, mosque]));
    return this._config.mosque_entities.map(entity => byEntity.get(entity)).filter(Boolean);
  }
  _activeEntity() {
    const mosques = this._mosques();
    if (this._selectedMosque && mosques.some(item => item.entity === this._selectedMosque)) return this._selectedMosque;
    // An explicitly ordered selection defines the default, even for older YAML
    // whose legacy entity property still names a different mosque.
    if (this._config.mosque_entities?.length) return mosques[0]?.entity || this._config.mosque_entities[0];
    if (this._config.entity) return this._config.entity;
    return mosques[0]?.entity || "";
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
      ui.language, ui.locale, ui.dir, Boolean(this._hass?.user?.is_admin),
      this._hass?.connection?.connected === false,
    ]);
  }

  _rememberBackgroundFrame() {
    // Capture the painted photograph, not just its outer card. The photo may
    // retain a slightly taller frame from an earlier render while viewport
    // measurement is settling. Saving only the shorter card rectangle causes
    // a visible image jump when Yesterday/Tomorrow remove the live panels.
    const card = this.shadowRoot?.querySelector?.("ha-card");
    const rect = card?.getBoundingClientRect?.();
    if (!rect || rect.height <= 0 || rect.width <= 0 || !this._config.show_mosque_background) return;
    const photoHeight = typeof getComputedStyle === "function"
      ? Number.parseFloat(getComputedStyle(card, "::before").height) : NaN;
    const height = Number.isFinite(photoHeight)
      ? Math.max(rect.height, photoHeight + 4) : rect.height;
    this._backgroundFrame = {entity: this._activeEntity(), width: rect.width, height};
  }

  _selection(data, now) {
    const next = nextSalah(data, now);
    const congregation = jamaatPanel(data, "context", now);
    return JSON.stringify([next, congregation, highlightedPrayer(data, now),
      hijriDisplayDate(data.date, data, this._selectedDay, this._config.hijri_day_boundary, now),
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

  _loadMonth(year, month) {
    const day = new Date(Date.UTC(year, month - 1, 1));
    if (!Number.isFinite(day.valueOf()) || day.getUTCFullYear() < 1 || day.getUTCFullYear() > 9999) return;
    const entity = this._activeEntity();
    const token = ++this._monthRequest;
    const actualYear = day.getUTCFullYear(), actualMonth = day.getUTCMonth() + 1;
    this._monthView = true;
    this._monthState = {entity, year: actualYear, month: actualMonth, loading: true, rows: []};
    this._sourceState = null;
    this._render();
    if (typeof this._hass?.callWS !== "function") {
      this._monthState.loading = false;
      this._monthState.error = true;
      this._render();
      return;
    }
    this._hass.callWS({type: "salah_timetable/month", entity_id: entity, year: actualYear, month: actualMonth})
      .then(result => {
        if (token !== this._monthRequest || entity !== this._activeEntity()) return;
        this._monthState = {...this._monthState, loading: false, rows: result.rows || []};
        this._render();
      })
      .catch(() => {
        if (token !== this._monthRequest) return;
        this._monthState = {...this._monthState, loading: false, error: true};
        this._render();
      });
  }

  _exportYear() {
    const year = this._monthState?.year, entity = this._activeEntity();
    if (typeof this._hass?.callWS !== "function" || !year) return;
    this._hass.callWS({type: "salah_timetable/year_csv", entity_id: entity, year})
      .then(result => {
        if (entity !== this._activeEntity() || typeof result.csv !== "string") return;
        const blob = new Blob([result.csv], {type: "text/csv;charset=utf-8"});
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `salah-timetable-${year}.csv`;
        link.click();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      })
      .catch(() => { this._monthExportError = true; this._render(); });
  }

  _loadSources() {
    const entity = this._activeEntity();
    if (typeof this._hass?.callWS !== "function") return;
    this._sourceState = {loading: true};
    this._render();
    this._hass.callWS({type: "salah_timetable/sources", entity_id: entity})
      .then(result => {
        if (entity !== this._activeEntity() || !this._monthView) return;
        this._sourceState = {sources: Array.isArray(result.sources) ? result.sources : []};
        this._render();
      })
      .catch(() => { if (this._monthView) { this._sourceState = {error: true}; this._render(); } });
  }

  _cardActions(ui, displayDate) {
    if (!this._config.show_month_view) return null;
    const mode = this._config.detail_level;
    const actions = [];
    const action = (key, className, iconName, onClick) => {
      const label = tr(ui, key);
      const button = node("button", undefined, className);
      button.type = "button";
      button.title = label;
      button.setAttribute("aria-label", label);
      const icon = node("ha-icon");
      icon.setAttribute("icon", iconName);
      icon.setAttribute("aria-hidden", "true");
      button.append(icon);
      // Compact uses a disclosure menu, where action labels must remain visible.
      // Narrow-card icon-only styling applies only to the Standard/Detailed toolbar.
      button.append(node("span", label));
      button.addEventListener("click", event => {
        event.stopPropagation();
        onClick();
      });
      actions.push(button);
      return button;
    };
    const toggle = action(
      this._monthView ? "month.daily" : "month.title",
      "month-toggle",
      this._monthView ? "mdi:calendar-today" : "mdi:calendar-month",
      () => {
        if (this._monthView) {
          this._monthView = false;
          this._monthRequest++;
          this._render();
        } else {
          this._loadMonth(Number(displayDate.slice(0, 4)), Number(displayDate.slice(5, 7)));
        }
      },
    );
    toggle.setAttribute("aria-expanded", String(this._monthView));
    if (this._monthView) {
      action("month.csv_export", "month-action", "mdi:file-delimited-outline", () => this._exportYear());
      action("month.sources", "month-action", "mdi:information-outline", () => this._loadSources());
      action("month.refresh", "month-action", "mdi:refresh", () => this._loadMonth(this._monthState.year, this._monthState.month));
    }
    if (mode === "compact") {
      const menu = node("details", undefined, "card-actions-menu");
      const trigger = node("summary", undefined, "card-more-toggle");
      trigger.title = tr(ui, "card.more_actions");
      trigger.setAttribute("aria-label", trigger.title);
      trigger.addEventListener("click", event => event.stopPropagation());
      const icon = node("ha-icon");
      icon.setAttribute("icon", "mdi:dots-vertical");
      icon.setAttribute("aria-hidden", "true");
      trigger.append(icon, node("span", tr(ui, "card.more_actions")));
      const list = node("div", undefined, "card-menu-items");
      list.append(...actions);
      menu.append(trigger, list);
      return menu;
    }
    const toolbar = node("nav", undefined, "card-action-strip");
    toolbar.setAttribute("aria-label", tr(ui, "card.timetable_actions"));
    toolbar.append(...actions);
    return toolbar;
  }

  _monthlyPanel(ui) {
    const current = this._monthState;
    const panel = node("section", undefined, "monthly-shell");
    panel.setAttribute("aria-label", tr(ui, "month.title"));
    const toolbar = node("div", undefined, "month-toolbar");
    const prev = node("button", tr(ui, "month.previous"), "month-nav");
    prev.type = "button";
    prev.addEventListener("click", () => this._loadMonth(current.year, current.month - 1));
    const label = node("h3", new Intl.DateTimeFormat(ui.locale || "en-GB", {month: "long", year: "numeric", timeZone: "UTC"}).format(new Date(Date.UTC(current.year, current.month - 1, 15))));
    const next = node("button", tr(ui, "month.next"), "month-nav");
    next.type = "button";
    next.addEventListener("click", () => this._loadMonth(current.year, current.month + 1));
    toolbar.append(prev, label, next);
    panel.append(toolbar);
    if (current.loading) panel.append(node("p", tr(ui, "month.loading"), "note"));
    else if (current.error) panel.append(node("p", tr(ui, "month.error"), "note"));
    else {
      const scroll = node("div", undefined, "table-scroll");
      scroll.setAttribute("tabindex", "0");
      const table = node("table", undefined, "monthly-table");
      const caption = node("caption", tr(ui, "month.caption"), "sr-only");
      const head = node("thead"), headings = node("tr");
      for (const key of ["month.date", "prayer.fajr", "prayer.dhuhr", "prayer.asr", "prayer.maghrib", "prayer.isha", "prayer.jumuah"]) {
        const th = node("th", tr(ui, key)); th.scope = "col"; headings.append(th);
      }
      head.append(headings);
      const body = node("tbody");
      const prayers = ["fajr", "dhuhr", "asr", "maghrib", "isha", "jumuah"];
      for (const item of current.rows) {
        const row = node("tr");
        const dateCell = node("th", item.date.slice(-2));
        dateCell.scope = "row";
        row.append(dateCell);
        for (const prayer of prayers) {
          const cell = node("td");
          const fields = prayer === "jumuah" ? ["jumuah"] : [`${prayer}_begin`, `${prayer}_jamaat`];
          const values = fields.flatMap(field => Array.isArray(item.times?.[field]) ? item.times[field] : []);
          cell.textContent = values.length ? values.join(" · ") : "—";
          row.append(cell);
        }
        if (!item.published) row.className = "missing-date";
        body.append(row);
      }
      table.append(caption, head, body);
      scroll.append(table);
      panel.append(scroll);
    }
    if (this._monthExportError) panel.append(node("p", tr(ui, "month.export_error"), "note"));
    if (this._sourceState) {
      const list = node("div", undefined, "source-summary");
      if (this._sourceState.loading) list.append(node("p", tr(ui, "month.loading")));
      else if (this._sourceState.error) list.append(node("p", tr(ui, "month.error")));
      else {
        list.append(node("h4", tr(ui, "month.sources")));
        for (const source of this._sourceState.sources) {
          list.append(node("p", `${source.source_id}: ${source.first_date} – ${source.last_date} · ${source.rows} rows · ${source.format || "legacy"} · ${source.check_status}`));
        }
      }
      panel.append(list);
    }
    return panel;
  }

  _render(now = Date.now()) {
    if (!this.shadowRoot) return;
    this._syncDashboardEditing();
    const ui = resolveUi(this._config, this._hass);
    direction(this, ui);
    this._renderedHassKey = this._hassRenderKey();
    this._live = null;
    const updates = [];
    const style = node("style", CARD_CSS);
    const card = direction(node("ha-card"), ui);
    if (this._config.kiosk_mode) card.classList.add("kiosk");
    const state = this._state();
    const background = this._config.show_mosque_background && chooseMosqueBackground(MOSQUE_BACKGROUNDS, this._config.mosque_background, (state?.attributes?.date || new Date(now).toISOString().slice(0, 10)));
    if (background) {
      card.classList.add("has-mosque-background");
      // Home Assistant may add/remove a vertical scrollbar when the countdown
      // panels disappear, changing the card width by roughly 10-20px. Treat
      // that as the same canvas, not a tablet/desktop resize, and lock BOTH
      // dimensions of the painted photograph across adjacent-day tabs.
      const frame = this._backgroundFrame;
      const previousWidth = this.shadowRoot?.querySelector?.("ha-card")?.getBoundingClientRect?.().width;
      const sameCanvas = frame && frame.entity === this._activeEntity() &&
        previousWidth > 0 && Math.abs(previousWidth - frame.width) <= 24;
      if (sameCanvas) {
        card.style.setProperty("--mosque-photo-frame-height", `${Math.max(0, frame.height - 4)}px`);
        card.style.setProperty("--mosque-photo-frame-width", `${Math.max(0, frame.width - 2)}px`);
      }
      card.style.setProperty("--mosque-background-image", `url("${background.path}")`);
      card.style.setProperty("--mosque-background-position", background.position || "center");
    }
    if (!this._activeEntity() || !state || ["unavailable", "unknown"].includes(state.state) || !isTimetableState(state)) {
      const key = !this._activeEntity() ? "card.choose_entity" : !state ? "card.entity_missing" : "card.unavailable";
      card.append(node("div", tr(ui, key), "empty"));
      this.shadowRoot.replaceChildren(style, card);
      this._scheduleViewportHeight();
      return;
    }
    const previousRegion = this.shadowRoot.querySelector?.(".table-scroll");
    const regionFocused = Boolean(previousRegion && this.shadowRoot.activeElement === previousRegion);
    const scrollLeft = previousRegion?.scrollLeft || 0;
    const data = state.attributes;
    const zone = data.time_zone || this._hass?.config?.time_zone || "UTC";
    const content = node("div", undefined, `content ${this._config.detail_level === "compact" ? "compact" : "expanded"}${this._config.kiosk_mode ? " kiosk" : ""}`);
    const baseDate = Date.parse(`${data.date || state.state}T12:00:00Z`);
    const selectedDate = Number.isFinite(baseDate) ? new Date(baseDate + this._selectedDay * 86400000).toISOString().slice(0, 10) : "";
    const displayDate = selectedDate || data.date || state.state;
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
        this._monthView = false;
        this._monthState = null;
        this._sourceState = null;
        this._monthRequest++;
        // Replacing the Shadow DOM must not strand keyboard focus on a removed select.
        const wasFocused = this.shadowRoot.activeElement === chooser;
        this._render();
        if (wasFocused) this.shadowRoot.querySelector(".mosque-select")?.focus({preventScroll: true});
      });
      title.append(chooser);
    } else {
      title.textContent = this._config.title || data.mosque_name;
      title.setAttribute("dir", "auto");
    }
    if (this._config.kiosk_mode) {
      const identity = node("div", undefined, "kiosk-identity");
      identity.append(title);
      if (this._config.show_timezone_note) {
        identity.append(node("small", tr(ui, "card.kiosk_timezone", {zone}), "kiosk-timezone"));
      }
      header.append(identity);
    } else {
      header.append(title);
    }
    // Kiosk dates remain visible even in Compact and follow the same per-card
    // and per-mosque visibility settings as the regular header.
    const dateTarget = this._config.kiosk_mode ? node("div", undefined, "kiosk-dates") : header;
    const showHeaderDates = this._config.kiosk_mode || this._config.detail_level !== "compact";
    const hijriDate = hijriDisplayDate(displayDate, data, this._selectedDay, this._config.hijri_day_boundary, now);
    if (showHeaderDates && this._config.show_hijri_date && data.show_hijri_date !== false) dateTarget.append(node("div", `${formatHijriDate(hijriDate, this._config.hijri_adjustment, ui)} · ${tr(ui, "card.hijri_calculated")}`, "date hijri"));
    if (showHeaderDates && this._config.show_gregorian_date) dateTarget.append(node("div", formatDate(displayDate, ui), "date gregorian"));
    if (showHeaderDates && this._config.show_hijri_date && data.show_hijri_date !== false && this._config.show_hijri_month_info) {
      // The month description tracks the selected day's Hijri date, too.
      const month = hijriMonthInfo(hijriDate, this._config.hijri_adjustment);
      if (month) dateTarget.append(node("div", month.summary_en, "month-description"));
    }
    // One cohesive glass surface for mosque identity and both live summaries.
    // Individual countdown components remain independent for timing and options.
    const summary = node("div", undefined, "summary-shell");
    this._fullscreenButton = null;
    let kioskToolbar = null;
    let kioskClock = null;
    let kioskToggle = null;
    if (this._config.kiosk_mode) {
      // Reuse the existing countdown tick so wall displays need no extra timer.
      kioskToolbar = node("div", undefined, "kiosk-toolbar");
      kioskClock = node("div", undefined, "kiosk-clock");
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
      // The fullscreen control is an icon embedded in the main summary.
      // Its label and glyph follow the actual Fullscreen API state, including Esc.
      kioskToggle = node("button", undefined, "kiosk-fullscreen");
      kioskToggle.type = "button";
      kioskToggle._enterFullscreenLabel = tr(ui, "card.kiosk_fullscreen_enter");
      kioskToggle._exitFullscreenLabel = tr(ui, "card.kiosk_fullscreen_exit");
      const fullscreenIcon = node("ha-icon");
      fullscreenIcon.setAttribute("icon", "mdi:fullscreen");
      fullscreenIcon.setAttribute("aria-hidden", "true");
      kioskToggle.append(fullscreenIcon);
      this._fullscreenButton = kioskToggle;
      this._syncFullscreenButton();
      // Pointer activation must not leave a persistent ring on a wall display.
      // Keyboard activation retains :focus-visible for accessibility.
      kioskToggle.addEventListener("pointerup", () => kioskToggle.blur());
      kioskToggle.addEventListener("click", () => {
        const surface = this.shadowRoot?.querySelector?.("ha-card");
        if (this._isKioskFullscreen()) {
          const exit = document.exitFullscreen?.();
          exit?.catch?.(() => {});
        } else {
          const enter = surface?.requestFullscreen?.();
          enter?.catch?.(() => {});
        }
      });
    }
    summary.append(header);
    const cardActions = this._cardActions(ui, displayDate);
    if (cardActions) {
      header.classList.add("has-month-action");
      if (this._monthView && this._config.detail_level !== "compact") {
        header.classList.add("has-many-month-actions");
      }
      if (kioskToolbar) kioskToolbar.append(cardActions);
      else header.append(cardActions);
    }
    if (kioskToolbar) {
      header.append(kioskClock);
      if (dateTarget.children.length) header.append(dateTarget);
      // Absolutely positioned over the glass, outside header/footer flow.
      summary.append(kioskToggle);
      // Monthly actions still live in the footer toolbar, when enabled.
    }
    content.append(summary);
    if (this._monthView && this._config.show_month_view && this._monthState) {
      const monthlyPanel = this._monthlyPanel(ui);
      content.append(monthlyPanel);
      if (kioskToolbar) {
        const footer = node("footer", undefined, "kiosk-footer kiosk-month-footer");
        footer.append(node("span", undefined, "kiosk-footer-placeholder"),
          node("span", undefined, "kiosk-footer-placeholder"), kioskToolbar);
        content.append(footer);
      }
      card.append(content);
      this.shadowRoot.replaceChildren(style, card);
      this._syncFullscreenButton();
      this._live = {data, updates, selection: this._selection(data, now)};
      this._scheduleViewportHeight();
      return;
    }
    const dateTabs = node("nav", undefined, "date-tabs");
    dateTabs.setAttribute("aria-label", tr(ui, "card.day_navigation"));
    for (const [offset, key] of [[-1, "yesterday"], [0, "today"], [1, "tomorrow"]]) {
      const button = node("button", tr(ui, `card.${key}`), "date-tab");
      button.type = "button";
      button.setAttribute("aria-pressed", String(this._selectedDay === offset));
      button.addEventListener("click", () => {
        if (this._selectedDay === offset) return;
        if (this._selectedDay === 0) this._rememberBackgroundFrame();
        this._selectedDay = offset;
        const wasFocused = this.shadowRoot.activeElement === button;
        this._render();
        // Focus the same day in the new DOM, without scrolling the dashboard.
        if (wasFocused) this.shadowRoot.querySelectorAll(".date-tab")[offset + 1]?.focus({preventScroll: true});
      });
      dateTabs.append(button);
    }
    const selectedPrayers = this._selectedDay === 0 ? data.prayers : data.day_prayers?.[selectedDate];
    const tableShell = node("div", undefined, "timetable-shell");
    if (!this._config.kiosk_mode && this._selectedDay !== 0 && (this._config.detail_level === "compact" || !this._config.show_gregorian_date)) {
      tableShell.append(node("div", formatDate(displayDate, ui), "selected-date"));
    }
    if (this._hass?.connection?.connected === false) summary.append(node("p", tr(ui, "card.disconnected"), "disconnected"));
    const next = nextSalah(data, now);
    const congregation = jamaatPanel(data, "context", now);
    const panels = node("div", undefined, "panels");
    if (this._selectedDay === 0 && this._config.show_salah_countdown) {
      const box = prayerPanel("salah", next, data, zone, ui, this._config, countdown(next?.timestamp, now, ui));
      if (this._config.kiosk_mode) {
        const dayLabel = kioskSalahDayLabel(next, now, zone, ui);
        if (dayLabel) {
          const indicator = node("span", dayLabel, "kiosk-next-day");
          indicator.setAttribute("data-role", "next-salah-day");
          box.label.append(indicator);
        }
      }
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
    if (panels.children.length === 1) panels.classList.add("single-panel");
    if (panels.children.length) summary.append(panels);
    const highlighted = highlightedPrayer(data, now);
    let tableRegion;
    if (!this._config.kiosk_mode && Array.isArray(selectedPrayers) && (this._selectedDay !== 0 || this._config.detail_level !== "compact")) {
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
    if (this._config.kiosk_mode) {
      content.append(kioskPrayerStrip(selectedPrayers, next, congregation, data, zone, ui, this._config, this._selectedDay, now));
      dateTabs.classList.add("kiosk-day-tabs");
    } else {
      if (!selectedPrayers) tableShell.append(node("div", tr(ui, "card.day_unavailable"), "empty"));
      tableShell.append(dateTabs);
      if (tableShell.children.length) content.append(tableShell);
    }
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
    if (this._selectedDay === 0 && this._config.detail_level !== "compact" &&
        this._config.show_night_calculations && data.night_calculations) {
      const night = node("section", undefined, "night-calculations");
      night.append(node("h3", tr(ui, "night.title")));
      const grid = node("div", undefined, "night-grid");
      for (const [label, value] of [
        ["night.midpoint", data.night_calculations.midpoint],
        ["night.final_third", data.night_calculations.last_third],
      ]) {
        const cell = node("div", undefined, "night-cell");
        cell.append(node("div", tr(ui, label), "label"),
          formattedNode("div", formatTime(value, zone, ui, timeFormat), "event"));
        grid.append(cell);
      }
      night.append(grid, node("p", tr(ui, "night.note"), "note"));
      content.append(night);
    }
    let kioskFooterInfo = null;
    if (this._config.kiosk_mode) {
      const footer = node("footer", undefined, "kiosk-footer");
      kioskFooterInfo = node("div", undefined, "kiosk-footer-info");
      const note = this._config.show_timezone_note
        ? node("p", tr(ui, "card.kiosk_missing_times"), "kiosk-footer-note")
        : node("span", undefined, "kiosk-footer-placeholder");
      if (this._config.show_timezone_note) note.setAttribute("data-role", "timezone-note");
      kioskFooterInfo.append(note);
      footer.append(kioskFooterInfo, dateTabs, kioskToolbar);
      content.append(footer);
    } else if (this._selectedDay === 0 && this._config.show_timezone_note) {
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
      if (kioskFooterInfo) kioskFooterInfo.append(credit);
      else content.append(credit);
    }
    card.append(content); this.shadowRoot.replaceChildren(style, card);
    this._syncFullscreenButton();
    if (this._selectedDay === 0 && background) this._rememberBackgroundFrame();
    if (tableRegion) {
      tableRegion.scrollLeft = scrollLeft;
      if (regionFocused) tableRegion.focus({preventScroll: true});
    }
    this._live = {data, updates, selection: this._selection(data, now)};
    this._scheduleViewportHeight();
  }
}

const EDITOR_GROUPS = [
  {id: "dates", icon: "mdi:calendar-month", keys: ["show_hijri_date", "show_gregorian_date", "show_hijri_month_info"]},
  {id: "countdowns", icon: "mdi:timer-outline", keys: ["show_salah_countdown", "show_jamaat_countdown"]},
  {id: "ramadan", icon: "mdi:moon-waning-crescent", keys: ["show_ramadan_details", "show_sehri_countdown", "show_iftar_countdown", "show_night_calculations"]},
  {id: "appearance", icon: "mdi:image-outline", keys: ["mosque_background"]},
  {id: "tools", icon: "mdi:calendar-text-outline", keys: ["show_month_view", "show_timezone_note"]},
  {id: "history", icon: "mdi:book-open-variant", keys: ["show_historical_day_events", "show_historical_month_highlights", "show_historical_sources", "show_disputed_historical_dates"]},
  {id: "advanced", icon: "mdi:tune-variant", keys: ["language", "bilingual_prayer_labels", "kiosk_mode", "time_format", "hijri_adjustment", "hijri_day_boundary"]},
];
const EDITOR_FUTURE_OPTIONS = new Set(["show_historical_day_events", "show_historical_month_highlights", "show_historical_sources", "show_disputed_historical_dates"]);

export class SalahTimetableCardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({mode: "open"}); this._config = normalizeConfig({}); this._expandedSection = "dates"; }
  setConfig(config) {
    const next = normalizeForUi(config, this._hass);
    const changed = JSON.stringify(next) !== JSON.stringify(this._config);
    this._config = next;
    if (changed || !this._controls) this._render();
  }
  set hass(value) { this._hass = value; this._render(); }
  _reminderButton(ui) {
    const button = node("button", tr(ui, "card.prayer_reminders"), "reminder-setup");
    button.type = "button";
    button.addEventListener("click", async () => {
      if (!this._hass?.user?.is_admin || this._config.kiosk_mode) return;
      button.disabled = true;
      try {
        const wizard = openReminderWizard(this._hass);
        await wizard.ready;
      } catch {
        button.insertAdjacentText("afterend", tr(ui, "card.reminders_load_error"));
      } finally {
        button.disabled = false;
      }
    });
    return button;
  }

  _changed(patch) {
    this._config = normalizeForUi({...this._config, ...patch}, this._hass);
    this._updateControls();
    this.dispatchEvent(new CustomEvent("config-changed", {detail: {config: {...this._config}}, bubbles: true, composed: true}));
  }
  _updateSections(ui = resolveUi(this._config, this._hass)) {
    for (const [id, section] of Object.entries(this._sections || {})) {
      section.title.textContent = tr(ui, `editor.section.${id}`);
      section.description.textContent = tr(ui, `editor.section.${id}.hint`);
      const expanded = this._expandedSection === id;
      section.toggle.setAttribute("aria-expanded", String(expanded));
      section.body.hidden = !expanded;
      const soon = Array.from(section.body.children).find(item => item.className === "editor-soon-note");
      if (soon) soon.textContent = tr(ui, "editor.history_unavailable");
    }
  }
  _updateControls() {
    if (!this._controls) return;
    const ui = resolveUi(this._config, this._hass);
    direction(this, ui); direction(this._form, ui);
    for (const [key, {control, checkbox, label, hint, field, options}] of Object.entries(this._extraControls || {})) {
      const title = tr(ui, `editor.${key}`);
      label.textContent = title;
      hint.textContent = tr(ui, `editor.hint.${key}`);
      control.setAttribute("aria-label", title);
      for (const {option, value} of options || []) {
        option.textContent = key === "hijri_adjustment"
          ? localizedNumber(value, ui, {signDisplay: "exceptZero"})
          : key === "mosque_background"
            ? (MOSQUE_BACKGROUNDS.find(item => item.id === value)?.name || tr(ui, `editor.background.${value}`))
            : tr(ui, `editor.${key}.${value}`);
      }
      const selected = key === "mosque_background" && !this._config.show_mosque_background ? "none" : this._config[key];
      if (checkbox) control.checked = this._config[key];
      else if (control.value !== String(selected)) control.value = String(selected);
      const disabled = EDITOR_FUTURE_OPTIONS.has(key)
        || (key === "show_hijri_month_info" && !this._config.show_hijri_date)
        || ((key === "show_sehri_countdown" || key === "show_iftar_countdown") && !this._config.show_ramadan_details)
        || (key === "show_night_calculations" && this._config.detail_level === "compact");
      control.disabled = disabled;
      field.setAttribute("data-disabled", String(disabled));
    }
    if (this._reminderAction) {
      this._reminderAction.hidden = !this._hass?.user?.is_admin || this._config.kiosk_mode;
      this._reminderAction.textContent = tr(ui, "card.prayer_reminders");
    }
    this._updateSections(ui);
    const {help, mosqueGroup, mosqueHeading, mosqueHint, mosqueList} = this._controls;
    const mosques = discoverTimetableEntities(this._hass);
    // Keep temporarily missing sensors in the list without exposing a second
    // selector. The checkbox list is the sole mosque-selection control.
    const listed = mosques.map(({entity, name}) => ({entity, name}));
    if (this._config.entity && !listed.some(item => item.entity === this._config.entity)) {
      listed.push({entity: this._config.entity, name: this._config.entity});
    }
    mosqueHeading.textContent = tr(ui, "editor.mosques");
    mosqueHint.textContent = tr(ui, "editor.mosque_reorder_hint");
    // Existing cards continue with all mosques. Their original primary remains
    // first when an ordered list is first saved; missing sensors remain listed.
    const selected = this._config.mosque_entities
      ? [...this._config.mosque_entities]
      : [...new Set([this._config.entity, ...listed.map(item => item.entity)].filter(Boolean))];
    for (const value of selected) {
      if (!listed.some(item => item.entity === value)) listed.push({entity: value, name: value});
    }
    const ordered = [
      ...selected.map(value => listed.find(item => item.entity === value)).filter(Boolean),
      ...listed.filter(item => !selected.includes(item.entity)),
    ];
    mosqueGroup.hidden = ordered.length < 2;
    mosqueList.replaceChildren();
    const enabled = new Set(selected);
    const reorder = (source, destination) => {
      const from = selected.indexOf(source), to = selected.indexOf(destination);
      if (from < 0 || to < 0 || from === to) return;
      const entities = [...selected];
      entities.splice(to, 0, entities.splice(from, 1)[0]);
      this._changed({mosque_entities: entities, entity: entities[0]});
    };
    for (const mosque of ordered) {
      const index = selected.indexOf(mosque.entity);
      const row = node("div", undefined, "mosque-choice");
      row.setAttribute("data-mosque-row", mosque.entity);
      row.setAttribute("data-selected", String(index >= 0));
      // Only the six-dot handle can initiate a drag; clicking the checkbox,
      // name or arrow controls must never unexpectedly drag the whole row.
      const grip = node("button", undefined, "mosque-grip");
      grip.type = "button";
      grip.draggable = index >= 0 && selected.length > 1;
      grip.disabled = !grip.draggable;
      grip.title = tr(ui, "editor.mosque_drag", {name: mosque.name});
      grip.setAttribute("aria-label", grip.title);
      const gripIcon = node("ha-icon");
      gripIcon.setAttribute("icon", "mdi:drag-vertical");
      gripIcon.setAttribute("aria-hidden", "true");
      grip.append(gripIcon);
      grip.addEventListener("dragstart", event => {
        if (!grip.draggable) { event.preventDefault(); return; }
        event.dataTransfer?.setData("text/plain", mosque.entity);
        if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
      });
      const choice = node("label", undefined, "mosque-choice-label");
      const checkbox = node("input"); checkbox.type = "checkbox";
      checkbox.checked = enabled.has(mosque.entity);
      checkbox.disabled = checkbox.checked && enabled.size === 1;
      checkbox.setAttribute("data-mosque-entity", mosque.entity);
      choice.append(checkbox, node("span", mosque.name));
      if (index === 0) choice.append(node("small", tr(ui, "editor.mosque_first"), "mosque-first"));
      checkbox.addEventListener("change", () => {
        const entities = [...selected];
        if (checkbox.checked) entities.push(mosque.entity);
        else entities.splice(entities.indexOf(mosque.entity), 1);
        if (!entities.length) { this._updateControls(); return; }
        this._changed({mosque_entities: entities, entity: entities[0]});
      });
      const move = (delta, label, iconName) => {
        const button = node("button", undefined, delta < 0 ? "mosque-move-up" : "mosque-move-down");
        button.type = "button";
        button.disabled = index < 0 || index + delta < 0 || index + delta >= selected.length;
        button.setAttribute("aria-label", tr(ui, label, {name: mosque.name}));
        button.title = tr(ui, label, {name: mosque.name});
        const icon = node("ha-icon"); icon.setAttribute("icon", iconName);
        icon.setAttribute("aria-hidden", "true");
        button.append(icon);
        button.addEventListener("click", () => {
          const wasFocused = this.shadowRoot.activeElement === button;
          reorder(mosque.entity, selected[index + delta]);
          if (wasFocused) {
            const movedRow = [...this._controls.mosqueList.children]
              .find(item => item.getAttribute?.("data-mosque-row") === mosque.entity);
            movedRow?.querySelector?.(delta < 0 ? ".mosque-move-up" : ".mosque-move-down")
              ?.focus?.({preventScroll: true});
          }
        });
        return button;
      };
      row.append(grip, choice,
        move(-1, "editor.mosque_move_up", "mdi:chevron-up"),
        move(1, "editor.mosque_move_down", "mdi:chevron-down"));
      row.addEventListener("dragover", event => {
        if (index < 0) return;
        event.preventDefault();
        if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
      });
      row.addEventListener("drop", event => {
        event.preventDefault();
        const source = event.dataTransfer?.getData("text/plain");
        if (source) reorder(source, mosque.entity);
      });
      mosqueList.append(row);
    }
    help.textContent = tr(ui, "editor.help");
  }
  _render() {
    if (!this.shadowRoot) return;
    if (this._controls) { this._updateControls(); return; }
    const style = node("style", EDITOR_CSS);
    const form = node("div", undefined, "form"); this._form = form;
    const mosqueGroup = node("div", undefined, "mosque-options");
    const mosqueHeading = node("div", undefined, "mosque-options-heading");
    const mosqueHint = node("div", undefined, "mosque-options-hint");
    const mosqueList = node("div", undefined, "mosque-options-list");
    mosqueGroup.append(mosqueHeading, mosqueHint, mosqueList);
    const help = node("div", undefined, "help");
    this._controls = {help, mosqueGroup, mosqueHeading, mosqueHint, mosqueList};
    this._extraControls = {};
    const settings = [
      ["detail_level", ["compact", "standard", "detailed"]],
      ["show_hijri_date"], ["show_gregorian_date"], ["show_hijri_month_info"],
      ["show_salah_countdown"], ["show_jamaat_countdown"],
      ["show_ramadan_details"], ["show_sehri_countdown"], ["show_iftar_countdown"], ["show_night_calculations"],
      ["mosque_background", ["none", "daily", ...MOSQUE_BACKGROUNDS.map(item => item.id)]],
      ["show_month_view"], ["show_timezone_note"],
      ["show_historical_day_events"], ["show_historical_month_highlights"], ["show_historical_sources"], ["show_disputed_historical_dates"],
      ["language", ["auto", "en", "ar"]], ["bilingual_prayer_labels"], ["kiosk_mode"], ["time_format", ["24h", "12h"]],
      ["hijri_adjustment", [-3, -2, -1, 0, 1, 2, 3]], ["hijri_day_boundary", ["midnight", "maghrib"]]
    ];
    const fields = new Map();
    for (const [key, choices] of settings) {
      const field = node(choices ? "label" : "div", undefined, "setting");
      const copy = node("span", undefined, "setting-copy");
      const label = node("span", undefined, "setting-label");
      const hint = node("span", undefined, "setting-hint");
      copy.append(label, hint); field.append(copy);
      const control = node(choices ? "select" : "ha-switch"); const options = [];
      if (choices) for (const value of choices) {
        const option = node("option"); option.value = String(value); control.append(option); options.push({option, value});
      }
      control.setAttribute("data-option", key);
      control.addEventListener("change", () => {
        if (control.disabled) return;
        if (key === "mosque_background") {
          // Keep the previous image choice when the background is turned off.
          this._changed(control.value === "none" ? {show_mosque_background: false}
            : {show_mosque_background: true, mosque_background: control.value});
          return;
        }
        this._changed({[key]: choices ? key === "hijri_adjustment" ? Number(control.value) : control.value : control.checked});
      });
      this._extraControls[key] = {control, checkbox: !choices, label, hint, field, options};
      field.append(control); fields.set(key, field);
    }
    this._sections = {};
    const groups = [];
    for (const {id, icon, keys} of EDITOR_GROUPS) {
      const section = node("section", undefined, "editor-section");
      const toggle = node("button", undefined, "editor-section-toggle"); toggle.type = "button";
      const graphic = node("ha-icon"); graphic.setAttribute("icon", icon);
      const text = node("span", undefined, "editor-section-copy");
      const heading = node("span", undefined, "editor-section-title");
      const description = node("span", undefined, "editor-section-hint");
      const chevron = node("ha-icon"); chevron.setAttribute("icon", "mdi:chevron-down");
      text.append(heading, description); toggle.append(graphic, text, chevron);
      const body = node("div", undefined, "editor-section-content");
      body.id = `editor-section-${id}`; toggle.setAttribute("aria-controls", body.id);
      for (const key of keys) body.append(fields.get(key));
      if (id === "history") body.append(node("p", undefined, "editor-soon-note"));
      toggle.addEventListener("click", () => {
        this._expandedSection = this._expandedSection === id ? null : id;
        this._updateSections();
      });
      section.append(toggle, body);
      this._sections[id] = {toggle, body, title: heading, description};
      groups.push(section);
    }
    // Keep reminder setup beside the detail selector, outside the dashboard card.
    this._reminderAction = this._reminderButton(resolveUi(this._config, this._hass));
    // One ordered checkbox list replaces the old duplicate radio selector.
    form.append(mosqueGroup, fields.get("detail_level"));
    if (this._reminderAction) form.append(this._reminderAction);
    form.append(...groups, help);
    this._updateControls();
    this.shadowRoot.replaceChildren(style, form);
  }
}

// HA 2026.8+ may install the scoped-custom-element-registry polyfill after
// our resource module evaluated. Elements defined in the earlier native
// registry then appear missing to the active registry, causing a permanent
// "Configuration error", especially on cold loads and Cast displays.
// Re-register the SAME constructors with the current registry after HA starts;
// never load a second copy of this module or forcibly reload the dashboard.
function registerSalahCardElements() {
  for (const [tag, constructor] of [
    ["salah-timetable-card", SalahTimetableCard],
    ["salah-timetable-card-editor", SalahTimetableCardEditor],
  ]) {
    if (customElements.get(tag)) continue;
    try {
      customElements.define(tag, constructor);
    } catch (error) {
      // If another source completed registration concurrently, that's fine.
      // A genuine failure must remain visible in logs for troubleshooting.
      if (!customElements.get(tag)) {
        console.warn("Salah Timetable: could not register", tag, error);
      }
    }
  }
}

registerSalahCardElements();

if (typeof customElements.whenDefined === "function") {
  // The Home Assistant shell is the earliest stable frontend signal. This
  // promise may be tied to the old registry, so bounded timers also check
  // when HA swaps/patches the registry later.
  customElements.whenDefined("home-assistant")
    .then(() => registerSalahCardElements())
    .catch(() => {});
}
for (const delay of [100, 1500, 4000]) {
  const timer = setTimeout(registerSalahCardElements, delay);
  timer?.unref?.(); // Do not hold Node's frontend unit-test process open.
}

window.customCards = window.customCards || [];
const registrationUi = resolveUi({}, {language: globalThis.navigator?.language});
if (!window.customCards.some(card => card.type === "salah-timetable-card")) window.customCards.push({type: "salah-timetable-card", name: tr(registrationUi, "card.name"), description: tr(registrationUi, "card.description"), preview: true});

