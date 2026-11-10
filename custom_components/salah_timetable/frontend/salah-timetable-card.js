import {hijriDisplayDate, highlightedPrayer, prayerIsPast, discoverEntity, discoverTimetableEntities, jamaatPanel, nextRamadanEvent, nextSalah, normalizeConfig, timestamp} from "./card-utils.js?v=3.6.1";
// Keep the direct versioned style import for release asset/cache validation.
// The rendering mixin reads the same cached module for its CSS content.
import {CARD_CSS} from "./card-styles.js?v=3.6.1";
import {resolveUi, tr} from "./card-i18n.js?v=3.6.1";
import {SECTION_IDS, sectionVisible, widgetSection, widgetType} from "./widget-utils.js?v=3.6.1";
import {joinSelectionGroup} from "./widget-selection.js?v=3.6.1";
import {buildJamaatChanges, buildTimetableHealth} from "./widget-renderers.js?v=3.6.1";
import {widgetTr} from "./widget-i18n.js?v=3.6.1";
import {SalahTimetableCardEditor} from "./card-editor.js?v=3.6.1";
import {node, normalizeForUi} from "./card-shared.js?v=3.6.1";
import {backgroundCredit} from "./card-view-helpers.js?v=3.6.1";
import {CardMonthlyMixin} from "./card-monthly.js?v=3.6.1";
import {CardRenderingMixin} from "./card-rendering.js?v=3.6.1";

export {SalahTimetableCardEditor};

