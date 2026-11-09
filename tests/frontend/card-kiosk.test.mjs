import {test, assert, SalahTimetableCard, find, attributes, hass} from "./card-test-harness.mjs";

test("kiosk 3.0 renders the three-zone display from published prayers and respects options", () => {
  const card = new SalahTimetableCard();
  const entity = "sensor.mosque_prayer_timetable";
  const date = "2026-10-21";
  const instant = (hour, minute) => date + "T" + String(hour).padStart(2, "0") +
    ":" + String(minute).padStart(2, "0") + ":00Z";
  const rows = [
    ["fajr", 4, 45, 5, 15], ["dhuhr", 11, 45, 13, 0],
    ["asr", 14, 10, 14, 45], ["maghrib", 16, 29, 16, 32],
    ["isha", 18, 26, 20, 0],
  ].map(([key, h, m, jh, jm]) => ({key, name: key,
    begin: instant(h, m), jamaat: [instant(jh, jm)]}));
  const data = {...attributes, date, prayers: rows, show_hijri_date: true,
    day_prayers: {"2026-10-20": rows, "2026-10-22": rows},
    beginning_events: rows.map(row => ({prayer: row.key, timestamp: row.begin})),
    jamaat_events: rows.map(row => ({prayer: row.key, timestamp: row.jamaat[0]}))};
  const start = Date.parse(instant(4, 40));
  card.setConfig({entity, kiosk_mode: true, detail_level: "compact",
    show_month_view: true, show_timezone_note: true,
    show_hijri_date: true, show_gregorian_date: true, show_hijri_month_info: true});
  card.hass = hass(data);
  card._render(start);
  const header = find(card.shadowRoot, "header")[0];
  const identity = find(header, "div").find(element => element.className === "kiosk-identity");
  const toolbar = find(card.shadowRoot, "div").find(element => element.className === "kiosk-toolbar");
  const dates = find(header, "div").find(element => element.className === "kiosk-dates");
  const clock = find(header, "time")[0];
  const strip = find(card.shadowRoot, "section").find(element => element.className === "kiosk-strip");
  const footer = find(card.shadowRoot, "footer")[0];
  assert.ok(identity);
  assert.match(identity.textContent, /Example Mosque/);
  assert.match(identity.textContent, /Europe\/London/);
  assert.ok(dates);
  assert.equal(clock.textContent, "05:40");
  assert.ok(find(dates, "div").some(element => element.className === "date hijri"));
  assert.ok(find(dates, "div").some(element => element.className === "date gregorian"));
  assert.ok(find(dates, "div").some(element => element.className === "month-description"));
  assert.ok(header.children.findIndex(child => child.className === "kiosk-clock") <
    header.children.indexOf(dates));
  assert.ok(strip);
  assert.equal(strip.children.length, 5, "Five prayer tiles use only published source rows");
  assert.deepEqual(strip.children.map(tile => tile.attributes["data-prayer"]),
    ["fajr", "dhuhr", "asr", "maghrib", "isha"]);
  assert.match(strip.textContent, /05:45/);
  assert.match(strip.textContent, /21:00/, "Published 20:00 UTC is 21:00 in Europe/London during BST");
  assert.ok(strip.children[0].className.includes("is-next"));
  assert.equal(find(card.shadowRoot, "table").length, 0, "Kiosk has no duplicate scrolling timetable");

  const tabs = find(card.shadowRoot, "nav").find(element => element.className === "date-tabs");
  assert.equal(footer.children[1], tabs);
  assert.equal(footer.children[2], toolbar);
  const summary = find(card.shadowRoot, "div").find(element => element.className === "summary-shell");
  const fullscreen = summary.children.find(child => child.className === "kiosk-fullscreen");
  assert.ok(fullscreen, "Fullscreen icon is a direct child of the glass summary");
  assert.equal(fullscreen.textContent, "", "Only the icon is visible, not button text");
  assert.equal(fullscreen.children[0].tagName, "ha-icon");
  assert.equal(fullscreen.children[0].attributes.icon, "mdi:fullscreen");
  assert.equal(fullscreen.attributes["aria-label"], "Enter fullscreen");
  assert.equal(fullscreen.attributes["aria-pressed"], "false");
  assert.ok(!toolbar.children.some(child => child.className === "kiosk-fullscreen"),
    "The previous footer fullscreen button is removed");
  assert.ok(toolbar.children.some(child => child.className === "card-actions-menu"),
    "Compact monthly actions stay in More disclosure");
  card._tick(start + 60000);
  assert.equal(find(card.shadowRoot, "time")[0], clock);
  assert.equal(clock.textContent, "05:41");

  card._render(Date.parse(instant(16, 15)));
  const nextStrip = find(card.shadowRoot, "section").find(element => element.className === "kiosk-strip");
  assert.ok(nextStrip.children[3].className.includes("is-next"), "Next published beginning is Maghrib");
  assert.ok(nextStrip.children[2].className.includes("is-current"), "Latest begun Salah is Asr");
  const changedTabs = find(card.shadowRoot, "nav").find(element => element.className === "date-tabs");
  changedTabs.children[2].dispatchEvent(new Event("click"));
  const tomorrowFooter = find(card.shadowRoot, "footer")[0];
  assert.ok(tomorrowFooter.children.some(child => child.className === "date-tabs"),
    "Adjacent dates retain bottom controls");
  assert.equal(find(card.shadowRoot, "section").find(element => element.className === "kiosk-strip").children.length, 5);
  find(card.shadowRoot, "nav").find(element => element.className === "date-tabs")
    .children[1].dispatchEvent(new Event("click"));

  card.setConfig({entity, kiosk_mode: true, detail_level: "compact", time_format: "12h",
    show_hijri_date: false, show_gregorian_date: false, show_timezone_note: false});
  card._render(start);
  assert.equal(find(card.shadowRoot, "div").filter(element => element.className === "kiosk-dates").length, 0);
  assert.equal(find(card.shadowRoot, "small").filter(element => element.className === "kiosk-timezone").length, 0);
  assert.match(find(card.shadowRoot, "time")[0].textContent, /05:40\s*am/i);
  assert.equal(find(card.shadowRoot, "div").filter(element => element.className === "kiosk-footer-note").length, 0);

  card.setConfig({entity, kiosk_mode: true, detail_level: "compact",
    show_hijri_date: true, show_gregorian_date: true});
  card.hass = hass({...data, show_hijri_date: false});
  card._render(start);
  const mosqueDates = find(card.shadowRoot, "div").find(element => element.className === "kiosk-dates");
  assert.ok(find(mosqueDates, "div").some(element => element.className === "date gregorian"));
  assert.ok(!find(mosqueDates, "div").some(element => element.className === "date hijri"));

  card.setConfig({entity, detail_level: "standard"});
  assert.equal(find(card.shadowRoot, "time").length, 0, "Non-kiosk has no live wall clock");
  assert.equal(find(card.shadowRoot, "section").filter(element => element.className === "kiosk-strip").length, 0);
  assert.equal(find(card.shadowRoot, "table").length, 1, "Normal timetable remains unchanged");
});

