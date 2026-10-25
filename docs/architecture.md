# Architecture

## Boundaries

- `config_flow.py`: mosque identity, UI creation, timezone/Ramadan options and import
  flow entry. Options updates preserve unrelated settings and reload the entry.
- `import_flow.py`: native HA file selector, bounded upload consumption, graphical
  column mapping and explicit approval/rejection of a durable proposal.
- `csv_parser.py`: dependency-free bounded parser. Returns a candidate; never mutates
  active HA state. PDF adapters delegate their explicit extracted columns to it.
- `import_model.py`: immutable source, SHA-256 provenance, coverage, warnings and
  parser protocol, selected date/field mapping and time format. Stored reports validate
  their metadata against the canonical rows.
- `model.py`: immutable dated prayer values independent of HA. Only Jumu'ah accepts
  multiple ordered times. Missing imported values remain missing.
- `storage.py`: versioned per-entry Store, staged candidate, approved sources and
  active table snapshot. Validate and persist before changing in-memory data.
- `ramadan.py`: explicit date confirmation and exact-date, immutable effective
  overrides. Published values take precedence over the documented Ramadan defaults.
- `events.py`: pure timezone-aware next/previous events and contextual Jamaat
  selection, independent of storage, UI and HA scheduling.
- `coordinator.py`: resolve yesterday/today/tomorrow in the mosque timezone, calculate
  events and schedule boundary refreshes, with no network calls. Its immutable snapshot
  also retains approved tables so changes outside that horizon notify the calendar.
- `calendar.py`: one read-only calendar per mosque, using approved effective dated
  rows, stable event UIDs and bounded timezone-aware queries. It preserves individual
  beginnings/Jamaat and multiple Jumu’ah starts with a 60-second calendar-only
  presentation interval.
- `coverage.py`: consecutive effective approved dates, cached by date/sources/Ramadan
  settings. Pending proposals never extend coverage; ambiguous dates beyond the live
  horizon stop coverage and expose `unresolved_date` without disabling valid current
  prayer events.
- `presentation.py`: serialize effective dates and absolute event timelines for the
  card without adding ticking countdown state.
- `sensor.py`: 26 entities per mosque with stable `{mosque_id}_{field}` unique IDs
  and HA registry persistence; the card's unique ID uses `{mosque_id}_dashboard`.
- `publication_profiles.py`: immutable versioned setup defaults for exact inspected
  PDF editions; validates date range, year, kind, layout and field meanings.
- `frontend.py` and `frontend/`: serve/register versioned bundled JavaScript and
  provide the responsive card, pure display helpers and graphical editor.
- `__init__.py`: typed runtime data, lifecycle, device registration and unloading.

## Import lifecycle

The options menu offers URL sources first, inspected-publication profiles, manual
PDF/CSV, mosque/Ramadan settings, and pending review.
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

Publication profiles add an explicit edition/year picker and manual PDF upload. They
require the profile's timezone without silently editing mosque settings, prefill the
existing mapping form and reuse ordinary persisted approval. Their exact date-range
contract rejects a mismatched publication. `publication_profile_id` is optional source
metadata validated against the immutable catalogue; older candidates omit it. It
survives staged/approved serialization without changing schema 3, original PDF bytes,
canonical rows or warnings. No current profile contains a verified live HTTPS URL.

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
dates. Review separately compares the proposed effective data with the adjusted
confirmed Ramadan window, including missing edge dates and annual/default fallback.
Absent source fields and unavailable effective timestamps are reported separately.

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
causes a setup error and a persistent, translated Repair with recovery guidance. The
issue contains no imported content and clears after successful recovery or entry
removal. Invalid structured files remain untouched; corrupt JSON uses HA Store’s
own recovery handling. Restore a backup rather than editing private storage.

