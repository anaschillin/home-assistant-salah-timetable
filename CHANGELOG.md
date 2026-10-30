# Changelog

## 0.9.20 — unreleased

- Update pypdf to 6.21.4 for [upstream reader security fixes](https://pypdf.readthedocs.io/en/stable/meta/CHANGELOG.html#version-6-21-4-2026-10-28);
  keep the runtime, development and both compatibility locks aligned.
- Reject import proposals if the integration reloads during monthly/source
  preparation; check the active runtime immediately before staging.
- Prune local virtual environments before checking documentation, and enforce
  LF fixture CSV bytes so provenance checks also work on Windows checkouts.
- Move the supported-current Home Assistant test lane to 2026.10.4 with
  pytest-homeassistant-custom-component 0.13.375; retain minimum support for
  Home Assistant 2026.10.0. Update Ruff and its pre-commit hooks to 0.17.3.
- Document existing prayer completeness checks, optional night calculations,
  kiosk display, authenticated monthly tables/CSV export, conservative generic
  PDF recognition and explicitly approved annual URL rollover.
- Remove completed roadmap proposals and dated acceptance diaries, correct
  module inventories and research boundaries, and complete contributor guidance.

## 0.9.19 — maintenance (29 October 2026)

- Preserve the focused day-navigation button and multi-mosque header selector after the card refreshes its Shadow DOM, with Chromium keyboard-focus regressions.
- Remove styles belonging to the retired wide mosque tab strip.
- Bump frontend cache/import versions to load the updated card rather than retaining cached 0.9.18 JavaScript.
- Align manifest-pinned pypdf with the 6.21.2 development and compatibility environments.
- Record the maintainer's AI-generated brand icon and synthetic screenshot origin attestation and retain checksum-based asset auditing.
- Clarify per-PR HACS/Container validation, manual HACS/HAOS acceptance and optional full HAOS restoration; add a user-facing quickstart.
- Add mosque name/timezone reconfiguration without changing mosque identity or approved imports; declare read-only entity update policy and move calendar icon/name into Home Assistant translation resources.
- Document the internal Home Assistant Integration Quality Scale audit, associated regression tests and release acceptance. Improve archive packaging checks for `icons.json`.
- Arabic implementation is intentionally deferred.

## 0.9.18 — 28 October 2026

- Redesign the dashboard as one compact mosque/Next Salah/contextual Jamaat
  summary and a matching prayer timetable. Put Yesterday/Today/Tomorrow in the
  timetable footer; header Gregorian/Hijri dates and month explanation follow
  the selected day. Hide live countdowns on adjacent days without fabricating
  published times.
- Support per-card mosque filtering and a single native header selector when
  multiple mosques are enabled; retain independent cards and dashboards.
- Add accessible, consistent CSS-first liquid glass to both surfaces, with
  decorative minaret/dome silhouettes, responsive mobile/tablet layouts,
  high-contrast/reduced-transparency fallbacks and preserved text selection.
- Fill the background-enabled card's allocated width and available viewport
  height with locally bundled mosque photographs; prevent date-tab/scrollbar
  changes from abruptly cropping the photograph. A full-height background may
  increase vertical space used in stacked dashboards.
- Remove the global background-photo opacity overlay and graphical editor
  control; silently discard legacy `mosque_background_opacity` on card
  configuration normalisation. Keep image selection/credits and the ability to
  disable photography.
- Refresh frontend resource/cache version, current dashboard documentation
  and responsive/browser/live Home Assistant tests.
- Squash-merged earlier change
  into `main` at [`80b8017`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/80b80173bc45257cc46fd31e81dcbaff87ab97ed).
  [Validate](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40744012961)
  and [CodeQL](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40744012733)
  passed on the merged PR head. These checks do not constitute a tagged
  release or full manual HACS acceptance.

## 0.9.6 — unreleased

- Keep tinted mosque background photographs inside the rounded Home Assistant
  card border, preventing thin bright image seams at the top and bottom on
  mobile and tablet dark themes. Add native-browser and CSS regressions.


## 0.9.5 — unreleased

- Disable unfinished Islamic-history switches in the graphical card editor.
- Allow per-card mosque visibility filters: fixed single-mosque cards or tabs among
  enabled mosques, independently on separate cards or dashboards. Preserve
  existing cards, missing sensors, and at least one enabled mosque.
- Refresh bundled frontend resource/cache versions and add regression coverage.

## 0.9.3 — unreleased

- Match Next Salah beginning, Jamaat and Fajr sunrise to the same approved, dated
  timetable row; show unavailable rather than silently borrowing today's times.
- Restore context-aware Next/Previous Jamaat: countdown before the current
  prayer's congregation and elapsed time from the exact Jamaat boundary.
- Format calculated Umm al-Qura dates using validated numeric fields and named
  Islamic months with AH/هـ eras, avoiding incorrect Android WebView Gregorian
  month and BC-era labels. Add boundary, next-day, Friday and locale regressions.


## 0.9.1 — unreleased

- Remove the optional inspected-publication-profile picker, edition catalogue,
  profile-specific parser wrapper, metadata validation, translations and its
  dedicated tests. Keep ordinary PDF/HTTPS imports, automatically detected
  strict MOSQUE_A/Mosque B layouts and all approval and safety checks.
- Continue loading older approved/staged imports containing legacy
  `publication_profile_id` metadata; omit the retired field on future saves
  without changing imported prayer data.
- List each configured mosque's actual **Prayer timetable** dashboard sensor by
  mosque name in the card editor. One reusable custom card type can be added
  more than once, with each card bound to its own mosque. Preserve stored
  selections through temporary sensor unavailability and test two cards in a
  real disposable Lovelace dashboard.
- Update the bundled card resource URL to invalidate cached 0.9.0 JavaScript,
  with matching manifest, project, frontend, import-cache and lock versions.
- Record successful full HACS removal/reinstallation and second-instance setup
  as user-reported acceptance; repeat full multi-mosque dashboard checks in CI.

## 0.9.0 — unreleased

- Add automatic or explicit English/Arabic dashboard and graphical-editor labels,
  optional bilingual prayer names, and right-to-left layouts for Arabic.
- Localize countdown/status text and regional digits while keeping Gregorian and
  calculated Umm al-Qura headers distinct and preserving published source values.
- Keep keyboard focus, text selection and countdown nodes stable across ordinary
  ticks and locale changes; retain Fajr end, Friday khutbah and mosque Hijri options.
- Remove the remaining PDF layout picker and select tested adapters automatically
  from Annual, Monthly or Ramadan. Protect both CSV and PDF monthly URL sources
  against changed date spans so earlier published months remain intact.
- Add separately locked minimum/current HA unit-suite environments, strict
  version checks and scheduled compatibility validation without changing the
  reproducible development/release lock.
- Dashboard localization is the first part of prior development. Integration-flow
  translations, reviewed Arabic wording and physical-device acceptance remain separate.

## 0.8.1 — unreleased

- Show the full calculated Umm al-Qura **Hijri date first**, including the
  actual named Islamic month. Display the secondary Gregorian date only when
  the independent per-card `show_gregorian_date` setting is enabled (default
  true for existing cards). Mosque-level and per-card Hijri visibility,
  display adjustment and Ramadan activation remain independent.
- Default PDF and HTTPS PDF import to strict automatic recognition of tested
  layouts. The user selects **Annual**, **Monthly** or **Ramadan**; the selected
  type disambiguates ordinary annual tables from a separate Ramadan page.
  A monthly import remains a partial ordinary annual source internally, but
  has its own date-span identity so subsequent nonoverlapping months do not
  delete earlier published rows. Monthly URL checks reject a silently
  changed date span.
- Fail closed for ambiguous, unsupported or mismatched publications; show
  recognized source/dates before approval. Persist the concrete detected parser
  for future URL checks,
  without changing original PDF bytes, prayer data or approval semantics.
- Add regression coverage for named Islamic month/date presentation,
  independent Gregorian visibility, multi-edition PDF recognition, single
  extraction, invalid/ambiguous layouts, staged manual upload and URL parser
  persistence.

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
- Retain the second-Jumu’ah khutbah footer on inspected MOSQUE_A annual/monthly
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
  At that historical version, explicit context/previous modes remained supported;
the card-facing mode selector was subsequently removed in 0.9.18 (see above).
- Add Gregorian and calculated Umm al-Qura Hijri dates with a per-card −3 to +3
  display adjustment, independent of Ramadan activation and source timetables.
- Add graphical compact/expanded layout, 12/24-hour time format, individual
  countdown visibility and Ramadan/timezone detail controls.
- Reconcile current dashboard, PDF support, fixture licensing and release guidance.

## 0.5.5 — unreleased

- Label published Jumu'ah congregation times in the daily Dhuhr row while retaining
  ordinary Dhuhr labels; preserve the maintainer's display fix and regression tests.
- Exercise real MOSQUE_A monthly Ramadan approval and explicit date confirmation.
- Retain CI browser diagnostics, prefer native Chrome and allow a bounded 15-second
  debugger startup. Handle private Chromium profile paths, partially written port
  files, process exits and signal failures with regression tests.

## 0.5.4

- Add live validation, HACS custom-repository and MIT license README badges.
- Support the inspected Mosque B 2026 annual PDF tables as a separate layout from
  its Ramadan page. Validate all 365 dates and 3,770 published values against an
  independent extraction; preserve missing Sehri fields and pre-noon Dhuhr values.
- Document and show the clipped May first-date interpretation before approval,
  retaining its original token. Never infer missing prayer times or activate
  Ramadan from printed Hijri headings.
- Test annual approval/reload, URL source profiles, separate Ramadan confirmation,
  daylight saving changes and tomorrow's actual Fajr through Home Assistant.

## 0.5.3

- Validate the contributed MOSQUE_A May–June 2022 monthly PDF and the separate Ramadan
  page in Mosque B Masjid's 2026 calendar with strict layout adapters and independent
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

- Support the inspected Mosque A annual PDF layout, alongside the
  strict synthetic sample layout, with explicit field meanings and fixture tests.
- Support UI URL/manual import, bounded HTTPS downloads, staged updates and
  approval while preserving the last validated source.

Earlier milestones established HACS repository structure, mosque configuration,
immutable prayer data, persistent storage, sensors and graphical CSV import.
