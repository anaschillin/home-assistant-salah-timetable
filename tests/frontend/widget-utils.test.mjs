import test from "node:test";
import assert from "node:assert/strict";
import {normalizeConfig} from "../../custom_components/salah_timetable/frontend/card-utils.js";
import {SECTIONS, SECTION_IDS, WIDGET_TYPES, widgetSection, widgetType, normalizeArrangement, sectionVisible, applyPreset, resetArrangement, jamaatChanges} from "../../custom_components/salah_timetable/frontend/widget-utils.js";

const event = (day, clock, field = "fajr_jamaat", offset = "Z") => ({timestamp: `${day}T${clock}:00${offset}`, field, prayer: field === "jumuah" ? "jumuah" : field.replace("_jamaat", "")});
const fixture = (today = "2026-10-21", tomorrow = "2026-10-22") => ({date: today, time_zone: "UTC", day_prayers: {[today]: [], [tomorrow]: []}, jamaat_events: [event(today, "05:30"), event(tomorrow, "05:30")], timetable_health: {completeness: {required_fields: ["fajr_begin", "fajr_jamaat"]}}});

test("legacy config keeps widgets opt-in and standalone types retain their identity", () => {
  const config = normalizeConfig({layout: "compact"});
  assert.equal(config.detail_level, "compact");
  assert.equal(config.arrangement, undefined);
  assert.equal(config.show_jamaat_changes, false);
  assert.equal(config.show_timetable_health, false);
  assert.equal(config.show_clock, false);
  assert.equal(config.show_dates, false);
  assert.equal(config.show_timetable, false);
  assert.equal(normalizeConfig({kiosk_mode: true, detail_level: "compact"}).show_clock, true);
  for (const id of SECTION_IDS) {
    const single = normalizeConfig({type: widgetType(id)});
    assert.equal(single.type, widgetType(id));
    assert.equal(widgetSection(single), id);
    assert.equal(single.show_mosque_background, false);
    assert.equal(sectionVisible(single, id), true);
    assert.equal(sectionVisible(single, SECTION_IDS.find(other => other !== id)), false);
  }
  assert.equal(Object.keys(WIDGET_TYPES).length, 10);
  assert.equal(normalizeConfig({type: widgetType("clock"), show_mosque_background: true}).show_mosque_background, true);
  assert.equal(widgetSection("toString"), null);
  assert.throws(() => normalizeConfig({type: "custom:unknown"}));
  assert.throws(() => normalizeConfig({type: "toString"}));
});

test("arrangements append omitted positions without mutating supplied ordering", () => {
  const source = {sections: [{id: "timetable", width: "half"}, {id: "dates", width: "full"}]};
  const before = structuredClone(source);
  const result = normalizeArrangement(source);
  assert.deepEqual(result.sections.slice(0, 2), source.sections);
  assert.deepEqual(result.sections.slice(2).map(section => section.id), SECTION_IDS.filter(id => !["timetable", "dates"].includes(id)));
  assert.deepEqual(source, before);
  assert.deepEqual(normalizeArrangement(result), result);
  assert.deepEqual(normalizeConfig({arrangement: source}).arrangement, result);
});

test("invalid arrangement structure, duplicates and widths have actionable errors", () => {
  for (const arrangement of [null, [], {}, {sections: null}, {sections: [null]}, {sections: [{id: "unknown", width: "full"}]}, {sections: [{id: "dates", width: "wide"}]}, {sections: [{id: "dates", width: "full"}, {id: "dates", width: "half"}]}]) {
    assert.throws(() => normalizeConfig({arrangement}), error => error.translationKey === "config.arrangement");
  }
  assert.equal(normalizeArrangement(undefined), undefined);
});

test("new flags validate booleans and groups normalize as bounded strings", () => {
  for (const option of ["show_mosque_selector", "show_dates", "show_clock", "show_timetable", "show_jamaat_changes", "show_timetable_health"]) {
    for (const invalid of ["true", null, 1]) assert.throws(() => normalizeConfig({[option]: invalid}), option);
    assert.equal(normalizeConfig({[option]: false})[option], false);
  }
  assert.equal(normalizeConfig({selection_group: "  upstairs  "}).selection_group, "upstairs");
  for (const selection_group of [null, 42, [], "x".repeat(101)]) assert.throws(() => normalizeConfig({selection_group}));
});

