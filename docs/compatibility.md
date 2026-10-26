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

The first single-process diagnostic attempt,
[Validate run 40305158405](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40305158405),
again cancelled the minimum job after about 20 minutes **without** a
minimum-lane artifact or readable archived log. Therefore the proposed
12-minute process watchdog has **not been shown to work** in that stuck
runner environment; it is not a proven fix for the underlying stall.

The sharded experiment revealed a distinct, reproducible failure in the
Home Assistant **2026.10.0 test fixture**: creating the pytest `hass_client`
before setting up the Salah Timetable entry freezes aiohttp's test router.
A later call to `async_setup_frontend()` fails with
`RuntimeError: Cannot register a resource into frozen router` and causes
PDF/CSV import approval tests to fail. Production Home Assistant deliberately
keeps its running HTTP router mutable; the test client is not equivalent.
The first fixture-order attempt set up the entire mosque entry before the
client, but HA 2026.10.0 then correctly rejected a **second entry setup**
with `ConfigEntryState.LOADED`. The corrected fixtures initialize the HTTP
component, call the integration's public `async_setup_frontend(hass)` helper
**only to register the card's static assets**, and then start `hass_client()`.
The actual mosque config entry remains NOT_LOADED until each test explicitly
sets it up. This preserves every import, approval and reload assertion. It
avoids the older pytest client's frozen-router artifact without changing
production behavior or suppressing errors.

For isolation, the minimum lane runs **nine independent pytest jobs**:
the three modulo-4 groups that completed (indices 1, 2 and 3) remain
unchanged; the slower previous index-0 group is subdivided into modulo-16
groups 0, 4, and 12, plus three single-module groups 8/64, 24/64
and 40/64 (splitting previous 8/16). All 50 sorted `tests/test_*.py` modules
are still covered **exactly once**, with no test exclusions or changes to
version pins. This split lets each independently running group finish and
publish a useful log without depending on a stalled sibling. The
supported-current HA lane runs all modules in one job. The shard index and modulus
appear in each job name, and the index in its artifact name; every shard writes a
`test-files.txt` manifest and an unbuffered `-vv` pytest transcript,
plus JUnit/coverage artifacts if produced. Pytest retains the per-test
`--timeout=30`; Python faulthandler can dump stacks after 120 seconds.
A process-level 12-minute watchdog attempts to leave time within the
15-minute job limit for the existing `if: always()` upload, but may still
not take effect if the underlying runner stalls or is externally cancelled.

Inspect each `ha-unit-compatibility-2026.10.0-shard-N` artifact,
especially `test-files.txt`, `pytest.log` and JUnit. If only one shard
fails, subdivide **that** set further, then reproduce the identified
test under the separate minimum-version lock. If all shards fail before
producing a test transcript, investigate pytest collection, runner or
fixture startup rather than blaming an individual test. A successful
sharded run proves the complete test-module set passed independently;
it does **not** prove that the original single-process hang is fixed.
Rerun evidence from the original commit is separate from this branch.

When changing a support target, update its project pins, regenerate only that
project's lock, update the workflow matrix and this guide, then run the lane and
the corresponding live Container checks before claiming compatibility.

## Source import test-module isolation (26 October 2026)

[Validate run 40313772094](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40313772094) completed eight of the nine minimum HA 2026.10.0 shards, all with success; **40/64** alone was cancelled without a log or artifact. It contained only `tests/test_source_flow.py`, so no single test could be named from that run. The entire current-version HA unit suite, standalone Python suite, live checks, frontend, HACS and hassfest all passed.

To isolate test interactions, the minimum 40/64 module runs in six independent processes. The subprocess selects top-level test functions by their stable AST order modulo six, keeping every pytest parameterization associated with its test function. The six case groups together cover every test in this file exactly once, while the other eight minimum groups and the full supported-current suite retain their test coverage. Each case group records `selected-tests.txt` separately, with a unique artifact name. This is an **isolation experiment**, not permission to omit failing tests or treat cancelled jobs as success.

Run [40318231655](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40318231655) confirmed source-flow case groups 1/6 through 5/6 succeeded in HA 2026.10.0. Only case group 0/6 remained in progress (three top-level test functions, including their parametrizations). The next experiment splits only these into separate `0/24`, `6/24`, `12/24` groups. Together with cases 1/6 to 5/6 and the other eight minimum shards, test coverage stays complete, with no skipped case or changed dependency pin.

## Individual invalid-PDF variants (26 October 2026)

[Validate run 40318506526](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40318506526) narrowed the remaining minimum-HA 2026.10.0 cancellation to case **6/24**, `test_invalid_pdf_upload_is_cleaned_up`. Its other fourteen compatibility groups and all other validations passed. Case 6/24 contains three parameter variants. Because cancelled job logs and artifacts were not preserved, the specific failing input was unknown. The compatibility matrix now runs all three with stable, explicit pytest param IDs: `non_pdf`, `malformed_pdf`, and `oversized_pdf`. The other function-level groups remain unchanged; none of the test inputs or assertions were removed. Each variant produces its own result and artifact.
