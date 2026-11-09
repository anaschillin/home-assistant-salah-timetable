/** Lovelace graphical editor, independent of the card renderer. */
import {openReminderWizard} from "./reminder-wizard.js?v=3.6.0";
import {MOSQUE_BACKGROUNDS} from "./mosque-backgrounds.js?v=3.6.0";
import {EDITOR_CSS} from "./card-styles.js?v=3.6.0";
import {discoverTimetableEntities, normalizeConfig} from "./card-utils.js?v=3.6.0";
import {localizedNumber, resolveUi, tr} from "./card-i18n.js?v=3.6.0";
import {widgetSection} from "./widget-utils.js?v=3.6.0";
import {widgetTr} from "./widget-i18n.js?v=3.6.0";
import {buildLayoutEditor} from "./layout-editor.js?v=3.6.0";
import {node, direction, normalizeForUi} from "./card-shared.js?v=3.6.0";

export class SalahTimetableCardEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({mode: "open"}); this._config = normalizeConfig({}); this._expandedSection = "dates"; this._activeTab = "settings"; }
  setConfig(config) {
    const next = normalizeForUi(config, this._hass);
    if (widgetSection(next) !== widgetSection(this._config)) {
      this._layoutRoot?.dispose(); this._layoutRoot = null; this._controls = null;
      this._activeTab = "settings";
    }
    const changed = JSON.stringify(next) !== JSON.stringify(this._config);
    this._config = next;
    if (changed || !this._controls) this._render();
  }
  set hass(value) { this._hass = value; this._render(); }
  connectedCallback() { this._render(); }
  disconnectedCallback() {
    this._layoutRoot?.dispose();
    this._layoutRoot = null;
    this._layoutPanel?.replaceChildren();
  }
  _replaceConfig(config) {
    this._config = normalizeForUi(config, this._hass);
    this._updateControls();
    this.dispatchEvent(new CustomEvent("config-changed", {detail: {config: {...this._config}}, bubbles: true, composed: true}));
  }
  _updateTabs(ui) {
    if (!this._tabs) return;
    const standalone = Boolean(widgetSection(this._config));
    this._tabs.hidden = standalone;
    if (standalone) this._activeTab = "settings";
    for (const [id, button] of Object.entries(this._tabButtons)) {
      button.textContent = widgetTr(ui, id === "layout" ? "layout.tab" : "layout.settings_tab");
      button.setAttribute("aria-selected", String(this._activeTab === id));
      button.tabIndex = this._activeTab === id ? 0 : -1;
    }
    const active = this._activeTab === "layout";
    this._form.hidden = active;
    this._layoutPanel.hidden = !active;
    if (active) {
      if (!this._layoutRoot) {
        this._layoutRoot = buildLayoutEditor({config: this._config, hass: this._hass, ui, onChange: next => this._replaceConfig(next)});
        this._layoutPanel.append(this._layoutRoot);
      } else this._layoutRoot.refresh({config: this._config, hass: this._hass, ui});
    } else if (this._layoutRoot) {
      this._layoutRoot.dispose(); this._layoutRoot = null; this._layoutPanel.replaceChildren();
    }
  }
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
      const title = key === "show_jamaat_changes" || key === "show_timetable_health" ? widgetTr(ui, `section.${key.slice(5)}`) : tr(ui, `editor.${key}`);
      label.textContent = title;
      hint.textContent = key === "show_jamaat_changes" || key === "show_timetable_health" ? widgetTr(ui, `widget.${key.slice(5)}.description`) : tr(ui, `editor.hint.${key}`);
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
        || ((key === "show_sehri_countdown" || key === "show_iftar_countdown") && !this._config.show_ramadan_details && widgetSection(this._config) !== "ramadan")
        || (key === "show_night_calculations" && !this._config.arrangement && this._config.detail_level === "compact");
      control.disabled = disabled;
      field.setAttribute("data-disabled", String(disabled));
    }
    if (this._reminderAction) {
      this._reminderAction.hidden = Boolean(widgetSection(this._config)) || !this._hass?.user?.is_admin || this._config.kiosk_mode;
      this._reminderAction.textContent = tr(ui, "card.prayer_reminders");
    }
    this._updateSections(ui);
    this._updateTabs(ui);
    if (this._groupControl) {
      const enabled = Boolean(this._config.selection_group);
      this._groupSyncLabel.textContent = widgetTr(ui, "group.sync_label");
      this._groupSyncHint.textContent = widgetTr(ui, "group.sync_hint");
      this._groupSyncControl.checked = enabled;
      this._groupSyncControl.setAttribute("aria-label", widgetTr(ui, "group.sync_label"));
      this._groupNameLabel.textContent = widgetTr(ui, "group.name_label");
      this._groupNameHint.textContent = widgetTr(ui, "group.name_hint");
      this._groupNameField.hidden = !enabled;
      this._groupControl.setAttribute("aria-label", widgetTr(ui, "group.name_label"));
      this._groupControl.value = this._config.selection_group || "";
    }
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
      ["show_month_view"], ["show_timezone_note"], ["show_jamaat_changes"], ["show_timetable_health"],
      ["show_historical_day_events"], ["show_historical_month_highlights"], ["show_historical_sources"], ["show_disputed_historical_dates"],
      ["language", ["auto", "en", "ar"]], ["bilingual_prayer_labels"], ["kiosk_mode"], ["time_format", ["24h", "12h"]],
      ["hijri_adjustment", [-3, -2, -1, 0, 1, 2, 3]], ["hijri_day_boundary", ["midnight", "maghrib"]]
    ];
    const standaloneSection = widgetSection(this._config);
    const standaloneKeys = {
      mosque_selector: [], dates: ["show_hijri_date", "show_gregorian_date", "show_hijri_month_info", "hijri_adjustment", "hijri_day_boundary"],
      clock: ["time_format"], salah: ["detail_level", "bilingual_prayer_labels", "time_format"], jamaat: ["bilingual_prayer_labels", "time_format"],
      timetable: ["detail_level", "bilingual_prayer_labels", "time_format", "show_month_view", "kiosk_mode"],
      ramadan: ["show_sehri_countdown", "show_iftar_countdown", "time_format"], night_calculations: ["time_format"],
      jamaat_changes: ["time_format", "bilingual_prayer_labels"], timetable_health: ["time_format"],
    };
    const allowed = standaloneSection ? new Set(["language", "mosque_background", ...standaloneKeys[standaloneSection]]) : null;
    const fields = new Map();
    for (const [key, choices] of settings.filter(([key]) => !allowed || allowed.has(key))) {
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
      for (const key of keys) if (fields.has(key)) body.append(fields.get(key));
      if (standaloneSection && !body.children.length) continue;
      if (id === "history" && !standaloneSection) body.append(node("p", undefined, "editor-soon-note"));
      toggle.addEventListener("click", () => {
        this._expandedSection = this._expandedSection === id ? null : id;
        this._updateSections();
      });
      section.append(toggle, body);
      this._sections[id] = {toggle, body, title: heading, description};
      groups.push(section);
    }
    const syncField = node("div", undefined, "setting group-sync-setting");
    const syncCopy = node("span", undefined, "setting-copy");
    this._groupSyncLabel = node("span", undefined, "setting-label");
    this._groupSyncHint = node("span", undefined, "setting-hint");
    syncCopy.append(this._groupSyncLabel, this._groupSyncHint);
    this._groupSyncControl = node("ha-switch");
    this._groupSyncControl.setAttribute("data-option", "synchronise_mosque_selection");
    this._groupSyncControl.addEventListener("change", () => {
      this._changed({selection_group: this._groupSyncControl.checked ? this._config.selection_group || "home" : ""});
    });
    syncField.append(syncCopy, this._groupSyncControl);
    this._groupNameField = node("label", undefined, "setting group-name-setting widget-group-setting");
    const nameCopy = node("span", undefined, "setting-copy");
    this._groupNameLabel = node("span", undefined, "setting-label");
    this._groupNameHint = node("span", undefined, "setting-hint");
    nameCopy.append(this._groupNameLabel, this._groupNameHint);
    this._groupControl = node("input"); this._groupControl.type = "text";
    this._groupControl.setAttribute("data-option", "selection_group");
    this._groupControl.addEventListener("change", () => this._changed({selection_group: this._groupControl.value}));
    this._groupNameField.append(nameCopy, this._groupControl);
    // Retain the advanced section for both the main card and every standalone type.
    this._sections.advanced?.body.append(syncField, this._groupNameField);
    // Keep reminder setup beside the detail selector, outside the dashboard card.
    this._reminderAction = this._reminderButton(resolveUi(this._config, this._hass));
    // One ordered checkbox list replaces the old duplicate radio selector.
    form.append(mosqueGroup);
    if (fields.has("detail_level")) form.append(fields.get("detail_level"));
    if (this._reminderAction) form.append(this._reminderAction);
    form.append(...groups, help);
    this._tabs = node("div", undefined, "editor-tabs"); this._tabs.setAttribute("role", "tablist");
    this._tabButtons = {};
    for (const id of ["settings", "layout"]) {
      const button = node("button"); button.type = "button"; button.setAttribute("role", "tab");
      button.id = `salah-editor-tab-${id}`;
      button.setAttribute("data-editor-tab", id); button.setAttribute("aria-controls", `salah-editor-${id}`);
      button.addEventListener("click", () => { this._activeTab = id; this._updateTabs(resolveUi(this._config, this._hass)); });
      button.addEventListener("keydown", event => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
        event.preventDefault();
        const ui = resolveUi(this._config, this._hass);
        const order = ui.dir === "rtl" ? ["layout", "settings"] : ["settings", "layout"];
        const index = order.indexOf(id);
        const next = event.key === "Home" ? order[0] : event.key === "End" ? order.at(-1)
          : order[(index + (event.key === "ArrowRight" ? 1 : order.length - 1)) % order.length];
        this._activeTab = next; this._updateTabs(ui);
        this._tabButtons[next].focus?.({preventScroll: true});
      });
      this._tabButtons[id] = button; this._tabs.append(button);
    }
    form.id = "salah-editor-settings"; form.setAttribute("role", "tabpanel"); form.setAttribute("aria-labelledby", "salah-editor-tab-settings");
    this._layoutPanel = node("div"); this._layoutPanel.id = "salah-editor-layout"; this._layoutPanel.setAttribute("role", "tabpanel"); this._layoutPanel.setAttribute("aria-labelledby", "salah-editor-tab-layout");
    this._updateControls();
    this.shadowRoot.replaceChildren(style, this._tabs, form, this._layoutPanel);
  }
}

