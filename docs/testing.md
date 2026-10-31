# Test suite guide

Pinned PDF parser dependency: <!-- docs:pypdf -->6.21.4<!-- /docs:pypdf --> (from `versions.toml`, mirrored into the integration manifest).

Pinned compatibility targets: Home Assistant <!-- docs:homeassistant_min -->2026.10.0<!-- /docs:homeassistant_min --> (minimum) and <!-- docs:homeassistant_tested -->2026.10.4<!-- /docs:homeassistant_tested --> (pinned current).

This is the authoritative inventory of automated tests and where to add new ones. Paths are relative to the repository root. The 54 Python test modules are grouped by the behaviour they protect, not by test framework. All 15 Node unit test modules live in `tests/frontend/` alongside the browser smoke harness. The root `tests/conftest.py` supplies shared pytest fixtures and configuration for every nested Python module.

## Run and debug

Install the locked Python dependencies and use Node.js <!-- docs:node_major -->24<!-- /docs:node_major --> with uv <!-- docs:uv -->0.13.6<!-- /docs:uv -->:

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

Pytest discovers all nested `test_*.py` modules through `testpaths = ["tests"]`. Plain `pytest` enforces the existing 94.5% aggregate line-coverage floor. CI also measures branches and runs `scripts/check_coverage.py`, which preserves that floor, requires **more than 95% combined statement/branch coverage in every integration Python module**, and requires **100% line and branch coverage in all three configuration/options flow modules** (`config_flow.py`, `imports/import_flow.py`, `sources/source_flow.py`). These are coverage checks, not an official quality-tier award; see the [rule audit](releasing.md#home-assistant-integration-quality-scale-internal-gap-audit).

Reproduce the CI coverage gate from the repository root:

```sh
uv run --frozen pytest --cov-branch --cov-fail-under=0 --cov-report=json:coverage-branch.json
uv run --frozen python scripts/check_coverage.py coverage-branch.json
```

The guard compares raw counts, so exactly 95% or a rounded-up percentage fails the per-module rule. It checks the source inventory against the report, including newly added modules, and rejects missing branch data. Empty package initializers have no executable statements and are reported explicitly. Badge data is written only after every gate passes.

For fast investigation of an area or a single test, **turn off whole-project coverage**; a focused run cannot be expected to reach the full-suite thresholds:

```sh
uv run --frozen pytest --no-cov tests/parsers/ -q
uv run --frozen pytest --no-cov tests/sources/test_source_updates.py -q
uv run --frozen pytest --no-cov tests/calendar/test_calendar.py::test_calendar_trigger_offset_before_local_midnight_uses_next_date -q
node --test tests/frontend/card-utils.test.mjs
```

The full suite should run on Linux/WSL because the isolated PDF worker uses POSIX process limits. Python unit and mocked-HA tests do not require network access or a production HA installation. The Python tests exercise real HA fixtures, registries, config entries, services and storage where appropriate; they are not all pure unit tests.

## Area maintenance guides

Every domain folder has a short [README](../tests/README.md) explaining **what belongs there**, the focused pytest command, fixture ownership, and boundaries with adjacent domains. Follow the matching guide before adding or moving tests:

| Area | Guide | What it owns |
| --- | --- | --- |
| Automations | [tests/automations](../tests/automations/README.md) | Adhan and media blueprints |
| Calendar | [tests/calendar](../tests/calendar/README.md) | Calendar/event calculations and HA delivery |
| Core | [tests/core](../tests/core/README.md) | Entities, coordinator, models, diagnostics |
| Frontend | [tests/frontend](../tests/frontend/README.md) | Dashboard, Node unit tests and browser smoke |
| Imports | [tests/imports](../tests/imports/README.md) | Setup, mapping, comparison and approval flows |
| Parsers | [tests/parsers](../tests/parsers/README.md) | CSV, PDF, layout recognition and worker limits |
| Ramadan | [tests/ramadan](../tests/ramadan/README.md) | Ramadan timetable options and date windows |
| Sources | [tests/sources](../tests/sources/README.md) | Remote downloads, profiles and updates |
| Storage | [tests/storage](../tests/storage/README.md) | Persistence, migrations, repairs and restore |
| Tooling | [tests/tooling](../tests/tooling/README.md) | Packaging, compatibility, provenance and inventory |

The suite is intentionally grouped at one domain level rather than making single-file subfolders such as `parsers/csv` or `imports/configuration`. Split an area further when it becomes too large to navigate, and update fixture paths, CI and this inventory in the same change.

`tests/tooling/test_suite_inventory.py` runs in normal pytest CI and fails if a Python/Node test module is missing from this inventory, a module is listed twice, the count is stale, or a category guide is absent. Whenever a module is added, moved, or removed, update the inventory table and relevant guide in the same PR.

## Python test modules (54)

The files below are the complete set of pytest test modules. When adding a regression, extend the relevant existing module before introducing a second module for the same responsibility.

| Area | File (`test_*.py`) | Responsibility |
| --- | --- | --- |
| **automations** | `test_adhan_controls.py` | Adhan blueprint controls and settings |
| | `test_blueprints.py` | Blueprint inputs, templates, triggers and rendered behaviour |
| | `test_media_blueprint.py` | Media pause/resume blueprint behaviour |
| **calendar** | `test_calendar.py` | Calendar entities, triggers, timezone and date boundaries |
| | `test_events.py` | Prayer event calculation and scheduling rules |
| | `test_month_data.py` | Approved Gregorian month queries, CSV export, source redaction and authenticated WebSocket reads |
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
| | `test_ci_changed_files.py` | Conservative Markdown-only CI classification and rename safety |
| | `test_coverage_badge.py` | Per-module/flow coverage gates, source inventory and measured badge publication |
| | `test_compatibility_environment.py` | Pinned HA/Python environment assertions |
| | `test_packaging.py` | Release file inclusion/exclusion and version integrity |
| | `test_release_preparation.py` | Release archive and notes preparation |
| | `test_suite_inventory.py` | Verify all Python/Node test modules and category guides remain documented |

Names indicate the primary module ownership; some tests deliberately span unit, integration and acceptance boundaries. Do not rely on folder names alone to infer a test's isolation level.

## JavaScript and browser tests

The following 15 Node unit modules are discovered by `npm test` (`node --test tests/frontend/*.test.mjs`):

| File in `tests/frontend/` | Responsibility |
| --- | --- |
| `browser-startup.test.mjs` | Browser-process startup and failure handling |
| `card-i18n.test.mjs` | Localisation and translation fallback |
| `card-styles.test.mjs` | CSS and responsive style expectations |
| `card-utils.test.mjs` | Date, duration and card formatting helpers |
| `card.test.mjs` | Card/editor rendering, interactions and state |
| `dashboard-options.test.mjs` | Dashboard editor options and display flags |
| `feature-releases.test.mjs` | Feature release CI gates, replacement, cleanup, races and stable-release protection |
| `stable-releases.test.mjs` | Stable release version/CI gates, safe tagging, idempotency and publication workflow security |
| `history-utils.test.mjs` | Islamic-history selection and defaults |
| `live-dates.test.mjs` | UTC midnight, leap-year and year-boundary smoke fixture dates |
| `live-dependency.test.mjs` | Live smoke dependency validation helpers |
| `live-readiness.test.mjs` | HA startup/readiness polling rules |
| `live-report.test.mjs` | Sanitised live smoke reporting |
| `mosque-backgrounds.test.mjs` | Mosque background catalogue and metadata |
| `visual-regression.test.mjs` | Screenshot comparison behaviour |

`tests/frontend/browser-smoke.mjs` is a separately executed Chromium smoke test via `npm run test:browser` (it intentionally has no `.test.mjs` suffix). `tests/frontend/browser-harness.js` supplies the synthetic HA card environment used by that smoke test. The comparator is `scripts/compare_screenshots.mjs`; pull-request CI compares the base and candidate screenshots, and requires explicit approval for intentional pixel differences. See [visual regression](testing.md#frontend-visual-regression).

The separate, network-enabled `scripts/live_smoke.mjs` creates a **disposable real Home Assistant Container**, verifies onboarding, config entry and browser behaviour, and cleans up the environment. It is not an ordinary local Node unit test. See [live smoke](testing.md#disposable-home-assistant-live-testing). Real-device/HACS acceptance and full HAOS backup restoration remain separate release checks.

## Fixtures, helpers and test data

- `tests/conftest.py`: shared fixtures for HA setup, authenticated uploads, config entries, timetable samples and storage; loaded for all Python subfolders.
- `tests/fixtures/csv/`: small valid and invalid-format CSV cases.
- `tests/fixtures/pdf/`: synthetic/anonymised PDFs and expected CSV oracles. PDF generator programs are fixture maintenance tools, not pytest modules. See [fixture README](../tests/fixtures/pdf/README.md) and asset provenance notes before modifying or replacing PDFs.
- `tests/fixtures/storage/`: historical/migration storage schemas and expected payloads; see its README.
- `scripts/disposable_backup_restore.py` and `scripts/verify_backup_restore.py`: dedicated backup/restore verification helpers, not default pytest modules.
- `tests/frontend/browser-harness.js`: browser smoke support code; do not add independent test assertions here that are omitted from the smoke runner.

When computing a fixture path from a Python test inside a domain folder, use `Path(__file__).resolve().parents[1] / "fixtures" / ...` (`parents[1]` is the `tests/` folder). Avoid `Path(__file__).parent / "fixtures"` inside the nested modules, and avoid moving shared fixture files as part of a purely organisational change.

## CI coverage and ownership

The README **coverage** badge is generated from the *measured Python line-coverage ratio* in the successful `Validate` tests job on `main`; it is not a hard-coded percentage. The existing test job uploads the calculated Shields.io JSON endpoint, and a separate publish job with limited `contents: write` access stores only `coverage.json` on an automatically created orphan `badges` branch. The branch is deliberately retained as generated badge data; its pushes do not trigger main-branch test workflows. Badge updates occur on successful main-branch tests, not on pull requests, and can lag briefly due to image caching. The **HACS** badge queries the actual `hacs` check-run status on `main`, not the aggregate Validate workflow status. These badges do not prove HACS Store listing or replace release acceptance.



| CI entry | What is verified |
| --- | --- |
| `.github/workflows/validate.yml` | Documentation integrity on every run; full Python pytest, coverage, Ruff, Node/Chromium, HACS/hassfest, packaging and HA checks for code PRs and all pushes to `main` |
| `.github/workflows/codeql.yml` | Python/JavaScript security analysis on code PRs, all `main` pushes and weekly; superseded PR scans cancel |
| `.github/workflows/unit-compatibility.yml` | **All recursively discovered Python test files**, in one pytest run on each pinned Home Assistant compatibility lane |
| `.github/workflows/live-smoke.yml` | Real disposable HA Container onboarding/browser smoke (manual and weekly; reusable workflow) |
| `.github/workflows/release.yml` | Tag, checksums, assets and release eligibility; not an alternative to functional testing |

Pull requests changing **only Markdown files** (including shared excerpts) run the documentation integrity check but skip heavyweight Python/Node, HACS/hassfest, HA integration/compatibility and CodeQL analysis jobs. Any non-Markdown file—including code, configuration, workflow definitions or asset metadata—activates full validation. Every push to `main`, manual run and scheduled security/compatibility check retains the full checks; the draft-release requirement for a successful full `Validate` push run on the tagged commit is preserved.

Workflow triggers are deliberately not filtered by `paths-ignore`: required checks could remain pending. Job-level skipping retains existing check names. The classifier uses a merge-base diff and includes the original path of renamed files to avoid bypassing code checks.

Keep `pytest` discovery recursive and the Node glob aligned with file locations. Update any literal file references in workflows and documentation when renaming or moving tests. Run Ruff formatting after Python edits and retain the full-suite coverage gate: focused subsets are for diagnosis, not release evidence.

## Adding tests: placement rules

1. Choose the directory based on the *production behaviour* being tested (e.g. import workflow versus parser versus source update), not just a shared mock or helper.
2. Extend an existing module when the case belongs to that module. Add another `test_*.py` or `*.test.mjs` only for a distinct responsibility.
3. Put reusable HA pytest fixtures in `tests/conftest.py`. Keep single-test fixtures local; keep synthetic bytes and historical schemas under `tests/fixtures/`.
4. A parser bug should normally receive a bounded fixture plus a parser regression; a config-flow bug should also prove review/approval where applicable. For reconfiguration, verify invalid input, unchanged mosque identity, preserved storage and entities, and single-reload behaviour. Add frontend unit and browser coverage for visible UI regressions.
5. Prefer test doubles for external services; maintain at least the existing real-HA and Chromium smoke paths. Do not add network dependence to normal unit runs.
6. Before proposing a merge, run focused tests, the full suites, Ruff and the relevant CI jobs, and update this inventory when creating/removing test modules.

PDF worker white-box coverage supplements, but does not replace, real isolated-subprocess tests. Focused tests are not expected to meet full-suite coverage thresholds.

## Compatibility test environments

The root test lock and supported-current compatibility lane target Home Assistant
**<!-- docs:homeassistant_tested -->2026.10.4<!-- /docs:homeassistant_tested -->**. `versions.toml`
owns that target and its matching test-plugin pin; the project metadata and
marked values in this guide are generated mirrors, while `uv.lock` records the
resolved environment. Two independent
projects run the same complete Python suite against supported releases:

| Lane | Home Assistant | Test plugin | Separate project |
| --- | --- | --- | --- |
| Minimum | <!-- docs:homeassistant_min -->2026.10.0<!-- /docs:homeassistant_min --> | <!-- docs:test_plugin_min -->0.13.371<!-- /docs:test_plugin_min --> | `compatibility/minimum` |
| Supported current | <!-- docs:homeassistant_tested -->2026.10.4<!-- /docs:homeassistant_tested --> | <!-- docs:test_plugin_tested -->0.13.375<!-- /docs:test_plugin_tested --> | `compatibility/supported-current` |

Each `pytest-homeassistant-custom-component` release requires its exact HA
version. The compatibility projects receive their version pairs from `versions.toml`
and resolve their own committed locks. They do not override dependencies or replace the
root development environment. Python must be **<!-- docs:python_min -->3.14.2<!-- /docs:python_min --> or later
within the supported Python series**.

“Supported current” means the reviewed support target rather than the latest
release available on PyPI. Promoting a newer Home Assistant/plugin pair
requires an explicit support update and verification. Follow the
[central version workflow](../CONTRIBUTING.md#keeping-documentation-variables-current):
edit `versions.toml`, run `python scripts/sync_versions.py --write`, then regenerate
affected locks with uv. `python scripts/sync_versions.py --check` rejects drift in
the generated code, configuration and documentation before test execution.

### Run a lane locally

Run these commands from the repository root, with uv <!-- docs:uv -->0.13.6<!-- /docs:uv --> and the
supported Python series available. `uv sync --project` creates the lane's own `.venv`; it leaves the
repository's root `.venv` and lock unchanged. The explicit environment setting
below also takes precedence over an inherited `UV_PROJECT_ENVIRONMENT`.
The version variables are exported from `versions.toml`, using the same values
as the generated compatibility projects.

```sh
source <(python3 scripts/sync_documentation.py --shell)
COMPAT_ENV="$PWD/compatibility/minimum/.venv"
COMPAT_TMPDIR="$(mktemp -d /tmp/salah-unit-minimum.XXXXXX)"
UV_PROJECT_ENVIRONMENT="$COMPAT_ENV" TMPDIR="$COMPAT_TMPDIR" \
  uv sync --project compatibility/minimum --frozen --python "$PYTHON_SERIES" --no-python-downloads
TMPDIR="$COMPAT_TMPDIR" uv pip check --python "$COMPAT_ENV/bin/python"
TMPDIR="$COMPAT_TMPDIR" "$COMPAT_ENV/bin/python" scripts/check_compatibility_environment.py \
  --ha-version "$HA_MIN_VERSION" --plugin-version "$PLUGIN_MIN_VERSION" \
  --environment "$COMPAT_ENV"
TMPDIR="$COMPAT_TMPDIR" COVERAGE_FILE="$COMPAT_TMPDIR/.coverage" \
  "$COMPAT_ENV/bin/python" -m pytest -c pyproject.toml --timeout=30
```

For the supported-current lane, use `compatibility/supported-current`,
`--ha-version "$HA_TESTED_VERSION"` and `--plugin-version "$PLUGIN_TESTED_VERSION"`; use
`salah-unit-supported-current.XXXXXX` in the temporary-directory command.
Run concurrent lanes in separate shells with their own environment, temporary
directory and coverage file. Home Assistant's file-upload tests use a directory
under Python's system temporary directory, so sharing `/tmp` directly can cause
collisions even when the virtual environments differ. The commands create a
fresh temporary directory before starting Python. Do not reuse the root
development environment for compatibility testing.

The environment check fails unless the distribution metadata, imported HA
version, plugin version, Python version and interpreter environment all match.
Use the checked environment's explicit Python path for pytest. The root pytest
configuration keeps imports and fixtures consistent while the tests exercise
configuration, real storage migrations and recovery, imports, entities,
automations, calendar behavior and frontend resource registration.

### Continuous validation

`Validate` calls the reusable `unit-compatibility.yml` workflow for **two
jobs**, one per pinned Home Assistant release. Each job runs **all** `test_*.py`
modules in a single pytest process, including the HTTP upload and source-flow
tests; there are no four-way core shards or dedicated source-flow shard.
Both jobs run even if the other fails.

The runner discovers tests directly from `tests/` and records the exact module
list, installed versions, installed packages, JUnit results, coverage XML and
verbose pytest output. Version assertions, frozen dependency locks, per-test
`--timeout=30`, the 12-minute process watchdog, the 15-minute job ceiling,
and failure evidence collection are retained.

The separately locked root development suite provides another layer of
validation. The **one** real Home Assistant Container live-acceptance job runs
on supported-current **<!-- docs:homeassistant_tested -->2026.10.4<!-- /docs:homeassistant_tested -->**. Unit compatibility uses Home Assistant
test fixtures; live acceptance checks real installation, dependencies,
configuration, reload, and frontend behavior. These are complementary checks,
not duplicates. Both reusable workflows can also run manually and on their
existing weekly schedules.

## Disposable Home Assistant live testing

The runner is used by the required **supported-current HA <!-- docs:homeassistant_tested -->2026.10.4<!-- /docs:homeassistant_tested -->** live job
in Validate and can also run manually. The reusable live workflow runs weekly as a
compatibility check. It creates a
disposable official HA container and synthetic timetable, runs authenticated APIs
and the real frontend, and removes its container and private configuration afterward.
No user configuration or credentials are checked into the repository.

Requirements: Docker, Node.js <!-- docs:node_major -->24<!-- /docs:node_major --> and Chromium/Chrome. Example:

```sh
source <(python3 scripts/sync_documentation.py --shell)
node scripts/live_smoke.mjs --ha-version "$HA_TESTED_VERSION" --output-dir /tmp/salah-live-results
```

The optional `--preload-pypdf` supplies the exact manifest-pinned pure-Python
package and metadata from the repository's development venv. It is an explicit
workaround for the test environment's proxy CA, not proof that fresh dependency
installation works. TLS verification remains enabled.
The default omits this preload and lets HA resolve the manifest requirement.
`--require-fresh-dependency` verifies that both pypdf metadata and import are absent
in the base image and match the manifest pin after the mosque has loaded. It fails
rather than treating a pre-existing/preloaded package as fresh-install evidence.
CI uses this flag. The runner verifies before/after dependency versions, but
public `results.json` records only boolean outcomes, including
`dependency.fresh_install_verified`, to avoid copying raw API or process data.

When a test environment uses a private outbound proxy CA, pass
`--ca-bundle /path/to/combined-ca-bundle.pem`. The bundle is mounted read-only and
selected with `SSL_CERT_FILE`/`PIP_CERT`; normal TLS verification stays enabled.
This opt-in trust setup is separate from preloading and supplies no package files.

### Readiness and reporting

Wait for HA `RUNNING` before configuration and shutdown. After restart, wait for
`RUNNING` and the specific mosque entry before checking timetable values. Terminal
setup/migration errors fail separately. Polling retries refused/reset connections,
transport timeouts and HTTP 502/503/504; authentication failures, incompatible APIs,
invalid JSON and assertions fail immediately. A fixed loopback host port preserves
the origin across restart. Browser startup uses bounded debugger discovery.

`results.json` contains fixed acceptance check names, boolean dependency,
restart and browser outcomes, the validated local source commit, and a generic
failure marker directing reviewers to the job log. It deliberately does not
persist raw HTTP responses, process output, image IDs, startup diagnostics,
or untrusted exception messages. Runtime diagnostics remain visible in the runner
logs, while screenshots can contain synthetic fixture values. Private
configuration files and authenticated-session logs are not exported. The
ten-minute run deadline and scoped cleanup remain mandatory. Docker creates/copies
can take several minutes in this environment.

Record candidate-specific outcomes in the pull request or release review.
Authenticated HACS installation and physical-device acceptance remain separate
checks; historical local runs do not establish the current candidate's readiness.

### UTC midnight stability

The disposable live-acceptance smoke creates synthetic annual records and confirms Ramadan for the current UTC day **and the following day**. Otherwise a real Home Assistant date rollover can deactivate a one-day Ramadan fixture while the card editor is being tested, making a valid preview falsely fail its visibility assertion. The December 31 boundary uses separate annual CSV imports for each year. The browser permits approved prayer timestamps to advance exactly one day while still checking Ramadan activation and the published prayer fields. See `scripts/live_dates.mjs` and `tests/frontend/live-dates.test.mjs`.

## Frontend visual regression

The Chromium smoke suite exercises 16 combinations: widths 320, 360, 400 and
900 px; English and Arabic; single-language and bilingual prayer labels.
It checks accessible semantics, overflow, RTL, calendar text, the editor,
keyboard focus, styles, and theme variables before capturing each screenshot.

On a **pull request**, the Validate workflow:

1. Runs the candidate card in Chromium and captures 16 PNG screenshots.
2. Checks out the **current base branch HEAD** in a separate directory.
   The workflow logs the resolved baseline commit SHA for reproducibility.
3. Runs the same browser smoke test on the base branch on the same CI runner,
   ensuring the same installed Chrome and system fonts.
4. Compares each candidate/base screenshot with
   `node scripts/compare_screenshots.mjs BASE_DIR CURRENT_DIR`.
   Dimensions must match. A pixel counts as changed only if one RGBA
   channel differs by more than 16 (out of 255); greater than **0.5%**
   changed pixels in any one fixture fails the frontend job.
5. On failure, uploads the candidate and baseline PNGs in a
   `frontend-visual-diff-<PR number>` artifact for human review. Approved
   visual redesigns upload the same artifact even when comparison succeeds,
   so reviewers can inspect the before/after evidence.

PNG files are local CI evidence, not source-controlled brand or mosque
fixtures. The decoder is dependency-free and accepts only bounded,
8-bit RGB/RGBA, noninterlaced PNGs from the local Chromium capture.

For deliberate visual redesigns (including changed card heights), inspect
the screenshot artifact, document the expected changes in the PR and have a
repository maintainer apply the `visual-change-approved` PR label. **Do not
apply this label to ordinary CSS/behavior fixes or unrelated feature PRs.**
The comparer still captures and decodes all 16 current/base screenshots,
checks their presence and filenames, prints dimension/pixel changes and emits
a GitHub Actions notice. Only an explicitly labelled PR may accept differences
beyond 0.5% or intentionally changed dimensions. Without that label, the
strict 0.5% threshold and dimension checks continue to fail unexpected changes.

The label represents manual design approval, **not proof of accessibility or
real-device acceptance**. Chromium overflow/RTL tests, frontend unit tests and
Home Assistant acceptance still run and must pass. The label only approves
the screenshot delta from the PR base. After merging the redesigned card, its
images become the normal baseline for later PRs; remove or avoid the approval
label on new unrelated changes. This does not raise the tolerance or disable
comparisons. If the base branch changes while a review is in progress, rerun
CI and record the resolved base SHA. Pushes to `main` still run browser smoke
tests but cannot compare against a pull-request base branch.

Run locally:

```bash
BROWSER_SCREENSHOT_DIR=/tmp/salah-current npm run test:browser
# Run the same command with a second checkout and a different output directory.
node scripts/compare_screenshots.mjs /tmp/salah-base /tmp/salah-current
```

The images use synthetic fixture data. Physical Home Assistant acceptance
on a phone/tablet, as described in [CSS acceptance](dashboard.md),
remains a separate release gate.
