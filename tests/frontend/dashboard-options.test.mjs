import test from "node:test";
import assert from "node:assert/strict";
import {eventProgress, formatDate, formatHijriDate, formatTime, highlightedPrayer, normalizeConfig, prayerIsPast} from "../../custom_components/salah_timetable/frontend/card-utils.js";
import {resolveUi} from "../../custom_components/salah_timetable/frontend/card-i18n.js";
const stamp = clock => `2026-10-23T${clock}:00Z`;
const at = clock => Date.parse(stamp(clock));
const row = (key, begin, ...jamaat) => ({key, begin: stamp(begin), jamaat: jamaat.map(stamp)});
const data = {prayers: [row("fajr", "05:00", "05:30"), row("dhuhr", "12:00", "12:30", "13:30"), row("asr", "15:00", "15:30"), row("isha", "19:00", "19:30")]};

test("highlight crosses beginning and final congregation boundaries", () => {
  for (const [time, key] of [["04:00", "fajr"], ["05:00", "fajr"], ["05:29", "fajr"], ["05:30", "dhuhr"], ["12:30", "dhuhr"], ["13:30", "asr"], ["19:29", "isha"], ["19:30", null]]) assert.equal(highlightedPrayer(data, at(time)), key, time);
  assert.equal(prayerIsPast(data.prayers[0], at("05:30")), true);
  assert.equal(prayerIsPast(data.prayers[1], at("12:30")), false);
});

test("missing congregation stays highlighted until next published beginning", () => {
  const missing = {prayers: [row("fajr", "05:00"), row("dhuhr", "12:00", "12:30")]};
  assert.equal(highlightedPrayer(missing, at("11:59")), "fajr");
  assert.equal(highlightedPrayer(missing, at("12:00")), "dhuhr");
  assert.equal(highlightedPrayer({prayers: []}, at("12:00")), null);
});

test("tomorrow's event never highlights today's completed prayer", () => {
  assert.equal(highlightedPrayer({...data, next_salah: {prayer: "fajr", timestamp: "2026-10-24T05:01:00Z"}}, at("23:00")), null);
});

test("progress measures consecutive real events independently", () => {
  assert.equal(eventProgress(data, false, {timestamp: stamp("12:00")}, at("08:30")), 50);
  assert.equal(eventProgress(data, true, {timestamp: stamp("12:30")}, at("09:00")), 50);
  assert.equal(eventProgress(data, false, {timestamp: stamp("05:00")}, at("04:00")), null);
  assert.equal(eventProgress(data, false, {timestamp: stamp("12:00")}, at("12:00")), null);
  assert.equal(eventProgress({}, false, null, at("12:00")), null);
});

test("progress follows elapsed instants across DST and year boundaries", () => {
  for (const [start, middle, end] of [
    ["2026-10-25T00:00:00+01:00", "2026-10-25T01:00:00+01:00", "2026-10-25T01:00:00+00:00"],
    ["2026-12-31T23:00:00Z", "2027-01-01T00:00:00Z", "2027-01-01T01:00:00Z"]
  ]) {
    const attrs = {beginning_events: [{timestamp: start}, {timestamp: end}]};
    assert.equal(eventProgress(attrs, false, {timestamp: end}, Date.parse(middle)), 50);
  }
});

test("Umm al-Qura display adjusts dates across months without host timezone effects", () => {
  assert.equal(formatHijriDate("2026-02-18", 0, "en-GB"), "1 Ramadan 1447 AH");
  assert.doesNotMatch(formatHijriDate("2026-10-23", 0, "en-GB"), /October/i);
  assert.match(formatHijriDate("2026-02-18", 0, "ar"), /رمضان/);
  assert.equal(formatHijriDate("2026-02-18", -1, "en-GB"), formatHijriDate("2026-02-17", 0, "en-GB"));
  for (const adjustment of [-3, 3]) assert.equal(formatHijriDate("2026-12-31", adjustment, "en-GB"), formatHijriDate(new Date(Date.parse("2026-12-31T12:00Z") + adjustment * 86400000).toISOString().slice(0, 10), 0, "en-GB"));
  assert.equal(formatHijriDate("2026-02-30"), "Hijri date unavailable");
  const original = Intl.DateTimeFormat;
  try {
    Intl.DateTimeFormat = class { resolvedOptions() { return {calendar: "gregory"}; } format() { return "fallback"; } };
    assert.equal(formatHijriDate("2026-02-18"), "Hijri date unavailable");
  } finally { Intl.DateTimeFormat = original; }
});

