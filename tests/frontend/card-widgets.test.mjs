import {test, assert, registry, timers, SalahTimetableCard, SalahTimetableCardEditor, find, attributes, hass} from "./card-test-harness.mjs";

function widgetAttributes() {
  return {...attributes,
    day_prayers: {"2026-10-21": attributes.prayers, "2026-10-22": attributes.prayers},
    jamaat_events: [
      {field: "fajr_jamaat", prayer: "fajr", timestamp: "2026-10-21T05:15:00Z"},
      {field: "fajr_jamaat", prayer: "fajr", timestamp: "2026-10-22T05:00:00Z"},
    ],
    config_entry_id: "example-entry",
    timetable_health: {
      coverage: {status: "expiring", available_through: "2026-10-22", days_remaining: 1, today_available: true, tomorrow_available: true},
      completeness: {status: "complete", required_fields: ["fajr_begin"], missing_today: [], missing_tomorrow: []},
      source: {status: "not_configured", pending_review: true, error_count: 0},
    },
  };
}
test("new widgets stay opt-in and share read-only sections with standalone cards", () => {
  const data = widgetAttributes();
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable"}); card.hass = hass(data);
  assert.ok(!card.shadowRoot.textContent.includes("15 min earlier"));
  card.setConfig({entity: "sensor.mosque_prayer_timetable", show_jamaat_changes: true, show_timetable_health: true});
  const sections = find(card.shadowRoot, "section");
  assert.ok(sections.some(section => section.attributes["data-section"] === "jamaat_changes"));
  assert.ok(sections.some(section => section.attributes["data-section"] === "timetable_health"));
  assert.ok(card.shadowRoot.textContent.includes("15 min earlier"));
  const Changes = registry.get("salah-widget-jamaat-changes");
  const widget = new Changes(); widget.setConfig({entity: "sensor.mosque_prayer_timetable"}); widget.hass = hass(data);
  assert.equal(widget._config.type, "custom:salah-widget-jamaat-changes");
  assert.equal(widget._config.show_mosque_background, false);
  assert.ok(widget.shadowRoot.textContent.includes("15 min earlier"));
  assert.equal(find(widget.shadowRoot, "table").length, 0);
});
test("health refreshes on pending changes and only administrators get setup navigation", () => {
  const Health = registry.get("salah-widget-timetable-health");
  const widget = new Health(); widget.setConfig({entity: "sensor.mosque_prayer_timetable"});
  const data = widgetAttributes(); const state = hass(data);
  widget.hass = state;
  assert.equal(find(widget.shadowRoot, "a").length, 0);
  widget.hass = {...state, user: {is_admin: true}};
  assert.ok(find(widget.shadowRoot, "a")[0].href.endsWith("?config_entry=example-entry"));
  data.timetable_health.source.pending_review = false;
  widget.hass = {...state, user: {is_admin: true}};
  assert.equal(find(widget.shadowRoot, "a")[0].textContent, "Open mosque setup");
  widget.hass = {...state, connection: {connected: false}};
  assert.equal(find(widget.shadowRoot, "a").length, 0);
  assert.ok(widget.shadowRoot.textContent.includes("unavailable"));
});
test("grouped widgets synchronize mosque and reject an excluded selection without fallback", () => {
  const data = widgetAttributes();
  const state = hass(data);
  state.states["sensor.other_prayer_timetable"] = {state: data.date, attributes: {...data, mosque_name: "Other mosque"}};
  const Selector = registry.get("salah-widget-mosque-selector");
  const selector = new Selector(); selector.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "example"}); selector.hass = state; selector.connectedCallback();
  const Health = registry.get("salah-widget-timetable-health");
  const health = new Health(); health.setConfig({entity: "sensor.mosque_prayer_timetable", mosque_entities: ["sensor.mosque_prayer_timetable"], selection_group: "example"}); health.hass = state; health.connectedCallback();
  selector._selectMosque("sensor.other_prayer_timetable");
  assert.equal(health._activeEntity(), "sensor.other_prayer_timetable");
  assert.ok(health.shadowRoot.textContent.includes("not enabled"));
  assert.ok(!health.shadowRoot.textContent.includes("approved through"));
  health.preview = true;
  selector._selectMosque("sensor.mosque_prayer_timetable");
  assert.equal(health._group, null, "Preview leaves live group");
  health.disconnectedCallback(); selector.disconnectedCallback();
  assert.equal(timers.size, 0);
});
test("standalone editor exposes its own settings without an ineffective hide toggle", () => {
  const editor = new SalahTimetableCardEditor();
  editor.setConfig({type: "custom:salah-widget-jamaat-changes", entity: "sensor.mosque_prayer_timetable"}); editor.hass = hass();
  const options = find(editor.shadowRoot, "ha-switch").map(item => item.attributes["data-option"]);
  assert.ok(!options.includes("show_jamaat_changes"));
  assert.ok(!options.includes("show_hijri_date"));
  assert.ok(find(editor.shadowRoot, "input").some(item => item.attributes["data-option"] === "selection_group"));
});