test("kiosk fullscreen icon enters, exits and follows external Escape", () => {
  const card = new SalahTimetableCard();
  const entity = "sensor.mosque_prayer_timetable";
  card.setConfig({entity, kiosk_mode: true, show_month_view: true});
  card.hass = hass();
  const summary = find(card.shadowRoot, "div").find(element => element.className === "summary-shell");
  const fullscreen = summary.children.find(child => child.className === "kiosk-fullscreen");
  const surface = find(card.shadowRoot, "ha-card")[0];
  const oldFullscreen = document.fullscreenElement;
  const oldExit = document.exitFullscreen;
  let enters = 0, exits = 0;
  card.shadowRoot.querySelector = selector => selector === "ha-card" ? surface : null;
  surface.requestFullscreen = () => {
    enters++;
    document.fullscreenElement = surface;
    card._onFullscreenChange();
    return Promise.resolve();
  };
  document.exitFullscreen = () => {
    exits++;
    document.fullscreenElement = null;
    card._onFullscreenChange();
    return Promise.resolve();
  };
  try {
    assert.equal(fullscreen.attributes["aria-label"], "Enter fullscreen");
    assert.equal(fullscreen.children[0].attributes.icon, "mdi:fullscreen");
    fullscreen.dispatchEvent(new Event("click"));
    assert.equal(enters, 1, "First tap requests fullscreen on this card only");
    assert.equal(document.fullscreenElement, surface);
    assert.equal(fullscreen.attributes["aria-label"], "Exit fullscreen");
    assert.equal(fullscreen.attributes["aria-pressed"], "true");
    assert.equal(fullscreen.children[0].attributes.icon, "mdi:fullscreen-exit");

    fullscreen.dispatchEvent(new Event("click"));
    assert.equal(exits, 1, "Second tap exits fullscreen to the previous view");
    assert.equal(document.fullscreenElement, null);
    assert.equal(fullscreen.attributes["aria-label"], "Enter fullscreen");
    assert.equal(fullscreen.attributes["aria-pressed"], "false");
    assert.equal(fullscreen.children[0].attributes.icon, "mdi:fullscreen");

    fullscreen.dispatchEvent(new Event("click"));
    document.fullscreenElement = null;
    card._onFullscreenChange();
    assert.equal(fullscreen.attributes["aria-label"], "Enter fullscreen",
      "Esc and external fullscreen exits must restore the expand icon");
    assert.equal(fullscreen.children[0].attributes.icon, "mdi:fullscreen");
  } finally {
    if (oldFullscreen === undefined) delete document.fullscreenElement;
    else document.fullscreenElement = oldFullscreen;
    if (oldExit === undefined) delete document.exitFullscreen;
    else document.exitFullscreen = oldExit;
  }
});

