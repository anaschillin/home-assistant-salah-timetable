# Ramadan timetable tests

Protect Ramadan activation, source selection, timetable overrides, date-window validation, and Ramadan-specific review/import options.

## Run just this area

```sh
uv run --frozen pytest --no-cov tests/ramadan/ -q
```

This skips the **whole-integration** coverage threshold for a focused run. Full-suite validation still requires `uv run --frozen pytest` and CI.

## Where to add tests

Keep Ramadan domain rules here, while generic CSV/PDF parsing remains in `parsers/` and generic staging/approval flows in `imports/`.

Shared Home Assistant fixtures belong in [`tests/conftest.py`](../conftest.py). The authoritative per-file inventory, Node/browser commands, and CI scope are in [the test suite guide](../../docs/testing.md).