test("today's complete status does not claim tomorrow's missing fields are complete", () => {
  const Health = registry.get("salah-widget-timetable-health");
  const widget = new Health(); widget.setConfig({entity: "sensor.mosque_prayer_timetable"});
  const data = widgetAttributes(); data.timetable_health.completeness.missing_tomorrow = ["fajr_begin"];
  widget.hass = hass(data);
  assert.ok(!widget.shadowRoot.textContent.includes("complete for today and tomorrow"));
  assert.ok(widget.shadowRoot.textContent.includes("Missing tomorrow"));
});


test("standalone cards retain photographer attribution when backgrounds are explicitly enabled", () => {
  const Health = registry.get("salah-widget-timetable-health");
  const widget = new Health();
  widget.setConfig({entity: "sensor.mosque_prayer_timetable", show_mosque_background: true}); widget.hass = hass(widgetAttributes());
  assert.ok(find(widget.shadowRoot, "small").some(item => item.className === "background-credit"));
  assert.ok(find(widget.shadowRoot, "a").some(item => item.textContent.startsWith("Photo:")));
});


function arrangedSections(card) {
  return find(card.shadowRoot, "section").filter(item => item.className === "arrangement-section");
}
test("custom arrangements order shared sections and show an explicitly enabled Compact timetable", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level: "compact", show_timetable: true, show_dates: true,
    arrangement: {sections: [{id: "timetable", width: "full"}, {id: "jamaat", width: "half"}, {id: "salah", width: "half"}]}});
  card.hass = hass(widgetAttributes());
  const sections = arrangedSections(card);
  assert.deepEqual(sections.slice(0, 3).map(item => item.attributes["data-section"]), ["timetable", "jamaat", "salah"]);
  assert.equal(sections[1].attributes["data-width"], "half");
  assert.equal(find(card.shadowRoot, "table").length, 1);
  assert.ok(sections.some(item => item.attributes["data-section"] === "dates"));
  assert.equal(find(card.shadowRoot, "nav").filter(item => item.className === "date-tabs").length, 1);
});
test("all ten standalone sections register with correct stub types and relevant independent content", () => {
  const ids = ["mosque-selector", "dates", "clock", "salah", "jamaat", "timetable", "ramadan", "night-calculations", "jamaat-changes", "timetable-health"];
  const data = widgetAttributes();
  data.ramadan = {active: true, sehri: "2026-10-21T04:45:00Z", iftar: "2026-10-21T17:00:00Z"};
  data.night_calculations = {midpoint: "2026-10-21T23:00:00Z", last_third: "2026-10-22T01:00:00Z"};
  for (const id of ids) {
    const Widget = registry.get(`salah-widget-${id}`);
    assert.ok(Widget, id);
    assert.equal(Widget.getStubConfig(hass()).type, `custom:salah-widget-${id}`);
    const card = new Widget(); card.setConfig({entity: "sensor.mosque_prayer_timetable", detail_level: "compact"}); card.hass = hass(data);
    card._render(Date.parse("2026-10-21T03:00:00Z"));
    if (!["mosque-selector", "jamaat-changes", "timetable-health"].includes(id)) assert.deepEqual(arrangedSections(card).map(item => item.attributes["data-section"]), [id.replaceAll("-", "_")]);
    assert.equal(find(card.shadowRoot, "table").length, id === "timetable" ? 1 : 0);
  }
});
test("standalone clock uses the host tick and conditional widgets explain inactive data", () => {
  const Clock = registry.get("salah-widget-clock");
  const clock = new Clock(); clock.setConfig({entity: "sensor.mosque_prayer_timetable"}); clock.hass = hass();
  clock._render(Date.parse("2026-10-21T03:00:00Z"));
  const time = find(clock.shadowRoot, "time")[0];
  assert.equal(time.textContent, "04:00");
  clock._tick(Date.parse("2026-10-21T03:01:00Z"));
  assert.equal(time.textContent, "04:01");
  for (const [id, message] of [["ramadan", "Ramadan"], ["night-calculations", "night"]]) {
    const Widget = registry.get(`salah-widget-${id}`); const card = new Widget();
    card.setConfig({entity: "sensor.mosque_prayer_timetable"}); card.hass = hass();
    assert.ok(card.shadowRoot.textContent.includes(message));
    assert.equal(arrangedSections(card).length, 1);
  }
});
test("custom kiosk keeps fullscreen fixed and puts day navigation inside the movable timetable", () => {
  const card = new SalahTimetableCard();
  card.setConfig({entity: "sensor.mosque_prayer_timetable", kiosk_mode: true, arrangement: {sections: [{id: "clock", width: "full"}, {id: "timetable", width: "full"}]}});
  card.hass = hass(widgetAttributes());
  const sections = arrangedSections(card);
  assert.equal(sections[0].attributes["data-section"], "clock");
  const table = sections.find(item => item.attributes["data-section"] === "timetable");
  assert.ok(find(table, "nav").some(item => item.className.includes("date-tabs")));
  assert.equal(find(card.shadowRoot, "button").filter(item => item.className === "kiosk-fullscreen").length, 1);
  assert.ok(find(card.shadowRoot, "div").some(item => item.className === "arrangement-toolbar"));
});
test("main editor offers a live isolated Layout tab and Reset removes saved placement", () => {
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "house"}); editor.hass = hass();
  const tab = find(editor.shadowRoot, "button").find(item => item.attributes["data-editor-tab"] === "layout");
  tab.dispatchEvent(new Event("click"));
  assert.ok(editor._layoutRoot);
  const preview = find(editor._layoutRoot, "custom-element").find(item => item instanceof SalahTimetableCard);
  assert.ok(preview?.preview);
  assert.equal(preview._config.selection_group, "");
  const preset = find(editor._layoutRoot, "select").find(item => item.attributes["data-layout-preset"] !== undefined);
  preset.value = "balanced"; preset.dispatchEvent(new Event("change"));
  assert.ok(editor._config.arrangement);
  const reset = find(editor._layoutRoot, "button").find(item => item.attributes["data-layout-reset"] !== undefined);
  reset.dispatchEvent(new Event("click"));
  assert.equal(editor._config.arrangement, undefined);
  assert.equal(editor._config.selection_group, "house");
  editor.disconnectedCallback();
  assert.equal(editor._layoutRoot, null);
});


