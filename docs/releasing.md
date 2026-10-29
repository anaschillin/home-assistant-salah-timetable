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

## Home Assistant Integration Quality Scale: internal gap audit

Audit baseline: 29 October 2026, against [the official 54-rule checklist](https://contributors.home-assistant.io/core/quality-scale/rules/). This is an **internal best-effort review of a custom HACS integration**, not an official Core tier or formal certification. A row marked **Implemented** means the required feature or convention is present in source, not that every real Home Assistant version or UI journey has passed acceptance. **Verify** means additional evidence is required; **Gap** means known incomplete work; **Adapted** and **N/A** require the documented non-hardware rationale and are not automatic official exemptions.

Do not set `manifest.json` to a claimed Core quality tier solely on this audit. Any future tier claim requires the official rule-specific tests and a maintainer review of each exemption.

### Bronze

| Rule | Assessment | Evidence / action |
| --- | --- | --- |
| [`action-setup`](https://contributors.home-assistant.io/core/quality-scale/action-setup/) | N/A | No integration-owned HA actions; automations are separate blueprints |
| [`appropriate-polling`](https://contributors.home-assistant.io/core/quality-scale/appropriate-polling/) | Adapted | 1-minute coordinator refreshes derived event snapshots; remote publication checks are scheduled separately |
| [`brands`](https://contributors.home-assistant.io/core/quality-scale/brands/) | Verify | Local brand/icon.png exists; verify any catalogue-specific brand requirements before publishing |
| [`common-modules`](https://contributors.home-assistant.io/core/quality-scale/common-modules/) | Gap | Coordinator remains at runtime/coordinator.py; do not add duplicate wrappers solely to satisfy a Core layout convention |
| [`config-flow`](https://contributors.home-assistant.io/core/quality-scale/config-flow/) | Implemented | UI setup validates name, stable ID and IANA timezone |
| [`config-flow-test-coverage`](https://contributors.home-assistant.io/core/quality-scale/config-flow-test-coverage/) | Verify | Config flow is tested, but its per-module 100% branch/line coverage has not been established |
| [`dependency-transparency`](https://contributors.home-assistant.io/core/quality-scale/dependency-transparency/) | Implemented | pypdf is pinned from public PyPI; inspect its licence/provenance on dependency changes |
| [`docs-actions`](https://contributors.home-assistant.io/core/quality-scale/docs-actions/) | N/A | No native integration actions |
| [`docs-conditions`](https://contributors.home-assistant.io/core/quality-scale/docs-conditions/) | N/A | No native condition platform |
| [`docs-high-level-description`](https://contributors.home-assistant.io/core/quality-scale/docs-high-level-description/) | Implemented | README explains approved published timetable imports |
| [`docs-installation-instructions`](https://contributors.home-assistant.io/core/quality-scale/docs-installation-instructions/) | Implemented | Getting-started guide covers HACS and manual setup |
| [`docs-removal-instructions`](https://contributors.home-assistant.io/core/quality-scale/docs-removal-instructions/) | Implemented | Getting-started guide explains per-mosque deletion and full uninstall |
| [`docs-triggers`](https://contributors.home-assistant.io/core/quality-scale/docs-triggers/) | N/A | No native trigger platform; optional HA automation blueprints documented |
| [`entity-event-setup`](https://contributors.home-assistant.io/core/quality-scale/entity-event-setup/) | Adapted | Coordinator and source manager own timers; platform entities do not register their own listeners |
| [`entity-unique-id`](https://contributors.home-assistant.io/core/quality-scale/entity-unique-id/) | Implemented | Sensors and calendar use stable mosque-scoped unique IDs |
| [`has-entity-name`](https://contributors.home-assistant.io/core/quality-scale/has-entity-name/) | Implemented | Entities use has_entity_name, with translated calendar name |
| [`runtime-data`](https://contributors.home-assistant.io/core/quality-scale/runtime-data/) | Implemented | Coordinator held in ConfigEntry.runtime_data |
| [`test-before-configure`](https://contributors.home-assistant.io/core/quality-scale/test-before-configure/) | N/A | No external login or connection at setup; validate timezone and identity locally |
| [`test-before-setup`](https://contributors.home-assistant.io/core/quality-scale/test-before-setup/) | Implemented | Storage is validated and first coordinator refresh runs before platform setup |
| [`unique-config-entry`](https://contributors.home-assistant.io/core/quality-scale/unique-config-entry/) | Implemented | Duplicate mosque IDs are rejected by unique ID |

### Silver

| Rule | Assessment | Evidence / action |
| --- | --- | --- |
| [`action-exceptions`](https://contributors.home-assistant.io/core/quality-scale/action-exceptions/) | N/A | No integration-owned Home Assistant actions |
| [`config-entry-unloading`](https://contributors.home-assistant.io/core/quality-scale/config-entry-unloading/) | Implemented | Unload stops source checks and coordinator callbacks; regression tests exist |
| [`docs-configuration-parameters`](https://contributors.home-assistant.io/core/quality-scale/docs-configuration-parameters/) | Verify | Review every import, Ramadan and source option against public instructions |
| [`docs-installation-parameters`](https://contributors.home-assistant.io/core/quality-scale/docs-installation-parameters/) | Implemented | Setup fields and mosque-ID rules documented |
| [`entity-unavailable`](https://contributors.home-assistant.io/core/quality-scale/entity-unavailable/) | Implemented | Missing Salah/event data makes timestamp sensors unavailable; source status remains independently readable |
| [`integration-owner`](https://contributors.home-assistant.io/core/quality-scale/integration-owner/) | Implemented | Maintainer recorded in manifest codeowners |
| [`log-when-unavailable`](https://contributors.home-assistant.io/core/quality-scale/log-when-unavailable/) | N/A | No continuously connected device; remote source errors represented by status instead |
| [`parallel-updates`](https://contributors.home-assistant.io/core/quality-scale/parallel-updates/) | Implemented | sensor.py and calendar.py declare PARALLEL_UPDATES = 0 |
| [`reauthentication-flow`](https://contributors.home-assistant.io/core/quality-scale/reauthentication-flow/) | N/A | No credentials are collected or stored for public HTTPS timetable downloads |
| [`test-coverage`](https://contributors.home-assistant.io/core/quality-scale/test-coverage/) | Gap | Current 94.5% overall line threshold does not prove >95% in every Python module |

### Gold

| Rule | Assessment | Evidence / action |
| --- | --- | --- |
| [`devices`](https://contributors.home-assistant.io/core/quality-scale/devices/) | Implemented | One logical Home Assistant device per configured mosque |
| [`diagnostics`](https://contributors.home-assistant.io/core/quality-scale/diagnostics/) | Implemented | Allowlisted, redacted per-entry diagnostic snapshot |
| [`discovery`](https://contributors.home-assistant.io/core/quality-scale/discovery/) | N/A | Mosques and their publications have no network discovery mechanism |
| [`discovery-update-info`](https://contributors.home-assistant.io/core/quality-scale/discovery-update-info/) | N/A | No discoverable device address to update |
| [`docs-data-update`](https://contributors.home-assistant.io/core/quality-scale/docs-data-update/) | Implemented | Source checking and user-approved update workflow documented |
| [`docs-examples`](https://contributors.home-assistant.io/core/quality-scale/docs-examples/) | Implemented | Automation and media blueprints supplied |
| [`docs-known-limitations`](https://contributors.home-assistant.io/core/quality-scale/docs-known-limitations/) | Implemented | PDF layout, date, HA compatibility and source limitations documented |
| [`docs-supported-devices`](https://contributors.home-assistant.io/core/quality-scale/docs-supported-devices/) | Adapted | No physical products; supported publication layouts are documented instead |
| [`docs-supported-functions`](https://contributors.home-assistant.io/core/quality-scale/docs-supported-functions/) | Verify | Cross-check the complete entity list against current sensor/calendar implementation |
| [`docs-troubleshooting`](https://contributors.home-assistant.io/core/quality-scale/docs-troubleshooting/) | Implemented | Getting-started and dashboard troubleshooting sections |
| [`docs-use-cases`](https://contributors.home-assistant.io/core/quality-scale/docs-use-cases/) | Implemented | README and automation examples cover dashboards and reminders |
| [`dynamic-devices`](https://contributors.home-assistant.io/core/quality-scale/dynamic-devices/) | N/A | Additional mosques are explicitly added via a config flow |
| [`entity-category`](https://contributors.home-assistant.io/core/quality-scale/entity-category/) | Implemented | Source and coverage status sensors are diagnostic |
| [`entity-device-class`](https://contributors.home-assistant.io/core/quality-scale/entity-device-class/) | Implemented | Prayer events are timestamp sensors; status sensors use enum device class |
| [`entity-disabled-by-default`](https://contributors.home-assistant.io/core/quality-scale/entity-disabled-by-default/) | Verify | Audit low-use sensors against dashboard dependencies before disabling anything |
| [`entity-translations`](https://contributors.home-assistant.io/core/quality-scale/entity-translations/) | Implemented | Sensor names and prayer calendar use translations |
| [`exception-translations`](https://contributors.home-assistant.io/core/quality-scale/exception-translations/) | Gap | Audit calendar and import UI exception paths for translatable messages |
| [`icon-translations`](https://contributors.home-assistant.io/core/quality-scale/icon-translations/) | Implemented | Calendar icon now declared via icons.json; device class supplies standard sensor icons |
| [`reconfiguration-flow`](https://contributors.home-assistant.io/core/quality-scale/reconfiguration-flow/) | Implemented | Name and timezone editable without changing mosque identity or storage |
| [`repair-issues`](https://contributors.home-assistant.io/core/quality-scale/repair-issues/) | Implemented | Corrupt or invalid timetable storage raises a persistent Repairs issue |
| [`stale-devices`](https://contributors.home-assistant.io/core/quality-scale/stale-devices/) | Verify | Confirm per-entry device cleanup and registry behaviour on removal/re-add |

### Platinum

| Rule | Assessment | Evidence / action |
| --- | --- | --- |
| [`async-dependency`](https://contributors.home-assistant.io/core/quality-scale/async-dependency/) | Adapted | Async downloads; synchronous PDF parsing is isolated in a worker/executor rather than called on the event loop |
| [`inject-websession`](https://contributors.home-assistant.io/core/quality-scale/inject-websession/) | N/A | No external API client library; separate HTTPS connector is a deliberate SSRF/DNS validation boundary |
| [`strict-typing`](https://contributors.home-assistant.io/core/quality-scale/strict-typing/) | Gap | Python integration is not yet checked with strict mypy |

### Prioritised follow-up

1. **Validate candidate CI:** run `uv run --frozen ruff check .`, `uv run --frozen ruff format --check .`, all Python tests, frontend tests, hassfest and HACS validation; inspect actual run results for this exact commit.
2. **Silver coverage:** produce a per-module coverage report; add genuine behaviour tests for every module at or below 95%. Retain the existing aggregate gate until every module is demonstrably above the official threshold.
3. **Gold usability:** review user-facing exception translations and low-use entity defaults, then verify deletion and entity-registry behaviour with a disposable two-mosque Home Assistant installation.
4. **Bronze structure:** document why the coordinator lives in the organized runtime package or migrate it cleanly to the conventional top-level module in a separate refactor; never duplicate implementations.
5. **Platinum:** treat strict mypy and an asynchronous dependency design review as optional later work; keep the explicit HTTPS security boundary.