test("custom arrangements use explicit visibility even in Compact", () => {
  const legacy = normalizeConfig({detail_level: "compact", show_timetable: true, show_dates: true, show_night_calculations: true});
  for (const id of ["timetable", "dates", "night_calculations"]) assert.equal(sectionVisible(legacy, id), false);
  const custom = normalizeConfig({...legacy, arrangement: {sections: []}});
  for (const id of ["timetable", "dates", "night_calculations"]) assert.equal(sectionVisible(custom, id), true);
  assert.equal(sectionVisible({...custom, show_dates: false}, "dates"), false);
  assert.equal(sectionVisible(custom, "unknown"), false);
});

test("presets have fixed responsive order and leave unrelated preferences intact", () => {
  const config = normalizeConfig({entity: "sensor.home", language: "ar", show_iftar_countdown: false, show_hijri_date: false});
  const cases = {
    countdown: ["mosque_selector", "dates", "salah", "jamaat", "jamaat_changes"],
    balanced: ["mosque_selector", "dates", "salah", "jamaat", "timetable", "jamaat_changes", "timetable_health", "ramadan"],
    timetable_first: ["mosque_selector", "dates", "timetable", "salah", "jamaat", "jamaat_changes", "timetable_health", "ramadan"],
    ramadan: ["mosque_selector", "dates", "ramadan", "salah", "jamaat", "night_calculations", "timetable", "jamaat_changes", "timetable_health"],
    wall: ["mosque_selector", "clock", "dates", "salah", "jamaat", "timetable", "jamaat_changes", "timetable_health", "ramadan"],
  };
  for (const [name, visible] of Object.entries(cases)) {
    const result = applyPreset(config, name);
    assert.deepEqual(result.arrangement.sections.filter(section => sectionVisible(result, section.id)).map(section => section.id), visible);
    assert.equal(result.entity, "sensor.home");
    assert.equal(result.language, "ar");
    assert.equal(result.show_iftar_countdown, false);
    assert.equal(result.show_hijri_date, false);
    for (const section of result.arrangement.sections) assert.equal(section.width, ["salah", "jamaat"].includes(section.id) ? "half" : "full");
    assert.deepEqual(normalizeConfig(result), result);
  }
  assert.equal(applyPreset(config, "wall").kiosk_mode, true);
  assert.equal(config.arrangement, undefined);
  assert.throws(() => applyPreset(config, "holiday"));
});

test("reset restores current mode defaults without clearing card or sub-section choices", () => {
  const result = resetArrangement(applyPreset(normalizeConfig({entity: "sensor.home", detail_level: "compact", show_iftar_countdown: false, show_gregorian_date: false}), "ramadan"));
  assert.equal(result.arrangement, undefined);
  assert.equal(result.show_timetable, false);
  assert.equal(result.show_dates, false);
  assert.equal(result.show_jamaat_changes, false);
  assert.equal(result.show_timetable_health, false);
  assert.equal(result.show_night_calculations, false);
  assert.equal(result.entity, "sensor.home");
  assert.equal(result.show_iftar_countdown, false);
  assert.equal(result.show_gregorian_date, false);
  const wall = resetArrangement(applyPreset(normalizeConfig({}), "wall"));
  assert.equal(wall.kiosk_mode, true);
  assert.equal(wall.show_clock, true);
  assert.equal(SECTIONS.every(section => typeof wall[section.show] === "boolean"), true);
});

test("Jamaat changes distinguish earlier, later and unchanged published clocks", () => {
  for (const [time, delta, status] of [["05:20", -10, "changed"], ["05:45", 15, "changed"], ["05:30", 0, "unchanged"]]) {
    const attrs = fixture(); attrs.jamaat_events[1] = event("2026-10-22", time);
    const before = structuredClone(attrs);
    const result = jamaatChanges(attrs);
    assert.equal(result.status, status);
    assert.equal(result.changes[0].delta_minutes, delta);
    assert.deepEqual(attrs, before);
  }
});

test("DST and local-date boundaries never produce a 23/25-hour difference", () => {
  for (const [today, tomorrow, leftOffset, rightOffset] of [["2026-10-24", "2026-10-25", "+01:00", "+00:00"], ["2026-03-28", "2026-03-29", "+00:00", "+01:00"]]) {
    const attrs = fixture(today, tomorrow); attrs.time_zone = "Europe/London";
    attrs.jamaat_events = [event(today, "05:30", "fajr_jamaat", leftOffset), event(tomorrow, "05:30", "fajr_jamaat", rightOffset)];
    assert.equal(jamaatChanges(attrs).status, "unchanged");
    assert.equal(jamaatChanges(attrs).changes[0].delta_minutes, 0);
  }
  const attrs = fixture("2026-12-31", "2027-01-01"); attrs.time_zone = "Pacific/Auckland";
  attrs.jamaat_events = [event("2026-12-30", "16:30"), event("2026-12-31", "16:40")];
  assert.equal(jamaatChanges(attrs).changes[0].delta_minutes, 10);
});