test("hiding the timetable cancels adjacent-day and monthly browsing so live panels remain reachable", () => {
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable", show_month_view: true}); card.hass = hass(widgetAttributes());
  card._selectedDay = 1; card._monthView = true; card._monthState = {loading: true};
  const request = card._monthRequest;
  card.setConfig({...card._config, show_timetable: false, arrangement: {sections: [{id: "salah", width: "full"}]}});
  assert.equal(card._selectedDay, 0);
  assert.equal(card._monthView, false);
  assert.equal(card._monthState, null);
  assert.ok(card._monthRequest > request);
  assert.ok(arrangedSections(card).some(item => item.attributes["data-section"] === "salah"));
});
test("standalone widgets and custom arrangements use automatic Sections dashboard height", () => {
  const Health = registry.get("salah-widget-timetable-health");
  const widget = new Health(); widget.setConfig({entity: "sensor.mosque_prayer_timetable"});
  assert.equal(widget.getGridOptions().rows, "auto");
  assert.equal(widget.getGridOptions().min_rows, 1);
  const card = new SalahTimetableCard(); card.setConfig({entity: "sensor.mosque_prayer_timetable"});
  assert.equal(typeof card.getGridOptions().rows, "number");
  card.setConfig({...card._config, arrangement: {sections: []}});
  assert.equal(card.getGridOptions().rows, "auto");
});
test("custom widget identity uses a saved title only for the primary mosque", () => {
  const primary = "sensor.mosque_prayer_timetable", other = "sensor.other_prayer_timetable";
  const state = hass(widgetAttributes());
  state.states[other] = {state: attributes.date, attributes: {...widgetAttributes(), mosque_name: "Other mosque"}};
  for (const type of ["custom:salah-widget-salah", "custom:salah-timetable-card"]) {
    const Card = type.endsWith("widget-salah") ? registry.get("salah-widget-salah") : SalahTimetableCard;
    const card = new Card();
    card.setConfig({type, entity: primary, title: "Home", show_mosque_selector: false, arrangement: {sections: []}});
    card.hass = state;
    const identity = () => {
      const label = find(card.shadowRoot, "div").find(item => item.className === "widget-mosque-name");
      if (label) return label.textContent;
      const chooser = find(card.shadowRoot, "select").find(item => item.className === "mosque-select");
      if (chooser) return find(chooser, "option").find(item => item.value === chooser.value)?.textContent;
      return find(card.shadowRoot, "h2")[0]?.textContent;
    };
    assert.equal(identity(), "Home");
    card._selectMosque(other); card._render();
    assert.equal(identity(), "Other mosque");
  }
});
test("Jamaat-change widgets honor bilingual prayer labels and direction metadata", () => {
  const Changes = registry.get("salah-widget-jamaat-changes");
  const card = new Changes(); card.setConfig({entity: "sensor.mosque_prayer_timetable", language: "en"});
  card.hass = hass(widgetAttributes());
  assert.ok(!card.shadowRoot.textContent.includes("الفجر"));
  card.setConfig({...card._config, bilingual_prayer_labels: true});
  assert.ok(card.shadowRoot.textContent.includes("Fajr / الفجر"));
  assert.ok(find(card.shadowRoot, "span").some(item => item.attributes.lang === "ar" && item.attributes.dir === "rtl"));
});
test("arrangement validation uses localized messages and tab navigation has one keyboard stop", () => {
  for (const language of ["en", "ar"]) {
    const card = new SalahTimetableCard();
    for (const invalid of [{arrangement: {sections: [{id: "unknown", width: "full"}]}}, {selection_group: 42}, {type: "custom:unknown"}]) {
      assert.throws(() => card.setConfig({...invalid, language}), error => !error.message.startsWith("config.") && (language === "en" || /[\u0600-\u06ff]/.test(error.message)));
    }
  }
  const editor = new SalahTimetableCardEditor(); editor.setConfig({entity: "sensor.mosque_prayer_timetable"}); editor.hass = hass();
  assert.ok(editor._sections.history.body.children.some(item => item.className === "editor-soon-note"));
  let focused = null;
  for (const [id, button] of Object.entries(editor._tabButtons)) button.focus = () => { focused = id; };
  assert.equal(editor._tabButtons.settings.tabIndex, 0);
  assert.equal(editor._tabButtons.layout.tabIndex, -1);
  const right = new Event("keydown", {cancelable: true}); Object.defineProperty(right, "key", {value: "ArrowRight"});
  editor._tabButtons.settings.dispatchEvent(right);
  assert.equal(editor._activeTab, "layout"); assert.equal(focused, "layout");
  assert.equal(editor._tabButtons.settings.tabIndex, -1);
  assert.equal(editor._tabButtons.layout.tabIndex, 0);
  const home = new Event("keydown", {cancelable: true}); Object.defineProperty(home, "key", {value: "Home"});
  editor._tabButtons.layout.dispatchEvent(home);
  assert.equal(editor._activeTab, "settings"); assert.equal(focused, "settings");
  editor.disconnectedCallback();
});

