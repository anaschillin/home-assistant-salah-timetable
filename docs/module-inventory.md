# Production code inventory and ownership

This is the file-by-file map of the code shipped under `custom_components/salah_timetable/`. It complements [architecture](architecture.md), [integration contracts](integration-architecture.md) and the [test suite guide](testing.md).

## Home Assistant and executable entry points (package root)

These files stay at the package root because Home Assistant discovers them there, they contain public integration wiring, or (for `pdf_worker.py`) a direct subprocess invocation depends on that entry path.

| File | Responsibility |
| --- | --- |
| `__init__.py` | Config-entry setup/unload, runtime data and device lifecycle |
| `calendar.py` | Read-only calendar entities built from approved dates |
| `config_flow.py` | HA configuration and options entrypoint |
| `const.py` | Domain, storage version and configuration keys |
| `diagnostics.py` | Privacy-conscious diagnostics export |
| `frontend.py` | Serve the versioned dashboard resource and register it in HA |
| `sensor.py` | Read-only sensor entities and dashboard attributes |
| `pdf_worker.py` | Standalone bounded PDF extraction subprocess; invoked by absolute file path |

## Grouped Python implementation

| Directory | File | Responsibility |
| --- | --- | --- |
| `domain/` | `model.py` | Immutable prayer data, field enumeration and time parsing |
| `domain/` | `ramadan.py` | Effective timetable and confirmed-date Ramadan overrides |
| `domain/` | `ramadan_validation.py` | Validate Ramadan selections and review content |
| `domain/` | `coverage.py` | Calculate supported approved date coverage |
| `domain/` | `events.py` | Determine prayer and Jamaat events over time |
| `domain/` | `presentation.py` | Serialize events for dashboard display |
| `parsers/` | `import_model.py` | Import candidates, parser contracts and validation bounds |
| `parsers/` | `csv_parser.py` | Bounded CSV parsing, date and column mapping |
| `parsers/` | `pdf_parser.py` | PDF inspection, layout selection and sandboxed worker launch |
| `parsers/` | `mosque_a_layout.py` | Mosque A annual publication adapter |
| `parsers/` | `mosque_a_monthly_layout.py` | Mosque A monthly publication adapter |
| `parsers/` | `mosque_b_annual_layout.py` | Mosque B annual publication adapter |
| `parsers/` | `mosque_b_ramadan_layout.py` | Mosque B Ramadan publication adapter |
| `imports/` | `import_flow.py` | Upload, mapping and approve/reject options flow |
| `imports/` | `import_comparison.py` | Compare approved and staged canonical values |
| `sources/` | `download.py` | Secure, bounded remote HTTPS fetch |
| `sources/` | `source_model.py` | Remote publication URL/profile validation and metadata |
| `sources/` | `source_flow.py` | Source configuration, inspection and management UI |
| `sources/` | `source_updates.py` | Periodic and manual URL update checks, staging only |
| `persistence/` | `storage.py` | Versioned per-entry approved/staged records and atomic writes |
| `runtime/` | `coordinator.py` | HA snapshot refresh, current dates, events and timers |

Each implementation directory has an `__init__.py`. Other production Python modules should import **the new grouped path** (for example, `from .domain.model import PrayerField` at root, or `from ..domain.model import PrayerField` from inside a sibling package). Use relative paths within the same directory.

### Compatibility paths

The 21 previous root import paths, such as `custom_components.salah_timetable.model` and `custom_components.salah_timetable.pdf_parser`, remain as **small module aliases**. They install the actual relocated module in `sys.modules` under the old name. This retains existing third-party imports and test patch targets, including module-level monkeypatching. Do not add implementation to these shims; new code should import the grouped path. Remove compatibility aliases only through a separate deprecation and test migration.

The standalone `pdf_worker.py` deliberately remains at root. The relocated `parsers/pdf_parser.py` resolves that worker's absolute path; its `python -I` subprocess boundary and resource limits are unchanged.

## Bundled frontend, metadata and assets

| Path | Responsibility |
| --- | --- |
| `frontend/salah-timetable-card.js` | Custom card and editor entrypoint, registered at its existing public URL |
| `frontend/card-utils.js` | Pure timestamp, time formatting and card model helpers |
| `frontend/history-utils.js` | Islamic history/date helper functions |
| `frontend/card-i18n.js` | Localized client-side labels |
| `frontend/card-styles.js` | Dashboard CSS and layout tokens |
| `frontend/mosque-backgrounds.js` | Background catalog and selection logic |
| `frontend/backgrounds/*.webp` | Attributed bundled mosque images; see [credits](mosque-background-credits.md) |
| `brand/icon.png` | Integration icon |
| `manifest.json` | HACS and HA integration metadata/dependencies |
| `strings.json`, `translations/en.json` | HA config and options UI localization |

The card's JavaScript imports remain in their existing relative locations to preserve the versioned static asset URL, browser cache behaviour, HACS packaging and frontend tests. Do not move these files without updating JS imports, frontend resource registration, release validation and browser tests together.

## Dependency and maintenance rules

1. **Domain** code should remain independent of Home Assistant, downloads and persistent storage; write deterministic unit tests in `tests/core/`, `tests/calendar/` or `tests/ramadan/`.
2. **Parsers** convert bounded PDFs/CSVs into immutable candidates; add layout tests in `tests/parsers/` and staged import scenarios in `tests/imports/`.
3. **Imports and sources** own user approval and URL management, respectively. A remote check may only stage changes; it must not silently activate them. Tests belong in `tests/imports/` and `tests/sources/`.
4. **Persistence** alone updates approved/staged records and enforces revision checks. Test in `tests/storage/`.
5. **Runtime and entry points** translate approved data into HA state, entities and refresh schedules; test in `tests/core/`, `tests/calendar/` and `tests/frontend/`.
6. **Frontend** UI assets stay under `frontend/`. Preserve module import query versions and run Node tests, browser tests, packaging tests and asset provenance validation when changing them.
7. Add any new implementation to the appropriate folder and this inventory. Keep public Home Assistant entrypoints at the root; do not add another root implementation module by default.