// Keep HA bookkeeping and unrelated entity updates out of the render decision.
const RENDER_ATTRIBUTES = [
  "mosque_name", "date", "time_zone", "prayers", "day_prayers", "beginning_events", "jamaat_events",
  "next_salah", "next_jamaat", "previous_jamaat", "context_jamaat", "context_mode",
  "ramadan", "sehri_events", "iftar_events", "next_sehri", "next_iftar",
  "show_hijri_date", "second_khutbah", "night_calculations", "timetable_health", "config_entry_id",
];
export class SalahTimetableCard extends CardRenderingMixin(CardMonthlyMixin(HTMLElement)) {
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
    this._connected = false;
    this._group = null;
    this._groupName = null;
    this._groupEntity = null;
  }

  static getConfigElement() { return document.createElement("salah-timetable-card-editor"); }
  static getStubConfig(hass) { return normalizeConfig({entity: discoverEntity(hass)}); }
  setConfig(config) {
    const next = normalizeForUi(config, this._hass);
    // Reordered mosque lists establish a new first (default) mosque.
    if (this._config?.entity !== next.entity) this._selectedMosque = null;
    this._config = next;
    if (next.arrangement && !sectionVisible(next, "timetable")) this._resetBrowsing();
    this._syncSelectionGroup();
    this._render();
  }
  set hass(value) {
    this._hass = value;
    this._syncSelectionGroup();
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
    this._syncSelectionGroup();
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
  getCardSize() { if (widgetSection(this._config)) return widgetSection(this._config) === "mosque_selector" ? 1 : 3; return (this._config.kiosk_mode ? 7 : this._config.detail_level === "compact" ? 3 : 5) + (this._state()?.attributes?.ramadan?.active && this._config.show_ramadan_details ? 2 : 0); }
  getGridOptions() {
    const standalone = Boolean(widgetSection(this._config));
    const naturalHeight = standalone || Boolean(this._config.arrangement);
    return {columns: 12, rows: naturalHeight ? "auto" : this.getCardSize(), min_columns: standalone ? 3 : 6, min_rows: naturalHeight ? 1 : 4};
  }

  connectedCallback() {
    this._connected = true;
    this._syncSelectionGroup();
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
    this._connected = false;
    this._leaveSelectionGroup();
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
    if (widgetSection(this._config) || typeof this.getBoundingClientRect !== "function") return;
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
    if (this._groupEntity !== null) return this._groupEntity;
    const mosques = this._mosques();
    if (this._selectedMosque && mosques.some(item => item.entity === this._selectedMosque)) return this._selectedMosque;
    // An explicitly ordered selection defines the default, even for older YAML
    // whose legacy entity property still names a different mosque.
    if (this._config.mosque_entities?.length) return mosques[0]?.entity || this._config.mosque_entities[0];
    if (this._config.entity) return this._config.entity;
    return mosques[0]?.entity || "";
  }
  _leaveSelectionGroup() {
    this._group?.leave();
    this._group = null;
    this._groupName = null;
    this._groupEntity = null;
  }
  _syncSelectionGroup() {
    const name = this._config.selection_group || "";
    const eligible = this._connected && !this.preview && !this.hasAttribute("dashboard-editing") && Boolean(name);
    if (!eligible) { this._leaveSelectionGroup(); return; }
    if (this._groupName === name || this._joiningGroup) return;
    this._leaveSelectionGroup();
    const initial = this._activeEntity();
    if (!initial) return;
    this._groupName = name;
    this._joiningGroup = true;
    try {
      this._group = joinSelectionGroup(this, name, initial, entity => {
        if (entity === this._groupEntity) return;
        this._groupEntity = entity;
        this._selectedMosque = entity;
        this._resetBrowsing();
        if (!this._joiningGroup) this._render();
      });
      this._groupEntity = this._group.entity;
    } finally { this._joiningGroup = false; }
  }
  _resetBrowsing() {
    this._selectedDay = 0;
    this._monthView = false;
    this._monthState = null;
    this._sourceState = null;
    this._monthRequest++;
  }
  _selectMosque(entity) {
    this._selectedMosque = entity;
    this._resetBrowsing();
    if (this._group) this._group.publish(entity);
  }
  _mosqueIdentity(ui, data) {
    const mosques = this._mosques();
    const title = node("h2");
    // Linked standalone status cards follow a shared controller; do not repeat it.
    // The main card and dedicated mosque-selector card keep their dropdowns.
    const follower = Boolean(this._config.selection_group) &&
      Boolean(widgetSection(this._config)) && widgetSection(this._config) !== "mosque_selector";
    if (mosques.length > 1 && !follower) {
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
        const wasFocused = this.shadowRoot.activeElement === chooser;
        this._selectMosque(chooser.value);
        // Replacing the Shadow DOM must not strand keyboard focus on a removed select.
        this._render();
        if (wasFocused) this.shadowRoot.querySelector(".mosque-select")?.focus({preventScroll: true});
      });
      title.append(chooser);
    } else {
      const active = this._activeEntity();
      const name = mosques.find(mosque => mosque.entity === active)?.name || data.mosque_name || active;
      title.textContent = active === this._config.entity && this._config.title ? this._config.title : name;
      title.setAttribute("dir", "auto");
      if (follower) {
        title.classList.add("linked-mosque-name");
        title.title = widgetTr(ui, "group.following");
      }
    }
    return title;
  }
  _standaloneContent(card, data, ui, background) {
    const section = widgetSection(this._config);
    const content = node("div", undefined, "content standalone-content");
    content.append(this._mosqueIdentity(ui, data));
    if (section === "jamaat_changes") content.append(buildJamaatChanges(data, ui, this._config, this._hass?.connection?.connected !== false));
    if (section === "timetable_health") content.append(buildTimetableHealth(data, ui, this._config, this._hass));
    if (this._hass?.connection?.connected === false) content.append(node("p", tr(ui, "card.disconnected"), "disconnected"));
    if (background) content.append(backgroundCredit(background));
    card.append(content);
    return content;
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


}

// HA 2026.8+ may install the scoped-custom-element-registry polyfill after
// our resource module evaluated. Elements defined in the earlier native
// registry then appear missing to the active registry, causing a permanent
// "Configuration error", especially on cold loads and Cast displays.
// Re-register the SAME constructors with the current registry after HA starts;
// never load a second copy of this module or forcibly reload the dashboard.
const STANDALONE_SECTIONS = SECTION_IDS;
const WIDGET_CONSTRUCTORS = STANDALONE_SECTIONS.map(section => {
  const type = widgetType(section);
  class SalahWidgetCard extends SalahTimetableCard {
    static getStubConfig(hass) { return normalizeConfig({type, entity: discoverEntity(hass)}); }
    setConfig(config) { super.setConfig({...config, type}); }
  }
  return [type.slice("custom:".length), SalahWidgetCard];
});
function registerSalahCardElements() {
  for (const [tag, constructor] of [
    ["salah-timetable-card", SalahTimetableCard],
    ["salah-timetable-card-editor", SalahTimetableCardEditor],
    ...WIDGET_CONSTRUCTORS,
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


for (const section of STANDALONE_SECTIONS) {
  const type = widgetType(section).slice("custom:".length);
  if (!window.customCards.some(card => card.type === type)) window.customCards.push({type, name: widgetTr(registrationUi, `section.${section}`), description: widgetTr(registrationUi, `widget.${section}.description`), preview: true});
}