test("time formats retain mosque timezone and missing-value marker", () => {
  assert.equal(formatTime(stamp("12:30"), "Europe/London", "en-GB", "24h"), "13:30");
  assert.match(formatTime(stamp("12:30"), "Europe/London", "en-GB", "12h"), /01:30\s*pm/i);
  assert.equal(formatTime(null, "UTC", "en", "12h"), "—");
});

test("config validates new types and preserves explicit old Jamaat modes", () => {
  assert.equal(normalizeConfig({}).detail_level, "standard");
  assert.equal(normalizeConfig({}).show_gregorian_date, true);
  assert.equal(normalizeConfig({show_gregorian_date: false}).show_hijri_date, true);
  assert.throws(() => normalizeConfig({show_gregorian_date: "false"}));
  for (const mode of ["context", "previous", "upcoming"]) assert.equal(normalizeConfig({mode}).mode, undefined);
  for (const invalid of [{detail_level: "tiny"}, {time_format: "auto"}, {hijri_adjustment: 4}, {hijri_adjustment: 0.5}, {hijri_adjustment: "1"}, {show_hijri_date: "false"}]) assert.throws(() => normalizeConfig(invalid));
});

test("display calculations do not mutate imported event payloads", () => {
  const copy = structuredClone(data); const before = JSON.stringify(copy);
  highlightedPrayer(copy, at("12:15")); eventProgress(copy, true, {timestamp: stamp("12:30")}, at("12:15"));
  assert.equal(JSON.stringify(copy), before);
});


test("missing middle and final Jamaats remain current until the next real beginning", () => {
  const missing = {prayers: [row("fajr", "05:00", "05:30"), row("dhuhr", "12:00"), row("asr", "15:00", "15:30"), row("isha", "19:00")]};
  for (const [time, expected] of [["11:59", "dhuhr"], ["12:00", "dhuhr"], ["14:59", "dhuhr"], ["15:00", "asr"], ["19:00", "isha"], ["23:59", "isha"]]) assert.equal(highlightedPrayer(missing, at(time)), expected);
  assert.equal(highlightedPrayer({prayers: [{key: "fajr", begin: "2026-10-24T05:00:00Z", jamaat: []}]}, Date.parse("2026-10-24T00:00:00Z")), "fajr");
});

test("progress remains congregation-to-congregation for multiple Friday events", () => {
  assert.equal(eventProgress(data, true, {timestamp: stamp("13:30")}, at("13:00")), 50);
  const overnight = {jamaat_events: [{prayer: "isha", timestamp: "2026-10-23T19:30:00Z"}, {prayer: "fajr", timestamp: "2026-10-24T05:30:00Z"}]};
  assert.equal(eventProgress(overnight, true, overnight.jamaat_events[1], Date.parse("2026-10-24T00:30:00Z")), 50);
});

