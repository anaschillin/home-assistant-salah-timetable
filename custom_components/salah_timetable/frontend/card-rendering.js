/** Main card rendering and custom arrangement layout, independent of card lifecycle.
 * This mixin uses the host's existing state, selection, and monthly action methods.
 */
import {MOSQUE_BACKGROUNDS, chooseMosqueBackground} from "./mosque-backgrounds.js?v=3.6.0";
import {CARD_CSS} from "./card-styles.js?v=3.6.0";
import {displayPrayerKey, hijriMonthInfo, formatHijriDate, hijriDisplayDate, highlightedPrayer, prayerIsPast, countdown, elapsed, formatDate, formatTime, isTimetableState, jamaatPanel, nextRamadanEvent, nextSalah, timestamp} from "./card-utils.js?v=3.6.0";
import {resolveUi, tr} from "./card-i18n.js?v=3.6.0";
import {sectionVisible, widgetSection} from "./widget-utils.js?v=3.6.0";
import {buildJamaatChanges, buildTimetableHealth} from "./widget-renderers.js?v=3.6.0";
import {widgetTr} from "./widget-i18n.js?v=3.6.0";
import {node, direction} from "./card-shared.js?v=3.6.0";
import {backgroundCredit, isolated, formattedNode, translatedRun, prayerNode, clockNode, kioskSalahDayLabel, prayerPanel, kioskPrayerStrip, mosqueClock} from "./card-view-helpers.js?v=3.6.0";