test("linked standalone widgets share mosque choice without repeated dropdowns", () => {
  const state = hass(widgetAttributes());
  state.states["sensor.other_prayer_timetable"] = {state: attributes.date, attributes: {...widgetAttributes(), mosque_name: "Other mosque"}};
  const Health = registry.get("salah-widget-timetable-health");
  const Selector = registry.get("salah-widget-mosque-selector");
  const linked = new Health();
  linked.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "home"});
  linked.hass = state;
  assert.equal(find(linked.shadowRoot, "select").length, 0);
  assert.ok(find(linked.shadowRoot, "h2").some(item => item.textContent === "Example Mosque"));
  assert.equal(linked.hasAttribute("data-standalone"), true);
  const separate = new Health();
  separate.setConfig({entity: "sensor.mosque_prayer_timetable"});
  separate.hass = state;
  assert.ok(find(separate.shadowRoot, "select").length > 0);
  const central = new Selector();
  central.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "home"});
  central.hass = state;
  assert.ok(find(central.shadowRoot, "select").length > 0);
  const main = new SalahTimetableCard();
  main.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "home"});
  main.hass = state;
  assert.ok(find(main.shadowRoot, "select").length > 0);
});

test("Advanced makes mosque synchronisation opt-in and retains existing groups", () => {
  const editor = new SalahTimetableCardEditor();
  editor.setConfig({entity: "sensor.mosque_prayer_timetable"}); editor.hass = hass();
  assert.ok(find(editor._sections.advanced.body, "ha-switch").includes(editor._groupSyncControl));
  assert.ok(find(editor._sections.advanced.body, "input").includes(editor._groupControl));
  assert.equal(editor._groupSyncControl.checked, false);
  assert.equal(editor._groupNameField.hidden, true);
  editor._groupSyncControl.checked = true;
  editor._groupSyncControl.dispatchEvent(new Event("change"));
  assert.equal(editor._config.selection_group, "home");
  assert.equal(editor._groupNameField.hidden, false);
  editor._groupControl.value = "kitchen"; editor._groupControl.dispatchEvent(new Event("change"));
  assert.equal(editor._config.selection_group, "kitchen");
  editor._groupSyncControl.checked = false; editor._groupSyncControl.dispatchEvent(new Event("change"));
  assert.equal(editor._config.selection_group, "");
  editor.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "legacy-linked"});
  assert.equal(editor._groupSyncControl.checked, true);
  assert.equal(editor._groupControl.value, "legacy-linked");
});

test("all other standalone sections retain a chooser only when independent", () => {
  const state = hass(widgetAttributes());
  state.states["sensor.other_prayer_timetable"] = {state: attributes.date, attributes: {...widgetAttributes(), mosque_name: "Other mosque"}};
  for (const id of ["dates", "clock", "salah", "jamaat", "timetable", "ramadan", "night-calculations"]) {
    const Card = registry.get(`salah-widget-${id}`);
    const unlinked = new Card();
    unlinked.setConfig({entity: "sensor.mosque_prayer_timetable"});
    unlinked.hass = state;
    assert.ok(find(unlinked.shadowRoot, "select").length > 0, `${id} allows independent choice`);
    const linked = new Card();
    linked.setConfig({entity: "sensor.mosque_prayer_timetable", selection_group: "home"});
    linked.hass = state;
    assert.equal(find(linked.shadowRoot, "select").length, 0, `${id} follows linked choice`);
  }
});
