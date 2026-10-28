# CSV and PDF parsing tests

Protect CSV parsing, PDF extraction/worker limits, PDF layout detection, and Mosque A/B publication adapters. The layout-specific modules own format recognition; `test_pdf_parser.py` covers sandboxed extraction and unsafe documents.

## Run just this area

```sh
uv run --frozen pytest --no-cov tests/parsers/ -q
```

This skips the **whole-integration** coverage threshold for a focused run. Full-suite validation still requires `uv run --frozen pytest` and CI.

## Where to add tests

Reuse synthetic/anonymised PDFs and expected outcomes under `tests/fixtures/pdf/` and CSV examples under `tests/fixtures/csv/`. Keep separate tests for invalid input, limits, year boundaries, and parser-specific layout changes. Do not replace real isolated-worker checks with only mocked checks.

Shared Home Assistant fixtures belong in [`tests/conftest.py`](../conftest.py). The authoritative per-file inventory, Node/browser commands, and CI scope are in [the test suite guide](../../docs/testing.md).
