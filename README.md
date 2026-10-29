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

Home Assistant **<!-- docs:homeassistant_min -->2026.10.0<!-- /docs:homeassistant_min --> or newer** is required.

<!-- docs:excerpt installation -->
1. In HACS, open **Custom repositories**, add `https://github.com/anaschillin/home-assistant-salah-timetable` and select **Integration**.
2. Download **Salah Timetable** and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → Salah Timetable**.
4. Enter the mosque name, a stable mosque ID and its IANA timezone (for example, `Europe/London`). Use a different ID to add another mosque.

This is a **HACS custom repository**, not a listing in the default HACS catalogue. For manual installation, copy `custom_components/salah_timetable` into Home Assistant's `config/custom_components/` directory and restart.
<!-- /docs:excerpt installation -->

After installation, follow [Getting started](docs/getting-started.md) to import and approve a timetable and add the dashboard card.

## Documentation

| Guide | Contents |
| --- | --- |
| [Getting started](docs/getting-started.md) | Setup, imports, reconfiguration, removal and troubleshooting |
| [Dashboard](docs/dashboard.md) | Card options and multiple mosques |
| [Importing and validation](docs/import_review.md) | PDF layouts, timetable review, Ramadan and source updates |
| [Automations](docs/automations.md) | Blueprints and coverage alerts |
| [Architecture](docs/architecture.md) | Internal design for contributors |
| [Testing](docs/testing.md) | Tests, coverage and development |
| [Releasing](docs/releasing.md) | Release workflow, sign-off and internal Quality Scale rule audit |
| [Roadmap](docs/roadmap.md) | Future plans only |
| [Assets and credits](docs/asset-provenance.md) | Source checks, image licensing and fixture provenance |
| [Islamic history research](research/islamic-history/islamic-history-source-audit.md) | Research proposals, not released features |

## Support and compatibility

<!-- docs:excerpt support-summary -->
Salah Timetable is a community-maintained, MIT-licensed integration without guaranteed response times or a paid support service. Compatibility is limited to the [pinned Home Assistant environments](docs/testing.md#compatibility-test-environments) and [documented timetable layouts](docs/import_review.md#supported-pdf-layouts).
<!-- /docs:excerpt support-summary -->

For safe bug reports and support requests, see the [support policy](docs/getting-started.md#support-and-compatibility-policy). Report vulnerabilities privately as described in [Security](SECURITY.md).

## Development

Use Python <!-- docs:python_min -->3.14.2<!-- /docs:python_min -->+ and the locked project environment:

<!-- docs:excerpt development-checks -->
```sh
uv sync --frozen --group dev
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
npm test
REQUIRE_BROWSER_TESTS=1 npm run test:browser
```
<!-- /docs:excerpt development-checks -->

GitHub Actions additionally performs HACS/hassfest and disposable Home Assistant checks.

<!-- docs:excerpt validation-boundaries -->
HACS repository validation does not prove installation through the authenticated HACS UI. Chromium tests use Home Assistant element stand-ins, and disposable Home Assistant Container checks do not establish physical-device behaviour or full Home Assistant OS/Supervisor restoration. Assess the **exact candidate version** through the manual [release acceptance checklist](docs/releasing.md#manual-hacs-and-home-assistant-acceptance).
<!-- /docs:excerpt validation-boundaries -->

See [Contributing](CONTRIBUTING.md), [Testing](docs/testing.md) and [Release guidance](docs/releasing.md).
