import test from "node:test";
import assert from "node:assert/strict";
import {CATALOGS, localizedNumber, prayerLabels, resolveUi, tr} from "../../custom_components/salah_timetable/frontend/card-i18n.js";

test("English and Arabic catalogs cover the same plain-text keys and placeholders", () => {
  const placeholders = value => [...value.matchAll(/\{([a-zA-Z][a-zA-Z0-9_]*)\}/g)].map(match => match[1]).sort();
  assert.deepEqual(Object.keys(CATALOGS.ar).sort(), Object.keys(CATALOGS.en).sort());
  for (const key of Object.keys(CATALOGS.en)) {
    for (const language of ["en", "ar"]) {
      assert.equal(typeof CATALOGS[language][key], "string", `${language}: ${key}`);
      assert.ok(CATALOGS[language][key].trim(), `${language}: ${key} is empty`);
      assert.doesNotMatch(CATALOGS[language][key], /<\/?[a-z][^>]*>/i, `${language}: ${key} contains HTML`);
    }
    assert.deepEqual(placeholders(CATALOGS.ar[key]), placeholders(CATALOGS.en[key]), key);
  }
  assert.ok(Object.isFrozen(CATALOGS));
  assert.ok(Object.isFrozen(CATALOGS.en));
  assert.ok(Object.isFrozen(CATALOGS.ar));
});

test("catalog covers card, editor, accessible labels, statuses and configuration errors", () => {
  for (const key of [
    "card.name", "card.description", "card.choose_entity", "card.entity_missing", "card.unavailable", "card.hijri_calculated", "card.disconnected", "card.timezone_note", "card.second_khutbah",
    "panel.next_salah", "panel.next_jamaat", "panel.previous_jamaat", "panel.no_event", "panel.progress_aria", "panel.salah_progress", "panel.jamaat_progress",
    "status.unavailable", "status.passed", "status.elapsed", "status.date_unavailable", "status.hijri_unavailable", "duration.days",
    "table.caption", "table.prayer", "table.beginning", "table.jamaat", "table.region", "table.scroll_help", "table.jumuah_time", "table.fajr_end",
    "ramadan.title", "ramadan.sehri_ends", "ramadan.iftar", "ramadan.taraweeh", "ramadan.no_time",
    ...["prayer", "fajr", "sunrise", "dhuhr", "jumuah", "asr", "maghrib", "isha"].map(key => `prayer.${key}`),
    "editor.entity", "editor.invalid_entity", "editor.mode", "editor.mode.context", "editor.mode.previous", "editor.mode.upcoming", "editor.title",
    "editor.layout", "editor.layout.expanded", "editor.layout.compact", "editor.time_format", "editor.time_format.12h", "editor.time_format.24h", "editor.hijri_adjustment",
    ...["show_hijri_date", "show_salah_countdown", "show_jamaat_countdown", "show_ramadan_details", "show_sehri_countdown", "show_iftar_countdown", "show_timezone_note"].map(key => `editor.${key}`),
    "editor.language", "editor.language.auto", "editor.language.en", "editor.language.ar", "editor.bilingual_prayer_labels", "editor.help",
    ...["required", "mode", "entity", "title", "layout", "time_format", "hijri_adjustment", "language", "boolean"].map(key => `config.${key}`),
  ]) assert.ok(Object.hasOwn(CATALOGS.en, key), key);
});

test("automatic UI language follows Home Assistant and preserves its regional formatting locale", () => {
  assert.deepEqual(resolveUi({}, {locale: {language: "ar-eg"}, language: "en-GB"}), {language: "ar", locale: "ar-EG", dir: "rtl"});
  assert.deepEqual(resolveUi({language: "auto"}, {language: "en-GB"}), {language: "en", locale: "en-GB", dir: "ltr"});
  assert.deepEqual(resolveUi({}, {locale: {language: "fr-FR"}}), {language: "en", locale: "fr-FR", dir: "ltr"});
  assert.deepEqual(resolveUi({}, {locale: {language: ""}, language: "ar-SA"}), {language: "ar", locale: "ar-SA", dir: "rtl"});
  assert.deepEqual(resolveUi({}, {locale: {language: "ar-EG-u-nu-latn"}}), {language: "ar", locale: "ar-EG-u-nu-latn", dir: "rtl"});
});

test("explicit card language retains a matching Home Assistant region only", () => {
  assert.deepEqual(resolveUi({language: "ar"}, {locale: {language: "ar-MA"}}), {language: "ar", locale: "ar-MA", dir: "rtl"});
  assert.deepEqual(resolveUi({language: "en"}, {language: "en-GB"}), {language: "en", locale: "en-GB", dir: "ltr"});
  assert.deepEqual(resolveUi({language: "ar"}, {language: "en-US"}), {language: "ar", locale: "ar", dir: "rtl"});
  assert.deepEqual(resolveUi({language: "en"}, {language: "ar-EG"}), {language: "en", locale: "en", dir: "ltr"});
  assert.deepEqual(resolveUi({language: "en"}, {language: "fr-FR"}), {language: "en", locale: "en", dir: "ltr"});
});

