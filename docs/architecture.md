# Architecture — Milestone 2

## Boundaries

- `config_flow.py`: mosque identity, UI creation, timezone options and import flow entry.
- `import_flow.py`: native HA file selector, bounded upload consumption, graphical
  column mapping and explicit approval/rejection of a durable proposal.
- `csv_parser.py`: dependency-free bounded parser. Returns a candidate; never mutates
  active HA state. Future PDF adapters can implement the same parser protocol.
- `import_model.py`: immutable source, SHA-256 provenance, coverage, warnings and
  parser protocol, selected date/field mapping and time format. Stored reports validate
  their metadata against the canonical rows.
- `model.py`: immutable dated prayer values independent of HA. Only Jumu'ah accepts
  multiple ordered times. No absent prayer value is inferred.
- `storage.py`: versioned per-entry Store, staged candidate, approved sources and
  active table snapshot. Validate and persist before changing in-memory data.
- `coordinator.py`: select annual records by mosque-local date, with no network calls.
- `sensor.py`: timestamp entities with `{mosque_id}_{field}` unique IDs and HA registry
  persistence. `__init__.py` owns typed runtime data, lifecycle/device registration.

## Import lifecycle

The options menu offers settings, CSV import, and review when a candidate is staged.
HA's authenticated `file_upload` dependency receives the file and returns an opaque
UUID. A single executor operation consumes and cleans up the upload context, reads
at most 512 KiB plus one byte, and inspects CSV shape/encoding. The mapping flow keeps
only bounded content in memory until the user selects explicit date/prayer columns,
year, kind and time format. Parsing and timezone validation occur off the event loop.

Staging writes a candidate with a random identity without changing active records.
The review shows coverage, missing counts, source hash, sample values and replacement
scope. Approval atomically replaces the same kind/year source and clears staging;
other years remain available. Rejection clears staging and retains active data.
Closing the review leaves the proposal durable. A resumed flow reads it from storage.
A stale preview identity cannot approve/reject a different proposal. A pending proposal
cannot be overwritten by another concurrent import.

Options import/review requires a loaded config entry so every operation uses its shared
storage lock. Timezone settings remain accessible when the integration is not loaded.
The coordinator refreshes immediately after approval. Unchanged settings are preserved.

## Source and coverage

Canonical date rows retain original CSV cells separately from parsed times; raw CSV
text, including any BOM, is stored with an exact UTF-8 SHA-256 digest. Annual and
Ramadan sources remain distinct. User confirmation of an explicit year avoids
system-date inference. Sources are keyed by kind/year; replacement is whole-source,
not a row merge. Legacy IDs are retained during migration; overlapping legacy annual
sources are rejected rather than overwritten through an unrelated import ID.

Dates are strict ISO and increasing. Times must match the explicitly selected 24-hour
or AM/PM format. Jamaat ditto markers resolve only in their own column from a prior
explicit value and reset on blanks; they never fill missing beginnings. Coverage counts
missing fields per supplied row. Annual missing dates span the declared calendar year;
Ramadan missing dates span only the first/last supplied dates and do not confirm lunar
dates. All gaps are visible and absent times remain unavailable.

## Persistence and failures

Schema 2 stores `timetables`, `approved_sources` and a nullable `staged` proposal. The
HA Store migration validates schema 1 before writing, carries its timetables forward,
and creates empty source metadata rather than fabricating provenance. Unsupported
versions are not overwritten. Source checksums and coverage are revalidated on load.

Store writes are private, atomic, serialized and use off-thread JSON serialization.
Storage instances share a per-entry lock and refresh disk state before each mutation
so an old options flow cannot overwrite another runtime's newer sources.
Because HA logs some write failures without raising them, the integration compares
saved payload/version on disk before promoting memory. Tests exercise real files,
write failures, migration failures, restart, stale approvals and separate mosque stores.
A failed import leaves the last approved snapshot available. Malformed stored data
causes a setup error instead of fabricated values; restore a backup for corruption.

## Current limitations

No network downloader, PDF parser, effective Ramadan overrides, next-event engine,
frontend assets or diagnostics download handler exists. Ramadan candidates can be
stored but are never selected over annual records. Iftar/Taraweeh defaults are not
applied yet. DST gaps and ambiguous folds are rejected; explicit fold handling can be
added with a separate, reviewed source model. The full product is not production-ready.
