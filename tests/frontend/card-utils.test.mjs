import test from "node:test";
import assert from "node:assert/strict";
import {countdown, duration, elapsed, formatDate, formatHijriDate, formatTime, isTimetableState, jamaatPanel, nextSalah, normalizeConfig, prayerName, timestamp, discoverEntity, discoverTimetableEntities, nextRamadanEvent, publishedTimes} from "../../custom_components/salah_timetable/frontend/card-utils.js";
import {resolveUi} from "../../custom_components/salah_timetable/frontend/card-i18n.js";

const instant = value => Date.parse(`2026-10-21T${value}:00Z`);
const event = (time, prayer, field = `${prayer}_jamaat`) => ({timestamp: `2026-10-21T${time}:00Z`, prayer, field});
const data = {
  mosque_name: "Example Mosque", date: "2026-10-21", time_zone: "Europe/London",
  prayers: [
    {key: "fajr", name: "Fajr", begin: event("05:00", "fajr").timestamp, jamaat: [event("05:30", "fajr").timestamp]},
    {key: "dhuhr", name: "Dhuhr", begin: event("12:00", "dhuhr").timestamp, jamaat: [event("12:30", "dhuhr").timestamp]},
    {key: "asr", name: "Asr", begin: event("15:00", "asr").timestamp, jamaat: [event("15:30", "asr").timestamp]},
    {key: "maghrib", name: "Maghrib", begin: event("17:00", "maghrib").timestamp, jamaat: [event("17:05", "maghrib").timestamp]},
    {key: "isha", name: "Isha", begin: event("19:00", "isha").timestamp, jamaat: [event("19:30", "isha").timestamp]},
  ],
  previous_jamaat: {timestamp: "2026-10-20T19:30:00Z", prayer: "isha", field: "isha_jamaat"},
  next_salah: {timestamp: "2026-10-22T05:03:00Z", prayer: "fajr", field: "fajr_begin"},
};

for (const [clock, mode, prayer, nextPrayer] of [
  ["04:59", "previous", "isha", "fajr"],
  ["05:00", "upcoming", "fajr", "dhuhr"],
  ["05:29", "upcoming", "fajr", "dhuhr"],
  ["05:30", "previous", "fajr", "dhuhr"],
  ["12:00", "upcoming", "dhuhr", "asr"],
  ["12:30", "previous", "dhuhr", "asr"],
  ["15:00", "upcoming", "asr", "maghrib"],
  ["15:30", "previous", "asr", "maghrib"],
  ["17:00", "upcoming", "maghrib", "isha"],
  ["17:05", "previous", "maghrib", "isha"],
  ["19:00", "upcoming", "isha", "fajr"],
  ["19:30", "previous", "isha", "fajr"],
]) {
  test(`context at ${clock} treats Jamaat as one event`, () => {
    const result = jamaatPanel(data, "context", instant(clock));
    assert.equal(result.mode, mode); assert.equal(result.event.prayer, prayer);
    assert.equal(nextSalah(data, instant(clock)).prayer, nextPrayer);
  });
}

test("independent previous/upcoming modes and tomorrow's actual Fajr", () => {
  assert.equal(jamaatPanel(data, "previous", instant("05:01")).event.prayer, "isha");
  assert.equal(jamaatPanel(data, "upcoming", instant("04:59")).event.prayer, "fajr");
  assert.equal(nextSalah(data, instant("22:00")).timestamp, "2026-10-22T05:03:00Z");
  assert.equal(nextSalah({...data, next_salah: null}, instant("22:00")), null);
});

test("Friday event metadata preserves both congregations and their names", () => {
  const friday = {...data, jamaat_events: [event("12:30", "jumuah", "jumuah"), event("13:30", "jumuah", "jumuah")]};
  assert.equal(jamaatPanel(friday, "context", instant("12:05")).event.prayer, "jumuah");
  assert.equal(jamaatPanel(friday, "context", instant("12:30")).event.timestamp, event("13:30", "jumuah").timestamp);
  assert.equal(jamaatPanel(friday, "context", instant("15:01")).event.prayer, "asr");
});

