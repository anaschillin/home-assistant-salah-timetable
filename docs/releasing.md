# Building and accepting a release

The packaging checks below are automated. A successful build does not certify a
live Home Assistant/HACS installation or publish a GitHub release. The remaining
manual checks are release acceptance work; record their results for each release.
The [validation record](validation.md) includes earlier disposable HA 2026.10.2 and
minimum-version 2026.10.0 manual-install/frontend checks, with explicit limits and a
dependency preload used by those earlier runs. The later local 0.6.2 run verified
fresh dependency installation using a trusted CA bundle for the proxy, without
preloading packages. The [physical-device confirmation from 24 October 2026](validation.md#user-confirmed-physical-device-acceptance--24-october-2026)
predates 0.7.0 and does not identify an installed version. Acceptance of the newer
calendar, recognized PDF layouts, speaker controls, import review, Hijri-first
header and Arabic/RTL controls remains separate. Hosted validation is recorded separately for exact commit
SHAs; a final release commit still needs its own successful required jobs.

## Current release readiness

**Status reviewed 26 October 2026.** This is the **only active release
acceptance checklist**. The [archived review plan](archive/review-action-plan-2026-10-25.md)
preserves the original REV-01–06 implementation history. REV-07's isolated
minimum/current unit and live-HA testing is implemented and has passed
hosted validation; REV-08's import change comparison is implemented in
Milestone 17. Milestone 10A's card/editor language and RTL features are
implemented in candidate **0.9.1**, with applicable manual release acceptance
still outstanding. Milestone 10B's integration translations and reviewed
Arabic wording belong in the [development backlog](remaining-work.md) unless
they uncover a blocker. The automated checks do not replace the manual or
asset-rights gates below.

| Gate | Recorded evidence | Decision / remaining action |
| --- | --- | --- |
| REV-01–03 code fixes | Squash-merged [#7](https://github.com/anaschillin/home-assistant-salah-timetable/pull/7), [#6](https://github.com/anaschillin/home-assistant-salah-timetable/pull/6) and [#8](https://github.com/anaschillin/home-assistant-salah-timetable/pull/8) | **Complete** — calendar interval, timer teardown and remote-source approval statuses |
| REV-04 asset redistribution | [PR #9](https://github.com/anaschillin/home-assistant-salah-timetable/pull/9) merged; [asset inventory](asset-provenance.json) and [rights review](asset-provenance.md) available | **Blocking:** obtain documented rights for contributed PDFs/derived oracles, icon and screenshots, or replace with rights-cleared originals and assess public Git history; `python scripts/check_asset_provenance.py --require-cleared` must pass |
| REV-06 HACS removal/re-addition | [PR #10](https://github.com/anaschillin/home-assistant-salah-timetable/pull/10) merged; real HA Container two-mosque isolation and config-entry removal/re-addition passed. **On 25 October the user also confirmed removal and reinstallation worked** in their installation; [evidence and limits](hacs-removal-acceptance.md#reported-hacs-removereinstall-outcome--25-october-2026). | **Partially user-confirmed, full gate pending:** capture whether the UI route was HACS and the environment/version, then verify two-mosque isolation, deleted-entry cleanup, single frontend resource/device identity and restart in the documented disposable acceptance sequence. Do not equate a successful reinstall alone with full REV-06 sign-off. |
| REV-05 full HAOS restore | [PR #11](https://github.com/anaschillin/home-assistant-salah-timetable/pull/11) merged; real **Home Assistant Container** backup archive creation and isolated restore passed on Core 2026.10.0 and 2026.10.3 | **Deferred / lower priority for the next work cycle; not yet verified:** restore an actual *full HAOS/Supervisor* backup into a **second disposable HAOS instance**, verify entry/entity IDs, approved versus pending source data, Ramadan options, dashboard resources, Repairs and a second restart; record redacted evidence using the [restore procedure](backup-restore-acceptance.md) |
| Required hosted validation | [26 October 2026 main Validate 40337238065](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40337238065) passed **12/12** jobs on `b6dbe14bb75b791fbb1171e981494d2a21dbe07e`: locked Python tests, five exhaustive minimum-HA 2026.10.0 groups, full current-HA 2026.10.3 unit suite, frontend/Chromium, hassfest, HACS and both live Container lanes. [CodeQL 40337238192](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40337238192) also passed. Calendar timing [#13](https://github.com/anaschillin/home-assistant-salah-timetable/issues/13) and minimum-HA cancellation [#24](https://github.com/anaschillin/home-assistant-salah-timetable/issues/24) are **closed**; consult [compatibility notes](compatibility.md) for the unsharded-hang limitation. | **Automated code validation complete at this SHA, not a tagged release:** the *eventual release-tagged commit* must independently pass its exact `main` validation, and the outstanding REV-04–06 and manual acceptance gates below must still be signed off. |
| Manual release acceptance | See [the UI/runtime checks below](#manual-home-assistant-and-hacs-acceptance) and [validation log](validation.md) | **Still requires recorded results** for every applicable real-world/UI scenario; a passing automated workflow is not a substitute |
| Version, packaging and publication | Build/release scripts and draft workflow exist | **Pending:** match manifest/project/card/cache versions, changelog and notes; review existing tag, successful CI and prepared draft before publishing |

The [validation log](validation.md) is the evidence record, **not** a second
checklist. The `--require-cleared` provenance audit deliberately blocks draft
release preparation while rights remain unresolved; this is not a licence grant
and must not be bypassed just because a release ZIP excludes the PDF fixtures.
No GitHub release has been published for candidate 0.9.0 or its 0.8.1/0.8.0/0.7.0 predecessors; successful
PR and main CI runs are implementation evidence, not publication or manual
release acceptance.

### Next priorities and final sign-off

**Order of work, as agreed 26 October 2026:** focus first on clearing asset
redistribution rights, recording HACS/two-mosque acceptance and performing the
remaining focused manual UI/runtime checks. Full HAOS/Supervisor backup-and-restore
validation is **lower priority**, given the integration's straightforward
configuration and successful separate Home Assistant Container restore coverage.
It has **not** been completed or implicitly waived: it remains a separate
formal release acceptance item unless the maintainer records an explicit
scope decision. Do not test it against the live household HAOS installation.

- [ ] All published-repository assets have reviewable redistribution evidence;
      the strict provenance audit passes for the release tag.
- [ ] Authenticated HACS UI remove/re-add and two-mosque coexistence pass on a
      disposable instance; expected per-entry storage deletion is documented.
- [ ] Remaining applicable manual runtime/editor/mobile/import/upgrade checks
      below have recorded outcomes or explicit maintainer-reviewed release decisions.
- [ ] Lower priority: full HAOS/Supervisor archive restore, restart and
      Repairs/resource checks pass on a second disposable instance (not just
      a Container or storage-only restore), or the maintainer explicitly
      documents a release-scope decision acknowledging the missing evidence.
- [ ] **Exact** release commit passes all required CI, including minimum/current
      Home Assistant unit compatibility and current-version live acceptance, and its metadata, assets and changelog agree.
- [ ] Maintainer reviews the tag, checksum, release notes and draft before
      publishing; release is never published automatically.

## Build a distributable archive

Use the project's Python 3.14 environment. Keep these versions equal when changing
integration behavior or bundled assets:

- `custom_components/salah_timetable/manifest.json`: `version`.
- `pyproject.toml`: project version, then refresh `uv.lock` with `uv lock`.
- `custom_components/salah_timetable/frontend.py`: `CARD_VERSION`.
- `custom_components/salah_timetable/frontend/salah-timetable-card.js` and
  `frontend/card-utils.js`: all `card-utils.js?v=…` and `card-i18n.js?v=…`
  import cache versions.

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
- Separately locked minimum/current HA unit suites with verified runtime versions.
- Node frontend tests and the required Chromium smoke harness.
- Official hassfest and HACS integration validation.
- The release consistency check and archive build.
- The reusable supported-current HA live acceptance, including strict before/after
  dependency proof, actual configuration/import/restart and editor acceptance.

The isolated Chromium harness uses stand-in Home Assistant controls. Its result
cannot replace a check of real HA selectors, card discovery or resource loading.
Review the workflow results on GitHub, rather than assuming local checks establish
hosted validation. One calendar end-trigger timing test failed on the first attempt
of [run 40195818111](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40195818111)
before the unchanged commit passed on attempt 2. The later local
[diagnosis](validation.md#combined-080-review-and-calendar-synchronization)
reproduced background calendar refresh work completing after the test advanced
its clock; the test now drains that work before checking the exact end event.
[Issue #13](https://github.com/anaschillin/home-assistant-salah-timetable/issues/13)
was closed after reproducing the background-refresh race locally, passing
20/20 repeated normal/delayed regression cases, and confirming the unchanged
start/end assertions in subsequent successful hosted validation, including
[main Validate run 40327531675](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40327531675).
Reopen if the timing failure recurs. Preserve the artifact checksum with the
reviewed release notes.

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
  preview, approval and rejection. Verify the import form offers
  Annual / Monthly / Ramadan without a PDF-layout picker and recognizes known
  PDFs automatically. Verify January and February monthly approvals coexist
  without deleting earlier dates, overlapping month sources are rejected, and
  changed monthly URL spans fail safely for both PDF and CSV sources. Check the supported MOSQUE_A annual layout against
  its publication. Confirm an unsupported PDF fails with a useful message.
- Verify the inspected-edition picker is **absent**. Upload an identified PDF
  through the standard manual route and verify strict automatic recognition,
  the printed year, mapping, timezone handling and explicit approval. Reload a
  previously stored approved import whose saved metadata included a legacy
  `publication_profile_id`; its original data must remain valid and the
  obsolete profile field must not be re-emitted.
- Configure two distinct mosques and add **two separate Salah Timetable cards**
  in a storage-mode dashboard. The graphical editor must offer both mosque
  names with only their dashboard sensors; each card displays the selected
  mosque's data, and removal/re-addition must not reassign the other card.
- Browse every page of a [large import comparison](import_review.md), including
  added/removed dates, changed times, all Jumu’ah congregations and source-token
  changes. Navigation must keep approved values and the staged identity unchanged;
  rejection/cancellation must preserve approved data. Exercise approved-baseline
  drift in a controlled disposable test: the review must reset to the first page
  with refreshed values and require another approval decision before replacement.
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
- Add the [prayer calendar](calendar.md) to a real calendar card, query approved
  dates and exercise a calendar start trigger with an offset. Verify separate
  exact beginning/Jamaat start instants and their one-minute calendar presentation
  intervals (not prayer durations), every published Jumu’ah congregation,
  mosque-timezone instants, future approved dates and stable IDs after restart.
  Pending proposals and missing dates must not add events.
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
  Verify Hijri appears first with a named Islamic month, and independently hide
  or show Gregorian without changing either calendar's meaning. Check Arabic HA
  automatic selection, explicit English/Arabic overrides, bilingual prayer names,
  RTL table/clock direction, 12/24-hour formatting and focused editor title/selection
  through language changes. Record fluent-language review of the draft Arabic and
  actual mobile/tablet results separately from automated browser checks.
  On a published-source day, verify **Fajr ends at Sunrise** in the correct mosque
  timezone (unavailable if the source omits Sunrise). On an MOSQUE_A Friday, verify
  the separately published **second khutbah** displays **only** as a note and
  does not alter Dhuhr beginning or Jumu’ah Jamaat; compare an ordinary weekday
  and a timetable without a recognized footer. Verify emphasis through the final
  congregation and independent progress bars.
- Check narrow mobile and tablet displays, light/dark themes, text zoom, keyboard
  access, unavailable data and a disconnected browser. Confirm ticking countdowns
  do not cause per-second sensor writes.
- Import the updated [Adhan blueprint](automations.md#adhan-playback-controls)
  separately and test it on the actual selected speakers with user-owned recordings.
  Check Fajr audio, disabled prayers, per-prayer volume, quiet hours and unavailable
  players. Verify acknowledged playback can restore the prior volume, while manual
  volume/content changes and another playback operation prevent restoration.
  Remove one player during acknowledgement and verify healthy players continue;
  change a device's volume/content away and back under the same context and verify
  the automation preserves that intervention rather than restoring over it.
- Test [pause/resume media](automations.md#pause-and-resume-media) on those speakers.
  Only playing players may be paused; invalid anchors must skip the whole operation.
  Verify resumption requires unchanged paused content and this operation's reported
  service context. Record whether each device retains that context; devices that drop
  it require manual resumption. Check manual intervention, overlapping automations,
  disabling/reloading changed settings and restart without catch-up. Separate pause
  automations must not be treated as a combined or extended pause window.
- Exercise URL failure and changed-content staging. Confirm last approved times
  remain available and a changed file requires approval. Restore the test backup
  and verify recoverability before documenting a recovery procedure.
- Restore a full HAOS/Supervisor backup archive into a second disposable HAOS
  instance as specified in the release gate above. Verify
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

Only inspected editions of the Mosque A annual/monthly calendars,
Mosque B 2026 annual tables and Ramadan appendix, and the synthetic PDF layout are
supported; see [PDF layouts](pdf_layouts.md). There is no general PDF recognizer, OCR,
scanned/encrypted-PDF support or invented-time fallback. The MOSQUE_A website's live
HTTPS availability remains unverified; its supplied HTTP URL is unsupported.
Downloads require public HTTPS and do not support environment proxies. Ambiguous
or nonexistent local DST times are rejected instead of choosing a fold. Ramadan
activation requires explicit Gregorian confirmation or manual activation; printed
Hijri dates do not activate it.

Invalid structured stored timetable records now create a persistent HA Repairs
issue with backup/reload guidance while preserving the affected file. Automated
tests verify safe issue content, clearing after successful recovery and clearing
on removal. Broader migration and backup/recovery acceptance remains necessary.

HACS installation, restart and updates are user-confirmed separately from the
disposable HA smoke. Automated two-mosque config-entry removal/re-addition and real
Home Assistant Container archive restoration also passed on the recorded remote
commits. HACS UI uninstall/reinstallation, full HAOS restoration and complete
release UI acceptance remain separate gates above.
The dated [physical-device confirmation](validation.md#user-confirmed-physical-device-acceptance--24-october-2026)
predates 0.7.0 and records no installed version; it does not complete the new-feature
and speaker checks above. Further PDF layouts, broad migration/HAOS recovery review,
reviewed release publication and HACS default catalogue submission remain follow-up
work. This packaging increment does not complete Milestone 6.

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
uv run --frozen python -m scripts.prepare_release --tag v0.9.0 --output-dir /tmp/salah-release-review
```

Use the manifest's current version in the tag argument. Local preparation validates
metadata and notes; the GitHub workflow additionally verifies tag existence,
ancestry and hosted validation. No execution of the draft-release workflow is
recorded. GitHub API access and successful Validate runs are now available; creating
or reviewing the release tag and running the draft workflow remain release work.
