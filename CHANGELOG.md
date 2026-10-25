# Changelog

## 0.8.0 — unreleased

- Compare pending imports with the exact approved source they replace. Show all
  added/removed dates, changed published values, multiple Jumuah congregations and
  retained source-token differences through paged review.
- Identify source/provenance changes even when canonical prayer values stay the
  same, without claiming every source-text change is merely formatting.
- Require a fresh comparison and another approval decision if the approved source
  changes while its review is open. Page navigation never activates a proposal.
- Keep healthy speakers eligible for Adhan volume restoration when another selected
  player disappears during acknowledgement. Intervening player updates, including
  same-context volume/content changes away and back, prevent restoration.

## 0.7.0 — unreleased

- Display the end of Fajr at the explicitly published Sunrise time in the
  bundled dashboard, without changing published Fajr beginning or Jamaat.
- Retain the second-Jumu’ah khutbah footer on inspected NMS annual/monthly
  publications and display it as a Friday-only note, **never** as an
  additional Jumu’ah congregation or revised Dhuhr beginning.
- Display the **full calculated Umm al-Qura Hijri date** (day, month, year)
  according to a mosque-wide visibility choice at initial setup and through
  subsequent settings; keep each card's existing additional hide toggle and
  independent display-day adjustment. Ramadan activation is unaffected.
- Add read-only source-scoped import comparisons in the pending review flow,
  with added/removed date and field counts, exact before/after times (including
  multi-congregation Jumu'ah), and 20-change pagination. Other years and
  Ramadan effective fallbacks are excluded; approval/rejection remains explicit.
- Add one read-only Home Assistant calendar per mosque, with separate published
  beginnings, Jamaats, Friday congregations and active Ramadan events. Query
  approved dated records with stable event IDs and timezone-aware boundaries.
- Add optional Fajr audio, individual prayer exclusions, graphical per-prayer
  volume overrides, quiet hours and guarded volume restoration to Adhan playback.
- Add an opt-in media pause/resume blueprint using published timestamp anchors
  and a user-chosen delay; resume only players still unchanged since the pause.
- Offer versioned setup profiles for four inspected PDF editions, with fixed
  layout/year/mapping, explicit timezone checks, retained profile provenance and
  the existing preview and approval flow.
- Use a 60-second **calendar presentation interval** with exact, unchanged
  published event starts, exclusive end-times, overlapping range queries and
  improved calendar start/end automation-trigger coverage. The minute is **not**
  a prayer or Jamaat duration.
- Stop coordinator boundary timers on successful unload/reload so an obsolete
  coordinator cannot continue scheduling callbacks.
- Distinguish explicitly rejected or unapproved remote publications from
  approved and up-to-date sources, retaining rejection-digest suppression until
  source content changes.
- Add inventory and fail-closed redistribution-rights checks for public assets;
  the release gate deliberately remains blocked until documented permissions
  or rights-cleared replacements are available.
- Expand live Home Assistant Container acceptance to cover independent mosques,
  config-entry removal/re-addition, and real backup-archive restoration into a
  second disposable configuration. These tests do **not** replace full HAOS
  backup restoration or actual HACS UI uninstall/reinstallation.
- Consolidate release-readiness sign-offs in `docs/releasing.md`, archive the
  dated code review plan, and record CI evidence. Calendar end-trigger test
  intermittency is tracked in
  [issue #13](https://github.com/anaschillin/home-assistant-salah-timetable/issues/13).

## 0.6.2 — unreleased

- Keep calendar-date subclass support while rejecting datetime values that cannot
  round-trip through timetable storage.
- Stop future coverage at an ambiguous source date without disabling valid current
  prayer data; expose the unresolved date separately from absent publication data.
- Exercise shipped automation blueprints through Home Assistant's actual scheduler
  and document sensor selection, offsets and health-alert behavior.
- Require the real minimum/current Home Assistant matrix in Validate, with a
  weekly compatibility run and explicit before/after runtime dependency proof.
- Refresh asset cache versions after the maintainer's rendering changes and retain
  all per-toggle preview, import approval and restart regression coverage.

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
