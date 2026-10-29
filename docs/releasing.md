# Building and accepting a release

Current integration version: <!-- docs:version -->0.9.19<!-- /docs:version -->.

## Current release readiness

Check the **exact candidate commit and version**; do not reuse validation claims from older changes. Manifest/project/frontend versions and release notes must agree. A successful CI run does not prove an authenticated HACS UI installation or every Home Assistant OS use case.

**Required:** passing Validate and CodeQL on the candidate commit, package/version checks, checksum review and documented relevant manual HACS/Home Assistant acceptance.

**Optional/deferred:** complete HAOS/Supervisor restore on a separate test instance. Automated Home Assistant Container backup/restore is narrower; neither is a per-PR requirement. See [Backup restore acceptance](releasing.md#optional-full-backup-and-restore-acceptance).

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

Confirm the hosted workflow checks on the actual release commit: locked Python tests and coverage, separate HA version suites, Chromium, hassfest, HACS validation, supported-current live Container smoke and release archive consistency. [Testing](testing.md), [Compatibility](testing.md#compatibility-test-environments) and [Live smoke](testing.md#disposable-home-assistant-live-testing) explain these checks.

## Manual HACS and Home Assistant acceptance

Use disposable configurations and synthetic timetables; note the installed HA/integration versions, client/device and outcome.

1. Install/update through the custom HACS repository and restart; confirm the integration and graphical card load.
2. Configure two different mosques; confirm their sensors, dashboards, selectors and source data remain isolated.
3. Test supported annual/monthly/Ramadan PDF/CSV and HTTPS imports, layout detection, date mapping, comparison, explicit approval/rejection and safe handling of unsupported input.
4. Verify pending-versus-approved state, updates, restart/upgrade persistence and safe removal/re-addition without affecting another mosque.
5. Test next Salah/Jamaat events, calendar, Friday entries, missing dates and DST/year boundaries.
6. Verify mobile/tablet readability, Yesterday/Today/Tomorrow dates, keyboard navigation and relevant optional blueprints.

Full HAOS/Supervisor restore is an **optional** additional test, documented in [Backup and restore](releasing.md#optional-full-backup-and-restore-acceptance). Do not describe Container tests as completing it.

## Draft release

The manually triggered **Prepare draft release** workflow accepts an existing `vMAJOR.MINOR.PATCH` tag for a commit on `main` with a passing Validate push run. It validates versions, changelog, ancestry and checksum, and creates a **draft**, not a published release.

For a local read-only review **after the matching tag exists**, use its version from the manifest:

```sh
source <(python3 scripts/sync_documentation.py --shell)
uv run --frozen python -m scripts.prepare_release --tag "v$INTEGRATION_VERSION" --output-dir /tmp/salah-release-review
```

Review the release notes and draft artifact before publishing.

## Validation and acceptance scope

Validation evidence is specific to an **exact commit**. The authoritative historical job logs, artifacts and results are on [GitHub Actions](https://github.com/anaschillin/home-assistant-salah-timetable/actions), rather than in an ever-growing per-PR diary.

### Automated checks

The validation workflow covers Python tests and coverage, Ruff, Node frontend tests, Chromium interaction/visual checks, minimum/current pinned Home Assistant compatibility, hassfest, HACS repository validation, package consistency and a disposable Home Assistant Container live smoke run.

<!-- docs:excerpt validation-boundaries -->
HACS repository validation does not prove installation through the authenticated HACS UI. Chromium tests use Home Assistant element stand-ins, and disposable Home Assistant Container checks do not establish physical-device behaviour or full Home Assistant OS/Supervisor restoration. Assess the **exact candidate version** through the manual [release acceptance checklist](releasing.md#manual-hacs-and-home-assistant-acceptance).
<!-- /docs:excerpt validation-boundaries -->

For reproducible commands and test boundaries see [Testing](testing.md), [Compatibility](testing.md#compatibility-test-environments), [Live smoke](testing.md#disposable-home-assistant-live-testing) and [Visual regression](testing.md#frontend-visual-regression).

### Manual acceptance

For a release candidate, record real HACS install/update and HAOS usage on the **exact version**; check import/approval, two-mosque isolation, dashboard rendering on mobile/tablet, date boundaries, storage after restart and relevant automation behaviour. Capture environment and results in the release review.

A full HAOS/Supervisor backup restore is optional/deferred, not a prerequisite for every change or release. See [Backup and restore](releasing.md#optional-full-backup-and-restore-acceptance).

The authoritative sign-off procedure is [Releasing](releasing.md).

## Optional full backup and restore acceptance

**Status: optional full HAOS restore exercise, deferred (29 October 2026).** Reproducible
tooling and passing disposable Home Assistant Container archive/restore checks
are available. A **full, observed restore on a separate disposable HAOS
instance** has not been performed; the existing migration/per-entry storage
checks are narrower and must not be represented as a full HAOS restore.
The maintainer reports routine HAOS/HACS testing after PRs; this does not
by itself establish that the particular full-backup restore below has passed. See the
[release sign-off list](releasing.md#current-release-readiness)
for the current separation between required PR checks and this optional
resilience check.

Home Assistant Container supports configuration backups and the official
`homeassistant.backup_restore` module; HAOS has a broader full-backup
contract including Supervisor-managed folders/apps. The tests below are
**different scopes** and must be recorded separately.

### Synthetic disposable test setup

Use only a disposable HAOS VM or Home Assistant Container, with synthetic
mosque times. Never target your existing Home Assistant installation.

1. Install the candidate integration on the disposable system; add one or
   preferably two mosques. Approve a synthetic annual source and stage a
   *different* proposal without accepting it. Configure a confirmed Ramadan
   window and a dashboard with the bundled card.
2. Record the test version/commit, config-entry IDs, source metadata,
   registered sensor/calendar IDs, resource count, approved vs pending state
   and any Repairs issues. Use sanitized screenshots/counts only.
3. In **Settings → System → Backups**, create a backup including the Home
   Assistant configuration and database. On HAOS, choose **Full backup**,
   retaining the encryption key securely. Wait for completion before copying
   the file. Do not upload this archive to the GitHub repository or CI
   artifacts: it contains real credentials even with synthetic timetable data.
4. Restore the **actual archive into a different clean disposable HAOS
   instance through the supported onboarding restore flow**. Supply the
   backup's encryption key privately, select all available parts, and let
   Core/apps finish reinstalling. Do not attempt this on the primary HAOS VM.
5. Confirm **same entry IDs, devices, entity unique IDs, registered calendar,
   dashboard/card resource and options**. Confirm approved source bytes and
   source-check timestamps/validators remain unchanged, pending remains
   pending, and no downloaded source becomes approved on restore.
6. Restart the restored HAOS once more. Verify the same results, no duplicate
   resources, no unexpected Repairs items and correct source isolation.
7. Record supported Core version, backup archive format, restore mechanism,
   redacted counts, restart results and any limitations in
   [validation.md](releasing.md#validation-and-acceptance-scope). Do not commit backups/auth tokens.

### Reproducible Home Assistant Container preflight

For a second disposable Home Assistant **Container**, create a real archive
with **Settings → System → Backups → Create backup** (or the documented
`backup.create` action). Container backups normally live under
`/config/backups`; copy the resulting `.tar` into a temporary private
directory only after backup creation reports completion.

Once you have a backup and the source container's configuration volume (as a
filesystem path), run:

```bash
source <(python3 scripts/sync_documentation.py --shell)
docker pull "ghcr.io/home-assistant/home-assistant:$HA_TESTED_VERSION"
python -m scripts.disposable_backup_restore \
  --backup /private/synthetic-test-backup.tar \
  --original /private/synthetic-source-config \
  --ha-version "$HA_TESTED_VERSION" \
  --confirm-disposable \
  --serve
```

This **does not restore onto the source**. It asks Home Assistant's own
backup restore module to restore the real archive into an ephemeral,
separately mounted configuration, and
`scripts/verify_backup_restore.py` compares config entries, stored
timetables, approved/staged separation, remote metadata, entity/device
registries and card resources **without printing their contents**. A
different, loopback-only test container then starts for an additional UI
check; press Enter to stop/delete the container and restored files. Use
`SALAH_TEST_BACKUP_PASSWORD` in the environment if an encrypted archive
requires a password, not a command-line argument.

Use the same Core patch version as the source for this preflight. In the example above,
`HA_TESTED_VERSION` is loaded from the supported-current compatibility project. For
automation, omit `--serve` to validate the archive and restored files
without booting the UI. The source reference must be a **stopped or
quiescent** disposable HA config immediately after backup creation; live
writes after the archive will otherwise correctly cause a comparison failure.

**Limits:** This helper validates only the HA Container configuration restore
using the official extraction implementation. It does not create the
archive, log into the restored UI, prove HAOS Supervisor/apps recovery,
prove physical hardware behavior, or replace the separate full HAOS
restore/restart acceptance.
