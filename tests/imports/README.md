# Configuration, mapping, and approval tests

Protect setup/options flows, PDF/CSV imports, user-selected mapping, canonical comparison, staged-versus-approved changes, and mosque-specific import workflows.

## Run just this area

```sh
uv run --frozen pytest --no-cov tests/imports/ -q
```

This skips the **whole-integration** coverage threshold for a focused run. Full-suite validation still requires `uv run --frozen pytest` and CI.

## Where to add tests

A new import regression belongs with its relevant flow; cover the approval/pending-review boundary, not just successful parsing. Parser-only issues belong under `parsers/`.

Shared Home Assistant fixtures belong in [`tests/conftest.py`](../conftest.py). The authoritative per-file inventory, Node/browser commands, and CI scope are in [the test suite guide](../../docs/testing.md).
