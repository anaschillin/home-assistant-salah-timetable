# Dashboard, card, and browser tests

Python tests verify Home Assistant frontend resources, HTTP endpoints, and dashboard presentation. JavaScript `*.test.mjs` files verify card/editor behavior, state, styling, localisation, backgrounds, and visual test infrastructure.

## Run just this area

```sh
uv run --frozen pytest --no-cov tests/frontend/ -q
```

This skips the **whole-integration** coverage threshold for a focused run. Full-suite validation still requires `uv run --frozen pytest` and CI.

## Where to add tests

Run `npm test` for Node unit tests and `REQUIRE_BROWSER_TESTS=1 npm run test:browser` for Chromium smoke checks. Keep shared browser helpers in `browser-harness.js`; put new interactive regression assertions in a test module or the smoke runner.

Shared Home Assistant fixtures belong in [`tests/conftest.py`](../conftest.py). The authoritative per-file inventory, Node/browser commands, and CI scope are in [the test suite guide](../../docs/testing.md).
