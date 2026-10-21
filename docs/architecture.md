# Architecture — Milestone 1

## Boundaries

- `config_flow.py`: UI creation, duplicate detection and timezone options. Mosque ID
  is a user-chosen stable identity, not inferred from a URL or mutable display name.
- `model.py`: immutable dated prayer records and source tables, independent of HA.
  `PrayerField` is the canonical vocabulary; missing fields are absent. Only Jumu'ah
  accepts multiple ordered congregation times. Local times have minute precision.
- `storage.py`: a versioned HA Store per config entry. Validate all source tables
  before replacing the snapshot. No automatic migration from unknown schemas.
- `coordinator.py`: select exact annual dates in the mosque timezone. Poll only the
  in-memory local date, never external services. `always_update=False` avoids state
  writes while the record is unchanged.
- `sensor.py`: timestamp entities with `{mosque_id}_{field}` unique IDs, attached to
  the entry's mosque device. HA's registry preserves entity IDs across reloads.
- `__init__.py`: typed config-entry runtime data, lifecycle, device registration and
  cleanup. Option changes reload and revalidate storage in the new timezone.

There is deliberately no source import service in this milestone. The internal
`TimetableStorage.async_replace()` API is exercised by tests; it is not an instruction
for users to seed storage manually. A future import flow will call it only after
staging, validation and user approval, then request a coordinator refresh.

## Source model

A `Timetable` has an ID, `annual` or `ramadan` kind, and dated `DailyPrayers` rows.
Each row holds immutable canonical field/time tuples and a separate immutable mapping
of original source labels and values. Serialized dates are ISO `YYYY-MM-DD`; times
are `HH:MM`. A year is not guessed from the system date. A source may span a year
boundary. Duplicate IDs, duplicate rows and overlapping annual dates are rejected.
The accepted model is not a claim of a working parser or complete annual coverage.

Future parser results should include source provenance, warnings, coverage reports
and a content digest in a staging model. Keep imported source records immutable;
compute effective Ramadan/manual overrides in a separate selection layer. Introduce
an explicit storage migration if the persisted schema changes.

## Persistence and errors

The HA Store uses atomic writes, private file permissions, and off-thread JSON
serialization. Replacement validation and serialization also run in the executor.
A lock serializes replacements. Because HA Store logs some write failures without
raising them, replacements verify the saved payload directly from disk before
promoting in-memory data. A mocked successful call is not sufficient evidence of
persistence. Tests exercise actual files and injected write failures.

Malformed records cause a config-entry setup error instead of silently creating
invented values. Stored data is retained for recovery. HA handles logging for setup
and filesystem failures. Unknown storage versions are not overwritten. Filesystem
corruption cannot be repaired automatically; restore a backup if necessary.

Timezone changes reinterpret the published wall-clock times and revalidate them.
If that creates an ambiguous/nonexistent event, setup fails without rewriting the
source. Explicit fold selection and timezone-change confirmation can be added with
the import review UI; this release rejects both folds as ambiguous.

## Deliberate limitations

No next-event engine, Ramadan resolution, countdowns, import/download code, frontend
assets, diagnostics download handler or external network access exists yet. The full
product is not production-ready. Missing data always remains unavailable. The next
milestones must preserve these guarantees and add fixture-based parser acceptance
tests before advertising any PDF layout compatibility.
