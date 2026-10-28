# Automation and blueprint tests

Protect blueprint configuration, rendered templates, adhan selection, and pausing/resuming media. Keep tests of Home Assistant service calls and entity triggers here, rather than in generic integration tests.

## Run just this area

```sh
uv run --frozen pytest --no-cov tests/automations/ -q
```

This skips the **whole-integration** coverage threshold for a focused run. Full-suite validation still requires `uv run --frozen pytest` and CI.

## Where to add tests

Add time/trigger edge cases beside the related blueprint tests. Mock external media services; use Home Assistant fixtures to verify actual blueprint behavior.

Shared Home Assistant fixtures belong in [`tests/conftest.py`](../conftest.py). The authoritative per-file inventory, Node/browser commands, and CI scope are in [the test suite guide](../../docs/testing.md).
