# Home Assistant compatibility unit tests

The development and release environment stays locked to Home Assistant
**2026.10.2** in the root `pyproject.toml` and `uv.lock`. Two independent
projects run the same complete Python suite against supported releases:

| Lane | Home Assistant | Test plugin | Separate project |
| --- | --- | --- | --- |
| Minimum | 2026.10.0 | 0.13.371 | `compatibility/minimum` |
| Supported current | 2026.10.3 | 0.13.374 | `compatibility/supported-current` |

Each `pytest-homeassistant-custom-component` release requires its exact HA
version. The compatibility projects preserve those requirements and resolve
their own committed locks. They do not override dependencies or replace the
root development environment. Python must be **3.14.2 or later in 3.14**.

“Supported current” means the reviewed support target, rather than the latest
release available on PyPI. HA 2026.10.4 and plugin 0.13.375 are available;
promoting that pair requires an explicit support update and validation.

## Run a lane locally

Run these commands from the repository root, with uv 0.12.23 and Python 3.14
available. `uv sync --project` creates the lane's own `.venv`; it leaves the
repository's root `.venv` and lock unchanged. The explicit environment setting
below also takes precedence over an inherited `UV_PROJECT_ENVIRONMENT`.

```sh
COMPAT_ENV="$PWD/compatibility/minimum/.venv"
COMPAT_TMPDIR="$(mktemp -d /tmp/salah-unit-minimum.XXXXXX)"
UV_PROJECT_ENVIRONMENT="$COMPAT_ENV" TMPDIR="$COMPAT_TMPDIR" \
  uv sync --project compatibility/minimum --frozen --python python3.14 --no-python-downloads
TMPDIR="$COMPAT_TMPDIR" uv pip check --python "$COMPAT_ENV/bin/python"
TMPDIR="$COMPAT_TMPDIR" "$COMPAT_ENV/bin/python" scripts/check_compatibility_environment.py \
  --ha-version 2026.10.0 --plugin-version 0.13.371 \
  --environment "$COMPAT_ENV"
TMPDIR="$COMPAT_TMPDIR" COVERAGE_FILE="$COMPAT_TMPDIR/.coverage" \
  "$COMPAT_ENV/bin/python" -m pytest -c pyproject.toml --timeout=30
```

For the supported-current lane, use `compatibility/supported-current`,
`--ha-version 2026.10.3` and `--plugin-version 0.13.374`; use
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

## Continuous validation

`Validate` calls the reusable `unit-compatibility.yml` workflow for both lanes.
The workflow also runs manually and weekly, separately from the existing live
Home Assistant Container matrix and locked development tests. Both lanes run
even when one fails. Evidence includes exact installed versions, installed
packages, JUnit results and coverage; the job fails if installation or testing
changes a committed lock. Each lane creates its own `TMPDIR` before installation
and testing. A compatibility failure is not resolved by silently
switching both jobs to the same HA version or relaxing the plugin's HA pin.

## Minimum-version CI regression and isolation

On 26 October 2026, the complete single-process Home Assistant **2026.10.0**
pytest run repeatedly stalled on hosted runners (see
[issue #24](https://github.com/anaschillin/home-assistant-salah-timetable/issues/24)).
The archived logs were unavailable, so the precise original blocking operation
was not established.

[PR #23](https://github.com/anaschillin/home-assistant-salah-timetable/pull/23)
identified and corrected a distinct minimum-version test-fixture bug: the
mock `hass_client()` freezes aiohttp's router, preventing later static frontend
registration. Upload tests now set up `file_upload` and register the card routes
before constructing the test client, without prematurely loading the mosque entry.
The previously problematic invalid-PDF test also now rejects non-PDF, malformed
PDF and oversized PDF inputs sequentially within one options-flow lifecycle;
every temporary upload and staged-candidate cleanup assertion remains.
[Validate run 40325768277](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40325768277)
and
[main run 40327531675](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40327531675)
completed all existing diagnostic shards successfully.

### Maintained CI layout

The old diagnostic matrix grew to 16 minimum-HA shards, including AST-selected
functions from `tests/test_source_flow.py`. It is replaced by **five** minimum
version groups and **one** supported-current group:

- `core-0` through `core-3`: all `test_*.py` modules other than
  `test_source_flow.py`, assigned exactly once in sorted module order.
- `source-flow`: the complete `test_source_flow.py` module (no parameter or
  function exclusions).
- `all`: the complete, unsharded suite on HA 2026.10.3.

`scripts/select_compatibility_tests.py` constructs these groups and verifies
that the minimum-version partitions cover the same file set as `all`, with
no omissions or overlaps. `tests/test_compatibility_test_selection.py` tests
the selector's completeness and failure behavior. Every job uses its separately
locked Python/HA/plugin installation, runs from the repository root and saves
the exact test-file list, verbose pytest transcript, JUnit report, coverage XML,
installed versions and environment evidence. All test assertions, runtime
version checks and lock-file checks remain required.

This removes the nested modulo-64/24/6 function-selection logic and reduces
the minimum-version CI jobs from 16 to 5 without reducing test coverage. The
shards remain intentionally separate because the original unsharded minimum-HA
stall has not yet been conclusively reproduced and eliminated. Continue to track
it in issue #24. Completing the five groups establishes supported-version
compatibility, but is not proof the previously stalled single-process test
lifecycle can now run end to end.

For local reproduction, run the commands in [Run a lane locally](#run-a-lane-locally)
and use the selector to list one group, for example:

```sh
python scripts/select_compatibility_tests.py source-flow
python scripts/select_compatibility_tests.py core-0
python scripts/select_compatibility_tests.py all
```

The runner retains per-test `--timeout=30`, a 12-minute process watchdog, a
15-minute job ceiling, faulthandler diagnostics and `if: always()` artifacts.
Cancelling superseded PR revisions remains enabled; manual, push and scheduled
runs are not automatically cancelled by a newer invocation of the same workflow.
