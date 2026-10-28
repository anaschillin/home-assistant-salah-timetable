# PDF worker and branch coverage

This branch adds white-box tests for the isolated `pdf_worker.py` entrypoint
without changing production subprocess boundaries. Existing parser/security
tests continue to run the worker with the current Python interpreter's `-I`
mode, bounded stdin, child resource limits, a small environment and suppressed
stderr. Those **real subprocess tests remain authoritative** for sandboxing.

The additional `tests/parsers/test_pdf_worker_unit.py` exercises worker validation
and output branches in the test process, substituting fake PDF pages,
stream sizes, pypdf reader results and harmless resource-limit callbacks.
It restores all pypdf guard settings afterwards. In-process test coverage
is not proof that the real child can be instrumented or that a new layout is
supported.

## Coverage policy

The root `Validate` Python job now enables `--cov-branch` and writes
`coverage-branch.json`, then uses `scripts/check_coverage.py` to check
that **line coverage stays at or above the existing 94.5% gate**. The
separate *branch* metric is printed as a diagnostic baseline; it has no
independent minimum until enough evidence supports a stable gate.
This avoids inadvertently weakening the existing line threshold when
pytest-cov uses a combined statements-and-branches percentage.

The two pinned Home Assistant compatibility lanes retain their original
line-coverage enforcement and continue exercising the full suite.

Both changed Python files go through the pinned Ruff formatter
(`uv run --frozen ruff format`) in CI, followed by a clean-tree check,
`ruff check`, and `ruff format --check`.

To run the measured suite locally:

```bash
uv run --frozen pytest --cov-branch --cov-fail-under=0 --cov-report=json:coverage-branch.json
uv run --frozen python scripts/check_coverage.py coverage-branch.json
```

Do not silently add coverage instrumentation or environment startup hooks
to the isolated PDF worker: the child deliberately receives only a minimal
environment and does not import Home Assistant or the integration package.
