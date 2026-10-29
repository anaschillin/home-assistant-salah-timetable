# Salah Timetable

[![Validate](https://github.com/anaschillin/home-assistant-salah-timetable/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/anaschillin/home-assistant-salah-timetable/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Current integration version: **<!-- docs:version -->0.9.19<!-- /docs:version -->**.

A Home Assistant custom integration for importing **published mosque Salah and Jamaat timetables**. Configure one or more mosques, import a supported PDF/CSV or public HTTPS source, explicitly approve the timetable, and display it with a bundled Lovelace card.

## Features

- Separate mosque configurations, sensors, independent next-Salah and next-Jamaat countdowns, and a prayer calendar.
- Annual, monthly and Ramadan sources; automatic recognition of **supported** PDF layouts, source comparison and approval before activation.
- Compact, standard and detailed responsive cards with multiple mosque selection, Yesterday/Today/Tomorrow navigation, Gregorian/Hijri dates and optional mosque photography.
- Optional prayer, media and timetable-coverage automation blueprints.

**Important:** Values come from approved publications; this integration does not calculate authoritative prayer schedules or invent missing times. Only [documented PDF layouts](docs/import_review.md#supported-pdf-layouts) are supported.

## Install

Home Assistant **<!-- docs:homeassistant_min -->2026.10.0<!-- /docs:homeassistant_min --> or newer** is required. The integration is available through a **HACS custom repository** (not claimed to be in the default catalogue).

1. In HACS choose **Custom repositories**, enter `https://github.com/anaschillin/home-assistant-salah-timetable` and select **Integration**.
2. Download **Salah Timetable** and restart Home Assistant.
3. Choose **Settings → Devices & services → Add integration → Salah Timetable**, then add a mosque ID, name and IANA timezone.
4. Use **Configure** to import a timetable, review its dates and mappings, and approve it.
5. Choose **Edit dashboard → Add card → Salah Timetable** and select a Prayer timetable sensor.

Manual installation: copy `custom_components/salah_timetable` into Home Assistant's `config/custom_components/` folder and restart.

## Documentation

| Guide | Contents |
| --- | --- |
| [Getting started](docs/getting-started.md) | Detailed setup, first import and troubleshooting |
| [Dashboard](docs/dashboard.md) | Card options and multiple mosques |
| [Importing and validation](docs/import_review.md) | PDF layouts, timetable review, Ramadan and source updates |
| [Automations](docs/automations.md) | Blueprints and coverage alerts |
| [Architecture](docs/architecture.md) | Internal design for contributors |
| [Testing](docs/testing.md) | Tests, coverage and development |
| [Releasing](docs/releasing.md) | Release workflow and sign-off |
| [Roadmap](docs/roadmap.md) | Future plans only |
| [Assets and credits](docs/asset-provenance.md) | Source checks, image licensing and fixture provenance |
| [Islamic history research](research/islamic-history/islamic-history-source-audit.md) | Research proposals, not released features |

## Development

Use Python <!-- docs:python_min -->3.14.2<!-- /docs:python_min -->+ and the locked project environment:

```sh
uv sync --frozen --group dev
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
npm test
REQUIRE_BROWSER_TESTS=1 npm run test:browser
```

GitHub Actions additionally performs HACS/hassfest and disposable Home Assistant checks. A CI pass does not replace real installation and release acceptance. See [Contributing](CONTRIBUTING.md), [Security](SECURITY.md) and [Release guidance](docs/releasing.md).
