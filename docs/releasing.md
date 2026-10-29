# Building and accepting a release

## Current release readiness

Check the **exact candidate commit and version**; do not reuse validation claims from older changes. Manifest/project/frontend versions and release notes must agree. A successful CI run does not prove an authenticated HACS UI installation or every Home Assistant OS use case.

**Required:** passing Validate and CodeQL on the candidate commit, package/version checks, checksum review and documented relevant manual HACS/Home Assistant acceptance.

**Optional/deferred:** complete HAOS/Supervisor restore on a separate test instance. Automated Home Assistant Container backup/restore is narrower; neither is a per-PR requirement. See [Backup restore acceptance](backup-restore-acceptance.md).

## Build and verify

Update `custom_components/salah_timetable/manifest.json`, `pyproject.toml`, `uv.lock` where dependencies changed, the frontend card/cache version strings and `CHANGELOG.md` consistently.

```sh
uv sync --frozen --group dev
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
npm test
REQUIRE_BROWSER_TESTS=1 npm run test:browser
uv run --frozen python scripts/build_release.py --check
uv run --frozen python scripts/build_release.py
```

The build produces a deterministic `dist/salah_timetable-VERSION.zip` and SHA-256 sidecar. The archive includes installable integration source and required frontend/brand assets and license, **not** tests, fixtures or original mosque timetables.

Confirm the hosted workflow checks on the actual release commit: locked Python tests and coverage, separate HA version suites, Chromium, hassfest, HACS validation, supported-current live Container smoke and release archive consistency. [Testing](testing.md), [Compatibility](compatibility.md) and [Live smoke](live-smoke.md) explain these checks.

## Manual HACS and Home Assistant acceptance

Use disposable configurations and synthetic timetables; note the installed HA/integration versions, client/device and outcome.

1. Install/update through the custom HACS repository and restart; confirm the integration and graphical card load.
2. Configure two different mosques; confirm their sensors, dashboards, selectors and source data remain isolated.
3. Test supported annual/monthly/Ramadan PDF/CSV and HTTPS imports, layout detection, date mapping, comparison, explicit approval/rejection and safe handling of unsupported input.
4. Verify pending-versus-approved state, updates, restart/upgrade persistence and safe removal/re-addition without affecting another mosque.
5. Test next Salah/Jamaat events, calendar, Friday entries, missing dates and DST/year boundaries.
6. Verify mobile/tablet readability, Yesterday/Today/Tomorrow dates, keyboard navigation and relevant optional blueprints.

Full HAOS/Supervisor restore is an **optional** additional test, documented in [Backup and restore](backup-restore-acceptance.md). Do not describe Container tests as completing it.

## Draft release

The manually triggered **Prepare draft release** workflow accepts an existing `vMAJOR.MINOR.PATCH` tag for a commit on `main` with a passing Validate push run. It validates versions, changelog, ancestry and checksum, and creates a **draft**, not a published release.

For a local read-only review with the actual release tag:

```sh
uv run --frozen python -m scripts.prepare_release --tag vMAJOR.MINOR.PATCH --output-dir /tmp/salah-release-review
```

Review the release notes and draft artifact before publishing.
