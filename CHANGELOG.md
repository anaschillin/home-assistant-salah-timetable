# Changelog

## 0.6.1 — unreleased

- Update countdown text and progress in place between event boundaries, preserving
  timetable nodes, keyboard focus and text selection during ordinary ticks.
- Skip card rebuilds for equivalent timetable and unrelated Home Assistant updates,
  while refreshing changed timetable data, locale, timezone and availability.
- Explain the agreed beginning-to-beginning/Jamaat-to-Jamaat progress intervals;
  clarify missing-Jamaat highlighting through the final daily prayer.
- Add narrow-table scrolling guidance and browser checks at 320/360/400/900 pixels,
  including 200% text, themes, text selection and editor configuration persistence.
- Fail live readiness polling immediately for authentication/API/response errors;
  retry only expected transient startup transport failures.
- Extend real HA editor acceptance to display controls and page reload. Record
  successful minimum-version HA restart acceptance separately from HACS installation.
- Check each visibility control independently off and on in the native browser
  fixture; add the same per-toggle preview checks to the opt-in live HA script.
- Upgrade the SHA-pinned `actions/setup-python` action to v7.0.0 in validation and
  draft-release workflows, with Python 3.14 retained.

## 0.6.0 — unreleased

- Highlight the prayer awaiting Jamaat, keep completed rows readable and align
  Beginning/Jamaat columns with individually labelled Jumu’ah congregations.
- Show independent Next Salah Begins and Next Jamaat countdowns by default,
  with larger numbers, published-event progress and card-width responsive layout.
  Explicit context/previous modes remain supported.
- Add Gregorian and calculated Umm al-Qura Hijri dates with a per-card −3 to +3
  display adjustment, independent of Ramadan activation and source timetables.
- Add graphical compact/expanded layout, 12/24-hour time format, individual
  countdown visibility and Ramadan/timezone detail controls.
- Reconcile current dashboard, PDF support, fixture licensing and release guidance.

## 0.5.5 — unreleased

- Label published Jumu'ah congregation times in the daily Dhuhr row while retaining
  ordinary Dhuhr labels; preserve the maintainer's display fix and regression tests.
- Exercise real NMS monthly Ramadan approval and explicit date confirmation.
- Retain CI browser diagnostics, prefer native Chrome and allow a bounded 15-second
  debugger startup. Handle private Chromium profile paths, partially written port
  files, process exits and signal failures with regression tests.

## 0.5.4

- Add live validation, HACS custom-repository and MIT license README badges.
- Support the inspected Zakariyya 2026 annual PDF tables as a separate layout from
  its Ramadan page. Validate all 365 dates and 3,770 published values against an
  independent extraction; preserve missing Sehri fields and pre-noon Dhuhr values.
- Document and show the clipped May first-date interpretation before approval,
  retaining its original token. Never infer missing prayer times or activate
  Ramadan from printed Hijri headings.
- Test annual approval/reload, URL source profiles, separate Ramadan confirmation,
  daylight saving changes and tomorrow's actual Fajr through Home Assistant.

## 0.5.3

- Validate the contributed NMS May–June 2022 monthly PDF and the separate Ramadan
  page in Zakariyya Masjid's 2026 calendar with strict layout adapters and independent
  expected values. Preserve printed years and post-Ramadan rows without activation.
- Increase the bounded PDF input limit to 4 MiB; keep all extraction resource,
  decompression, page and text limits, and HTTPS protections.
- Review coverage across confirmed Ramadan dates, annual fallback, default Iftar
  and unavailable timestamps. Warn about contradictory source/effective times
  without changing published data.
- Recheck active Ramadan source ambiguity at approval; retain approved values and
  the pending proposal when a conflict is found.

## 0.5.2

- Keep prayer tables contained and keyboard accessible at large text sizes; add a
  native Chromium regression at 200% root text size.

- Report actual integration load state and safe row/event availability in diagnostics.
- Strengthen historical storage migration and backup recovery tests, and add checked
  release-note preparation with a manual, validation-gated draft workflow.

## 0.5.1

- Keep published Sehri/Iftar times visible after their events on the final confirmed
  Ramadan date, with “Passed” rather than an unavailable value. Future countdown
  events remain separate from today's published information.
- Align the final prayer row's borders and refresh bundled asset cache versions.

## 0.5.0

- Calculate next Salah beginning and next/previous Jamaat independently, using
  absolute timestamps and tomorrow’s actual timetable. Handle prayer boundaries,
  multiple Friday congregations, DST and year/leap-day changes without estimating
  missing events.
- Add confirmed-date Ramadan settings, manual activation and date adjustment.
  Apply exact-date overrides separately from imported data; preserve published
  Iftar and use Maghrib beginning only as its documented fallback. Taraweeh defaults
  to the text “After Isha Jamaat” without a fabricated time.
- Bundle a responsive Lovelace card with graphical mosque/mode/title settings,
  local countdowns, theme support and Ramadan details. Register assets automatically
  for storage- and YAML-resource dashboards.
- Add persistent Repair guidance for invalid stored timetable records, with cleanup
  after recovery/removal. Keep invalid structured files intact.
- Add frontend and Chromium smoke tests, reproducible install ZIPs/checksums and
  release-version/asset validation. Real Home Assistant/HACS installation and
  real-device acceptance remain required before publishing a tested release.

## 0.3.1

- Support the inspected Nuneaton Muslim Society annual PDF layout, alongside the
  strict synthetic sample layout, with explicit field meanings and fixture tests.
- Support UI URL/manual import, bounded HTTPS downloads, staged updates and
  approval while preserving the last validated source.

Earlier milestones established HACS repository structure, mosque configuration,
immutable prayer data, persistent storage, sensors and graphical CSV import.
