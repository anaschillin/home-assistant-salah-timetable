# Calendar and event tests

Protect calendar entities, prayer-event scheduling, trigger offsets, timezone/DST boundaries, and Home Assistant event integration.

## Run just this area

```sh
uv run --frozen pytest --no-cov tests/calendar/ -q
```

This skips the **whole-integration** coverage threshold for a focused run. Full-suite validation still requires `uv run --frozen pytest` and CI.

## Where to add tests

Freeze time explicitly in boundary cases, and distinguish calculation tests from tests of event delivery through Home Assistant.

Shared Home Assistant fixtures belong in [`tests/conftest.py`](../conftest.py). The authoritative per-file inventory, Node/browser commands, and CI scope are in [the test suite guide](../../docs/testing.md).

Approved monthly timetable range queries, CSV export and redacted source details are tested in `test_month_data.py` using the real HA WebSocket interface. Keep missing dates and unauthorised users out of any result.
