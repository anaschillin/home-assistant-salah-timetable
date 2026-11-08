# Dashboard, card, and browser tests

Python tests verify Home Assistant frontend resources, HTTP endpoints, and dashboard presentation. JavaScript `*.test.mjs` files verify card/editor behavior, state, styling, localisation, backgrounds, and visual test infrastructure.

The dependency-free Node suite also owns `feature-releases.test.mjs` and
`stable-releases.test.mjs`, which test release automation against a simulated
GitHub API without publishing or deleting real releases.

## Run just this area

```sh
uv run --frozen pytest --no-cov tests/frontend/ -q
```

This skips the **whole-integration** coverage threshold for a focused run. Full-suite validation still requires `uv run --frozen pytest` and CI.

## Where to add tests

Run `npm test` for Node unit tests and `REQUIRE_BROWSER_TESTS=1 npm run test:browser` for Chromium smoke checks. Keep shared browser helpers in `browser-harness.js`; put new interactive regression assertions in a test module or the smoke runner.

Shared Home Assistant fixtures belong in [`tests/conftest.py`](../conftest.py). The authoritative per-file inventory, Node/browser commands, and CI scope are in [the test suite guide](../../docs/testing.md).

The editor smoke tests cover the single ordered mosque checkbox list, six-dot
drag handle and up/down fallback, and preservation of YAML titles during graphical
edits. Browser smoke uses pointer clicks to open and leave the monthly timetable
in each mode (Compact More menu, Standard/Detailed labelled header actions). Browser
acceptance must also check mobile/tablet sizing, RTL and Home Assistant's
native drag-and-drop behaviour before the PR is merged.

Widget tests cover field-preserving Jamaat comparisons, mosque-local clock
differences across DST, saved configuration and temporary view-scoped mosque
selection. The Chromium smoke runner uses `widget-browser-fixture.js` to prepare
native widget fixtures; assertions stay in `browser-smoke.mjs`. It checks status
rendering, permission-aware setup links, independent view groups and preview
isolation alongside the existing card matrix.