## Downloads and PDF adapters

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
refresh it even when daily prayer data has not changed. The latest validated
checksum (`last_seen_sha256`), explicitly rejected checksum
(`rejected_sha256`), approved candidate checksum, and last successful check
are distinct. `up_to_date` requires identical validated and approved bytes
for the same configured URL; a successful check alone does not imply approval.
The rejected checksum survives unchanged/HTTP 304 checks (including restarts)
and is cleared on a new staged version or approval. Existing schema-3 checks
without a separate rejection digest stay readable; an existing `rejected`
state is upgraded on the next unchanged check. `diagnostics.py` exports only
allowlisted counts, kinds, years and error codes, never config-entry identity, source
URLs, HTTP validators, imported rows or original content. Logs use fixed error codes.

## Effective Ramadan data

Ramadan settings live in config-entry options, separately from schema 3 source
storage. Automatic activation needs an explicitly confirmed, inclusive Gregorian
range of 1–35 days. Manual on is explicit confirmation until changed; off disables
the layer. A whole-day adjustment from -3 to +3 shifts only the confirmation window.
Imported coverage and Hijri text never activate Ramadan or move a row to another date.

The resolver starts with the exact-date annual row and overlays fields from the
exact-date Ramadan row only when active. An explicit source selection resolves
overlapping Ramadan tables; ambiguous automatic selection is rejected. Missing
override fields retain annual values. A published Iftar value from either source is
preserved; otherwise effective Maghrib beginning supplies Iftar when available.
Absent published Taraweeh produces the text “After Isha Jamaat”, with no timestamp.
The immutable result retains references to the annual and Ramadan rows; neither
canonical nor original imported values are rewritten.

`ramadan_validation.py` reviews a prospective replacement without mutating storage.
It reports exact-window coverage, annual retention, default Iftar and unavailable
timestamps, plus advisory source/effective time-order warnings. The same selection
validator runs when saving Ramadan settings and, under the store lock, before
approval using the current config-entry options. Conflicts preserve both the
approved snapshot and pending proposal. No storage-schema change is required.

## Events and HA state

The pure event engine orders absolute, timezone-aware timestamps by UTC and examines
yesterday, today and tomorrow. Next Salah beginning and next Jamaat are independent.
Tomorrow's Fajr must exist in tomorrow's actual effective timetable, including across
year/leap-day boundaries. The engine never reuses today's Fajr or searches distant
dates to conceal missing coverage. Multiple Jumu'ah congregations remain individual
events associated with Dhuhr for context.

Context selects the previous congregation before a prayer begins, the upcoming
congregation after its beginning, then the previous congregation once its scheduled
instant arrives. At the exact beginning, that prayer has begun; at the exact Jamaat
instant, it is previous with zero elapsed time. A congregation has no duration.
The card can instead request unconditional previous or upcoming Jamaat. Sehri/Iftar
events are drawn only from active Ramadan dates.

The coordinator returns an immutable snapshot and schedules a UTC callback for the
next beginning, Jamaat, Sehri, Iftar or mosque-local midnight. A one-minute fallback
handles missed scheduling. Equal snapshots do not produce repeated entity writes.
Approval triggers a refresh; options changes reload the config entry. Unload cancels
the boundary callback along with HA's coordinator timers.

The calendar uses the same Ramadan resolver across actual approved stored dates,
including dates beyond the sensor event horizon and later years. Time-aware queries
are half-open `[start, end)` and limited to 366 local dates. Beginnings, Jamaat,
Sunrise and active Ramadan events retain separate stable UIDs derived from mosque ID,
date, field and UTC instant. Effective Iftar fallback is labelled separately from an
explicitly published Iftar. Missing dates produce no events; ambiguous queried dates
raise a safe error rather than choosing a source. An unresolved future date is skipped
when finding the next calendar event and remains visible through coverage diagnostics.
Calendar presentation events have 60-second intervals, so their state is briefly
on while a published instant is displayed. Start triggers retain the exact
published timestamps; end triggers are calendar-only (not prayer duration).
Queries include event-range overlaps, including across local midnight. The unique ID is
`{mosque_id}_prayer_calendar`, linked to the existing mosque device. See
[calendar behavior](calendar.md).

