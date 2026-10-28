# Quality, release, and inventory tests

Protect distribution packaging, asset provenance, pinned compatibility checks, release preparation, and the test-suite inventory itself.

## Run just this area

```sh
uv run --frozen pytest --no-cov tests/tooling/ -q
```

This skips the **whole-integration** coverage threshold for a focused run. Full-suite validation still requires `uv run --frozen pytest` and CI.

## Where to add tests

Keep checks of repository metadata and documentation here, not in feature-level integration tests. Run the full suite before merging: focused category runs intentionally disable whole-project coverage.

Shared Home Assistant fixtures belong in [`tests/conftest.py`](../conftest.py). The authoritative per-file inventory, Node/browser commands, and CI scope are in [the test suite guide](../../docs/testing.md).