test("absolute timezone offsets compare by instant, including DST", () => {
  assert.equal(timestamp("2026-10-25T01:30:00+01:00"), Date.parse("2026-10-25T00:30:00Z"));
  assert.equal(formatTime("2026-10-25T00:30:00Z", "Europe/London", "en-GB"), "01:30");
  assert.equal(formatTime("2026-10-25T01:30:00Z", "Europe/London", "en-GB"), "01:30");
  assert.equal(timestamp("2026-10-25T01:30:00"), null);
});

test("countdowns and elapsed values have exact event boundaries", () => {
  assert.equal(countdown("2026-10-21T05:30:00Z", instant("05:29")), "00:01:00");
  assert.equal(countdown("2026-10-21T05:30:00Z", instant("05:30")), "00:00:00");
  assert.equal(countdown("2026-10-21T05:30:00Z", instant("05:31")), "Passed");
  assert.equal(elapsed("2026-10-21T05:30:00Z", instant("05:31")), "00:01:00");
  assert.equal(elapsed("2026-10-21T05:30:00Z", instant("05:29")), "Unavailable");
  assert.equal(duration(90061000), "1d 01:01:01");
});

test("missing/malformed values remain unavailable", () => {
  assert.equal(countdown(null), "Unavailable"); assert.equal(formatTime("bad"), "—");
  assert.equal(formatTime(event("05:00", "fajr").timestamp, "Mars/Invalid"), "—");
  assert.equal(formatDate("2026-02-30"), "Date unavailable");
  assert.deepEqual(jamaatPanel({prayers: [null, {}, {key: "fajr", begin: null, jamaat: []}]}, "context", instant("05:00")), {mode: "previous", event: null});
  assert.equal(nextSalah({prayers: []}, instant("05:00")), null);
});

test("configuration validates modes/entities while allowing graphical setup", () => {
  assert.equal(normalizeConfig({}).detail_level, "standard");
  assert.equal(normalizeConfig({mode: "interval"}).detail_level, "standard");
  assert.throws(() => normalizeConfig({entity: "light.example"}));
  assert.throws(() => normalizeConfig({title: "a".repeat(101)}));
  const hass = {states: {"sensor.other": {attributes: {}}, "sensor.mosque": {attributes: data}}};
  assert.equal(discoverEntity(hass), "sensor.mosque"); assert.equal(isTimetableState(hass.states["sensor.other"]), false);
});


test("tomorrow's earlier congregation never becomes today's context", () => {
  const incomplete = {time_zone: "UTC", prayers: [{key: "fajr", begin: "2026-10-21T05:00:00Z", jamaat: ["2026-10-21T05:30:00Z"]}], next_jamaat: {timestamp: "2026-10-22T04:30:00Z", prayer: "fajr"}};
  assert.equal(jamaatPanel(incomplete, "context", instant("20:00")).mode, "previous");
  assert.equal(jamaatPanel(incomplete, "context", instant("20:00")).event.timestamp, "2026-10-21T05:30:00Z");
});


test("an older late congregation cannot hide the current prayer's Jamaat", () => {
  const overlaps = {...data, jamaat_events: [event("15:05", "jumuah", "jumuah"), event("15:30", "asr")]};
  assert.equal(jamaatPanel(overlaps, "upcoming", instant("15:01")).event.prayer, "jumuah");
  assert.equal(jamaatPanel(overlaps, "context", instant("15:01")).event.prayer, "asr");
});

test("Ramadan countdowns advance to an actual next-day event at the boundary", () => {
  const attrs = {ramadan: {sehri: "2026-10-21T04:30:00Z", iftar: "2026-10-21T17:00:00Z"}, sehri_events: [{timestamp: "2026-10-21T04:30:00Z"}, {timestamp: "2026-10-22T04:32:00Z"}]};
  assert.equal(nextRamadanEvent(attrs, "sehri", instant("04:30")), "2026-10-22T04:32:00Z");
  assert.equal(nextRamadanEvent(attrs, "iftar", instant("04:30")), "2026-10-21T17:00:00Z");
});


test("published Ramadan times remain visible after the last confirmed day's events", () => {
  const attrs = {ramadan: {active: true, sehri: "2026-10-21T04:30:00Z", iftar: "2026-10-21T17:00:00Z"}, next_sehri: null, next_iftar: null, sehri_events: [], iftar_events: []};
  for (const kind of ["sehri", "iftar"]) {
    const value = nextRamadanEvent(attrs, kind, instant("20:00"));
    assert.equal(value, attrs.ramadan[kind]);
    assert.equal(countdown(value, instant("20:00")), "Passed");
    assert.notEqual(formatTime(value, "Europe/London"), "—");
  }
});

