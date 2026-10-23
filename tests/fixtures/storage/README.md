# Historical storage fixtures

These are synthetic records created with the repository's historical code, frozen
as JSON instead of being rebuilt by the current parser during tests. They contain
no real mosque timetable or personal data and use the repository's MIT license.

- `v1_multi_year.json` uses the `DailyPrayers`/`Timetable` serializers from foundation
  commit `8430623`. Its legacy source ID spans 2026 and 2027 and has no import
  provenance, approval metadata or pending source.
- `v2_approved_pending.json` uses `CsvParser` and candidate serializers from schema-2
  commit `722c17b`. It contains an approved annual source with a UTF-8 BOM, an
  unmapped synthetic note and a quoted Jamaat ditto, plus a pending replacement
  with fixed stage ID `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`. Both source checksums,
  coverage reports and warning strings are those emitted by that historical code.

The files contain the Store `data` payload. Tests add the entry-specific storage
key and historical envelope version. Tests must not regenerate the legacy fields
from today's parser, since that would hide backwards-compatibility regressions.
