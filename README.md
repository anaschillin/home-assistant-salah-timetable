# Salah Timetable

[![Validate](https://github.com/anaschillin/home-assistant-salah-timetable/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/anaschillin/home-assistant-salah-timetable/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5)](#requirements-and-installation)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A Home Assistant custom integration for mosque prayer timetables.

**Status: Milestones 1–5 implemented — imports, event calculations, Ramadan and a bundled dashboard card.**
Configure a mosque, add a public HTTPS PDF/CSV source or upload a file, map columns,
and approve a validated timetable in the Home Assistant UI. Changes are never
activated automatically. No YAML sensors, templates or regex setup are required.

**PDF compatibility is limited to documented layouts.** The inspected Nuneaton Muslim
Society annual and monthly calendars, Zakariyya Masjid’s 2026 annual tables and
separate Ramadan page, and the synthetic sample layout are validated. Other editions
and mosque layouts are unsupported. See [supported PDF layouts](docs/pdf_layouts.md).

The integration includes independent next-Salah/next-Jamaat events, confirmed-date
Ramadan overrides and a graphical Lovelace card. A disposable Home Assistant runtime
and real frontend have passed the [recorded checks](docs/validation.md). HACS
installation and further release acceptance remain. See [milestones](docs/milestones.md),
the [remaining work](docs/remaining-work.md), and the [release checklist](docs/releasing.md).

## Requirements and installation

Home Assistant **2026.10.0 or newer**. Development uses Python **3.14.2+** and is
tested against Home Assistant 2026.10.2. The integration requires no API keys;
setting up HACS requires its separate GitHub authorization. URL sources require
HTTPS Internet access. PDF extraction
requires Linux/POSIX process resource limits (as provided by supported HA systems).

Install and configure HACS first, following its
[initial setup guide](https://www.hacs.xyz/docs/use/configuration/basic/).
Then use its [custom repository route](https://www.hacs.xyz/docs/faq/custom_repositories/):

1. In HACS, open the three-dot menu and choose **Custom repositories**.
2. Add `https://github.com/anaschillin/home-assistant-salah-timetable` with type **Integration**.
3. Download **Salah Timetable** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Salah Timetable**.
5. Enter a mosque name, a stable mosque ID and an IANA timezone such as `Europe/London`.

The repository uses the HACS integration layout; it is not claimed to be in the
default HACS catalogue. Authenticated HACS installation of this integration remains
an acceptance check; the recorded live tests used manual installation.
For manual installation, copy `custom_components/salah_timetable`
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

Ramadan imports are stored and reviewed separately. After approval, use
**Configure → Ramadan settings** to confirm when they may override annual records.

## Ramadan settings

- **Automatic** activates Ramadan only within the confirmed Gregorian start/end
  dates, inclusive. Supply both dates or leave both empty; an empty range is inactive.
  A confirmed range may span 1–35 days. Imported coverage and printed Hijri dates do
  not confirm Ramadan.
- **Manual on** is explicit activation until changed and ignores the date window.
  **Off** disables Ramadan overrides and defaults.
- **Date adjustment** shifts the confirmed window by a whole number from -3 to +3
  days. It does not move timetable rows to another date.
- **Ramadan timetable source** can use the unique matching source or an explicitly
  selected imported Ramadan table. Overlapping sources require a selection.

During Ramadan, published fields from the matching Ramadan date override the same
annual date; other annual fields remain. Missing Ramadan dates never reuse another
day's values. A separate published Iftar time is retained; otherwise effective Iftar
uses Maghrib beginning when available. Without a published Taraweeh time, the card
shows **After Isha Jamaat** and the Taraweeh timestamp remains unavailable. Original
imported values are kept separately from these effective values.

Import review compares the proposed data with the adjusted confirmed window and
shows annual fallback, default Iftar and unavailable timestamps separately. Source
and effective time-order conflicts are warnings; values are never corrected.
Ambiguous active sources block approval while retaining the approved data and
pending proposal. A printed Ramadan heading or 31-row table does not confirm the
month’s dates. See [Ramadan validation](docs/ramadan_validation.md).

## Dashboard

The integration bundles the **Salah Timetable** Lovelace card and its graphical
editor. After importing a timetable, edit a dashboard, add the card and choose the
mosque's **Prayer timetable** sensor. Choose **Upcoming Jamaat** (default), **Context aware** or **Previous Jamaat**. No separate card download or Card Mod is required.

The card shows Gregorian and calculated Umm al-Qura Hijri dates, independent Salah
and Jamaat countdowns with progress, highlighted prayer rows and active Ramadan details.
Its editor offers compact/expanded layouts, individual countdown visibility, 12/24-hour
times, a Hijri display-day adjustment and additional-detail controls. The Hijri
adjustment is independent of Ramadan activation and never changes timetable data.
Countdowns run in the browser from absolute timestamps, without per-second Home
Assistant state writes. The card follows HA's theme
and uses responsive layouts. Ordinary ticks update clocks and progress in place;
unrelated Home Assistant updates preserve the rendered card. See
[dashboard setup and behavior](docs/dashboard.md)
for resource troubleshooting and the event boundary rules.

## Automations and coverage alerts

Import the optional Adhan, before-Jamaat, Sehri and timetable-health blueprints
through Home Assistant's Blueprints screen. Select the mosque's timestamp sensors,
your own recording/speakers or reminder actions. The **Timetable coverage** diagnostic
reports consecutive approved dates and warns when coverage is missing or nearing
its end; pending proposals never extend it. See [setup and behavior](docs/automations.md).

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

Only layouts listed in [PDF layouts](docs/pdf_layouts.md) are supported. Select
**Nuneaton Muslim Society annual calendar (v1)** for the supplied 2026 calendar,
Annual kind, year 2026 and 24-hour format. Date/prayer mappings are preselected; check
the review before approval. Its 365 dates and 5,110 event values were compared with an
independent extraction. Additional real fixtures validate the NMS May–June 2022
monthly layout, all twelve annual tables and the separate Ramadan page in
Zakariyya’s 2026 calendar. Its annual adapter validates 365 dates and 3,770 published
values; review explicitly explains the clipped May first-date label. The
`pdf_table_v1` adapter remains a separate synthetic sample, not a general recognizer. Unknown
layouts, scanned/image-only PDFs, encrypted and corrupt documents are rejected.
There is no OCR or fallback that guesses a missing time.

For NMS, Dawn supplies Fajr beginning; Sehri Ends is separate. Sunset supplies
Maghrib beginning, while the distinct published Maghrib (Iftaar) cell supplies both
Jamaat and Iftar. Friday's shared Dhuhr/Jumu’ah slot supplies Jumu’ah only. Second-
Khutbah notes are not imported as congregation times, and Hijri dates do not confirm
Ramadan activation. No Taraweeh time is invented. The adapter documents its fixed
morning/noon/evening interpretation of the printed 12-hour columns.

The supplied reference PDF validates manual import. The website's live HTTPS
availability
has not been verified; the supplied HTTP URL is not accepted by the secure downloader.

PDF input is limited to **4 MiB, 16 pages and 256 KiB extracted text**. Extraction
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

## Entities and event behavior

Each mosque creates 26 sensors. Sixteen expose **today's effective event timestamps** in the mosque timezone.
Home Assistant stores/displays these according to its standard timestamp behavior.

| Prayer or event | Sensors |
| --- | --- |
| Fajr, Dhuhr, Asr, Maghrib, Isha | Beginning and Jamaat for each |
| Sunrise | Published time |
| Sehri ends | Published time |
| Jumu'ah | First congregation; all congregations in `scheduled_times` |
| Istewa/noon | Published time |
| Iftar | Published time, or Maghrib beginning during active Ramadan |
| Taraweeh | Published time, only when explicitly provided |

The remaining sensors are **Next Salah**, **Next Jamaat**, **Previous Jamaat**,
**Next Sehri**, **Next Iftar**, **Ramadan status**, **Taraweeh status**, the diagnostic
**Source status**, diagnostic **Timetable coverage**, and **Prayer timetable** for
the bundled card. Next Sehri/Iftar consider active Ramadan dates only. The dashboard sensor contains the local date and
absolute event data; select it in the card editor instead of an individual prayer.

Next Salah beginning and next Jamaat are calculated independently. In context mode,
the card follows the latest published prayer beginning: it shows the next
congregation for that prayer and date while one remains, otherwise the previous
Jamaat with elapsed time. This includes successive Jumu'ah congregations.
At an exact Jamaat time that event becomes previous, while a later congregation
for the same prayer can keep the context panel upcoming. Jamaat has no start/end
interval.
After Isha, next Salah uses tomorrow's actual Fajr. Calculations inspect yesterday,
today and tomorrow; missing future data stays unavailable rather than extrapolated.

Missing dates or fields make their event sensors **unavailable**, apart from the
explicit Ramadan Iftar default above. No missing prayer times are invented. A shared
coordinator refreshes at event boundaries and mosque-local midnight, with a one-minute
fallback. Approval refreshes immediately; options changes reload the entry. Equal
data does not trigger repeated sensor writes. No per-second countdown states exist.

## Storage and safety

Per-mosque files in `.storage/salah_timetable.<entry_id>` use schema version **3**.
Version 1/2 migrations retain approved and pending data without inventing source
metadata. Staged files, checksums, coverage, source settings and original values survive
restarts.
Source and canonical records are immutable. Ramadan options are stored in the config
entry; effective overrides are computed separately without rewriting imported rows.

Writes are atomic, serialized and checked on disk before replacing in-memory data.
A failed staging, approval or rejection preserves the prior snapshot. Invalid stored
records create a Home Assistant Repair with recovery guidance and remain untouched;
the issue clears after recovery or removal. HA handles corrupt JSON through its own
storage recovery mechanism. Removing the integration deletes its storage;
unloading/restarting does not. Back up Home Assistant normally and do not edit `.storage` manually. Retained CSV can contain unmapped source
columns, so avoid uploading private information.

File selection uses HA's authenticated upload service and opaque upload IDs, never
arbitrary paths. Reading, parsing, validation and JSON serialization run in executor
threads. Uploaded temporary files are deleted when consumed, including invalid imports.
CSV's 512 KiB and PDF's 4 MiB limits are acceptance limits; HA's shared upload endpoint
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
npm test
# Requires Chromium/Chrome; set CHROME_BIN if it is not on a standard path.
REQUIRE_BROWSER_TESTS=1 npm run test:browser
uv run --frozen python scripts/build_release.py --check
```

`uv.lock` fixes development dependencies. The integration uses HA's bundled
`file_upload` component and pinned `pypdf==6.21.1`. Tests use actual config
flows, registries, platforms, authenticated local HTTP uploads and atomic storage in
temporary directories. Transport tests mock remote responses and exercise real connector resolution; PDF
fixtures execute the isolated worker. The suite requires no external network or
production HA instance. Worker execution is black-box tested; its isolated process
intentionally does not inherit coverage/environment instrumentation. Event tests cover
exact boundaries, Friday congregations, DST and year/leap-day transitions. Frontend
tests use Node and an isolated headless Chromium harness with HA element stand-ins.
The required live HA matrix checks the minimum/current supported runtime versions;
local 0.6.2 acceptance also verified fresh dependency installation and real editor
controls. Physical-device checks are user-confirmed complete on their latest
installation. Authenticated HACS installation remains separate acceptance work;
see the [validation record](docs/validation.md).
Synthetic parser fixtures use this repository's MIT license. Contributed real
publications have separate provenance and require redistribution review; see the
[fixture notes](tests/fixtures/pdf/README.md).

GitHub Actions runs pytest, frontend tests, lint/format checks, hassfest and HACS
validation, and builds an install archive with a checksum. Hosted validation must
pass before release; adding a workflow does not prove its hosted run
passed. See [architecture](docs/architecture.md), [milestones](docs/milestones.md),
[dashboard documentation](docs/dashboard.md), [support policy](docs/support.md),
and [contributing](CONTRIBUTING.md).
Licensed under [MIT](LICENSE).