test("missing comparison dates and missing required fields never mean unchanged", () => {
  const missing = fixture(); delete missing.day_prayers["2026-10-22"];
  assert.equal(jamaatChanges(missing).status, "unavailable");
  const partial = fixture(); partial.jamaat_events.pop();
  const result = jamaatChanges(partial);
  assert.equal(result.status, "incomplete");
  assert.equal(result.changes[0].delta_minutes, null);
  assert.deepEqual(result.changes[0].tomorrow, []);
  assert.equal(result.changes[0].status, "unavailable");
  partial.jamaat_events = [];
  assert.equal(jamaatChanges(partial).status, "incomplete");
  partial.timetable_health.completeness.required_fields = ["fajr_begin"];
  assert.equal(jamaatChanges(partial).status, "unavailable");
});

test("Friday sessions remain distinct from ordinary Dhuhr and Khutbah", () => {
  const attrs = fixture("2026-10-22", "2026-10-23");
  attrs.jamaat_events.push(event("2026-10-22", "13:00", "dhuhr_jamaat"), event("2026-10-23", "13:30", "jumuah"), event("2026-10-23", "12:30", "jumuah"), event("2026-10-23", "12:15", "khutbah"));
  const result = jamaatChanges(attrs);
  assert.equal(result.status, "incomplete", "Thursday Dhuhr and Friday Jumuah are distinct, not moved");
  assert.equal(result.changes.find(entry => entry.field === "dhuhr_jamaat").delta_minutes, null);
  const friday = result.changes.find(entry => entry.field === "jumuah");
  assert.deepEqual(friday.today, []);
  assert.deepEqual(friday.tomorrow, ["2026-10-23T12:30:00Z", "2026-10-23T13:30:00Z"]);
  assert.equal(friday.delta_minutes, null);
  assert.equal(result.changes.some(entry => entry.field === "khutbah"), false);
});

test("multiple congregations show lists without inventing identities or deltas", () => {
  const attrs = fixture();
  attrs.jamaat_events = [event("2026-10-21", "12:30", "jumuah"), event("2026-10-21", "13:30", "jumuah"), event("2026-10-22", "12:45", "jumuah"), event("2026-10-22", "13:30", "jumuah")];
  attrs.timetable_health.completeness.required_fields = ["fajr_begin"];
  const result = jamaatChanges(attrs);
  assert.equal(result.status, "changed");
  assert.equal(result.changes.length, 1);
  assert.equal(result.changes[0].delta_minutes, null);
});

test("invalid or duplicate events cannot create extra sessions or inferred changes", () => {
  const attrs = fixture();
  attrs.jamaat_events.push({...attrs.jamaat_events[0]}, null, {}, event("2026-10-20", "05:30"), {...attrs.jamaat_events[0], timestamp: "invalid"}, {...attrs.jamaat_events[0], timestamp: "2026-10-21T05:30:00"});
  assert.equal(jamaatChanges(attrs).status, "unchanged");
  assert.equal(jamaatChanges(attrs).changes[0].today.length, 1);
  for (const value of [undefined, {}, {...attrs, date: "2026-02-30"}, {...attrs, time_zone: "Invalid/Zone"}, {...attrs, date: "9999-12-31"}, {...attrs, jamaat_events: null}]) assert.equal(jamaatChanges(value).status, "unavailable");
});

test("one-sided optional Jamaat is not treated as a moved congregation", () => {
  const attrs = fixture();
  attrs.timetable_health.completeness.required_fields = ["fajr_begin"];
  attrs.jamaat_events.push(event("2026-10-21", "13:15", "dhuhr_jamaat"));
  const result = jamaatChanges(attrs);
  assert.equal(result.status, "incomplete");
  const dhuhr = result.changes.find(item => item.field === "dhuhr_jamaat");
  assert.equal(dhuhr.status, "unavailable");
  assert.equal(dhuhr.delta_minutes, null);
  assert.deepEqual(dhuhr.tomorrow, []);
});
