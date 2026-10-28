# Test suite guide

This is the authoritative inventory of automated tests and where to add new ones. Paths are relative to the repository root. The 50 Python test modules are grouped by the behaviour they protect, not by test framework. All 12 Node unit test modules live in `tests/frontend/` alongside the browser smoke harness. The root `tests/conftest.py` supplies shared pytest fixtures and configuration for every nested Python module.

## Run and debug

Install the locked Python dependencies and use Node.js 24:

```sh
uv sync --frozen --group dev
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
npm test
REQUIRE_BROWSER_TESTS=1 npm run test:browser
```

Pytest discovers all nested `test_*.py` modules through `testpaths = ["tests"]`. The complete Python run enforces the existing integration line-coverage gate (94.5%). For fast investigation of an area or a single test, **turn off whole-project coverage**; a focused run cannot be expected to reach that global threshold:

```sh
uv run --frozen pytest --no-cov tests/parsers/ -q
uv run --frozen pytest --no-cov tests/sources/test_source_updates.py -q
uv run --frozen pytest --no-cov tests/calendar/test_calendar.py::test_calendar_trigger_offset_before_local_midnight_uses_next_date -q
node --test tests/frontend/card-utils.test.mjs
```

The full suite should run on Linux/WSL because the isolated PDF worker uses POSIX process limits. Python unit and mocked-HA tests do not require network access or a production HA installation. The Python tests exercise real HA fixtures, registries, config entries, services and storage where appropriate; they are not all pure unit tests.

## Python test modules (50)

The files below are the complete set of pytest test modules. When adding a regression, extend the relevant existing module before introducing a second module for the same responsibility.

| Area | File (`test_*.py`) | Responsibility |
| --- | --- | --- |
| **automations** | `test_adhan_controls.py` | Adhan blueprint controls and settings |
| | `test_blueprints.py` | Blueprint inputs, templates, triggers and rendered behaviour |
| | `test_media_blueprint.py` | Media pause/resume blueprint behaviour |
| **calendar** | `test_calendar.py` | Calendar entities, triggers, timezone and date boundaries |
| | `test_events.py` | Prayer event calculation and scheduling rules |
| | `test_event_integration.py` | End-to-end HA event/calendar wiring |
| **core** | `test_coordinator_lifecycle.py` | Coordinator creation, updates and teardown |
| | `test_coverage.py` | Timetable coverage and expiry diagnostics |
| | `test_diagnostics.py` | Diagnostic data and redaction |
| | `test_integration.py` | Component setup, entities and unload behaviour |
| | `test_model.py` | Prayer/timetable domain models |
| **frontend** | `test_dashboard_details.py` | Python-side dashboard field presentation |
| | `test_frontend.py` | Frontend resources, HTTP assets and installation |
| **imports** | `test_canonical_comparison.py` | Canonical values and comparison rules |
| | `test_config_flow.py` | Main HA setup/config flow |
| | `test_csv_flow.py` | CSV upload/mapping/review flow |
| | `test_import_comparison.py` | Staged vs approved import comparisons |
| | `test_import_comparison_flow.py` | Comparison and approval through config flows |
| | `test_import_model.py` | Staging/import domain model |
| | `test_mapping_selection.py` | Import mapping choices |
| | `test_mosque_a_flow.py` | Mosque A annual and monthly PDF import flow |
| | `test_mosque_b_annual_flow.py` | Mosque B annual publication import flow |
| | `test_published_pdf_flow.py` | Published PDF import and activation gating |
| **parsers** | `test_csv_parser.py` | CSV time parsing and malformed/adversarial input |
| | `test_mosque_a_layout.py` | Mosque A annual PDF adapter |
| | `test_mosque_a_monthly_layout.py` | Mosque A monthly PDF adapter |
| | `test_mosque_a_parser.py` | Mosque A PDF parser integration |
| | `test_mosque_b_annual_layout.py` | Mosque B annual PDF adapter |
| | `test_mosque_b_annual_parser.py` | Mosque B annual PDF parsing |
| | `test_mosque_b_ramadan_layout.py` | Mosque B Ramadan PDF adapter |
| | `test_pdf_auto_detect.py` | PDF layout detection and unsupported formats |
| | `test_pdf_parser.py` | Isolated PDF extraction, bounds and parsing |
| | `test_pdf_worker_unit.py` | In-process worker branches and error handling |
| **ramadan** | `test_ramadan.py` | Ramadan timetable rules and activation |
| | `test_ramadan_flow.py` | Ramadan upload, review and selection flow |
| | `test_ramadan_validation.py` | Ramadan dates, consistency and validation |
| **sources** | `test_download.py` | Remote HTTP downloads and safety constraints |
| | `test_source_flow.py` | URL/source configuration flow |
| | `test_source_model.py` | Source profile and metadata models |
| | `test_source_updates.py` | Scheduled refreshes, checksums and approval gates |
| **storage** | `test_backup_restore_acceptance.py` | Backup/restore acceptance checks |
| | `test_import_storage.py` | Imported timetable persistence |
| | `test_remote_storage.py` | Remote-source persistence |
| | `test_storage.py` | Core HA storage and round-trips |
| | `test_storage_repairs.py` | Storage corruption and repair paths |
| | `test_upgrade_recovery.py` | Older storage schemas and migration/recovery |
| **tooling** | `test_asset_provenance.py` | Licensed asset metadata and release gate |
| | `test_compatibility_environment.py` | Pinned HA/Python environment assertions |
| | `test_packaging.py` | Release file inclusion/exclusion and version integrity |
| | `test_release_preparation.py` | Release archive and notes preparation |

