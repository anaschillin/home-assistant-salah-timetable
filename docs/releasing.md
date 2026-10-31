# Building and accepting a release

Current integration version: <!-- docs:version -->1.0.0<!-- /docs:version -->.

## Current release readiness

Check the **exact candidate commit and version**; do not reuse validation claims from older changes. The generated manifest/project/frontend versions must agree with `versions.toml` and the release notes. A successful CI run does not prove an authenticated HACS UI installation or every Home Assistant OS use case.

**Required:** passing Validate and CodeQL on the candidate commit, package/version checks, checksum review and documented relevant manual HACS/Home Assistant acceptance.

**Quality-scale reference:** the [internal 54-rule audit](releasing.md#home-assistant-integration-quality-scale-internal-gap-audit) records implemented, outstanding, unverified and not-applicable rules. It is not an official Home Assistant quality tier.

**Optional/deferred:** complete HAOS/Supervisor restore on a separate test instance. Automated Home Assistant Container backup/restore is narrower; neither is a per-PR requirement. See [Backup restore acceptance](releasing.md#optional-full-backup-and-restore-acceptance).

## Build and verify

Edit the release version or dependency/toolchain pins only in
[`versions.toml`](../versions.toml), then run `python scripts/sync_versions.py --write`.
This refreshes required metadata, frontend cache/import query versions, CI values
and documentation together. Keep the candidate's `CHANGELOG.md` heading and notes
accurate; historical release headings remain unchanged.

Regenerate `uv.lock` with `uv lock` after changing the root project version or pins,
and regenerate affected compatibility locks after their dependency pins change.
See the [central version workflow](../CONTRIBUTING.md#keeping-documentation-variables-current)
for the lane commands. The synchronizer does not resolve or download dependencies.
Commit the central configuration, generated files and locks together before
running the candidate checks:

```sh
python scripts/sync_versions.py --check
uv sync --frozen --group dev
uv run --frozen pytest --cov-branch --cov-fail-under=0 --cov-report=json:coverage-branch.json
uv run --frozen python scripts/check_coverage.py coverage-branch.json
uv run --frozen ruff check .
uv run --frozen ruff format --check .
npm test
REQUIRE_BROWSER_TESTS=1 npm run test:browser
uv run --frozen python scripts/build_release.py --check
uv run --frozen python scripts/build_release.py
```

The build produces a deterministic `dist/salah_timetable-VERSION.zip` and SHA-256 sidecar. The archive includes installable integration source, `icons.json`, translations, required frontend/brand assets and license, **not** tests, fixtures or original mosque timetables.

Confirm the hosted workflow checks on the actual release commit: locked Python tests and coverage, separate HA version suites, Chromium, hassfest, HACS validation, supported-current live Container smoke and release archive consistency. [Testing](testing.md), [Compatibility](testing.md#compatibility-test-environments) and [Live smoke](testing.md#disposable-home-assistant-live-testing) explain these checks.

## Manual HACS and Home Assistant acceptance

Use disposable configurations and synthetic timetables; note the installed HA/integration versions, client/device and outcome.

1. Install/update through the custom HACS repository and restart; confirm the integration and graphical card load.
2. Configure two different mosques; confirm their sensors, dashboards, selectors and source data remain isolated.
3. Reconfigure one mosque's name and timezone; verify its mosque ID, existing entities, approved timetable and the other mosque remain intact. Check timezone interpretation and that Configure → Mosque settings retains the updated timezone.
4. Test supported annual/monthly/Ramadan PDF/CSV and HTTPS imports, layout detection, date mapping, comparison, explicit approval/rejection and safe handling of unsupported input.
5. Verify pending-versus-approved state, updates, restart/upgrade persistence and safe removal/re-addition without affecting another mosque.
6. Test next Salah/Jamaat events, translated calendar name/icon, Friday entries, missing dates and DST/year boundaries.
7. Verify mobile/tablet readability, Yesterday/Today/Tomorrow dates, keyboard navigation and relevant optional blueprints.

Full HAOS/Supervisor restore is an **optional** additional test, documented in [Backup and restore](releasing.md#optional-full-backup-and-restore-acceptance). Do not describe Container tests as completing it.

## Automatic feature test releases

After this workflow is merged into `main`, each **non-draft, same-repository PR
targeting `main`** gets one published GitHub prerelease when its latest Validate
and CodeQL PR runs both succeed for the current feature-branch head. Known merge
conflicts and unsuccessful external commit statuses block publication. Mark a
draft PR **Ready for review** when it is ready for Home Assistant testing; this
does not merge it or replace manual acceptance.

- The tag is `vVERSION-pr.PR_NUMBER.FULL_HEAD_SHA`, using the branch's manifest
  version and exact commit. The release notes link to its PR and identify its
  branch. The reserved `-pr.NUMBER.SHA` tag namespace belongs to this automation.
- A new commit removes the previous candidate release and tag. A replacement is
  published only after the new head passes CI. Repeated notifications for the same
  passing commit leave the existing release intact.
- Merging, closing, returning to draft or retargeting away from `main` removes
  the candidate release and tag. Stable releases and feature branches are untouched.
- These are published **prereleases**, never GitHub's latest stable release. HACS
  installs the tagged repository source with the existing `hacs.json` configuration;
  there is no separate attached integration ZIP. GitHub's source ZIP includes
  `custom_components/salah_timetable` for manual copying into the HA configuration.

In HACS, enable pre-release/beta versions for Salah Timetable, refresh repository
information, then use **Redownload** to select the candidate tag. Restart Home
Assistant and refresh the browser/app cache. The manifest and frontend cache
version remain the branch's values, so switching candidates with the same manifest
version can require a forced cache refresh. After testing/merge, select the desired
stable release again; deleting a GitHub release does not change an installed HA
instance. Actual HACS/device installation remains a manual acceptance check.

`Feature release lifecycle` is a read-only PR-event notification workflow.
`Reconcile feature releases` responds to it and to Validate/CodeQL runs, and always
loads its script from trusted `main`. It reads PR metadata/manifest data through
GitHub's API and never checks out or executes feature code with write credentials.
Publication is serialized; current PR state is rechecked around creation. Fork PRs
do not receive releases. Only the built-in `GITHUB_TOKEN` is needed.

For already-green PRs after initial installation, or to recover after a failed or
cancelled automation run, run **Actions → Reconcile feature releases → Run workflow**
on `main`. This reconciles all eligible PRs and cleans orphan candidate tags. The
workflow must be on `main` before automatic publication can operate; its own PR
cannot exercise the full publication lifecycle before that merge. GitHub event
delivery/runner queues determine cleanup timing.

## Automatic stable releases

After the **current integration version in `versions.toml`** is merged into
`main`, the [Publish stable HACS release](../.github/workflows/stable-release.yml)
workflow runs as soon as both `Validate` and `CodeQL` have passed on the **same
exact latest main commit**. It is triggered by the completion of either workflow
and can also be retried via **Actions → Publish stable HACS release → Run workflow**.
The workflow always reads the current `main`, not a pull request branch or
untrusted workflow artifact. Document the manual HACS/Home Assistant acceptance
on the release PR **before merging**; that acceptance is not independently
performed by the publishing workflow.

The pipeline:

1. Requires complete successful `Validate` (including HACS, hassfest, Python,
   browser and Home Assistant compatibility) and `CodeQL` push workflow runs
   for the exact currently checked-out `main` commit. Pending, failing, stale,
   PR-only and non-main results cannot publish.
2. Checks synchronised versions, the release-notes section, runtime archive
   content, cleared asset-provenance inventory and ZIP SHA-256 checksum.
3. Creates an immutable `vMAJOR.MINOR.PATCH` tag at that validated commit,
   then publishes a **stable** GitHub release with the changelog notes,
   deterministic installation ZIP and checksum. HACS installs the tagged
   integration directory; the attached ZIP is also available for manual installs.
4. Skips subsequent pushes with the **same already published version**. It will
   never move an existing tag, overwrite an existing release, or publish a lower
   stable version after a newer one. Existing draft/prerelease releases with the
   same tag cause a safe error requiring a maintainer decision.
5. Rechecks the latest `main` and both CI results immediately before creating
   the release. All writes use the built-in `GITHUB_TOKEN`, with serialisation to
   prevent overlapping stable-release runs.

**Bump `versions.toml` and add a `CHANGELOG.md` section for each new stable
version.** Run `python scripts/sync_versions.py --write`, regenerate the
relevant lockfiles, and merge the usual reviewed PR. The stable pipeline only
publishes a new version; it deliberately never invents a version number or
publishes modified source code under an existing version.

**HACS catalogue inclusion is a separate one-time submission.** This release
pipeline publishes GitHub releases, which HACS can install as a custom repository
now and track as catalogue updates after the
[`hacs/default` application](https://hacs.dev/docs/publish/include/) is approved.
It cannot automatically bypass that upstream review.

## Optional manual draft release

The manually triggered **Prepare draft release** workflow remains available as
a fallback to prepare reviewable artifacts from an **existing** validated tag.
Do not create a manual draft for a tag intended for automatic publication:
the automated pipeline intentionally refuses to overwrite or auto-publish it.

The manually triggered **Prepare draft release** workflow accepts an existing `vMAJOR.MINOR.PATCH` tag for a commit on `main` with a passing Validate push run. It validates versions, changelog, ancestry and checksum, and creates a **draft**, not a published release.

For a local read-only review **after the matching tag exists**, export its version from the central configuration:

```sh
source <(python3 scripts/sync_documentation.py --shell)
uv run --frozen python -m scripts.prepare_release --tag "v$INTEGRATION_VERSION" --output-dir /tmp/salah-release-review
```

Review the release notes and draft artifact before publishing.

## Publishing to the HACS / Home Assistant Marketplace catalogue

Salah Timetable is already installable as a **custom HACS repository**. Listing it in the
default catalogue requires an additional pull request to
[`hacs/default`](https://github.com/hacs/default). Home Assistant 2026.11's built-in
Marketplace uses the same catalogue; the existing HACS repository link continues
to work in both.

1. Complete the [release acceptance](releasing.md#manual-hacs-and-home-assistant-acceptance)
   for the **exact** candidate on `main`. Confirm both HACS and hassfest pass
   without ignored checks, plus the repository's required Validate/CodeQL checks.
2. Ensure the public repository has a descriptive GitHub **About** description,
   topics, enabled issues, a README and the bundled `brand/icon.png`.
3. Publish a **stable GitHub release** before requesting catalogue inclusion.
   Follow [Automatic stable releases](#automatic-stable-releases): a new version
   in `versions.toml` is tagged and published after Validate and CodeQL pass on
   the same latest `main` commit. Check the published release and its assets;
   do not create a competing manual tag or draft for that version. If automatic
   publication is unavailable, use the [manual draft fallback](#optional-manual-draft-release)
   with an existing validated tag, review its artifacts and explicitly publish
   the draft as a non-prerelease release. Ephemeral PR feature
   prereleases, tags alone and drafts do **not** satisfy the catalogue requirement.
4. Fork [`hacs/default`](https://github.com/hacs/default) under the owner's
   personal GitHub account, create a branch from its `master`, and insert
   `anaschillin/home-assistant-salah-timetable` **alphabetically** in the
   JSON `integration` list. Do not submit from an organisation or edit the fork's
   `master` directly.
5. Open an editable pull request to `hacs/default:master` using the full
   upstream template. Include links to the published stable release and the
   passing HACS and hassfest jobs for the release's exact commit. Do not request
   reviewer attention, and do not mark any checklist item as complete before it is.
6. Once the catalogue PR is merged and the next catalogue scan has populated
   the listing, update [the installation instructions](../README.md#install)
   and their synchronized source excerpt to distinguish marketplace search
   from the optional manual custom-repository route.

Useful references: [HACS catalogue instructions](https://hacs.dev/docs/publish/include/),
[Marketplace publishing guide](https://contributors.home-assistant.io/marketplace/guides/catalog/),
and [HACS submission PRs](https://github.com/hacs/default/pulls). The upstream
review queue can take months; a passing submission does not mean instant listing.

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

Audit reviewed: 30 October 2026, against [the official 54-rule checklist](https://contributors.home-assistant.io/core/quality-scale/rules/), including each rule's applicability and exceptions. This is an **internal best-effort review of a custom HACS integration**, not an official Core tier or formal certification. A row marked **Implemented** means the required feature or convention is present with the cited evidence, not that every real Home Assistant version or UI journey has passed acceptance. **Verify** means additional evidence is required; **Gap** means known incomplete work. **N/A (reviewed)** identifies a specific official exception and its implementation evidence; absence of physical hardware alone is not a blanket exemption.

Keep candidate-specific test counts, coverage reports, installed versions and CI links in the pull request or release review. Re-run the [current validation commands](testing.md#run-and-debug) after code or dependency changes; historical results do not establish release readiness.

Do not set `manifest.json` to a claimed Core quality tier solely on this audit. Any future tier claim requires the official rule-specific tests and a maintainer review of each exemption.

### Bronze

| Rule | Assessment | Evidence / action |
| --- | --- | --- |
| [`action-setup`](https://contributors.home-assistant.io/core/quality-scale/action-setup/) | N/A (reviewed) | No integration-owned HA actions; automations are separate blueprints |
| [`appropriate-polling`](https://contributors.home-assistant.io/core/quality-scale/appropriate-polling/) | Implemented | Minute refreshes and absolute event boundaries derive local approved snapshots; publication checks run separately every 24 hours |
| [`brands`](https://contributors.home-assistant.io/core/quality-scale/brands/) | Implemented (custom integration) | Valid 256×256 `brand/icon.png`; the [official local-brand route](https://contributors.home-assistant.io/blog/2026/02/24/brands-proxy-api/) is supported since HA 2026.3, before this integration's minimum HA version. Core submission would require its own brands-repository review |
| [`common-modules`](https://contributors.home-assistant.io/core/quality-scale/common-modules/) | Implemented | Sole coordinator implementation at top-level `coordinator.py`; release archive includes all Python packages, with no compatibility wrappers |
| [`config-flow`](https://contributors.home-assistant.io/core/quality-scale/config-flow/) | Implemented | UI setup validates name, stable ID and IANA timezone |
| [`config-flow-test-coverage`](https://contributors.home-assistant.io/core/quality-scale/config-flow-test-coverage/) | Implemented (CI guard) | 100% line/branch coverage in `config_flow.py`, `imports/import_flow.py` and `sources/source_flow.py`; real HA tests assert unique identity, duplicate rejection, error recovery and unload/reload/stale-proposal approval boundaries. The rule includes reconfiguration and options flows, not only initial setup |
| [`dependency-transparency`](https://contributors.home-assistant.io/core/quality-scale/dependency-transparency/) | Implemented | pypdf is pinned from public PyPI; inspect its licence/provenance on dependency changes |
| [`docs-actions`](https://contributors.home-assistant.io/core/quality-scale/docs-actions/) | N/A (reviewed) | No native integration actions |
| [`docs-conditions`](https://contributors.home-assistant.io/core/quality-scale/docs-conditions/) | N/A (reviewed) | No native condition platform |
| [`docs-high-level-description`](https://contributors.home-assistant.io/core/quality-scale/docs-high-level-description/) | Implemented | README explains approved published timetable imports |
| [`docs-installation-instructions`](https://contributors.home-assistant.io/core/quality-scale/docs-installation-instructions/) | Implemented | Getting-started guide covers HACS and manual setup |
| [`docs-removal-instructions`](https://contributors.home-assistant.io/core/quality-scale/docs-removal-instructions/) | Implemented | Getting-started guide explains per-mosque deletion and full uninstall |
| [`docs-triggers`](https://contributors.home-assistant.io/core/quality-scale/docs-triggers/) | N/A (reviewed) | No native trigger platform; optional HA automation blueprints documented |
| [`entity-event-setup`](https://contributors.home-assistant.io/core/quality-scale/entity-event-setup/) | Implemented | Sensors/calendar inherit `CoordinatorEntity`, which registers in `async_added_to_hass` and unsubscribes through `async_on_remove`; lifecycle tests cover unload/reload and failed setup |
| [`entity-unique-id`](https://contributors.home-assistant.io/core/quality-scale/entity-unique-id/) | Implemented | Sensors and calendar use stable mosque-scoped unique IDs |
| [`has-entity-name`](https://contributors.home-assistant.io/core/quality-scale/has-entity-name/) | Implemented | Entities use has_entity_name, with translated calendar name |
| [`runtime-data`](https://contributors.home-assistant.io/core/quality-scale/runtime-data/) | Implemented | Coordinator held in ConfigEntry.runtime_data |
| [`test-before-configure`](https://contributors.home-assistant.io/core/quality-scale/test-before-configure/) | Implemented (scoped) | Initial mosque setup validates identity/timezone locally and has no connection; optional HTTPS source configuration downloads and validates before saving/staging its profile |
| [`test-before-setup`](https://contributors.home-assistant.io/core/quality-scale/test-before-setup/) | Implemented | Storage is validated and first coordinator refresh runs before platform setup |
| [`unique-config-entry`](https://contributors.home-assistant.io/core/quality-scale/unique-config-entry/) | Implemented | Duplicate mosque IDs are rejected by unique ID |

### Silver

| Rule | Assessment | Evidence / action |
| --- | --- | --- |
| [`action-exceptions`](https://contributors.home-assistant.io/core/quality-scale/action-exceptions/) | N/A (reviewed) | No integration-owned Home Assistant actions |
| [`config-entry-unloading`](https://contributors.home-assistant.io/core/quality-scale/config-entry-unloading/) | Implemented | Unload stops source checks and coordinator callbacks; regression tests exist |
| [`docs-configuration-parameters`](https://contributors.home-assistant.io/core/quality-scale/docs-configuration-parameters/) | Implemented | [Configuration reference](import_review.md#configuration-fields-and-defaults) cross-checked against every settings/import/mapping/review/source/Ramadan form, including defaults, limits and approval effects |
| [`docs-installation-parameters`](https://contributors.home-assistant.io/core/quality-scale/docs-installation-parameters/) | Implemented | Setup fields and mosque-ID rules documented |
| [`entity-unavailable`](https://contributors.home-assistant.io/core/quality-scale/entity-unavailable/) | Implemented | Missing Salah/event data makes timestamp sensors unavailable; source status remains independently readable |
| [`integration-owner`](https://contributors.home-assistant.io/core/quality-scale/integration-owner/) | Implemented | Maintainer recorded in manifest codeowners |
| [`log-when-unavailable`](https://contributors.home-assistant.io/core/quality-scale/log-when-unavailable/) | Implemented (source transitions) | Optional URL checks and source storage log one sanitized warning per failure episode and one recovery message, without publication identifiers; approved rows remain usable. Expected missing dates/fields are data absence, not a connection failure |
| [`parallel-updates`](https://contributors.home-assistant.io/core/quality-scale/parallel-updates/) | Implemented | sensor.py and calendar.py declare PARALLEL_UPDATES = 0 |
| [`reauthentication-flow`](https://contributors.home-assistant.io/core/quality-scale/reauthentication-flow/) | N/A (reviewed) | No credentials are collected or stored for public HTTPS timetable downloads |
| [`test-coverage`](https://contributors.home-assistant.io/core/quality-scale/test-coverage/) | Implemented (CI guard) | [Coverage gate](testing.md#run-and-debug) requires >95% combined statement/branch coverage for every Python module using raw counts and a source inventory; preserves the 94.5% aggregate line floor and rejects missing branch/module data |

### Gold

| Rule | Assessment | Evidence / action |
| --- | --- | --- |
| [`devices`](https://contributors.home-assistant.io/core/quality-scale/devices/) | Implemented | One logical Home Assistant device per configured mosque |
| [`diagnostics`](https://contributors.home-assistant.io/core/quality-scale/diagnostics/) | Implemented | Allowlisted, redacted per-entry diagnostic snapshot |
| [`discovery`](https://contributors.home-assistant.io/core/quality-scale/discovery/) | N/A (reviewed) | Mosques and their publications have no network discovery mechanism |
| [`discovery-update-info`](https://contributors.home-assistant.io/core/quality-scale/discovery-update-info/) | N/A (reviewed) | No discoverable device address to update |
| [`docs-data-update`](https://contributors.home-assistant.io/core/quality-scale/docs-data-update/) | Implemented | Source checking and user-approved update workflow documented |
| [`docs-examples`](https://contributors.home-assistant.io/core/quality-scale/docs-examples/) | Implemented | Automation and media blueprints supplied |
| [`docs-known-limitations`](https://contributors.home-assistant.io/core/quality-scale/docs-known-limitations/) | Implemented | PDF layout, date, HA compatibility and source limitations documented |
| [`docs-supported-devices`](https://contributors.home-assistant.io/core/quality-scale/docs-supported-devices/) | N/A (reviewed) | Official exception for integrations without physical devices; [supported publication layouts](import_review.md#supported-pdf-layouts) are documented separately |
| [`docs-supported-functions`](https://contributors.home-assistant.io/core/quality-scale/docs-supported-functions/) | Implemented | [Complete entity reference](automations.md#entities-per-mosque) cross-checked against all 27 sensors and read-only calendar, including attributes, availability and defaults |
| [`docs-troubleshooting`](https://contributors.home-assistant.io/core/quality-scale/docs-troubleshooting/) | Implemented | Getting-started and dashboard troubleshooting sections |
| [`docs-use-cases`](https://contributors.home-assistant.io/core/quality-scale/docs-use-cases/) | Implemented | README and automation examples cover dashboards and reminders |
| [`dynamic-devices`](https://contributors.home-assistant.io/core/quality-scale/dynamic-devices/) | N/A (reviewed) | Official fixed-device exception: exactly one static logical mosque device per config entry; additional mosques require separate entries |
| [`entity-category`](https://contributors.home-assistant.io/core/quality-scale/entity-category/) | Implemented | Source and coverage status sensors are diagnostic |
| [`entity-device-class`](https://contributors.home-assistant.io/core/quality-scale/entity-device-class/) | Implemented | Prayer events are timestamp sensors; status sensors use enum device class |
| [`entity-disabled-by-default`](https://contributors.home-assistant.io/core/quality-scale/entity-disabled-by-default/) | Implemented | Standalone Previous Jamaat is opt-in for new registrations because the card already gets it from Prayer timetable and bundled blueprints do not use it. Other sensors/calendar provide primary timetable, reminder or health functions. Registry tests preserve existing user choices and prove enable/reload |
| [`entity-translations`](https://contributors.home-assistant.io/core/quality-scale/entity-translations/) | Implemented | Sensor names and prayer calendar use translations |
| [`exception-translations`](https://contributors.home-assistant.io/core/quality-scale/exception-translations/) | Implemented (targeted) | Calendar query and invalid-storage `HomeAssistantError` subclasses use `translation_domain`/`translation_key`; option forms already use translated error keys. Review any newly introduced HA exception paths |
| [`icon-translations`](https://contributors.home-assistant.io/core/quality-scale/icon-translations/) | Implemented | Calendar icon now declared via icons.json; device class supplies standard sensor icons |
| [`reconfiguration-flow`](https://contributors.home-assistant.io/core/quality-scale/reconfiguration-flow/) | Implemented | Name and timezone editable without changing mosque identity or storage |
| [`repair-issues`](https://contributors.home-assistant.io/core/quality-scale/repair-issues/) | Implemented | Corrupt or invalid timetable storage raises a persistent Repairs issue |
| [`stale-devices`](https://contributors.home-assistant.io/core/quality-scale/stale-devices/) | N/A (reviewed) | Official fixed-device exception: one logical mosque device belongs to each entry and is removed with it; two-mosque removal regression protects the remaining device, entities and storage |

### Platinum

| Rule | Assessment | Evidence / action |
| --- | --- | --- |
| [`async-dependency`](https://contributors.home-assistant.io/core/quality-scale/async-dependency/) | N/A (reviewed) | Dependency-without-I/O exception: pypdf reads already-downloaded in-memory `BytesIO`, with no dependency network/file access. PDF CPU/process work is isolated off the event loop; executor isolation alone would not establish an exception |
| [`inject-websession`](https://contributors.home-assistant.io/core/quality-scale/inject-websession/) | Gap | HTTP downloads mean the no-HTTP exception does not apply. A dedicated connector enforces public-only DNS resolution on every connection/redirect. The pinned HA session helper supplies its own connector; redesign needs proof that this SSRF boundary survives before adopting it |
| [`strict-typing`](https://contributors.home-assistant.io/core/quality-scale/strict-typing/) | Gap | Python integration is not yet checked with strict mypy |

### Exemption review and remaining work

Each absence-based exception was checked independently: `action-setup`, `docs-actions` and `action-exceptions` have no integration-owned actions; `docs-conditions` has no condition platform; `docs-triggers` has no trigger platform; `reauthentication-flow` collects no authentication credentials. Generic HA calendar/state/time triggers and optional blueprints do not create integration-owned platforms. `discovery` and `discovery-update-info` have no discoverable protocol or endpoint. The physical-device, fixed-device and dependency-without-I/O exceptions are explained in their individual rows above.

`brands` and `common-modules` have no blanket custom-integration exception. Local branding uses the supported custom route; the coordinator follows the standard layout. `log-when-unavailable` does not qualify for the no-entities exception, and `inject-websession` does not qualify for the no-HTTP exception. Their implementation/gap must be assessed directly.

1. **Validate release candidates:** re-run Ruff, Python/branch coverage, frontend, HACS/hassfest, both supported HA compatibility versions, live acceptance and CodeQL for the release candidate; a previous green run does not validate later commits.
2. **Preserve rule evidence:** retain the per-module guard, check error-to-success recovery when extending any flow, and review new public fields, entities and exception paths against this audit.
3. **Platinum gaps:** strict mypy and HA-managed websession adoption remain incomplete. Preserve the downloader's DNS/redirect validation during any session redesign. These are gaps, not exemptions.
4. **Tier review:** retain the custom-integration scope and obtain a maintainer review of all applicable rules and each exception before making any tier claim; no `quality_scale` value is added to the manifest.
