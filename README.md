# Salah Timetable

A Home Assistant custom integration for mosque prayer timetables.

**Status: Milestone 2 — manual CSV import with validation and approval.**
Configure a mosque, upload a CSV, map its columns, review the coverage and approve
it through the Home Assistant UI. Published values become timestamp sensors without
YAML sensors, templates or regex configuration.

PDF parsing, URL downloads, automatic updates, Ramadan activation, next-prayer
calculations and the Lovelace card are planned; they are **not implemented**.

## Requirements and installation

Home Assistant **2026.10.0 or newer**. Development uses Python **3.14.2+** and is
tested against Home Assistant 2026.10.2. No API keys or external services are needed.

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

1. Open the mosque's **Configure → Import CSV timetable**.
2. Select a UTF-8 CSV file, its year and **Annual** or **Ramadan** kind.
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

Each source is identified by kind and year (for example `annual-2026`). An approved
import **replaces that entire source**, not just the uploaded dates. The preview
reports the existing row count before replacement. A partial replacement can remove
previously available dates; check coverage before approving. Other years remain
stored, so next year's timetable can be imported in advance and selected by date.
A mosque must be successfully loaded to import; settings remain accessible if setup
fails.

**Ramadan imports are stored and reviewed separately, but do not override annual
records yet.** Automatic/manual Ramadan activation belongs to a later milestone.

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
data does not trigger repeated sensor writes. No per-second countdown states exist.

## Storage and safety

Per-mosque files in `.storage/salah_timetable.<entry_id>` use schema version **2**.
The version 1 migration retains approved legacy timetables without inventing source
metadata. Staged CSV, checksum, coverage and original values survive restarts.
Source and canonical records are immutable; future overrides will be separate.

Writes are atomic, serialized and checked on disk before replacing in-memory data.
A failed staging, approval or rejection preserves the prior snapshot. Removing the
integration deletes its storage; unloading/restarting does not. Back up Home Assistant
normally and do not edit `.storage` manually. Retained CSV can contain unmapped source
columns, so avoid uploading private information.

File selection uses HA's authenticated upload service and opaque upload IDs, never
arbitrary paths. Reading, parsing, validation and JSON serialization run in executor
threads. Uploaded temporary files are deleted when consumed, including invalid imports.
The 512 KiB limit is this integration's acceptance limit; HA's shared upload endpoint
can receive larger temporary files before the integration rejects them.

No external source is downloaded. Files must be uploaded manually. DST gaps/folds
are rejected rather than guessed. Changing the mosque timezone revalidates records;
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

`uv.lock` fixes development dependencies. The integration has no third-party runtime
requirements beyond HA's bundled `file_upload` component. Tests use actual config
flows, registries, platforms, authenticated local HTTP uploads and atomic storage in
temporary directories. They require neither an external network nor a production HA
instance. Parser fixtures are synthetic and redistributable under this repository's
MIT license.

GitHub Actions runs pytest, lint/format checks, hassfest and HACS validation. Hosted
validation must pass before release; adding a workflow does not prove its hosted run
passed. See [architecture](docs/architecture.md), [milestones](docs/milestones.md),
and [contributing](CONTRIBUTING.md). Licensed under [MIT](LICENSE).
