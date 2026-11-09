/** Browser setup shared by native widget assertions in browser-smoke.mjs. */

const FIELD_TIMES = [
  ["fajr", "05:10", "05:40"], ["dhuhr", "12:10", "13:10"],
  ["asr", "15:10", "15:40"], ["maghrib", "17:10", "17:15"],
  ["isha", "19:10", "19:40"],
];

function nextDate(day, offset) {
  return new Date(Date.parse(`${day}T12:00:00Z`) + offset * 86400000).toISOString().slice(0, 10);
}

function attributes(name, today, offset = 0) {
  const tomorrow = nextDate(today, 1);
  const stamp = (day, value, extra = 0) => new Date(Date.parse(`${day}T${value}:00Z`) + (offset + extra) * 60000).toISOString();
  const prayers = day => FIELD_TIMES.map(([key, begin, jamaat]) => ({
    key, name: key, begin: stamp(day, begin), jamaat: [stamp(day, jamaat, day === tomorrow && key === "asr" ? 10 : 0)],
  }));
  const todayRows = prayers(today);
  const tomorrowRows = prayers(tomorrow);
  const events = kind => [...todayRows, ...tomorrowRows].flatMap(row => {
    const values = kind === "jamaat" ? row.jamaat : [row.begin];
    return values.map(timestamp => ({timestamp, field: `${row.key}_${kind === "jamaat" ? "jamaat" : "begin"}`, prayer: row.key}));
  });
  return {
    mosque_name: name, date: today, time_zone: "UTC", show_hijri_date: true,
    config_entry_id: `entry_${offset}`, prayers: todayRows,
    day_prayers: {[today]: todayRows, [tomorrow]: tomorrowRows},
    beginning_events: events("begin"), jamaat_events: events("jamaat"),
    next_salah: {timestamp: todayRows[0].begin, prayer: "fajr", field: "fajr_begin"},
    next_jamaat: {timestamp: todayRows[0].jamaat[0], prayer: "fajr", field: "fajr_jamaat"},
    ramadan: {active: false},
    night_calculations: {midpoint: stamp(today, "23:10"), last_third: stamp(tomorrow, "01:10"), method: "published_maghrib_to_next_fajr"},
    timetable_health: {
      coverage: {status: "covered", today_available: true, tomorrow_available: true, available_through: nextDate(today, 31), days_remaining: 31, warning_days: 7, unresolved_date: null},
      completeness: {status: "complete", required_fields: ["fajr_begin", "dhuhr_begin", "asr_begin", "maghrib_begin", "isha_begin"], missing_today: [], missing_tomorrow: [], complete_days_remaining: 31, first_incomplete_date: nextDate(today, 32), unresolved_date: null},
      // Pending manual imports must remain visible without a configured URL.
      source: {status: "not_configured", configured_sources: 0, pending_review: true, error_count: 0, last_checked: null, last_success: null},
    },
  };
}

export function mountWidgetFixture({language = "en", bilingual = false} = {}) {
  const day = new Date().toISOString().slice(0, 10);
  const now = Date.parse(`${day}T00:00:00Z`);
  const first = "sensor.widget_first_prayer_timetable";
  const second = "sensor.widget_second_prayer_timetable";
  const firstData = attributes("First Example Mosque", day);
  const secondData = attributes("Second Example Mosque", day, 20);
  const view = document.createElement("hui-view");
  view.style.cssText = "display:block;width:100%;min-width:0";
  document.body.append(view);
  const cards = [];
  const editors = [];
  const hass = {
    states: {[first]: {state: day, attributes: firstData}, [second]: {state: day, attributes: secondData}},
    language, locale: {language}, user: {is_admin: true},
    config: {time_zone: "UTC"}, connection: {connected: true},
    callService() { throw new Error("Widgets must not write timetable state"); },
  };
  const base = {entity: first, mosque_entities: [first, second], language, bilingual_prayer_labels: bilingual, show_mosque_background: false};
  function mount(type, config = {}, container = view) {
    const card = document.createElement(type);
    card.setConfig({...base, ...config, type: `custom:${type}`});
    card.hass = hass;
    container.append(card);
    window.clearInterval(card._timer);
    card._render(now);
    cards.push(card);
    return card;
  }
  const group = "browser-status-widgets";
  const selector = mount("salah-widget-mosque-selector", {selection_group: group});
  const changes = mount("salah-widget-jamaat-changes", {selection_group: group});
  const health = mount("salah-widget-timetable-health", {selection_group: group});
  function mountEditor(config = {}) {
    const editor = document.createElement("salah-timetable-card-editor");
    const state = {editor, config: {...base, type: "custom:salah-timetable-card", ...config}, changes: []};
    editor.setConfig(state.config);
    editor.hass = hass;
    editor.addEventListener("config-changed", event => {
      state.config = event.detail.config;
      state.changes.push(event.detail.config);
      editor.setConfig(event.detail.config);
    });
    view.append(editor);
    editors.push(editor);
    return state;
  }
  return {
    view, cards, hass, base, now, first, second, selector, changes, health, mount, mountEditor,
    select(entity) {
      const control = selector.shadowRoot.querySelector(".mosque-select");
      control.value = entity;
      control.dispatchEvent(new Event("change", {bubbles: true}));
    },
    destroy() {
      for (const editor of editors) editor.remove();
      for (const card of cards) card.remove();
      view.remove();
    },
  };
}