test("Arabic countdowns localize digits, days and statuses at exact boundaries", () => {
  const ui = resolveUi(normalizeConfig({}), {locale: {language: "ar-EG"}});
  const value = "2026-10-21T05:30:00Z";
  assert.equal(duration(90061000, ui), "١ يوم ٠١:٠١:٠١");
  assert.equal(countdown(value, instant("05:29"), ui), "٠٠:٠١:٠٠");
  assert.equal(countdown(value, instant("05:30"), ui), "٠٠:٠٠:٠٠");
  assert.equal(countdown(value, instant("05:31"), ui), "انقضى");
  assert.equal(elapsed(value, instant("05:31"), ui), "٠٠:٠١:٠٠");
  for (const unavailable of [duration(NaN, ui), countdown(null, instant("05:30"), ui), elapsed(value, instant("05:29"), ui)]) assert.equal(unavailable, "غير متاح");
  assert.equal(prayerName(event("05:30", "fajr"), ui), "الفجر");
  assert.equal(prayerName({field: "jumuah_jamaat"}, ui), "الجمعة");
  assert.equal(prayerName(null, ui), "غير متاح");
  assert.equal(prayerName({prayer: "unknown"}, ui), "الصلاة");
});

test("automatic French locale retains English UI while formatting published dates in French", () => {
  const ui = resolveUi(normalizeConfig({}), {locale: {language: "fr-FR"}});
  assert.equal(ui.language, "en");
  assert.equal(ui.locale, "fr-FR");
  assert.equal(formatDate("2026-10-21", ui), "mercredi 21 octobre 2026");
  assert.equal(duration(90061000, ui), "1d 01:01:01");
  assert.equal(countdown(null, instant("05:30"), ui), "Unavailable");
  const invalidUi = resolveUi(normalizeConfig({}), {locale: {language: "bad_locale!"}});
  assert.deepEqual(invalidUi, {language: "en", locale: "en", dir: "ltr"});
  assert.notEqual(formatDate("2026-10-21", invalidUi), "Date unavailable");
  assert.equal(formatTime(event("05:00", "fajr").timestamp, "UTC", invalidUi), "05:00");
});

test("configuration errors preserve English messages with localization metadata", () => {
  const cases = [
    [null, "required", "A card configuration is required"],
    [{detail_level: "invalid"}, "detail_level", "Choose compact, standard or detailed card display"],
    [{entity: "light.example"}, "entity", "Choose a timetable sensor"],
    [{title: "a".repeat(101)}, "title", "Title must be at most 100 characters"],
    [{detail_level: "tiny"}, "detail_level", "Choose compact, standard or detailed card display"],
    [{time_format: "auto"}, "time_format", "Choose 12h or 24h time format"],
    [{hijri_adjustment: 4}, "hijri_adjustment", "Hijri adjustment must be a whole day from −3 to +3"],
    [{language: "fr"}, "language", "Choose auto, en or ar language"],
    [{show_hijri_date: "false"}, "boolean", "show_hijri_date must be true or false", {option: "show_hijri_date"}],
    [{bilingual_prayer_labels: "true"}, "boolean", "bilingual_prayer_labels must be true or false", {option: "bilingual_prayer_labels"}],
  ];
  for (const [config, key, message, params = {}] of cases) assert.throws(() => normalizeConfig(config), error => {
    assert.equal(error.message, message);
    assert.equal(error.translationKey, `config.${key}`);
    assert.deepEqual(error.params, params);
    return true;
  });
});