Optional blueprint policies remain separate from prayer calculations. Adhan controls
choose user-owned media, volume and quiet hours. Volume restoration checks playback
context/content and the still-set volume before writing. The pause/resume blueprint
captures a published anchor and explicit user delay, claims only players paused by
its own operation and resumes only unchanged claimed players. Neither policy assigns
a duration to prayer data. Single-run automations ignore overlapping triggers;
separate pause automations do not arbitrate a shared or extended pause window.

Sixteen daily timestamps, five next/previous timestamps, Ramadan/Taraweeh enums, the
source-status and coverage diagnostics, and the Prayer timetable sensor make
26 sensors per mosque, plus the prayer calendar. Daily sensors expose effective rows.
Missing event values are unavailable,
apart from the explicit Iftar default. The Prayer timetable sensor's date state and
attributes carry five prayer rows, yesterday/today/tomorrow absolute event arrays,
current next/previous selections and Ramadan details. No entity stores a per-second
countdown. The backend and card behavior have separate boundary tests.

## Bundled card lifecycle

`frontend.py` registers the bundled directory at `/salah_timetable` through HA's
asynchronous static-path API. For storage-mode Lovelace resources it creates or
updates the integration's relative module URL, removes duplicate registrations and
uses `?v=0.7.0` for cache changes. For YAML resources it uses HA's extra-JavaScript
helper without editing user YAML. Setup retries when frontend/Lovelace loads later;
a resource-registration failure is logged without disabling valid prayer entities.

The `custom:salah-timetable-card` custom element and graphical editor use the mosque's
Prayer timetable entity. The card computes countdowns/elapsed time locally from
absolute timestamps and updates countdown/progress nodes in place once per second.
Changes to the selected sensor's state or consumed attributes, HA locale, effective
timezone, connection status or card configuration rebuild the card, as do event-boundary
transitions. Equivalent sensor replacements, unrelated HA updates and ordinary ticks
preserve its static table, focus and text selection. It stops its timer
when disconnected from the DOM. Imported/user text is assigned through `textContent`.
Time labels follow the mosque timezone and HA locale; responsive CSS uses HA theme
variables without Card Mod. The editor emits standard `config-changed` events and
supports upcoming (default), context and previous modes, optional title, compact/expanded
layout, countdown/detail visibility and 12/24-hour times. The calculated Umm al-Qura
header has a per-card day adjustment and never participates in Ramadan activation.

Node tests cover helpers, rendering, safe text and editor round trips. An isolated
headless Chromium harness checks real custom-element rendering with HA element
stand-ins, narrow layouts, theme changes and editor interactions. These checks do not
prove installation in a live HA frontend or visual behavior on real phones/tablets.
An earlier disposable HA 2026.10.2 manual-install smoke verified the actual frontend
and editor, including a 0.5.0-to-0.5.1 resource upgrade. Candidate 0.6.1 also passed a
manual-install smoke on the minimum HA 2026.10.0 version, including the actual card
picker/editor and saved display options after page reload. That run explicitly
preloaded the locked PDF dependency. The subsequent 0.6.2 minimum-version run passed
20 checks, with before/after proof of fresh pinned dependency installation and no
package preload. Physical-device checks are user-confirmed complete for their latest
installation. See the
[validation record](validation.md) and [dashboard setup](dashboard.md).

## Remaining limitations

Only the documented Nuneaton Muslim Society annual/monthly, Zakariyya 2026
annual/Ramadan and synthetic sample layouts are supported. Other mosque layouts, OCR and scanned PDFs remain unsupported.
The live NMS HTTPS source is unverified. DST gaps and ambiguous folds are rejected
rather than guessed; explicit fold handling needs a separately reviewed source model.
The calculated Hijri header is display-only; users explicitly confirm Ramadan.

HACS installation, restart and updates are user-confirmed. Release hardening still
needs removal/re-addition in a test instance, full HA backup restoration, provenance
review and hosted validation for each final release commit. Physical-device completion is recorded separately from automated checks.
Invalid stored records already have actionable Repair guidance. Reproducible install
archives and synchronized metadata/cache versions are checked by release tooling. Hosted GitHub validation must be checked before release; local
tests and workflow definitions alone do not establish that it passed.
