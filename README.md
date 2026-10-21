# Salah Timetable

A Home Assistant custom integration for mosque prayer timetables.

**Status: Milestone 3 infrastructure — secure URL sources and staged update checks.**
Configure a mosque, add a public HTTPS PDF/CSV source or upload a file, map columns,
and approve a validated timetable in the Home Assistant UI. Changes are never
activated automatically. No YAML sensors, templates or regex setup are required.

**PDF compatibility is limited to the documented synthetic sample layout.** The
requested NMS UK timetable has not yet been downloaded/inspected, so compatibility
with it is not claimed. See [supported PDF layouts](docs/pdf_layouts.md).

Ramadan activation, next-prayer calculations and the Lovelace card remain planned.

## Requirements and installation

Home Assistant **2026.10.0 or newer**. Development uses Python **3.14.2+** and is
tested against Home Assistant 2026.10.2. No API keys are needed. URL sources require HTTPS Internet access. PDF extraction
requires Linux/POSIX process resource limits (as provided by supported HA systems).

1. In HACS, open **Custom repositories**.
2. Add `https://github.com/anaschillin/home-assistant-salah-timetable` with type **Integration**.
3. Download **Salah Timetable** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Salah Timetable**.
5. Enter a mosque name, a stable mosque ID and an IANA timezone such as `Europe/London`.

The repository uses the HACS integration layout; it is not claimed to be in the
default HACS catalogue. For manual installation, copy `custom_components/salah_timetable`
into Home Assistant's `config/custom_components/` directory and restart.

Each distinct mosque ID creates one config entry and one device. IDs use letters,
numbers, underscores and hyphens; case and surrounding whitespace are normalized.
Use the same ID to avoid duplicate configuration. Display names may be the same for
different mosques. IDs are immutable. **Configure → Mosque settings** changes the
mosque timezone without changing registered unique IDs or entity IDs. Home Assistant
allows users to rename entity IDs independently.

## Import a timetable

1. Open the mosque's **Configure → Add or replace a URL source (recommended)**.
2. Enter a public HTTPS URL, PDF/CSV type, explicit year and Annual/Ramadan kind.
   Select a documented PDF layout. Alternatively use **Upload a supported PDF** or
   **Import CSV timetable**. CSV does not use the PDF-layout selection.
3. Select the date column and each published prayer column. Recognized headings are
   suggested, but check every mapping. Leave fields without published times unselected.
4. Choose **24-hour HH:MM** or **Explicit HH:MM AM/PM**. No AM/PM is inferred.
5. Review dates, missing fields, warnings, sample times, checksum and replacement scope.
6. Choose **Approve and save timetable**, or **Reject and keep the active timetable**.

Nothing becomes active before approval. Closing/cancelling after the preview leaves
the staged import available under **Configure → Review pending import**, including
after a Home Assistant restart. Review or reject it before uploading another file.
Closing before the preview discards the in-progress mapping; upload the file again.
A saving error keeps the existing timetable; check Home Assistant logs and retry.
For a URL import, the reproducible source settings are saved with the staged file.
The UI's source-import menu is URL-first after initial mosque identity setup.

Each source is identified by kind and year (for example `annual-2026`). An approved
import **replaces that entire source**, not just the uploaded dates. The preview
reports the existing row count before replacement. A partial replacement can remove
previously available dates; check coverage before approving. Other years remain
stored, so next year's timetable can be imported in advance and selected by date.
A mosque must be successfully loaded to import; settings remain accessible if setup
fails.

**Ramadan imports are stored and reviewed separately, but do not override annual
records yet.** Automatic/manual Ramadan activation belongs to a later milestone.

## URL checking and approval

Configured URL sources are checked daily, with persisted check times used to catch
up after restarts. **Configure → Check URL sources now** runs a manual check.
The **Source status** diagnostic sensor reports configured/up-to-date/pending/error
state and safe timestamps/counts. Failed downloads or parses preserve approved data.

Checks use ETag/Last-Modified when a valid seen-file baseline exists, and compare
SHA-256 bytes. Changed, valid content is staged, never auto-activated. A pending
proposal blocks other changes from replacing its review slot. Rejection preserves
the seen digest, so the same rejected file is not proposed repeatedly. A later
changed source is reviewed again. Invalid content does not advance the baseline.

**Manage URL sources** can check or remove a source. Removal stops its future checks
and retains approved data. Import a new URL for the same kind/year to change source
settings. Source profiles, validators, check status and pending proposals survive a
restart; running requests and timers do not.

Public HTTPS on port 443 is required. Credentials, HTTP, local/private/link-local/
reserved destinations and unsafe redirects are rejected. All resolved addresses are
checked by the resolver used for the actual connection, including after redirects;
this avoids a separate DNS preflight/rebinding gap. TLS verification stays enabled.
Downloads use an isolated session with no inherited cookies, credentials or environment
proxies. Deployments that require an outbound proxy are not supported by this path.
At most three redirects and 30 seconds are allowed; compressed HTTP responses,
misleading content types/signatures and oversized streamed bodies are rejected.

## PDF format and limits

Only layouts listed in [PDF layouts](docs/pdf_layouts.md) are supported. The current
`pdf_table_v1` adapter has original synthetic golden fixtures; it is not a general
PDF-to-table recognizer and is not evidence of real mosque compatibility. Unknown
layouts, scanned/image-only PDFs, encrypted and corrupt documents are rejected.
There is no OCR or fallback that guesses a missing time.

PDF input is limited to **2 MiB, 16 pages and 256 KiB extracted text**. Extraction
runs outside HA's event loop in an isolated Python worker using pinned pypdf, with
an 8-second wall limit, CPU/memory limits and decompression guards. Original binary
PDF, checksum, extracted canonical values and selected mapping are retained.