test("missing, malformed and unsupported locales have a deterministic fallback", () => {
  for (const locale of [undefined, null, "", "not_a_locale", "ar_XX", "zz-ZZ", {}, ["ar-EG"]]) {
    assert.deepEqual(resolveUi({}, {locale: {language: locale}}), {language: "en", locale: "en", dir: "ltr"});
    assert.deepEqual(resolveUi({language: "ar"}, {locale: {language: locale}}), {language: "ar", locale: "ar", dir: "rtl"});
  }
  assert.deepEqual(resolveUi(), {language: "en", locale: "en", dir: "ltr"});
  assert.deepEqual(resolveUi(null, null), {language: "en", locale: "en", dir: "ltr"});
  assert.deepEqual(resolveUi({}, {locale: {language: "bad_locale"}, language: "ar"}), {language: "en", locale: "en", dir: "ltr"});
});

test("translation substitutes literal values without interpreting HTML or replacement syntax", () => {
  assert.equal(tr("ar", "table.prayer"), "الصلاة");
  assert.equal(tr({language: "ar", locale: "ar-EG", dir: "rtl"}, "panel.progress_aria", {label: "الفجر"}), "الفجر: التقدم بين المواعيد المنشورة");
  assert.equal(tr("en", "card.timezone_note", {zone: "<b>$&</b>"}), "Times shown in <b>$&</b>. Missing times are not estimated.");
  assert.equal(tr("en", "duration.days", {days: 0, clock: "00:00:00"}), "0d 00:00:00");
  assert.equal(tr("en", "card.timezone_note"), CATALOGS.en["card.timezone_note"]);
  assert.equal(tr("en", "missing.key"), "missing.key");
  assert.equal(tr("fr", "table.prayer"), "Prayer");
  assert.equal(tr("bad_locale", "table.prayer"), "Prayer");
  assert.equal(tr("en", "toString"), "toString");
  assert.equal(tr("en", "config.boolean", Object.create({option: "inherited"})), "{option} must be true or false");
});

test("prayer labels carry explicit language and direction in UI-first bilingual order", () => {
  assert.deepEqual(prayerLabels("fajr", "ar", true), [
    {text: "الفجر", lang: "ar", dir: "rtl"},
    {text: "Fajr", lang: "en", dir: "ltr"},
  ]);
  assert.deepEqual(prayerLabels("jumuah", "en", true), [
    {text: "Jumu’ah", lang: "en", dir: "ltr"},
    {text: "الجمعة", lang: "ar", dir: "rtl"},
  ]);
  assert.deepEqual(prayerLabels("sunrise", {language: "ar"}), [{text: "الشروق", lang: "ar", dir: "rtl"}]);
  assert.deepEqual(prayerLabels("custom", "ar"), [{text: "الصلاة", lang: "ar", dir: "rtl"}]);
  const first = prayerLabels("fajr", "en"); first[0].text = "changed";
  assert.equal(prayerLabels("fajr", "en")[0].text, "Fajr");
});

test("localized numbers preserve zero padding and regional digit preferences", () => {
  const arabic = resolveUi({}, {language: "ar-EG"});
  assert.equal(localizedNumber(3, arabic, {minimumIntegerDigits: 2}), "٠٣");
  assert.equal(localizedNumber(1200, "en"), "1200");
  assert.equal(localizedNumber(1200, "en", {useGrouping: true}), "1,200");
  assert.equal(localizedNumber(3, resolveUi({}, {language: "ar-EG-u-nu-latn"}), {minimumIntegerDigits: 2}), "03");
  assert.equal(localizedNumber(1234, resolveUi({}, {language: "fr-FR"}), {useGrouping: true}), new Intl.NumberFormat("fr-FR").format(1234));
  assert.equal(localizedNumber(4, {language: "en", locale: "bad_locale"}, {minimumIntegerDigits: 2}), "04");
  assert.equal(localizedNumber(4, "bad_locale", {minimumIntegerDigits: 2}), "04");
  assert.equal(localizedNumber(4, "ar", {minimumIntegerDigits: -1}), "4");
  assert.equal(localizedNumber(12n, "en"), "12");
  for (const value of [NaN, Infinity, undefined, null, "12"]) assert.equal(localizedNumber(value, arabic), "—");
});

test("locale and translation helpers never mutate configuration or Home Assistant state", () => {
  const config = Object.freeze({language: "auto", bilingual_prayer_labels: true});
  const hass = Object.freeze({locale: Object.freeze({language: "ar-EG"}), states: Object.freeze({})});
  const before = JSON.stringify({config, hass});
  const ui = resolveUi(config, hass);
  tr(ui, "card.timezone_note", {zone: "Europe/London"});
  prayerLabels("isha", ui, config.bilingual_prayer_labels);
  localizedNumber(7, ui);
  assert.equal(JSON.stringify({config, hass}), before);
});
