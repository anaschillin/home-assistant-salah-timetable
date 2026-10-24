# Building and accepting a release

The packaging checks below are automated. A successful build does not certify a
live Home Assistant/HACS installation or publish a GitHub release. The remaining
manual checks are release acceptance work; record their results for each release.
The current [validation record](validation.md) includes a disposable HA 2026.10.2
manual installation and real frontend smoke, with explicit limits and a dependency
preload required by the test environment’s proxy certificate.

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

The isolated Chromium harness uses stand-in Home Assistant controls. Its result
cannot replace a check of real HA selectors, card discovery or resource loading.
Review the workflow results on GitHub, rather than assuming local checks establish
hosted validation. Preserve the artifact checksum with the reviewed release notes.

## Manual Home Assistant and HACS acceptance

Use a disposable supported Home Assistant installation, not a user's live mosque
configuration. Keep a backup of the test configuration and use synthetic fixtures
where possible. Record the HA/integration versions and browser/device used.

- Install through the documented HACS custom-repository route on the minimum
  supported HA version and a current stable HA version. Add two distinct mosques
  through the UI; check one device/config entry per mosque and stable entity IDs.
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
  Verify emphasis through the final congregation and independent progress bars.
- Check narrow mobile and tablet displays, light/dark themes, text zoom, keyboard
  access, unavailable data and a disconnected browser. Confirm ticking countdowns
  do not cause per-second sensor writes.
- Exercise URL failure and changed-content staging. Confirm last approved times
  remain available and a changed file requires approval. Restore the test backup
  and verify recoverability before documenting a recovery procedure.
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

HACS installation, complete manual UI acceptance and real-device visual checks
remain separate from the completed disposable HA smoke. Further PDF layouts, a
broader migration/recovery review, reviewed release publication and submission to
the HACS default catalogue remain follow-up work. This packaging increment does not complete Milestone 6.

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
uv run --frozen python -m scripts.prepare_release --tag v0.6.1 --output-dir /tmp/salah-release-review
```

Use the manifest's current version in the tag argument. Local preparation validates
metadata and notes; the GitHub workflow additionally verifies tag existence,
ancestry and hosted validation. It has not been triggered from this environment
because the required tag and readable GitHub API are unavailable.
