# Salah Timetable

A Home Assistant custom integration for mosque prayer timetables.

**Status: Milestone 1 — development foundation, not yet a timetable importer.**
UI setup, per-mosque devices, versioned storage and timestamp sensors are implemented
and tested. There is no PDF/CSV import UI, URL downloader, automatic update service,
Ramadan activation, next-prayer calculation or Lovelace card yet. A newly configured
mosque has unavailable sensors until a future import feature supplies validated data.
Do not use this initial release as your source of prayer times.

## Requirements and installation

Home Assistant **2026.10.0 or newer**. Development uses Python **3.14.2+** and is
tested against Home Assistant 2026.10.2. No API keys or external services are needed.

### HACS custom repository

1. In HACS, open **Custom repositories**.
2. Add `https://github.com/anaschillin/home-assistant-salah-timetable` with type **Integration**.
3. Download **Salah Timetable** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Salah Timetable**.
5. Enter a mosque name, a stable mosque ID and an IANA timezone such as `Europe/London`.

This repository uses the HACS integration layout; it is not claimed to be in the
default HACS catalogue. These instructions apply once the changes are published to
GitHub. For manual installation, copy `custom_components/salah_timetable` into
Home Assistant's `config/custom_components/` directory and restart.

Each distinct mosque ID creates one config entry and one device. IDs use letters,
numbers, underscores and hyphens; case and surrounding whitespace are normalized.
Use the same ID to avoid duplicate configuration. Display names may be the same
for different mosques. The ID is immutable; changing a timezone through **Configure**
reloads the entry without changing unique IDs or registered entity IDs. Home Assistant
allows users to rename entity IDs independently.

No YAML, templates, regex configuration or manually created sensors are required.

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

Missing dates or fields make their sensors **unavailable**. No time is calculated or
filled in. In particular, Iftar and Taraweeh defaults belong to the later Ramadan
milestone. A Jamaat timestamp represents a single scheduled event, not an interval.
These are today's events, **not next-event sensors**.

A shared coordinator checks the local date once per minute, so midnight selection
can take up to one minute. Equal daily data does not trigger repeated sensor writes.
No per-second countdown states are produced.

## Storage and safety

Validated records use explicit Gregorian dates, allowing multiple years and leap days.
Annual sources cannot overlap on the same date. Ramadan sources are stored separately
and are never implicitly applied. Original source labels and values are retained
separately from normalized times; there is no override mutation in this milestone.

Per-entry files live in Home Assistant's `.storage/salah_timetable.<entry_id>` and
use schema version 1. Writes are atomic, serialized, and checked on disk before the
active snapshot is replaced. A failed save preserves the prior snapshot. Removal of
the integration deletes its timetable storage; unloading or restarting does not.
Back up Home Assistant normally. Do not manually edit `.storage` files.

Times must be explicit 24-hour `HH:MM`. Nonexistent and ambiguous local times at DST
transitions are rejected rather than guessed. Terminology normalization recognizes
Zuhr/Zohar/Dhuhr, Asr/Asar and Isha/Esha, but does not infer which column is beginning
or Jamaat. Quotation-mark repetition is not parsed in this milestone.

There are **no outbound downloads** in this release. Download safety, parser limits,
staged validation and approval are requirements for the import milestones, not
claims about implemented functionality.

## Development

```sh
# From the repository root; uv installs the matching Python if necessary.
uv sync --frozen --group dev
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
```

`uv.lock` fixes the development dependency graph. The integration itself has no
third-party runtime requirements beyond Home Assistant. Tests use real Home Assistant
config flows, registries, platforms and atomic filesystem storage in isolated temporary
directories; they do not start a production HA instance or access the network.

GitHub Actions runs pytest, lint/format checks, Home Assistant hassfest and HACS
validation on pushes and pull requests. Hosted validation must pass before release;
adding a workflow does not establish that its hosted run passed.

See [architecture](docs/architecture.md), [milestones](docs/milestones.md), and
[contributing](CONTRIBUTING.md). Licensed under [MIT](LICENSE).
