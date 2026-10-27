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
on supported-current **2026.10.3**. Unit compatibility uses Home Assistant
test fixtures; live acceptance checks real installation, dependencies,
configuration, reload, and frontend behavior. These are complementary checks,
not duplicates. Both reusable workflows can also run manually and on their
existing weekly schedules.

## Historical minimum-version CI hangs

On 26 October 2026, some single-process minimum-version runs hung on hosted
runners (see [issue #24](https://github.com/anaschillin/home-assistant-salah-timetable/issues/24)).
[PR #23](https://github.com/anaschillin/home-assistant-salah-timetable/pull/23)
fixed a frozen aiohttp-router fixture used by upload tests. Subsequent CI
diagnostics also revealed multi-megabyte pytest parameter IDs that overwhelmed
verbose GitHub Actions logging. The tests now use concise IDs without relaxing
their large-payload assertions.

The former four core shards plus dedicated source-flow shard were a temporary
isolation strategy. The October 27 CI simplification returns to two complete
suites, preserving version pins, runtime checks, coverage and watchdogs.
Confirm the exact commit's hosted validation before merging or releasing.
