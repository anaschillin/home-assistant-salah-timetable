# Building and accepting a release

The packaging checks below are automated. A successful build does not certify a
live Home Assistant/HACS installation or publish a GitHub release. The remaining
manual checks are release acceptance work; record their results for each release.
The [validation record](validation.md) includes earlier disposable HA 2026.10.2 and
minimum-version 2026.10.0 manual-install/frontend checks, with explicit limits and a
dependency preload used by those earlier runs. The later local 0.6.2 run verified
fresh dependency installation using a trusted CA bundle for the proxy, without
preloading packages. Physical-device checks are user-confirmed complete for their
latest installation. Hosted validation is recorded separately for exact commit
SHAs; a final release commit still needs its own successful required jobs.

## Current release readiness — 25 October 2026

**This document is the single active checklist for release acceptance.** The
[archived 25 October review plan](archive/review-action-plan-2026-10-25.md)
records REV-01–06 implementation history; use this section for the outstanding
sign-offs. Feature follow-ups (REV-07 compatibility expansion and REV-08
localization/import-diff UX) belong in [remaining work](remaining-work.md), not
in the current release gate unless they uncover a blocking regression.

| Gate | Recorded evidence | Decision / remaining action |
| --- | --- | --- |
| REV-01–03 code fixes | Squash-merged [#7](https://github.com/anaschillin/home-assistant-salah-timetable/pull/7), [#6](https://github.com/anaschillin/home-assistant-salah-timetable/pull/6) and [#8](https://github.com/anaschillin/home-assistant-salah-timetable/pull/8) | **Complete** — calendar interval, timer teardown and remote-source approval statuses |
| REV-04 asset redistribution | [PR #9](https://github.com/anaschillin/home-assistant-salah-timetable/pull/9) merged; [asset inventory](asset-provenance.json) and [rights review](asset-provenance.md) available | **Blocking:** obtain documented rights for contributed PDFs/derived oracles, icon and screenshots, or replace with rights-cleared originals and assess public Git history; `python scripts/check_asset_provenance.py --require-cleared` must pass |
| REV-05 full HAOS restore | [PR #11](https://github.com/anaschillin/home-assistant-salah-timetable/pull/11) merged; real **Home Assistant Container** backup archive creation and isolated restore passed on Core 2026.10.0 and 2026.10.3 | **Blocking:** restore an actual *full HAOS/Supervisor* backup into a **second disposable HAOS instance**, verify entry/entity IDs, approved versus pending source data, Ramadan options, dashboard resources, Repairs and a second restart; record redacted evidence using the [restore procedure](backup-restore-acceptance.md) |
| REV-06 HACS removal/re-addition | [PR #10](https://github.com/anaschillin/home-assistant-salah-timetable/pull/10) merged; real HA Container two-mosque isolation, config-entry removal/re-addition and frontend resource checks passed | **Blocking:** run *HACS UI* uninstall/reinstallation on disposable HA with two mosques and verify card/resource/device cleanup and recovery; record evidence per the [HACS acceptance guide](hacs-removal-acceptance.md) |
| Required hosted validation | [Main Validate run 40208986292](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40208986292) passed **all six jobs**, including **880 Python tests**, on main commit `e48463d53417909809ff30c1708127d9917f1786` (Milestone 17). Earlier intermittent calendar end-trigger failure remains tracked in [issue #13](https://github.com/anaschillin/home-assistant-salah-timetable/issues/13) | **Passed for that commit only;** candidate dashboard changes in [PR #16](https://github.com/anaschillin/home-assistant-salah-timetable/pull/16) require their **own green exact-commit CI** and live/manual acceptance before release |
| Manual release acceptance | See [the UI/runtime checks below](#manual-home-assistant-and-hacs-acceptance) and [validation log](validation.md) | **Still requires recorded results** for every applicable real-world/UI scenario; a passing automated workflow is not a substitute |
| Version, packaging and publication | Build/release scripts and draft workflow exist | **Pending:** match manifest/project/card/cache versions, changelog and notes; review existing tag, successful CI and prepared draft before publishing |

The [validation log](validation.md) is the evidence record, **not** a second
checklist. The `--require-cleared` provenance audit deliberately blocks draft
release preparation while rights remain unresolved; this is not a licence grant
and must not be bypassed just because a release ZIP excludes the PDF fixtures.
No GitHub release was created by the REV-04–06 merges.

### Final sign-off for each candidate

- [ ] All published-repository assets have reviewable redistribution evidence;
      the strict provenance audit passes for the release tag.
- [ ] Full HAOS/Supervisor archive restore, restart and Repairs/resource checks
      pass on a second disposable instance (not just a Container or storage-only restore).
- [ ] Authenticated HACS UI remove/re-add and two-mosque coexistence pass on a
      disposable instance; expected per-entry storage deletion is documented.
- [ ] Remaining applicable manual runtime/editor/mobile/import/upgrade checks
      below have recorded outcomes or explicit maintainer-reviewed release decisions.
- [ ] **Exact** release commit passes all required CI, including minimum/current
      Home Assistant live acceptance, and its metadata, assets and changelog agree.
- [ ] Maintainer reviews the tag, checksum, release notes and draft before
      publishing; release is never published automatically.

## Build a distributable archive

Use the project's Python 3.14 environment. Keep these versions equal when changing
integration behavior or bundled assets:

- `custom_components/salah_timetable/manifest.json`: `version`.
- `pyproject.toml`: project version, then refresh `uv.lock` with `uv lock`.
- `custom_components/salah_timetable/frontend.py`: `CARD_VERSION`.
- `custom_components/salah_timetable/frontend/salah-timetable-card.js`: the
  `card-utils.js?v=…` import cache version.

Run the checks and build from the repository root:

```sh
uv run --frozen python scripts/build_release.py --check
uv run --frozen python scripts/build_release.py
```

The script writes `dist/salah_timetable-VERSION.zip` and a SHA-256 sidecar. Use
`--output-dir /tmp/salah-release` to choose another destination. It validates
versions and required assets before creating the output directory. It does not
import Home Assistant or require network access.

The archive contains `custom_components/salah_timetable/` and the MIT `LICENSE`.
Only Python/JSON source and the allowlisted frontend, translation and brand assets
are included. Tests, fixtures, caches, hidden directories, node modules and original
imported PDF/CSV files are excluded; source symlinks are rejected. Archive entries
have a fixed order, timestamp and file mode. Identical source produces identical
ZIP bytes in the same Python/zlib environment, regardless of checkout timestamps
or permissions. Automated tests verify content, cache-version consistency,
reproducibility and rejection of missing assets or symlinks.

For manual installation, unpack into a temporary directory, then copy its
`custom_components/salah_timetable` directory into Home Assistant's
`config/custom_components/` directory and restart Home Assistant. The repository's
normal HACS custom-repository installation remains unchanged; this ZIP is an
additional artifact for inspection/manual installation, not HACS ZIP-release mode.
Do not publish a tag, release or artifact as a tested release until acceptance is
complete.

## Automated release gate

Require the validation workflow to pass on the exact commit being released:

- Locked Python tests, Ruff lint and formatting.
- Node frontend tests and the required Chromium smoke harness.
- Official hassfest and HACS integration validation.
- The release consistency check and archive build.
- The reusable minimum/current HA live matrix, including strict before/after
  dependency proof, actual configuration/import/restart and editor acceptance.

The isolated Chromium harness uses stand-in Home Assistant controls. Its result
cannot replace a check of real HA selectors, card discovery or resource loading.
Review the workflow results on GitHub, rather than assuming local checks establish
hosted validation. One calendar end-trigger timing test failed on the first attempt
of [run 40195818111](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40195818111)
before the unchanged commit passed on attempt 2. Its root cause is unknown;
[issue #13](https://github.com/anaschillin/home-assistant-salah-timetable/issues/13)
tracks investigation. Review recurrence and release impact before sign-off; do not
claim a green rerun alone resolved the underlying cause. Preserve the artifact
checksum with the reviewed release notes.

## Manual Home Assistant and HACS acceptance

Use a disposable supported Home Assistant installation, not a user's live mosque
configuration. Keep a backup of the test configuration and use synthetic fixtures
where possible. Record the HA/integration versions and browser/device used.

- Install through the documented HACS custom-repository route on the minimum
  supported HA version and a current stable HA version. Add two distinct mosques
  through the UI; check one device/config entry per mosque and stable entity IDs.
- Start with a clean runtime and let HA install the manifest-pinned PDF dependency.
  Record the installed version and confirm it was not preloaded. A successful
  development `uv sync` or preloaded live run does not complete this check.
- Exercise URL-first import and manual PDF/CSV upload, graphical column mapping,
  preview, approval and rejection. Check the supported NMS annual layout against
  its publication. Confirm an unsupported PDF fails with a useful message.
- Restart with both approved and pending imports. Upgrade from the previous
  released version with a backup, then verify the same entities and approved
  values remain. Test removal/re-addition without affecting the other mosque.
- In the disposable test instance, exercise invalid structured timetable records.
  Check the persistent Home Assistant Repairs issue, useful recovery guidance and
  preservation of the affected file. Restore a known-working backup and reload;
  successful validation must clear the issue. Removing the failed mosque also
  clears its issue, but deletes its timetable data and is not a recovery step.
- Import next year's timetable before year end. Verify date selection at local
  midnight, year boundaries and relevant daylight-saving changes. Missing dates
  or fields must stay unavailable.
- Check the three Jamaat contexts before a beginning, between beginning/Jamaat,
  and at/after Jamaat. Verify independent next beginning/Jamaat and tomorrow's
  actual Fajr after Isha. A congregation is one scheduled event.
- Confirm Ramadan dates, shift the active window and try manual On/Off. Check
  exact-date overrides, preservation of published Iftar, the Maghrib-beginning
  fallback and the text-only Taraweeh default. Restart to verify settings persist.
- Add the bundled card through the real graphical picker/editor. Select each
  mosque, change modes/title and reopen the editor. Check automatic loading in
  storage-resource and YAML-resource dashboard modes without editing YAML.
- Check compact/expanded layouts, individual countdown/detail switches, both time
  formats and calculated Hijri adjustment without altering Ramadan activation.
  Enable and disable the **full Hijri date** during initial mosque setup and later
  under **Configure → Mosque settings**; verify the per-card toggle can also hide
  it, older entries default to visible, and preferences persist after restart.
  On a published-source day, verify **Fajr ends at Sunrise** in the correct mosque
  timezone (unavailable if the source omits Sunrise). On an NMS Friday, verify
  the separately published **second khutbah** displays **only** as a note and
  does not alter Dhuhr beginning or Jumu’ah Jamaat; compare an ordinary weekday
  and a timetable without a recognized footer. Verify emphasis through the final
  congregation and independent progress bars.
- Check narrow mobile and tablet displays, light/dark themes, text zoom, keyboard
  access, unavailable data and a disconnected browser. Confirm ticking countdowns
  do not cause per-second sensor writes.
- Exercise URL failure and changed-content staging. Review **all pages** of
  Milestone 17's date/field comparison, including removed dates, multiple
  Jumu’ah values and unchanged canonical values; return to review and explicitly
  approve/reject. Confirm last approved times remain available and a changed
  file requires approval. Restore the test backup
  and verify recoverability before documenting a recovery procedure.
- Restore a complete HA backup archive into a clean test configuration. Verify
  config entries, registries, entity IDs, approved/pending imports and Ramadan
  options. Restoring only the integration's timetable-store bytes is narrower
  coverage and does not complete full backup restoration.
- Download diagnostics and inspect logs for accidental mosque identity, URLs,
  HTTP validators or imported content. Review fixture, icon and other asset
  licensing before distribution.

Only mark an item complete after observing it. Add actionable failures to the next
focused change; do not replace a failed manual check with a statement that unit
tests pass.

## Current support limits

Only inspected editions of the Nuneaton Muslim Society annual/monthly calendars,
Zakariyya 2026 annual tables and Ramadan appendix, and the synthetic PDF layout are
supported; see [PDF layouts](pdf_layouts.md). There is no general PDF recognizer, OCR,
scanned/encrypted-PDF support or invented-time fallback. The NMS website's live
HTTPS availability remains unverified; its supplied HTTP URL is unsupported.
Downloads require public HTTPS and do not support environment proxies. Ambiguous
or nonexistent local DST times are rejected instead of choosing a fold. Ramadan
activation requires explicit Gregorian confirmation or manual activation; printed
Hijri dates do not activate it.

Invalid structured stored timetable records now create a persistent HA Repairs
issue with backup/reload guidance while preserving the affected file. Automated
tests verify safe issue content, clearing after successful recovery and clearing
on removal. Broader migration and backup/recovery acceptance remains necessary.

HACS installation, restart and updates were user-confirmed; automated
two-mosque config-entry removal/re-addition is also now validated in the disposable
Home Assistant Container matrix. This **does not** prove HACS frontend
uninstall/reinstallation, which remains a release gate above. Physical-device
checks were user-confirmed complete for the latest installation, as recorded in
the validation log. Further PDF layouts, broad migration/HAOS recovery review,
release publication and HACS default catalogue submission remain follow-up work.

## Prepare a reviewed draft

The **Prepare draft release** workflow is manually triggered with an existing
`vMAJOR.MINOR.PATCH` tag. Create/review that tag only after choosing the exact commit;
the workflow does not create or move tags. It requires the tagged commit to be on
main and to have a successful **Validate** push run on main, then checks that the
tag, manifest, project version, asset cache versions and changelog agree.

A read-only preparation job builds the ZIP, checksum and notes. A separate job with
release-write permission verifies the checksum and creates a **draft** with those
assets. Existing releases are preserved; rerunning for an existing release fails.
The workflow never publishes a release automatically. Complete the release checklist
and review the draft before publishing through GitHub.

For local asset review, without creating any GitHub tag or release:

```sh
uv run --frozen python -m scripts.prepare_release --tag v0.7.0 --output-dir /tmp/salah-release-review
```

Use the manifest's current version in the tag argument. Local preparation validates
metadata and notes; the GitHub workflow additionally verifies tag existence,
ancestry and hosted validation. No execution of the draft-release workflow is
recorded. GitHub API access and successful Validate runs are now available; creating
or reviewing the release tag and running the draft workflow remain release work.
