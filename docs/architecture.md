# Architecture — Milestone 3

## Boundaries

- `config_flow.py`: mosque identity, UI creation, timezone options and import flow entry.
- `import_flow.py`: native HA file selector, bounded upload consumption, graphical
  column mapping and explicit approval/rejection of a durable proposal.
- `csv_parser.py`: dependency-free bounded parser. Returns a candidate; never mutates
  active HA state. PDF adapters delegate their explicit extracted columns to it.
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

The options menu offers URL sources first, manual PDF/CSV, settings, and pending review.
HA's authenticated `file_upload` dependency receives the file and returns an opaque
UUID. A single executor operation consumes and cleans up the upload context, reads
at most the format limit plus one byte, and inspects structure/encoding. The mapping flow keeps
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

Schema 3 stores `timetables`, `approved_sources`, a nullable `staged` proposal,
`remote_sources` and `remote_checks`. Migration validates legacy schema 1/2 before
writing, carries approved and pending data forward, and creates empty source metadata
where necessary rather than fabricating provenance. Unsupported versions are not
overwritten. Source checksums and coverage are revalidated on load.

Store writes are private, atomic, serialized and use off-thread JSON serialization.
Storage instances share a per-entry lock and refresh disk state before each mutation
so an old options flow cannot overwrite another runtime's newer sources.
Because HA logs some write failures without raising them, the integration compares
saved payload/version on disk before promoting memory. Tests exercise real files,
write failures, migration failures, restart, stale approvals and separate mosque stores.
A failed import leaves the last approved snapshot available. Malformed stored data
causes a setup error instead of fabricated values; restore a backup for corruption.

## Current limitations

Only the inspected Nuneaton Muslim Society annual layout and the synthetic sample
layout are supported. Other mosque PDFs are rejected. Effective Ramadan overrides,
next-event calculation and frontend assets do not exist. Ramadan candidates can be
stored but are never selected over annual records. Iftar/Taraweeh defaults are not
applied yet. DST gaps and ambiguous folds are rejected; explicit fold handling can be
added with a separate, reviewed source model. The full product is not production-ready.

## Milestone 3 additions

`source_flow.py` makes the options menu URL-first and also offers manual PDF/CSV.
Every route reuses graphical mapping and explicit persisted review. `download.py`
owns a dedicated HTTPS session/connector whose resolver validates actual connection
addresses. Redirects, body size, time, content encoding/type/signatures and HTTP
validators are bounded. No environment proxy or authenticated shared session is reused.

`pdf_parser.py` dispatches tested layouts, converts extracted values into canonical
CSV and delegates value validation to the existing parser. `pdf_worker.py` extracts
untrusted PDF text in a separate, isolated, resource-limited process. Unknown layouts
fail closed. `nms_layout.py` validates the inspected annual table: 14 pages, explicit
cover/month years, exact headings, all Gregorian dates/weekdays and 13 physical time
columns. It applies documented column meridiems, resolves same-column quotation marks
before splitting Friday Jumu’ah from ordinary Dhuhr, and retains all raw cells. The
selected field subset must keep the known meanings and 24-hour canonical format.
It does not interpret Khutbah notes or Hijri dates as scheduled congregations or
confirmed Ramadan dates. See `pdf_layouts.md`.

`source_model.py` holds immutable URL/parser profiles and allowlisted check metadata.
`source_updates.py` serializes manual and scheduled checks. A source comparison inside
the storage transaction prevents an old download from staging after its profile has
changed or been removed. Seen digest/HTTP validators are advanced only for validated
content; rejection retains the baseline without making the source active. No polling
path calls approval. An occupied pending slot is preserved. Unload cancels downloads,
joins already-started writes and removes its timer.

Storage schema **3** adds remote profiles/checks and original binary PDF provenance;
CSV candidates from schema 2 remain readable. Version 1/2 migrations preserve approved
and pending data. Original PDF bytes are base64-encoded with their byte checksum;
extracted canonical text and mapping remain distinct. Config entry options do not
contain raw files. Candidate/profile/check writes stay atomic and off the event loop.

The diagnostic source-status entity uses safe aggregate state; explicit notifications
refresh it even when daily prayer data has not changed. `diagnostics.py` exports only
allowlisted counts, kinds, years and error codes, never config-entry identity, source
URLs, HTTP validators, imported rows or original content. Logs use fixed error codes.