export const CardRenderingMixin = Base => class extends Base {
  _arrangeContent(content, sections, ui, data, fixed = [], fullscreen = null) {
    const standalone = widgetSection(this._config);
    content.classList.add("custom-arrangement");
    const grid = node("div", undefined, "arrangement-grid");
    const ordered = standalone ? [{id: standalone, width: "full"}] : this._config.arrangement.sections;
    const chrome = [];
    if (standalone !== "mosque_selector" && (standalone || !sectionVisible(this._config, "mosque_selector"))) {
      if (standalone && !this._config.selection_group) {
        // Independent standalone sections keep their own mosque chooser.
        const chooser = this._mosqueIdentity(ui, data);
        chooser.classList.add("widget-mosque-control");
        chrome.push(chooser);
      } else {
        // Linked cards follow the dedicated selector or linked main card.
        const active = this._activeEntity();
        const name = active === this._config.entity && this._config.title
          ? this._config.title : data.mosque_name || active;
        chrome.push(node("div", name, "widget-mosque-name"));
      }
    }
    for (const {id, width} of ordered) {
      if (!sectionVisible(this._config, id)) continue;
      let section = sections[id];
      if (!section && standalone) {
        section = node("section", undefined, "widget-panel");
        section.append(node("h3", widgetTr(ui, `section.${id}`), "widget-heading"));
        const key = id === "ramadan" ? "widget.inactive_ramadan" : id === "night_calculations" ? "widget.unavailable_night" : id === "dates" ? "widget.dates_hidden" : "widget.unavailable";
        section.append(node("p", widgetTr(ui, key), "widget-status"));
      }
      if (!section) continue;
      const wrapper = node("section", undefined, "arrangement-section");
      wrapper.setAttribute("data-section", id);
      wrapper.setAttribute("data-width", width);
      wrapper.setAttribute("aria-label", widgetTr(ui, `section.${id}`));
      if (id === "salah" || id === "jamaat") {
        const shell = node("div", undefined, "summary-shell");
        const panels = node("div", undefined, "panels single-panel");
        panels.append(section); shell.append(panels); wrapper.append(shell);
      } else if (id === "mosque_selector" || id === "clock") {
        const shell = node("div", undefined, "widget-panel"); shell.append(section); wrapper.append(shell);
      } else wrapper.append(section);
      grid.append(wrapper);
    }
    if (this._hass?.connection?.connected === false) chrome.push(node("p", tr(ui, "card.disconnected"), "disconnected"));
    if (fullscreen) {
      const toolbar = node("div", undefined, "arrangement-toolbar");
      toolbar.append(fullscreen); chrome.push(toolbar);
    }
    content.replaceChildren(...chrome, grid, ...fixed);
  }
  _render(now = Date.now()) {
    if (!this.shadowRoot) return;
    this._syncDashboardEditing();
    // A standalone widget must not inherit the card picker's available height.
    if (widgetSection(this._config)) this.setAttribute("data-standalone", "");
    else this.removeAttribute("data-standalone");
    const ui = resolveUi(this._config, this._hass);
    direction(this, ui);
    this._renderedHassKey = this._hassRenderKey();
    this._live = null;
    const updates = [];
    const style = node("style", CARD_CSS);
    const card = direction(node("ha-card"), ui);
    if (this._config.kiosk_mode) card.classList.add("kiosk");
    if (widgetSection(this._config)) card.classList.add("standalone-widget");
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
    if (this._groupEntity !== null && this._config.mosque_entities && !this._config.mosque_entities.includes(this._groupEntity)) {
      card.append(node("p", widgetTr(ui, "group.not_enabled"), "empty group-selection-error"));
      this.shadowRoot.replaceChildren(style, card);
      return;
    }
    if (!this._activeEntity() || !state || ["unavailable", "unknown"].includes(state.state) || !isTimetableState(state)) {
      const key = !this._activeEntity() ? "card.choose_entity" : !state ? "card.entity_missing" : "card.unavailable";
      card.append(node("div", tr(ui, key), "empty"));
      this.shadowRoot.replaceChildren(style, card);
      this._scheduleViewportHeight();
      return;
    }
    if (["mosque_selector", "jamaat_changes", "timetable_health"].includes(widgetSection(this._config))) {
      this._standaloneContent(card, state.attributes, ui, background);
      this.shadowRoot.replaceChildren(style, card);
      return;
    }
    const previousRegion = this.shadowRoot.querySelector?.(".table-scroll");
    const regionFocused = Boolean(previousRegion && this.shadowRoot.activeElement === previousRegion);
    const scrollLeft = previousRegion?.scrollLeft || 0;
    const data = state.attributes;
    const modern = Boolean(this._config.arrangement || widgetSection(this._config));
    const showSalah = modern ? sectionVisible(this._config, "salah") : this._config.show_salah_countdown;
    const showJamaat = modern ? sectionVisible(this._config, "jamaat") : this._config.show_jamaat_countdown;
    const singleCountdown = showSalah !== showJamaat;
    // Arranged sections have their own tiles even when both sections are enabled.
    const timelineNow = singleCountdown || modern ? now : undefined;
    const sections = {};
    const fixed = [];
    const zone = data.time_zone || this._hass?.config?.time_zone || "UTC";
    const content = node("div", undefined, `content ${this._config.detail_level === "compact" ? "compact" : "expanded"}${this._config.kiosk_mode ? " kiosk" : ""}`);
    if (singleCountdown) content.classList.add("single-countdown");
    const baseDate = Date.parse(`${data.date || state.state}T12:00:00Z`);
    const selectedDate = Number.isFinite(baseDate) ? new Date(baseDate + this._selectedDay * 86400000).toISOString().slice(0, 10) : "";
    const displayDate = selectedDate || data.date || state.state;
    const timeFormat = this._config.time_format;
    const header = node("header", undefined, "header");
    const mosques = this._mosques();
    const title = this._mosqueIdentity(ui, data);
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
    const dateTarget = modern ? node("section", undefined, "widget-panel widget-dates") : this._config.kiosk_mode ? node("div", undefined, "kiosk-dates") : header;
    const showHeaderDates = modern ? sectionVisible(this._config, "dates") : this._config.kiosk_mode || this._config.detail_level !== "compact";
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
      kioskClock = mosqueClock(zone, ui, timeFormat, now, updates);
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
    if (modern) {
      sections.mosque_selector = header;
      if (dateTarget.children.length) sections.dates = dateTarget;
      if (!kioskClock && sectionVisible(this._config, "clock")) kioskClock = mosqueClock(zone, ui, timeFormat, now, updates);
      sections.clock = kioskClock;
    }
    summary.append(header);
    const cardActions = this._cardActions(ui, displayDate);
    if (cardActions && !modern) {
      header.classList.add("has-month-action");
      if (this._monthView && this._config.detail_level !== "compact") {
        header.classList.add("has-many-month-actions");
      }
      if (kioskToolbar) kioskToolbar.append(cardActions);
      else header.append(cardActions);
    }
    if (kioskToolbar) {
      if (!modern) {
        header.append(kioskClock);
        if (dateTarget.children.length) header.append(dateTarget);
      }
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
      if (modern) {
        sections.timetable = monthlyPanel;
        if (cardActions) monthlyPanel.append(cardActions);
        this._arrangeContent(content, sections, ui, data, background ? [backgroundCredit(background)] : [], kioskToggle);
      } else if (background) content.append(backgroundCredit(background));
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
    if (!this._config.kiosk_mode && this._selectedDay !== 0 && (this._config.detail_level === "compact" || !this._config.show_gregorian_date || (modern && !sectionVisible(this._config, "dates")))) {
      tableShell.append(node("div", formatDate(displayDate, ui), "selected-date"));
    }
    if (this._hass?.connection?.connected === false) summary.append(node("p", tr(ui, "card.disconnected"), "disconnected"));
    const next = nextSalah(data, now);
    const congregation = jamaatPanel(data, "context", now);
    const panels = node("div", undefined, "panels");
    if (this._selectedDay === 0 && showSalah) {
      const box = prayerPanel("salah", next, data, zone, ui, this._config, countdown(next?.timestamp, now, ui), {timelineNow});
      if (this._config.kiosk_mode) {
        const dayLabel = kioskSalahDayLabel(next, now, zone, ui);
        if (dayLabel) {
          const indicator = node("span", dayLabel, "kiosk-next-day");
          indicator.setAttribute("data-role", "next-salah-day");
          box.label.append(indicator);
        }
      }
      updates.push(instant => { box.clock.run.textContent = countdown(next?.timestamp, instant, ui); });
      if (box.updateTimeline) updates.push(box.updateTimeline);
      sections.salah = box;
      panels.append(box);
    }
    if (this._selectedDay === 0 && showJamaat) {
      const congregationClock = instant => congregation.mode === "upcoming"
        ? countdown(congregation.event?.timestamp, instant, ui)
        : elapsed(congregation.event?.timestamp, instant, ui);
      const box = prayerPanel("jamaat", congregation.event, data, zone, ui, this._config, congregationClock(now), {mode: congregation.mode, timelineNow});
      updates.push(instant => { box.clock.run.textContent = congregationClock(instant); });
      if (box.updateTimeline) updates.push(box.updateTimeline);
      sections.jamaat = box;
      panels.append(box);
    }
    if (panels.children.length === 1) panels.className = "panels single-panel";
    if (panels.children.length) summary.append(panels);
    const highlighted = highlightedPrayer(data, now);
    let tableRegion;
    if (!this._config.kiosk_mode && Array.isArray(selectedPrayers) && (modern ? sectionVisible(this._config, "timetable") : this._selectedDay !== 0 || this._config.detail_level !== "compact")) {
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
      name.append(prayerNode(displayPrayerKey(data, prayer.key, selectedDate),
        ui, this._config.bilingual_prayer_labels, prayer.name));
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
      const strip = kioskPrayerStrip(selectedPrayers, next, congregation, data, zone, ui, this._config, this._selectedDay, selectedDate, now);
      if (modern) tableShell.append(strip, dateTabs);
      else content.append(strip);
      dateTabs.classList.add("kiosk-day-tabs");
    } else {
      if (!selectedPrayers) tableShell.append(node("div", tr(ui, "card.day_unavailable"), "empty"));
      tableShell.append(dateTabs);
      if (tableShell.children.length) content.append(tableShell);
    }
    if (modern) {
      if (cardActions) tableShell.append(cardActions);
      sections.timetable = tableShell;
    }
    if (this._selectedDay === 0 && this._config.detail_level === "detailed" && timestamp(data.second_khutbah) !== null && typeof data.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(data.date) && new Date(`${data.date}T12:00:00Z`).getUTCDay() === 5) {
      (modern ? tableShell : content).append(translatedRun("p", ui, "card.second_khutbah", "time", formatTime(data.second_khutbah, zone, ui, timeFormat), "note khutbah"));
    }
    if (this._selectedDay === 0 && data.ramadan?.active && (modern ? sectionVisible(this._config, "ramadan") : this._config.show_ramadan_details)) {
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
      sections.ramadan = ramadan;
      ramadan.append(grid); content.append(ramadan);
    }
    if (this._selectedDay === 0 && (modern || this._config.detail_level !== "compact") &&
        (modern ? sectionVisible(this._config, "night_calculations") : this._config.show_night_calculations) && data.night_calculations) {
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
      sections.night_calculations = night;
      content.append(night);
    }
    if (this._selectedDay === 0 && (modern ? sectionVisible(this._config, "jamaat_changes") : this._config.show_jamaat_changes)) {
      sections.jamaat_changes = buildJamaatChanges(data, ui, this._config, this._hass?.connection?.connected !== false);
      content.append(sections.jamaat_changes);
    }
    if (this._selectedDay === 0 && (modern ? sectionVisible(this._config, "timetable_health") : this._config.show_timetable_health)) {
      sections.timetable_health = buildTimetableHealth(data, ui, this._config, this._hass);
      content.append(sections.timetable_health);
    }
    let kioskFooterInfo = null;
    if (this._config.kiosk_mode && !modern) {
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
      if (modern) fixed.push(note);
    }
    if (background) {
      const credit = backgroundCredit(background);
      if (kioskFooterInfo) kioskFooterInfo.append(credit);
      else content.append(credit);
      if (modern) fixed.push(credit);
    }
    if (modern) this._arrangeContent(content, sections, ui, data, fixed, kioskToggle);
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
};