## CSV format

```csv
Date,Fajr Start,Fajr Jamaat,Sunrise,Zuhr Begin,Zuhr Jamaat
2026-01-01,06:15,06:45,08:10,12:15,13:00
2026-01-02,06:15,"""",08:10,12:15,13:00
```

The second row's four double quotes are the standard CSV encoding of one literal
quotation-mark cell. It repeats only the previous explicit value in that Jamaat
column. A blank resets the preceding value; a quotation mark without a preceding
explicit value is rejected. Beginning times and unrelated fields never use ditto
resolution. Curly quotation marks and the double-prime mark are also recognized.

- Comma-separated UTF-8, with or without BOM, and one unique nonempty header row.
- One date per row: exact `YYYY-MM-DD`, increasing order, all within the chosen year.
- At most **512 KiB**, **366 dated rows**, **32 columns**, **256 characters per cell**.
- Exact zero-padded `HH:MM`, or `HH:MM AM/PM` when explicitly selected. Do not mix formats.
- Multiple Jumu’ah times use a semicolon, for example `01:00 PM;02:00 PM`. Values must
  be unique and increasing. Other fields accept one time.
- Empty prayer cells stay missing. Each row needs at least one mapped published time.
- Alternate headings (Zuhr/Zohar/Dhuhr, Asr/Asar, Isha/Esha) are suggested in mapping.
  Any unique heading can be selected manually; its meaning is never guessed silently.
- Annual coverage warnings compare against the entire declared year, including leap
  day. Ramadan coverage warnings compare the first and last supplied dates; these
  are **not** a confirmation of Ramadan dates.

See [CSV examples](examples/) for a small, synthetic example. Missing dates/fields
are warnings that require review; malformed dates/times, duplicates, ambiguous DST
events, invalid encoding, oversized input and unresolved ditto values block staging.
Unmapped columns and original imported strings remain stored alongside parsed values.

## Current entities

Sixteen sensors expose **today's absolute event timestamps** in the mosque timezone.
Home Assistant stores/displays these according to its standard timestamp behavior.

| Prayer or event | Sensors |
| --- | --- |
| Fajr, Dhuhr, Asr, Maghrib, Isha | Beginning and Jamaat for each |
| Sunrise | Published time |
| Sehri ends | Published time |
| Jumu'ah | First congregation; all congregations in `scheduled_times` |
| Istewa/noon | Published time |
| Iftar | Published time |
| Taraweeh | Published time, only when explicitly provided |

Missing dates or fields make their sensors **unavailable**. No times are calculated
or filled in. Iftar and Taraweeh defaults belong to the later Ramadan milestone.
Jamaat is a single scheduled event, not an interval. These are today's events,
**not next-event sensors**. New mosques have unavailable sensors until approval.

A shared coordinator checks the mosque-local date once per minute, so midnight
selection can take up to one minute. Approval requests an immediate refresh. Equal
data does not trigger repeated sensor writes. No per-second countdown states exist. A seventeenth diagnostic sensor reports URL
source status; it is separate from the sixteen prayer-event sensors.

## Storage and safety

Per-mosque files in `.storage/salah_timetable.<entry_id>` use schema version **3**.
Version 1/2 migrations retain approved and pending data without inventing source
metadata. Staged files, checksums, coverage, source settings and original values survive
restarts.
Source and canonical records are immutable; future overrides will be separate.

Writes are atomic, serialized and checked on disk before replacing in-memory data.
A failed staging, approval or rejection preserves the prior snapshot. Removing the
integration deletes its storage; unloading/restarting does not. Back up Home Assistant
normally and do not edit `.storage` manually. Retained CSV can contain unmapped source
columns, so avoid uploading private information.

File selection uses HA's authenticated upload service and opaque upload IDs, never
arbitrary paths. Reading, parsing, validation and JSON serialization run in executor
threads. Uploaded temporary files are deleted when consumed, including invalid imports.
CSV's 512 KiB and PDF's 2 MiB limits are acceptance limits; HA's shared upload endpoint
can receive larger temporary files before the integration rejects them. Diagnostics
include allowlisted counts/status only, not mosque identity, URLs, raw files or values.
Source URLs may contain private query parameters: they are not included in logs or
diagnostic downloads, but remain in private HA storage.

Downloaded PDF/CSV bytes receive the same validation and approval as manual imports.
DST gaps/folds are rejected rather than guessed. Changing the mosque timezone revalidates records;
if setup then fails, choose the correct timezone in Mosque settings without rewriting
the original source.

## Development

```sh
# From the repository root; uv installs the matching Python if necessary.
uv sync --frozen --group dev
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
```

`uv.lock` fixes development dependencies. The integration uses HA's bundled
`file_upload` component and pinned `pypdf==6.21.1`. Tests use actual config
flows, registries, platforms, authenticated local HTTP uploads and atomic storage in
temporary directories. Transport tests mock remote responses and exercise real connector resolution; PDF
fixtures execute the isolated worker. The suite requires no external network or
production HA instance. Worker execution is black-box tested; its isolated process
intentionally does not inherit coverage/environment instrumentation. Parser fixtures are synthetic and redistributable under this repository's
MIT license.

GitHub Actions runs pytest, lint/format checks, hassfest and HACS validation. Hosted
validation must pass before release; adding a workflow does not prove its hosted run
passed. See [architecture](docs/architecture.md), [milestones](docs/milestones.md),
and [contributing](CONTRIBUTING.md). Licensed under [MIT](LICENSE).
