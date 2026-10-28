# Remote download and update tests

Protect remote download constraints, source metadata, URL-based configuration, scheduled checks, checksums, and pending-review behavior when remote files change.

## Run just this area

```sh
uv run --frozen pytest --no-cov tests/sources/ -q
```

This skips the **whole-integration** coverage threshold for a focused run. Full-suite validation still requires `uv run --frozen pytest` and CI.

## Where to add tests

Prefer fake network responses. Test that a changed remote source does not silently replace approved timetable data; cover reload/persistence separately when needed.

Shared Home Assistant fixtures belong in [`tests/conftest.py`](../conftest.py). The authoritative per-file inventory, Node/browser commands, and CI scope are in [the test suite guide](../../docs/testing.md).
