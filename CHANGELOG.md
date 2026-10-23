# Changelog

## 0.5.3 — unreleased

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
