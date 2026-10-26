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

## Diagnosing a stalled hosted minimum-version suite

On 26 October 2026, [Validate run 40294570513](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40294570513) on `1aa2719`
reported the HA 2026.10.0 unit job as **cancelled** while executing pytest.
Its installation and exact-version checks succeeded; the HA 2026.10.3 suite
finished 978 tests, while the minimum job did not publish a JUnit artifact.
The cancelled job's archived log could not be retrieved, so there is **no
identified failing test**. A job-level `timeout-minutes: 15` was configured,
but the observed job lifetime was roughly 20 minutes; that discrepancy alone
does not prove pytest itself emitted a timeout.

The compatibility workflow now streams verbose per-test progress (`-vv`),
keeps Python output unbuffered, emits a faulthandler traceback after 120
seconds in a stuck pytest phase, and writes `pytest.log` to the compatibility
artifact folder. An explicit **12-minute process watchdog** exits before the
15-minute Actions job timeout, so the `if: always()` artifact step has an
opportunity to preserve the log and any partial JUnit/coverage outputs. Existing
`--timeout=30` per-test enforcement is unchanged. The watchdog does not
silently skip tests or claim a timeout is a passing result.

If the minimum suite stalls again, inspect the latest `ha-unit-compatibility-2026.10.0`
artifact's `pytest.log`, identify the last `-vv` test and traceback, and
reproduce that test against the **separate minimum lock** before considering
any test or application changes. Rerun evidence from the original commit is
separate from testing this diagnostic workflow.

When changing a support target, update its project pins, regenerate only that
project's lock, update the workflow matrix and this guide, then run the lane and
the corresponding live Container checks before claiming compatibility.