Names indicate the primary module ownership; some tests deliberately span unit, integration and acceptance boundaries. Do not rely on folder names alone to infer a test's isolation level.

## JavaScript and browser tests

The following 12 Node unit modules are discovered by `npm test` (`node --test tests/frontend/*.test.mjs`):

| File in `tests/frontend/` | Responsibility |
| --- | --- |
| `browser-startup.test.mjs` | Browser-process startup and failure handling |
| `card-i18n.test.mjs` | Localisation and translation fallback |
| `card-styles.test.mjs` | CSS and responsive style expectations |
| `card-utils.test.mjs` | Date, duration and card formatting helpers |
| `card.test.mjs` | Card/editor rendering, interactions and state |
| `dashboard-options.test.mjs` | Dashboard editor options and display flags |
| `history-utils.test.mjs` | Islamic-history selection and defaults |
| `live-dependency.test.mjs` | Live smoke dependency validation helpers |
| `live-readiness.test.mjs` | HA startup/readiness polling rules |
| `live-report.test.mjs` | Sanitised live smoke reporting |
| `mosque-backgrounds.test.mjs` | Mosque background catalogue and metadata |
| `visual-regression.test.mjs` | Screenshot comparison behaviour |

`tests/frontend/browser-smoke.mjs` is a separately executed Chromium smoke test via `npm run test:browser` (it intentionally has no `.test.mjs` suffix). `tests/frontend/browser-harness.js` supplies the synthetic HA card environment used by that smoke test. The comparator is `scripts/compare_screenshots.mjs`; pull-request CI compares the base and candidate screenshots, and requires explicit approval for intentional pixel differences. See [visual regression](visual-regression.md).

The separate, network-enabled `scripts/live_smoke.mjs` creates a **disposable real Home Assistant Container**, verifies onboarding, config entry and browser behaviour, and cleans up the environment. It is not an ordinary local Node unit test. See [live smoke](live-smoke.md). Real-device/HACS acceptance and full HAOS backup restoration remain separate release checks.

## Fixtures, helpers and test data

- `tests/conftest.py`: shared fixtures for HA setup, authenticated uploads, config entries, timetable samples and storage; loaded for all Python subfolders.
- `tests/fixtures/csv/`: small valid and invalid-format CSV cases.
- `tests/fixtures/pdf/`: synthetic/anonymised PDFs and expected CSV oracles. PDF generator programs are fixture maintenance tools, not pytest modules. See [fixture README](../tests/fixtures/pdf/README.md) and asset provenance notes before modifying or replacing PDFs.
- `tests/fixtures/storage/`: historical/migration storage schemas and expected payloads; see its README.
- `scripts/disposable_backup_restore.py` and `scripts/verify_backup_restore.py`: dedicated backup/restore verification helpers, not default pytest modules.
- `tests/frontend/browser-harness.js`: browser smoke support code; do not add independent test assertions here that are omitted from the smoke runner.

When computing a fixture path from a Python test inside a domain folder, use `Path(__file__).resolve().parents[1] / "fixtures" / ...` (`parents[1]` is the `tests/` folder). Avoid `Path(__file__).parent / "fixtures"` inside the nested modules, and avoid moving shared fixture files as part of a purely organisational change.

## CI coverage and ownership

| CI entry | What is verified |
| --- | --- |
| `.github/workflows/validate.yml` | Full Python pytest suite with branch coverage reported, existing line-coverage gate, Ruff, Node frontend unit suite, Chromium screenshots, HACS/hassfest and packaging |
| `.github/workflows/unit-compatibility.yml` | **All recursively discovered Python test files**, in one pytest run on each pinned Home Assistant compatibility lane |
| `.github/workflows/live-smoke.yml` | Real disposable HA Container onboarding/browser smoke (manual and weekly; reusable workflow) |
| `.github/workflows/release.yml` | Tag, checksums, assets and release eligibility; not an alternative to functional testing |

Keep `pytest` discovery recursive and the Node glob aligned with file locations. Update any literal file references in workflows and documentation when renaming or moving tests. Run Ruff formatting after Python edits and retain the full-suite coverage gate: focused subsets are for diagnosis, not release evidence.

## Adding tests: placement rules

1. Choose the directory based on the *production behaviour* being tested (e.g. import workflow versus parser versus source update), not just a shared mock or helper.
2. Extend an existing module when the case belongs to that module. Add another `test_*.py` or `*.test.mjs` only for a distinct responsibility.
3. Put reusable HA pytest fixtures in `tests/conftest.py`. Keep single-test fixtures local; keep synthetic bytes and historical schemas under `tests/fixtures/`.
4. A parser bug should normally receive a bounded fixture plus a parser regression; a config-flow bug should also prove review/approval where applicable. Add frontend unit and browser coverage for visible UI regressions.
5. Prefer test doubles for external services; maintain at least the existing real-HA and Chromium smoke paths. Do not add network dependence to normal unit runs.
6. Before proposing a merge, run focused tests, the full suites, Ruff and the relevant CI jobs, and update this inventory when creating/removing test modules.
