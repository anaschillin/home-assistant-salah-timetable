# Test directory

Tests are grouped by responsibility. The complete file-by-file inventory, fixture locations, CI behaviour, maintenance conventions and commands are documented in [docs/testing.md](../docs/testing.md).

Run the full Python suite from the repository root with `uv run --frozen pytest`. Use `uv run --frozen pytest --no-cov tests/<area>/ -q` for a focused run (the normal coverage gate applies to the **whole** integration). Run `npm test` for the frontend Node unit tests and `REQUIRE_BROWSER_TESTS=1 npm run test:browser` for Chromium smoke.

Do not move or duplicate `conftest.py` or shared `fixtures/` for a domain-specific test. The test hierarchy is deliberately shallow to keep pytest collection and fixture resolution predictable.