test("kiosk distinguishes tomorrow's Salah and the next published Jamaat", () => {
  const entity = "sensor.mosque_prayer_timetable";
  const card = new SalahTimetableCard();
  const start = Date.parse("2026-10-21T18:28:00Z");
  const rows = [
    ["fajr", "04:45", "05:15"], ["dhuhr", "11:45", "13:00"],
    ["asr", "14:10", "14:45"], ["maghrib", "16:29", "16:32"],
    ["isha", "18:26", "20:00"],
  ].map(([key, begin, jamaat]) => ({
    key, name: key,
    begin: `2026-10-21T${begin}:00Z`,
    jamaat: [`2026-10-21T${jamaat}:00Z`],
  }));
  const data = {
    ...attributes, date: "2026-10-21", time_zone: "Europe/London",
    prayers: rows,
    beginning_events: rows.map(row => ({timestamp: row.begin, prayer: row.key})),
    jamaat_events: rows.map(row => ({timestamp: row.jamaat[0], prayer: row.key})),
    next_salah: {timestamp: "2026-10-22T04:45:00Z", prayer: "fajr"},
  };
  card.setConfig({entity, kiosk_mode: true});
  card.hass = hass(data);
  card._render(start);
  const day = find(card.shadowRoot, "span").find(element => element.className === "kiosk-next-day");
  assert.equal(day?.textContent, "Tomorrow", "Next Salah's day is relative to the mosque timezone");
  assert.equal(day?.attributes["data-role"], "next-salah-day");
  const isha = find(card.shadowRoot, "div").find(element => element.attributes["data-prayer"] === "isha");
  assert.ok(isha?.className.includes("is-next-jamaat"), "Upcoming Isha Jamaat gets a subtle tile outline");
  assert.equal(isha?.attributes["data-next-jamaat"], "true");
  assert.ok(!isha.className.includes("is-next "), "Tomorrow's Fajr should not highlight today's Isha as next beginning");
  assert.equal(find(card.shadowRoot, "div").filter(element => element.attributes["data-next-jamaat"] === "true").length, 1);

  // A UTC date can still be tomorrow in Europe/London (BST).
  card.hass = hass({...data, next_salah: {timestamp: "2026-10-21T23:10:00Z", prayer: "fajr"}});
  card._render(start);
  assert.equal(find(card.shadowRoot, "span").find(element => element.className === "kiosk-next-day")?.textContent, "Tomorrow");
  card.hass = hass({...data, time_zone: "UTC", next_salah: {timestamp: "2026-10-21T23:10:00Z", prayer: "fajr"}});
  card._render(start);
  assert.equal(find(card.shadowRoot, "span").filter(element => element.className === "kiosk-next-day").length, 0,
    "Same UTC day must not be mislabelled Tomorrow");

  // Previous Jamaat is not an upcoming congregation and should not highlight a tile.
  card.hass = hass({...data, next_salah: {timestamp: "2026-10-22T04:45:00Z", prayer: "fajr"}});
  card._render(Date.parse("2026-10-21T20:10:00Z"));
  assert.equal(find(card.shadowRoot, "div").filter(element => element.attributes["data-next-jamaat"] === "true").length, 0);
  card.setConfig({entity});
  assert.equal(find(card.shadowRoot, "span").filter(element => element.className === "kiosk-next-day").length, 0,
    "Normal dashboard modes are unchanged");
});