test("discovery lists each mosque dashboard sensor but no individual prayer sensor", () => {
  const hass = {states: {
    "sensor.second_prayer_timetable": {attributes: {...data, mosque_name: "Second Mosque"}},
    "sensor.example_prayer_timetable": {attributes: {...data, mosque_name: "Example Mosque"}},
    "sensor.example_fajr_beginning": {state: "2026-10-21T04:45:00Z", attributes: {}},
    "binary_sensor.other": {attributes: {...data, mosque_name: "Not a mosque sensor"}},
  }};
  assert.deepEqual(discoverTimetableEntities(hass), [
    {entity: "sensor.example_prayer_timetable", name: "Example Mosque"},
    {entity: "sensor.second_prayer_timetable", name: "Second Mosque"},
  ]);
  assert.equal(discoverEntity(hass), "sensor.example_prayer_timetable");
  assert.deepEqual(discoverTimetableEntities({states: {}}), []);
});


test("Hijri date uses an Islamic month and AH era rather than Gregorian BC", () => {
  const value = formatHijriDate("2026-10-27", 0, resolveUi({language: "en"}, {locale: {language: "en-GB"}}));
  assert.match(value, /1448/);
  assert.doesNotMatch(value, /\b(?:BC|BCE|October|May)\b/i);
  assert.match(value, /\b(?:AH|Muharram|Safar|Rabi|Jumada|Rajab|Shaban|Sha.ban|Ramadan|Shawwal|Dhu)\b/i);
});


test("next-day Fajr panel uses its dated beginning, Jamaat and sunrise, never today's row", () => {
  const today = {key: "fajr", begin: "2026-10-27T04:58:00Z", jamaat: ["2026-10-27T06:15:00Z"], end: "2026-10-27T06:53:00Z"};
  const tomorrow = {key: "fajr", begin: "2026-10-28T04:59:00Z", jamaat: ["2026-10-28T06:16:00Z"], end: "2026-10-28T06:55:00Z"};
  const attrs = {
    prayers: [today],
    day_prayers: {"2026-10-27": [today], "2026-10-28": [tomorrow]},
    next_salah: {prayer: "fajr", field: "fajr_begin", timestamp: tomorrow.begin},
  };
  const next = nextSalah(attrs, Date.parse("2026-10-27T20:00:00Z"));
  assert.equal(next.timestamp, tomorrow.begin);
  assert.deepEqual(publishedTimes(attrs, next), {begin: tomorrow.begin, jamaat: tomorrow.jamaat[0], end: tomorrow.end});
  assert.deepEqual(publishedTimes({...attrs, day_prayers: {}}, next), {begin: tomorrow.begin, jamaat: null, end: null});
  assert.deepEqual(publishedTimes(attrs, null), {begin: null, jamaat: null, end: null});
});

test("Jamaat card switches at the exact published Isha boundary", () => {
  const attrs = {time_zone: "Europe/London", prayers: [
    {key: "maghrib", begin: "2026-10-27T16:46:00Z", jamaat: ["2026-10-27T16:49:00Z"]},
    {key: "isha", begin: "2026-10-27T18:41:00Z", jamaat: ["2026-10-27T20:00:00Z"]},
  ]};
  const before = jamaatPanel(attrs, "context", Date.parse("2026-10-27T19:59:59Z"));
  assert.equal(before.mode, "upcoming");
  assert.equal(before.event.prayer, "isha");
  assert.equal(countdown(before.event.timestamp, Date.parse("2026-10-27T19:59:59Z")), "00:00:01");
  assert.deepEqual(publishedTimes(attrs, before.event, true), {begin: attrs.prayers[1].begin, jamaat: attrs.prayers[1].jamaat[0], end: null});
  const after = jamaatPanel(attrs, "context", Date.parse("2026-10-27T20:00:00Z"));
  assert.equal(after.mode, "previous");
  assert.equal(after.event.prayer, "isha");
  assert.equal(elapsed(after.event.timestamp, Date.parse("2026-10-27T20:00:00Z")), "00:00:00");
});

test("Friday Jamaat displays the specifically selected congregation", () => {
  const row = {key: "dhuhr", begin: "2026-10-23T11:50:00Z", jamaat: ["2026-10-23T12:15:00Z", "2026-10-23T13:15:00Z"]};
  const attrs = {prayers: [row]};
  const event = {prayer: "jumuah", field: "jumuah_jamaat", timestamp: row.jamaat[1]};
  assert.deepEqual(publishedTimes(attrs, event, true), {begin: row.begin, jamaat: row.jamaat[1], end: null});
  assert.deepEqual(publishedTimes({prayers: []}, event, true), {begin: null, jamaat: event.timestamp, end: null});
});
