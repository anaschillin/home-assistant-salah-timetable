# Test directory

Tests are grouped by the **behavior they protect**, with one folder for each production area. See [docs/testing.md](../docs/testing.md) for the complete, file-by-file inventory of 51 Python and 13 Node unit modules, shared fixture guidance, and CI responsibilities.

## Choose the right area

| Directory | Main responsibility |
| --- | --- |
| [automations/](automations/README.md) | Adhan, triggers, and media blueprints |
| [calendar/](calendar/README.md) | Prayer events, calendar entities, and timezone boundaries |
| [core/](core/README.md) | Setup/unload, models, coordinators, and diagnostics |
| [frontend/](frontend/README.md) | Card/editor, resources, JS tests, and browser smoke |
| [imports/](imports/README.md) | Config flows, mapping, staging, and approval |
| [parsers/](parsers/README.md) | CSV/PDF parsing, PDF layouts, and sandbox limits |
| [ramadan/](ramadan/README.md) | Ramadan data, activation, and date-window validation |
| [sources/](sources/README.md) | Remote downloads, source profiles, and update checks |
| [storage/](storage/README.md) | Persistence, repairs, schema upgrades, and backup acceptance |
| [tooling/](tooling/README.md) | Packaging, compatibility, provenance, and inventory safeguards |

The README in each directory provides a focused test command and where-to-add-test guidance. For overlapping behaviors, place a regression in the area that **owns the behavior** rather than the area supplying a mock.

## Run tests

```sh
uv sync --frozen --group dev
uv run --frozen pytest
uv run --frozen pytest --no-cov tests/parsers/ -q
npm test
REQUIRE_BROWSER_TESTS=1 npm run test:browser
```

The normal Python run enforces the whole-integration coverage gate. Use `--no-cov` for focused diagnosis, not as release evidence.

Shared Home Assistant fixtures remain in [conftest.py](conftest.py), and input files remain under [fixtures/](fixtures/). Test inventory checks in [tooling/test_suite_inventory.py](tooling/test_suite_inventory.py) catch undocumented additions, moves, or missing area guides in CI. Keep the documented inventory and category guide up to date when adding or relocating tests.
