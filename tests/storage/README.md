# Persistence and recovery tests

Protect timetable persistence, remote-source records, schema migrations, corruption/repair paths, and backup/restore acceptance checks.

## Run just this area

```sh
uv run --frozen pytest --no-cov tests/storage/ -q
```

This skips the **whole-integration** coverage threshold for a focused run. Full-suite validation still requires `uv run --frozen pytest` and CI.

## Where to add tests

Use historical payloads under `tests/fixtures/storage/`. These tests are not a substitute for an actual disposable HAOS backup-and-restore acceptance exercise.

Shared Home Assistant fixtures belong in [`tests/conftest.py`](../conftest.py). The authoritative per-file inventory, Node/browser commands, and CI scope are in [the test suite guide](../../docs/testing.md).
