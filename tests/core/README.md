# Core integration and model tests

Protect component setup/unload, coordinator lifecycle, timetable models, coverage/expiry reporting, and diagnostics/redaction. `test_coverage.py` covers **timetable coverage**, not the pytest coverage tool.

## Run just this area

```sh
uv run --frozen pytest --no-cov tests/core/ -q
```

This skips the **whole-integration** coverage threshold for a focused run. Full-suite validation still requires `uv run --frozen pytest` and CI.

## Where to add tests

Add entity lifecycle and cross-component integration cases here. Put import approval, parsing, and persistence cases in their own domains.

Shared Home Assistant fixtures belong in [`tests/conftest.py`](../conftest.py). The authoritative per-file inventory, Node/browser commands, and CI scope are in [the test suite guide](../../docs/testing.md).