test("language and bilingual settings validate YAML types and survive config round trips", () => {
  const defaults = normalizeConfig({});
  assert.equal(defaults.language, "auto");
  assert.equal(defaults.bilingual_prayer_labels, false);
  for (const language of ["auto", "en", "ar"]) for (const bilingual_prayer_labels of [false, true]) {
    const config = normalizeConfig({entity: "sensor.mosque", mode: "context", title: "My mosque", language, bilingual_prayer_labels, show_hijri_date: false, show_gregorian_date: false, hijri_adjustment: -3});
    assert.deepEqual(normalizeConfig(JSON.parse(JSON.stringify(config))), config);
    assert.equal(config.language, language);
    assert.equal(config.bilingual_prayer_labels, bilingual_prayer_labels);
    assert.equal(config.show_hijri_date, false);
    assert.equal(config.show_gregorian_date, false);
    assert.equal(config.detail_level, "standard");
  }
  for (const language of [null, true, false, 0, 1, {}, [], "", "AR", "ar-EG", "fr"]) assert.throws(() => normalizeConfig({language}), error => error.translationKey === "config.language");
  for (const bilingual_prayer_labels of [null, 0, 1, {}, [], "", "false", "true"]) assert.throws(() => normalizeConfig({bilingual_prayer_labels}), error => error.translationKey === "config.boolean" && error.params.option === "bilingual_prayer_labels");
  // Existing graphical and falsy-option defaults retain their earlier behavior.
  assert.equal(normalizeConfig({mode: null, entity: ""}).detail_level, "standard");
});

test("Gregorian source dates override locale calendar extensions while Hijri stays Umm al-Qura", () => {
  for (const locale of ["en-GB-u-ca-islamic", "ar-EG-u-ca-islamic"]) {
    const ui = resolveUi({language: "auto"}, {locale: {language: locale}});
    const expected = new Intl.DateTimeFormat(locale, {calendar: "gregory", dateStyle: "full", timeZone: "UTC"}).format(Date.parse("2026-10-25T12:00:00Z"));
    assert.equal(formatDate("2026-10-25", locale), expected);
    assert.equal(formatDate("2026-10-25", ui), expected);
  }
  for (const locale of ["en-GB", "ar-EG"]) assert.equal(formatHijriDate("2026-02-18", 0, `${locale}-u-ca-gregory`), formatHijriDate("2026-02-18", 0, locale));
  const ui = resolveUi({language: "ar"});
  for (const date of ["2026-02-29", "1900-02-29", "2026-04-31", "2026-00-01", "2026-13-01", "2026-2-18"]) {
    assert.equal(formatDate(date, ui), "التاريخ غير متاح", date);
    assert.equal(formatHijriDate(date, 0, ui), "التاريخ الهجري غير متاح", date);
  }
  for (const date of ["2024-02-29", "2000-02-29"]) {
    assert.notEqual(formatDate(date, ui), "التاريخ غير متاح");
    assert.notEqual(formatHijriDate(date, 0, ui), "التاريخ الهجري غير متاح");
  }
});

test("localized times keep mosque timezone and hour format across both DST transitions", () => {
  const ui = resolveUi({}, {locale: {language: "ar-EG-u-ca-islamic"}});
  for (const value of ["2026-10-25T00:30:00Z", "2026-10-25T01:30:00Z"]) assert.equal(formatTime(value, "Europe/London", ui, "24h"), "٠١:٣٠");
  assert.equal(formatTime("2026-03-29T00:30:00Z", "Europe/London", ui, "24h"), "٠٠:٣٠");
  assert.equal(formatTime("2026-03-29T01:30:00Z", "Europe/London", ui, "24h"), "٠٢:٣٠");
  assert.equal(formatTime(stamp("12:30"), "Europe/London", ui, "24h"), "١٣:٣٠");
  assert.match(formatTime(stamp("12:30"), "Europe/London", ui, "12h"), /^٠١:٣٠\s*م$/u);
  assert.equal(formatTime(null, "Europe/London", ui), "—");
});

test("invalid direct locale inputs preserve graceful formatter fallbacks", () => {
  assert.equal(formatDate("2026-10-23", "bad_locale!"), "2026-10-23");
  assert.equal(formatTime(stamp("12:30"), "UTC", "bad_locale!"), "—");
  assert.equal(formatHijriDate("2026-10-23", 0, "bad_locale!"), "Hijri date unavailable");
});
