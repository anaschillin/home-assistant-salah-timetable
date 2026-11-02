/** Guided prayer reminders, saved as ordinary Home Assistant automations. */
const STYLE = `
:host{font-family:var(--paper-font-body1_-_font-family,Roboto,sans-serif);color:var(--primary-text-color,#222)}
dialog{box-sizing:border-box;width:min(42rem,calc(100vw - 2rem));max-height:calc(100dvh - 2rem);padding:0;border:1px solid var(--divider-color,#bbb);border-radius:12px;background:var(--card-background-color,#fff);color:inherit;box-shadow:0 12px 40px #0005}
dialog::backdrop{background:#0008}form{display:flex;flex-direction:column;max-height:calc(100dvh - 2rem);margin:0}header,main,footer{padding:1rem 1.25rem}header{border-bottom:1px solid var(--divider-color,#ddd)}h2{font-size:1.35rem;margin:0 0 .3rem}h3{font-size:1.1rem;margin:.4rem 0 1rem}p{line-height:1.5;margin:.5rem 0}main{overflow:auto;min-height:8rem}footer{display:flex;gap:.6rem;flex-wrap:wrap;border-top:1px solid var(--divider-color,#ddd)}.spacer{flex:1}fieldset{min-width:0;border:1px solid var(--divider-color,#ddd);border-radius:8px;margin:1rem 0;padding:.75rem}legend{font-weight:600}.choice{display:flex;align-items:flex-start;gap:.6rem;padding:.5rem 0;line-height:1.4}.choice span{min-width:0;overflow-wrap:anywhere}.delivery-filters{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.7rem}.delivery-filters label{min-width:0}.delivery-filters select{min-width:0}.delivery-tabs{display:flex;gap:.5rem;border-bottom:1px solid var(--divider-color,#ddd);padding-bottom:.6rem;margin:.8rem 0}.delivery-tabs button{flex:1}.delivery-tabs [aria-selected=true]{border-color:var(--primary-color,#0366d6);box-shadow:inset 0 -3px var(--primary-color,#0366d6)}.choice input{margin-top:.2rem;flex:none;min-height:1.1rem;min-width:1.1rem}label.field{display:block;margin:.8rem 0}label.field span{display:block;margin-bottom:.4rem}input[type=text],input[type=number],select{box-sizing:border-box;width:100%;padding:.7rem;border:1px solid var(--divider-color,#888);border-radius:6px;background:var(--secondary-background-color,#f5f5f5);color:inherit;font:inherit}button{cursor:pointer;min-height:44px;padding:.5rem .9rem;border:1px solid var(--divider-color,#888);border-radius:6px;background:var(--secondary-background-color,#eee);color:inherit;font:inherit}button.primary{background:var(--primary-color,#0366d6);border-color:var(--primary-color,#0366d6);color:var(--text-primary-color,#fff)}button:disabled{opacity:.6;cursor:wait}:focus-visible{outline:3px solid var(--primary-color,#0366d6);outline-offset:2px}.muted{color:var(--secondary-text-color,#666);font-size:.9rem}.error{padding:.7rem;border:1px solid var(--error-color,#b00020);border-radius:6px;color:var(--error-color,#b00020)}h2,h3,p{overflow-wrap:anywhere}ul{padding-inline-start:1.3rem}li{line-height:1.5;overflow-wrap:anywhere}a{color:var(--primary-color,#0366d6)}.review{border-bottom:1px solid var(--divider-color,#ddd);padding:.4rem 0 .8rem}summary{cursor:pointer}.status{min-height:1.4rem} @media(max-width:420px){header,main,footer{padding:.8rem}dialog{width:calc(100vw - 1rem);max-height:calc(100dvh - 1rem)}}
`;
const el = (tag, text, className) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
};
const beginning = value => value.endsWith("_begin");
const jamaat = value => value.endsWith("_jamaat") || value === "jumuah";
const isMinutes = value => Number.isInteger(value) && value >= 0 && value <= 180;
const newDelivery = () => ({notification_actions: [], notification_entities: [], media_players: [], media_content_id: "", media_content_type: "audio/mpeg", volume: null});
const newFilters = () => ({integration: "", device_type: ""});
const normalizeChoice = (choice, key) => ({
  ...choice, key,
  integration: choice.integration || "unknown",
  integration_name: choice.integration_name || (choice.integration && choice.integration !== "unknown" ? choice.integration : "Other / unknown"),
  device_type: choice.device_type || "unknown",
  device_type_name: choice.device_type_name || (choice.device_type && choice.device_type !== "unknown" ? choice.device_type : "Other / unknown"),
});
const deliveryName = kind => kind === "beginning" ? "Beginning reminders" : "Jamaat reminders";
const destinationLabel = (id, name) => name && name !== id ? `${name} (${id})` : id;
// Local HTTP Home Assistant addresses do not expose crypto.randomUUID.
const newAutomationId = () => {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return [...bytes].map(value => value.toString(16).padStart(2, "0")).join("");
};

