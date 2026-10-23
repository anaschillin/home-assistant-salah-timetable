import test from "node:test";
import assert from "node:assert/strict";
import {countdown, duration, elapsed, formatDate, formatTime, isTimetableState, jamaatPanel, nextSalah, normalizeConfig, timestamp, discoverEntity, nextRamadanEvent} from "../../custom_components/salah_timetable/frontend/card-utils.js";

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
  assert.equal(normalizeConfig({}).mode, "context");
  assert.throws(() => normalizeConfig({mode: "interval"}));
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
