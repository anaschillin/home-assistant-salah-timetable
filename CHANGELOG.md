# Changelog

## 0.5.0 — unreleased

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