export class SalahReminderWizard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this._step = "loading";
    this._selected = new Set();
    this._settings = new Map();
    this._prayerIndex = 0;
    this._timingIndex = 0;
    this._delivery = {beginning: newDelivery(), jamaat: newDelivery()};
    this._deliveryIndex = 0;
    this._deliveryTabs = {beginning: "notifications", jamaat: "notifications"};
    this._deliveryFilters = {
      beginning: {notifications: newFilters(), sound: newFilters()},
      jamaat: {notifications: newFilters(), sound: newFilters()},
    };
    this._name = "Prayer reminders";
    this._error = "";
    this._status = "";
    this._saving = false;
    this._automationId = `salah_reminders_${newAutomationId()}`;
    this._controlId = 0;
  }

  async start(hass) {
    this._hass = hass;
    this._previousFocus = document.activeElement;
    while (this._previousFocus?.shadowRoot?.activeElement) this._previousFocus = this._previousFocus.shadowRoot.activeElement;
    this._dialog = el("dialog");
    this._dialog.setAttribute("aria-labelledby", "reminder-title");
    this._dialog.addEventListener("cancel", event => {
      event.preventDefault();
      if (!this._saving) this.close();
    });
    const style = el("style", STYLE);
    this.shadowRoot.append(style, this._dialog);
    this._render();
    this._dialog.showModal();
    await this._load();
  }

  async _load() {
    this._error = "";
    this._step = "loading";
    this._render();
    try {
      this._options = await this._hass.callWS({type: "salah_timetable/reminder_options"});
      const mosques = this._options.mosques || [];
      for (const mosque of mosques) {
        if (!this._settings.has(mosque.id)) this._settings.set(mosque.id, {id: mosque.id, fields: [], begin_minutes: 10, jamaat_minutes: 10});
      }
      if (mosques.length === 1) {
        this._selected.add(mosques[0].id);
        this._step = "prayers";
      } else this._step = "mosques";
    } catch {
      this._step = "load_error";
      this._error = "Could not load reminder setup. Check administrator access, the integration status and your connection, then retry.";
    }
    if (this.isConnected) this._render();
  }

  close() {
    if (this._saving) return;
    this._dialog.close();
    this.remove();
    this._previousFocus?.focus?.();
  }

  _mosques() { return (this._options?.mosques || []).filter(mosque => this._selected.has(mosque.id)); }
  _setting(mosque) { return this._settings.get(mosque.id); }
  _deliveryKinds() {
    const selected = this._mosques().flatMap(mosque => this._setting(mosque).fields);
    return [selected.some(beginning) ? "beginning" : null, selected.some(jamaat) ? "jamaat" : null].filter(Boolean);
  }
  _activeDeliveryKind() { return this._deliveryKinds()[this._deliveryIndex]; }
  _switchDeliveryTab(tab) {
    this._deliveryTabs[this._activeDeliveryKind()] = tab;
    this._render();
    this.shadowRoot.querySelector(`[data-key="tab:${tab}"]`)?.focus();
  }
  _button(text, action, className) {
    const button = el("button", text, className);
    button.type = "button";
    button.disabled = this._saving;
    button.addEventListener("click", action);
    return button;
  }
  _choice(parent, text, checked, changed, key) {
    const label = el("label", undefined, "choice");
    const input = el("input");
    input.type = "checkbox";
    input.checked = checked;
    input.dataset.key = key;
    input.addEventListener("change", () => changed(input.checked));
    label.append(input, el("span", text));
    parent.append(label);
    return input;
  }
  _field(parent, text, value, changed, {type = "text", min, max, step, key} = {}) {
    const label = el("label", undefined, "field");
    const input = el("input");
    input.type = type;
    input.value = value;
    input.id = `reminder-control-${++this._controlId}`;
    input.dataset.key = key;
    if (min !== undefined) input.min = min;
    if (max !== undefined) input.max = max;
    if (step !== undefined) input.step = step;
    input.addEventListener("input", () => changed(type === "number" ? (input.value === "" ? NaN : Number(input.value)) : input.value));
    label.append(el("span", text), input);
    parent.append(label);
    return input;
  }
  _group(parent, title) { const group = el("fieldset"); group.append(el("legend", title)); parent.append(group); return group; }
  _toggle(values, value, checked) { return checked ? [...new Set([...values, value])] : values.filter(item => item !== value); }

  _render() {
    this._controlId = 0;
    const form = el("form");
    form.addEventListener("submit", event => { event.preventDefault(); this._next(); });
    const header = el("header");
    const title = el("h2", "Prayer reminders"); title.id = "reminder-title";
    const labels = {loading: "Loading setup…", load_error: "Setup unavailable", mosques: "Select masjids", prayers: "Select prayer times", timing: "Set advance reminders", delivery: "Choose delivery", review: "Review configuration", done: "Reminders saved"};
    header.append(title, el("p", labels[this._step], "muted"));
    const main = el("main");
    main.tabIndex = -1;
    if (this._error) {
      const error = el("p", this._error, "error"); error.setAttribute("role", "alert"); main.append(error);
    }
    if (this._step === "load_error") main.append(this._button("Retry", () => this._load()));
    if (this._step === "mosques") this._renderMosques(main);
    if (this._step === "prayers") this._renderPrayers(main);
    if (this._step === "timing") this._renderTiming(main);
    if (this._step === "delivery") this._renderDelivery(main);
    if (this._step === "review") this._renderReview(main);
    if (this._step === "done") {
      main.append(el("p", "Your reminder automation has been saved. Open it to check that it is enabled, or to edit, disable or delete it."));
      const link = el("a", "Open saved automation");
      link.href = `/config/automation/edit/${this._automationId}`;
      main.append(link);
    }
    if (this._status) { const status = el("p", this._status, "status"); status.setAttribute("role", "status"); main.append(status); }
    const footer = el("footer");
    footer.append(this._button(this._step === "done" ? "Close" : "Cancel", () => this.close()));
    footer.append(el("span", undefined, "spacer"));
    if (["prayers", "timing", "delivery", "review"].includes(this._step) && !(this._step === "prayers" && this._prayerIndex === 0 && (this._options?.mosques || []).length === 1)) {
      footer.append(this._button("Back", () => this._back()));
    }
    if (["mosques", "prayers", "timing", "delivery", "review"].includes(this._step)) {
      footer.append(this._button(this._saving ? "Saving…" : this._step === "review" ? "Finish" : "Next", () => this._next(), "primary"));
    }
    form.append(header, main, footer);
    this._dialog.replaceChildren(form);
    if (this._dialog.open) main.focus();
  }

  _renderMosques(main) {
    const mosques = this._options.mosques || [];
    main.append(el("p", "Choose one or more masjids for this reminder automation."));
    if (!mosques.length) main.append(el("p", "No configured masjids were found. Add Salah Timetable and approve a timetable first."));
    const group = this._group(main, "Masjids");
    for (const mosque of mosques) this._choice(group, `${mosque.name} (${mosque.time_zone})${mosque.ready ? "" : " — timetable currently unavailable"}`, this._selected.has(mosque.id), checked => {
      if (checked) this._selected.add(mosque.id); else this._selected.delete(mosque.id);
    }, `mosque:${mosque.id}`);
  }

  _renderPrayers(main) {
    const mosques = this._mosques(), mosque = mosques[this._prayerIndex];
    if (!mosque) return;
    const settings = this._setting(mosque);
    main.append(el("h3", mosque.name));
    main.append(el("p", `Masjid ${this._prayerIndex + 1} of ${mosques.length}. Select one or more beginnings and/or congregations.`));
    if (!mosque.ready) main.append(el("p", "Timetable unavailable: reminders will wait for approved published times.", "muted"));
    for (const [title, matcher] of [["Beginning times", beginning], ["Jamaat times", jamaat]]) {
      const group = this._group(main, title);
      for (const field of mosque.fields.filter(item => matcher(item.value))) this._choice(group, field.value === "jumuah" ? `${field.label} — every published congregation` : field.label, settings.fields.includes(field.value), checked => {
        settings.fields = this._toggle(settings.fields, field.value, checked);
      }, `field:${field.value}`);
    }
    if (mosques.length > 1) main.append(this._button("Apply these prayers to all selected masjids", () => {
      for (const item of mosques) {
        const allowed = new Set(item.fields.map(field => field.value));
        this._setting(item).fields = settings.fields.filter(field => allowed.has(field));
      }
      this._status = "Prayer choices applied. You can adjust each masjid before continuing.";
      this._render();
    }));
  }

  _renderTiming(main) {
    const mosques = this._mosques(), mosque = mosques[this._timingIndex];
    if (!mosque) return;
    const settings = this._setting(mosque);
    main.append(el("h3", mosque.name));
    main.append(el("p", `Masjid ${this._timingIndex + 1} of ${mosques.length}. Enter positive minutes before the published time; 0 means at the time.`));
    if (settings.fields.some(beginning)) this._field(main, "Minutes before selected beginning times", settings.begin_minutes, value => { settings.begin_minutes = value; }, {type: "number", min: 0, max: 180, step: 1, key: "begin_minutes"});
    if (settings.fields.some(jamaat)) this._field(main, "Minutes before selected Jamaat times", settings.jamaat_minutes, value => { settings.jamaat_minutes = value; }, {type: "number", min: 0, max: 180, step: 1, key: "jamaat_minutes"});
  }

  _destinationChoices(tab) {
    if (tab === "notifications") return ["notification_actions", "notification_entities"].flatMap(key =>
      (this._options[key] || []).map(choice => normalizeChoice(choice, key)));
    const players = Array.isArray(this._options.media_players) ? this._options.media_players :
      Object.entries(this._hass.states || {}).filter(([id]) => id.startsWith("media_player.")).map(([value, state]) => ({value, label: state.attributes?.friendly_name || value}));
    return players.map(choice => normalizeChoice(choice, "media_players"));
  }

  _filteredDestinations(parent, tab, delivery) {
    const all = this._destinationChoices(tab);
    const filters = this._deliveryFilters[this._activeDeliveryKind()][tab];
    const controls = el("div", undefined, "delivery-filters");
    for (const [key, title, name] of [["integration", "Integration", "integration_name"], ["device_type", "Device type", "device_type_name"]]) {
      const values = new Map(all.map(item => [item[key], item[name]]));
      if (filters[key] && !values.has(filters[key])) filters[key] = "";
      const label = el("label", undefined, "field"), select = el("select");
      select.id = `delivery-filter-${key}`;
      select.dataset.key = `filter:${key}`;
      const options = [["", "All"], ...[...values].sort((a, b) => a[1].localeCompare(b[1]))];
      for (const [value, text] of options) {
        const option = el("option", text); option.value = value; select.append(option);
      }
      select.value = filters[key];
      select.addEventListener("change", () => {
        filters[key] = select.value;
        this._render();
        this.shadowRoot.querySelector(`[data-key="filter:${key}"]`)?.focus();
      });
      label.append(el("span", title), select); controls.append(label);
    }
    const visible = all.filter(item => (!filters.integration || item.integration === filters.integration) && (!filters.device_type || item.device_type === filters.device_type));
    const keys = tab === "notifications" ? ["notification_actions", "notification_entities"] : ["media_players"];
    const shown = new Set(visible.map(item => `${item.key}:${item.value}`));
    const selected = keys.flatMap(key => delivery[key].map(value => `${key}:${value}`));
    const hidden = selected.filter(key => !shown.has(key)).length;
    const summary = el("p", `${selected.length} selected destination${selected.length === 1 ? "" : "s"}.${hidden ? ` ${hidden} selected destination${hidden === 1 ? "" : "s"} hidden from this list.` : ""} Filters only change this list; selections are kept.`, "muted");
    summary.dataset.role = "delivery-filter-summary";
    parent.append(controls, summary);
    if (!visible.length) parent.append(el("p", "No destinations match these filters.", "muted"));
    return visible;
  }

  _renderDelivery(main) {
    const kind = this._activeDeliveryKind(), delivery = this._delivery[kind];
    if (!delivery) return;
    this._field(main, "Automation name", this._name, value => { this._name = value; }, {key: "name"});
    main.append(el("h3", deliveryName(kind)));
    main.append(el("p", `Configure notifications and/or sound for selected ${kind === "beginning" ? "beginning" : "Jamaat"} times across all selected masjids. The other reminder type has its own delivery settings.`));
    const tabs = el("div", undefined, "delivery-tabs");
    tabs.setAttribute("role", "tablist");
    tabs.setAttribute("aria-label", `${deliveryName(kind)} delivery`);
    const current = this._deliveryTabs[kind];
    for (const [key, title] of [["notifications", "Notifications"], ["sound", "Sound"]]) {
      const button = this._button(title, () => this._switchDeliveryTab(key));
      button.id = `delivery-${kind}-tab-${key}`;
      button.dataset.key = `tab:${key}`;
      button.setAttribute("role", "tab");
      button.setAttribute("aria-selected", String(current === key));
      button.setAttribute("aria-controls", `delivery-${kind}-panel`);
      button.tabIndex = current === key ? 0 : -1;
      button.addEventListener("keydown", event => {
        if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
          event.preventDefault();
          this._switchDeliveryTab(event.key === "Home" ? "notifications" : event.key === "End" ? "sound" : key === "notifications" ? "sound" : "notifications");
        }
      });
      tabs.append(button);
    }
    const panel = el("section");
    panel.id = `delivery-${kind}-panel`;
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", `delivery-${kind}-tab-${current}`);
    main.append(tabs, panel);
    const destinations = this._filteredDestinations(panel, current, delivery);
    panel.append(el("p", "Device types use the integration's reported type or Home Assistant device/entity labels when available. Other devices appear under Other / unknown.", "muted"));
    if (current === "notifications") {
      const choices = [["notification_actions", "Notification actions"], ["notification_entities", "Notification entities"]];
      for (const [key, title] of choices) {
        const group = this._group(panel, title);
        const available = destinations.filter(choice => choice.key === key);
        for (const choice of available) this._choice(group, destinationLabel(choice.value, choice.label), delivery[key].includes(choice.value), checked => {
          delivery[key] = this._toggle(delivery[key], choice.value, checked);
          this._render();
          this.shadowRoot.querySelector(`[data-key="${key}:${choice.value}"]`)?.focus();
        }, `${key}:${choice.value}`);
        if (!available.length) group.append(el("p", `No matching ${title.toLowerCase()}.`, "muted"));
      }
      panel.append(el("p", "Choose one notification route per device to avoid duplicate alerts. Phone notification sounds follow the Companion app and device settings.", "muted"));
    } else {
      const players = this._group(panel, "Sound playback");
      for (const choice of destinations) this._choice(players, destinationLabel(choice.value, choice.label), delivery.media_players.includes(choice.value), checked => {
        delivery.media_players = this._toggle(delivery.media_players, choice.value, checked);
        this._render();
        this.shadowRoot.querySelector(`[data-key="media_player:${choice.value}"]`)?.focus();
      }, `media_player:${choice.value}`);
      if (!destinations.length) players.append(el("p", "No matching media players.", "muted"));
      if (delivery.media_players.length) {
        this._field(panel, "Sound media URL or media-source ID", delivery.media_content_id, value => { delivery.media_content_id = value; }, {key: "media_content_id"});
        panel.append(el("p", "Use your own recording that the chosen speakers can reach. For a Music Assistant URI, select its Music Assistant player and use music as the media content type.", "muted"));
        this._field(panel, "Media content type", delivery.media_content_type, value => { delivery.media_content_type = value; }, {key: "media_content_type"});
        this._choice(panel, "Set speaker volume", delivery.volume !== null, checked => { delivery.volume = checked ? 0.5 : null; this._render(); }, "set_volume");
        if (delivery.volume !== null) this._field(panel, "Speaker volume (0–1)", delivery.volume, value => { delivery.volume = value; }, {type: "number", min: 0, max: 1, step: 0.05, key: "volume"});
      }
    }
  }

  _renderReview(main) {
    main.append(el("h3", this._name));
    for (const mosque of this._mosques()) {
      const section = el("section", undefined, "review"), settings = this._setting(mosque);
      section.append(el("h3", mosque.name), el("p", `Timetable timezone: ${mosque.time_zone}`, "muted"));
      const list = el("ul");
      for (const [matcher, minutes] of [[beginning, settings.begin_minutes], [jamaat, settings.jamaat_minutes]]) {
        const labels = mosque.fields.filter(field => settings.fields.includes(field.value) && matcher(field.value)).map(field => field.value === "jumuah" ? `${field.label} (all published congregations)` : field.label);
        if (labels.length) list.append(el("li", `${labels.join(", ")}: ${minutes === 0 ? "at the published time" : `${minutes} minutes before`}`));
      }
      section.append(list); main.append(section);
    }
    for (const kind of this._deliveryKinds()) {
      const delivery = this._delivery[kind], list = el("ul");
      for (const key of ["notification_actions", "notification_entities"]) for (const id of delivery[key]) {
        list.append(el("li", `Notify: ${destinationLabel(id, (this._options[key] || []).find(item => item.value === id)?.label)}`));
      }
      for (const id of delivery.media_players) list.append(el("li", `Play sound: ${destinationLabel(id, this._options.media_players?.find(item => item.value === id)?.label || this._hass.states[id]?.attributes?.friendly_name)}`));
      main.append(el("h3", `${deliveryName(kind)} delivery`), list);
      if (delivery.media_players.length) {
        main.append(el("p", `Recording: ${delivery.media_content_id}`), el("p", `Media content type: ${delivery.media_content_type}`, "muted"));
        if (delivery.volume !== null) main.append(el("p", `Set volume: ${delivery.volume}. This changes the speaker's volume without restoring it afterward.`, "muted"));
      }
    }
    main.append(el("p", "To test delivery after saving, expand the Beginning or Jamaat reminders branch in Home Assistant and run an individual action. A manual whole-automation run does not select a reminder type.", "muted"));
    main.append(el("p", "Existing reminder automations keep running. Disable any reminders you are replacing to avoid duplicate alerts.", "muted"));
    main.append(el("p", "Only approved published times are used. Missing times are skipped, and missed reminders are not replayed. A reminder does not track whether you have prayed or establish a prayer deadline.", "muted"));
  }

  _next() {
    if (this._saving) return;
    this._error = "";
    this._status = "";
    const mosques = this._mosques();
    if (this._step === "mosques") {
      if (!mosques.length) this._error = "Select at least one masjid.";
      else { this._prayerIndex = 0; this._step = "prayers"; }
    } else if (this._step === "prayers") {
      const settings = this._setting(mosques[this._prayerIndex]);
      if (!settings.fields.length) this._error = "Select at least one beginning or Jamaat time for this masjid.";
      else if (this._prayerIndex < mosques.length - 1) {
        const current = settings.fields;
        this._prayerIndex++;
        const next = this._setting(mosques[this._prayerIndex]);
        if (!next.fields.length) {
          const available = new Set(mosques[this._prayerIndex].fields.map(field => field.value));
          next.fields = current.filter(field => available.has(field));
        }
      } else { this._timingIndex = 0; this._step = "timing"; }
    } else if (this._step === "timing") {
      const settings = this._setting(mosques[this._timingIndex]);
      if ((settings.fields.some(beginning) && !isMinutes(settings.begin_minutes)) || (settings.fields.some(jamaat) && !isMinutes(settings.jamaat_minutes))) this._error = "Enter whole minutes from 0 to 180.";
      else if (this._timingIndex < mosques.length - 1) this._timingIndex++;
      else { this._deliveryIndex = 0; this._step = "delivery"; }
    } else if (this._step === "delivery") {
      const kind = this._activeDeliveryKind(), delivery = this._delivery[kind];
      if (!this._name.trim() || this._name.trim().length > 100) this._error = "Enter an automation name of 1–100 characters.";
      else if (!delivery.notification_actions.length && !delivery.notification_entities.length && !delivery.media_players.length) this._error = "Choose at least one notification destination or media player.";
      else if (delivery.media_players.length && (!delivery.media_content_id.trim() || !delivery.media_content_type.trim())) {
        this._error = "Enter the recording's media URL or ID and content type.";
        this._deliveryTabs[kind] = "sound";
      } else if (delivery.media_players.length && delivery.volume !== null && (!Number.isFinite(delivery.volume) || delivery.volume < 0 || delivery.volume > 1)) {
        this._error = "Enter a speaker volume from 0 to 1.";
        this._deliveryTabs[kind] = "sound";
      } else if (this._deliveryIndex < this._deliveryKinds().length - 1) this._deliveryIndex++;
      else this._step = "review";
    } else if (this._step === "review") { this._save(); return; }
    this._render();
  }

  _back() {
    if (this._saving) return;
    this._error = ""; this._status = "";
    if (this._step === "prayers") {
      if (this._prayerIndex > 0) this._prayerIndex--;
      else this._step = "mosques";
    } else if (this._step === "timing") {
      if (this._timingIndex > 0) this._timingIndex--;
      else { this._prayerIndex = this._mosques().length - 1; this._step = "prayers"; }
    } else if (this._step === "delivery") {
      if (this._deliveryIndex > 0) this._deliveryIndex--;
      else { this._timingIndex = this._mosques().length - 1; this._step = "timing"; }
    } else if (this._step === "review") { this._deliveryIndex = this._deliveryKinds().length - 1; this._step = "delivery"; }
    this._render();
  }

  _payload() {
    const delivery = {};
    for (const kind of this._deliveryKinds()) {
      delivery[kind] = structuredClone(this._delivery[kind]);
      if (!delivery[kind].media_players.length) { delivery[kind].media_content_id = ""; delivery[kind].media_content_type = "audio/mpeg"; delivery[kind].volume = null; }
    }
    return {type: "salah_timetable/reminder_preview", name: this._name.trim(), mosques: this._mosques().map(mosque => {
      const setting = structuredClone(this._setting(mosque));
      if (!setting.fields.some(beginning)) setting.begin_minutes = 10;
      if (!setting.fields.some(jamaat)) setting.jamaat_minutes = 10;
      return setting;
    }), delivery};
  }

  async _save() {
    if (this._saving) return;
    this._saving = true; this._error = ""; this._render();
    try {
      const preview = await this._hass.callWS(this._payload());
      if (!preview?.config || typeof this._hass.callApi !== "function") throw new Error("Automation API unavailable");
      await this._hass.callApi("POST", `config/automation/config/${this._automationId}`, preview.config);
      this._step = "done";
    } catch {
      this._error = "Could not save the reminder automation. Check your connection and that Home Assistant's automation configuration is available, then retry. Retrying uses the same automation ID to avoid duplicates.";
    } finally {
      this._saving = false;
      if (this.isConnected) this._render();
    }
  }
}

if (!customElements.get("salah-reminder-wizard")) customElements.define("salah-reminder-wizard", SalahReminderWizard);

export function openReminderWizard(hass) {
  const wizard = document.createElement("salah-reminder-wizard");
  document.body.append(wizard);
  wizard.ready = wizard.start(hass).catch(error => {
    wizard._saving = false;
    if (wizard._dialog?.open) wizard._dialog.close();
    wizard.remove();
    wizard._previousFocus?.focus?.();
    throw error;
  });
  return wizard;
}
