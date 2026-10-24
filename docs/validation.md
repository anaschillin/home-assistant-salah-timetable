# Validation record

## Current recorded status — 24 October 2026

The current candidate is **0.6.2**. Its local verification passed **758 Python
tests** (95% aggregate integration coverage), **81 Node tests**, native Chromium
at 320/360/400/900px, and **20 live HA 2026.10.0 checks**. The expanded blueprint
reload check also passed in an eight-case focused rerun. The live run verified
pypdf absent before setup and manifest-pinned 6.21.1 installed/imported afterward,
with no package preloading. A trusted combined CA bundle was mounted read-only for
the session proxy, with TLS verification enabled. Actual card/editor, each display
toggle and saved configuration after reload passed. See the
[0.6.2 evidence](#repository-review-and-milestone-7--candidate-062).

The latest recorded hosted **Validate** result is
[40138323440](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40138323440)
for pushed **0.6.2 commit `b7b0c74`**. It completed successfully, including the real
minimum/current HA matrix with strict dependency proof. The reusable live matrix
also runs weekly. Later release commits still need their own required checks.

**Physical-device checks are complete by user confirmation on 24 October 2026.**
The user reported updating their installation to the latest available version.
Specific hardware, browsers and HA/integration version numbers were not supplied;
this records their completed checks without assigning them to the previously
unpublished local 0.6.2 tree.

HACS installation, restart and updates are user-confirmed complete through the
custom-repository route. Removal/re-addition in a test instance, full HA backup
restoration, asset provenance and reviewed release publication remain pending.
HACS CI is repository validation; the installation confirmation is separate evidence.
See the [current acceptance checklist](remaining-work.md). Dated sections below
retain the results and limitations observed at that time; this summary supersedes
their older pending statuses.

The obsolete `codex/live-smoke-runner` and merged Dependabot setup-python branches
were deleted after their review and the successful v7 upgrade. Historical entries
below retain the test counts, versions and environment limitations observed at the
time; they are not current acceptance status.

## Initial validation — 23 October 2026

Source tested: `9c613caae88fe66e86a09f44ee86f8749241afdb` (integration 0.5.1).
This records observed results, not certification of every supported installation.

### Automated checks

- `uv run --frozen pytest`: **551 passed**, 94% aggregate integration line coverage.
  PDF worker behavior is tested through its subprocess; the isolated worker does
  not inherit coverage instrumentation.
- `npm test`: **31 passed**.
- `REQUIRE_BROWSER_TESTS=1 npm run test:browser`: passed native Chromium checks
  at 360px and 900px, with 20 assertions per viewport. These fixtures use stand-in
  Home Assistant controls, separately from the live runtime check below.
- Ruff lint and formatting checks passed.
- The official hassfest container reported one integration and zero invalid
  integrations, including manifest, dependencies and translations.
- Release consistency checks and archive construction passed. Packaging tests
  verify required assets, private-file exclusion, version consistency, checksums
  and reproducibility across source timestamps/permissions.

### Disposable Home Assistant runtime

The official `ghcr.io/home-assistant/home-assistant:2026.10.2` image ran with a
fresh temporary configuration and loopback-only HTTP access. The integration was
mounted as a manual installation; this was not a HACS installation.

Observed through real authenticated Home Assistant APIs:

- Initial onboarding and mosque Config Flow completed.
- A synthetic CSV for the current date and tomorrow passed authenticated upload,
  graphical-mapping flow, persisted preview and explicit approval.
- All 25 mosque sensors were registered with actual Home Assistant states.
- The bundled card resource was registered automatically.
- Reload retained approved values and avoided duplicate resource registration.
- A dashboard configuration containing the bundled card was saved successfully.
- Confirmed-date Ramadan settings persisted across restart. Iftar used the published
  Maghrib beginning when no separate Iftar existed; Taraweeh remained text without
  an invented timestamp.
- A staged replacement survived restart alongside the approved source. Rejecting
  it retained approved values. Removing a second mosque preserved the first
  mosque's entity IDs and states.
- Upgrading from the initial 0.5.0 runtime to 0.5.1 preserved approved/pending data
  and changed the existing card resource to the new version without duplicates.
- The supplied Nuneaton Muslim Society 2026 PDF passed authenticated upload,
  isolated extraction, layout mapping and review of all 365 dates. Rejection kept
  approved data intact. The original PDF was not copied into the repository.

Chromium also opened the actual HA frontend at phone/tablet viewport sizes. The
bundled card loaded from its automatically registered resource. Its editor used
real HA selectors and the native title input; programmatic mode/title changes,
`config-changed` round trips, focus preservation and picker registration passed.
This exercises real components but does not replace manual exploration of every
picker/editor interaction or physical mobile/tablet devices.

This live check found a final-date Ramadan display bug, fixed in 0.5.1: today’s
published Sehri/Iftar values now remain visible after their events when no future
confirmed event exists. The browser showed Sehri **05:55 / Passed** while the next
Sehri timestamp remained unavailable. Regression tests cover both a final confirmed
date and a following active date. See the [screenshots](dashboard.md#preview).

The container's package installer could not validate this environment's outbound
proxy certificate. The exact locked `pypdf==6.21.1` package and its metadata were
supplied from the existing local development environment into the disposable
container’s normal global site-packages directory. TLS verification and integration dependency requirements were kept enabled. This
validates runtime behavior with that dependency present, not fresh dependency
installation through the affected proxy.

### Remaining acceptance at that time

The [release checklist](releasing.md) still requires the HACS custom-repository
installation route, upgrades from a previous release, minimum-version checks and
real mobile/tablet devices. The NMS website's live HTTPS availability is unverified;
manual PDF compatibility is established by the inspected layout, fixture tests
and this live import check.
Hosted GitHub Actions results were not readable from this environment and must be
reviewed on GitHub before publishing a tested release. No release/tag was published.


## Follow-up hardening after repository updates

The maintainer's changes through `5966ab0` were pulled and preserved. Formatting
was reconciled in `d876793` with parenthesized exception handlers retained.
Upgrade/recovery and diagnostic hardening are recorded in `806776c`.

The combined Python suite passed **569 tests**, with 94% aggregate integration
coverage. New cases include literal historical schema-1/schema-2 fixtures, pending
approval after migration, exact preservation/retry after failed migration writes,
future-schema rejection and complete timetable-store restoration with stable entity
IDs and Repair cleanup. This does not substitute for a full HA backup-archive restore.
Diagnostics now distinguish unloaded entries from retained runtime objects and expose
only allowlisted coverage/event flags.

Local release-note preparation passed its seven tests and generated a ZIP, checksum
and version-specific notes. The manual draft-release workflow was parsed and reviewed
but was not triggered; GitHub API access remains blocked in this environment.


A new Chromium check reproduced phone-width overflow at 200% root text size. The
prayer table now stays in a labelled, keyboard-focusable scroll region; the enlarged
layout passes at both 360px and 900px. The native fixture now has 21 checks per
viewport. Asset cache versions are advanced in candidate 0.5.2.

A separate minimum-version runner started HA 2026.10.0 and completed configuration,
CSV approval, Ramadan and independent-mosque checks. Its first restart failed because
Docker reassigned an automatic host port; an explicit stable port corrected that
runner issue. A subsequent attempt still did not confirm expected Fajr after restart.
At this point, full minimum-version acceptance remained unverified. The draft runner
was preserved separately for startup/state investigation and was not yet included in
main-branch validation tooling. The later runner and restart results are recorded
below. Task containers and private configurations were removed.


Final candidate 0.5.2 checks after merging the maintainer updates: **569 Python
tests**, **31 Node frontend tests**, both native Chromium viewport fixtures
(including the enlarged-text regression), Ruff lint/format, release asset/note
preparation and official hassfest all passed. No GitHub release/tag was published.


## Contributed Ramadan publications — candidate 0.5.3

Pulled maintainer fixtures through `daa6a1a`. The original binary files are unchanged;
attribution and SHA-256 hashes are recorded in the [fixture README](../tests/fixtures/pdf/README.md).

- NMS `nms ramadhan.pdf` is May–June **2022**, not a complete Ramadan-only file.
  The strict monthly adapter produces 61 exact dates and 854 event values.
- Zakariyya `zak.pdf` is the 2026 annual calendar plus a final Ramadan page. The new
  adapter imports only that page: February 18–March 20, 31 dates and 341 published
  values. Its final post-Ramadan Hijri-1 row does not activate Ramadan.
- Every date and event value matched separately constructed Poppler spatial-text
  CSV oracles, independently of production pypdf extraction and layout helpers.
- Actual isolated extraction and native HA authenticated upload/map/review/approve
  flows passed for both real PDFs. Source binary/checksum and parsed provenance
  round-trip through persistence and config-entry reload without activation.
- Explicit confirmation in the example February 18–March 19 window enables
  Zakariyya's permitted default Iftar and text-only Taraweeh; March 20 stays inactive.
  This test window is not a declaration of observed Ramadan dates.
- Confirmed-window edge gaps, annual field retention, unavailable fields, default
  Iftar, manual/off modes, date adjustment, source exclusion, advisory source/effective
  chronology and legacy-source conflicts have regression coverage. Approval checks
  current options and retains both approved data and pending proposals on conflict;
  a conflicting proposal can still be rejected normally.
- The PDF input bound is 4 MiB. Tests exercise acceptance at the exact boundary and
  rejection above it by the isolated worker, plus upload/download limits. Page,
  stream, text, decompression, CPU/memory and timeout protections are unchanged.

The full Python suite passed **670 tests** (95% aggregate integration coverage;
the isolated worker remains outside coverage instrumentation). After the metadata
update, **23** frontend/packaging/release-preparation cases passed. Ruff lint/format,
**31** Node tests, Chromium smoke at 360/900 pixels and official hassfest all passed.
The reproducible 0.5.3 integration ZIP builds successfully and excludes PDF fixtures.
No hosted Actions result, HACS installation, release or tag is claimed by these checks.

The complete NMS Ramadan publication, full Zakariyya annual parsing and native
cross-Gregorian-year PDF imports remain outside this change. See
[Ramadan validation](ramadan_validation.md) and [remaining work](remaining-work.md).


## Zakariyya annual tables and README badges — candidate 0.5.4

The same maintainer-supplied `zak.pdf` now has a separate annual adapter:
`zak_annual_v1`. It imports twelve complete monthly tables and excludes the
separate Ramadan appendix. All **365 Gregorian dates and 3,770 published event
values** match a separately constructed Poppler spatial-text CSV oracle; no
production pypdf extraction or adapter helpers generated that oracle.

Sehri is published on 120 dates, February–May; the other 245 dates retain no Sehri
value. No Maghrib Jamaat, Jumu'ah, Iftar, Istewa or Taraweeh value is invented.
November's pre-noon Dhuhr values remain 11:xx AM. All published timestamps validate
in `Europe/London`, including both DST changes.

The visually clipped first May date, “May …”, is interpreted as 2026-05-01 only
with its printed May 2026 heading, Friday weekday, complete 31-row month and exact
subsequent dates 2–31. The original token and explicit interpretation note persist,
and the review screen calls this out before approval. May's printed Hijri 1446
caption remains unchanged in the binary publication; it never changes Gregorian
dates or confirms Ramadan activation.

Native HA tests cover authenticated PDF upload, suggested mappings, review,
approval/reload, original provenance, Friday column meanings and absent fields.
They also cover URL profile persistence, separate Ramadan source confirmation,
permitted effective Iftar fallback, text-only Taraweeh and post-Ramadan annual
fallback without mutating sources. Exact UTC sensor states on March 29 and October
25 pass; after Isha on March 28, next Salah uses March 29's actual printed Fajr
across the clock change. Incorrect column reassignment remains unstaged and allows
a corrected retry.

**724 Python tests passed**, with 95% aggregate integration coverage. Ruff
lint/format, **31 Node tests**, real Chromium smoke at 360/900 pixels, official
hassfest and reproducible 0.5.4 release-asset/note preparation passed. PDF fixtures
remain outside integration release archives.

README badges now show dynamic Validate status for main, HACS **Custom** repository
support and the code's MIT license. The GitHub badge endpoint was fetched and
reported passing for main before these commits. This coarse status is not proof of
validation for the new release commit: GitHub API access still returns Forbidden,
so exact hosted results and the remaining release acceptance checks remain pending.
A release badge is deferred until an actual tagged release is published.


## Maintainer updates and browser-startup hardening — candidate 0.5.5

Pulled the maintainer's Chrome diagnostic step, NMS monthly confirmation test and
Jumu'ah/Dhuhr display fix through `a1773eb`; those changes are retained. The reported
hosted failure timed out waiting six seconds for `DevToolsActivePort`. Its D-Bus
stderr alone does not establish why Chrome failed to expose that file.

The smoke harness now prefers native Chrome before Chromium wrappers, with the CI
job explicitly selecting `/usr/bin/google-chrome`. Local Chromium remains supported.
Startup has a bounded 15-second budget, accepts Chrome's loopback-only stderr
announcement when a confined profile file is invisible, and waits for a complete,
valid port line. Spawn failures, numeric exits and signal termination are reported
immediately. The whole test and browser process remain bounded and cleaned up;
mandatory CI browser checks are not skipped or retried until they pass.

Seven launcher regressions cover delayed/partial writes, private-profile discovery,
invalid ports/non-loopback endpoints, exits, signals, spawn errors and timeout
stderr. **40 Node tests** and real Chromium smoke at 360/900 pixels passed. The
selected local binary was `/usr/bin/chromium`. **26 focused Python tests** covering
the maintainer's NMS flow and frontend/packaging/release preparation also passed,
as did Ruff lint/format. The new hosted Actions run remains to be checked after push;
these local results do not establish its outcome.

## Release runner follow-up — 24 October 2026

The connected GitHub API confirmed that Validate run
[39998754702](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/39998754702)
completed successfully for `9642db372d439f44ec6783f1c7f4ad7561199438`.
This establishes hosted validation for that commit only; subsequent changes need
validation on their own exact release commit.

The experimental live runner from `codex/live-smoke-runner` is now available in
`scripts/`, with explicit HA RUNNING and config-entry readiness gates. Restart
results distinguish setup/migration failures from a missing or mismatched Fajr
state, recording only presence/availability/match flags. The real browser driver
uses the existing bounded debugger discovery helper. The runner remains opt-in;
no CI acceptance or minimum-version success is claimed.

`node --test --test-isolation=none tests/frontend/*.test.mjs` passed all **46 tests**,
including six readiness regressions. Script syntax, CLI help and whitespace checks
passed. Docker socket access was denied by the workspace sandbox. The Chromium
smoke attempt aborted inside Node's native `InternalCallbackScope::Close` assertion,
before producing a browser acceptance result. These environment limitations leave
live HA 2026.10.0 restart and real picker acceptance pending.

## Dashboard refresh — candidate 0.6.0

The card now highlights the prayer awaiting its final congregation, shows independent
upcoming Salah/Jamaat panels with elapsed-interval progress, and adds a calculated
Umm al-Qura date. Compact/expanded layouts, 12/24-hour times and independent
countdown/detail visibility are configured in the graphical editor. The Hijri
adjustment is display-only and never changes Ramadan activation or imported values.

Observed locally:

- **59 Node tests passed**, including date conversion/adjustment and calendar fallback,
  missing times, multiple congregations, exact highlighting boundaries, tomorrow's
  Fajr, elapsed progress across DST/year boundaries, all main-panel visibility
  combinations and new editor round trips. Source payloads remain unchanged.
- Ruff lint and formatting passed; JavaScript syntax and whitespace checks passed.
- `uv lock --offline --check` resolved the unchanged 169-package dependency graph.
  Project/manifest/resource versions and virtual-project lock metadata agree on 0.6.0.
- Release consistency validated 33 runtime files. Draft-note preparation produced
  the integration archive and SHA-256 sidecar without publishing a tag or release.

The Chromium fixture now covers the new date, highlighting, progress, 12-hour
formatting, single-panel layout and keyboard-focus preservation through ticks.
It could not run here: Node aborted in `InternalCallbackScope::Close`, and a direct
Chromium startup reported `setsockopt: Operation not permitted`. The focused Python
suite likewise stalled in HA fixture setup; a diagnostic traceback showed asyncio's
self-pipe send denied with `PermissionError: Operation not permitted`. Bounded
attempts were stopped; neither suite is reported as passing.

Existing screenshots remain labelled historical. New browser screenshots, real HA
editor acceptance, physical-device checks and hosted validation for the eventual
0.6.0 release commit remain required. The earlier hosted result applies only to
`9642db3`, not these local dashboard changes.


## Peer-review follow-up — candidate 0.6.1

Reviewed all six findings against `dd184154` and the local follow-up tree. These
results describe the local 0.6.1 follow-up tree based on that commit; they do not
establish hosted validation for a future release commit.

| Review finding | Disposition and evidence |
| --- | --- |
| A: missing-Jamaat highlight | Not reproduced in 0.6.0: the latest begun row already returned before future-row selection. Simplified that rule and added missing middle/final Jamaat, exact next-beginning, end-of-day and next-local-day regressions. No timetable values changed. |
| B: progress interval ambiguity | Retained the agreed beginning-to-beginning / Jamaat-to-Jamaat policy. Each bar now visibly explains its interval; multiple Friday congregations, overnight and DST cases pass. |
| C: full DOM rebuild on every tick | Routine ticks now update existing clock/progress nodes. Structural changes rebuild at event boundaries or data/config changes. Native Chromium verifies stable table nodes, retained text selection and keyboard focus. |
| D: narrow-table scrolling | Retained accessible scrolling and added visible swipe/keyboard guidance on narrow cards. Chromium passes 320/360/400/900px, 200% text and scrolling without card overflow. |
| E: polling masks errors | Polling fails immediately for auth/API errors, invalid JSON, assertions and cancellation; only expected transient startup failures retry. Regression tests cover both paths. |
| F: live editor feature coverage | The real HA editor exercised layout, both time formats, Hijri adjustment and every visibility control. Saved options survived page reload; rendered layout/times and unchanged prayer data/Ramadan activation were checked. |

### Automated and browser results

- **725 Python tests passed**, with 95% aggregate integration coverage. The isolated
  PDF worker remains outside coverage instrumentation. This full run preceded the
  metadata-only 0.6.1 version bump; **23 focused frontend/packaging/release tests**
  passed again afterward.
- **70 Node tests passed**. Ruff lint/format, JavaScript syntax, whitespace checks,
  offline lock consistency and 0.6.1 release-note/archive/checksum preparation passed.
- Native Chromium passed all four width fixtures, including themes, 200% root text,
  date/time rendering, progress, text selection, scrolling guidance and editor focus.
  Fresh synthetic screenshots are linked from [dashboard](dashboard.md#preview).
- These runs used socket-enabled execution. The earlier sandbox-denied results
  above remain historical; they no longer block these specific completed checks.

### Disposable minimum-version Home Assistant

The official HA **2026.10.0** image, ID
`sha256:e5ee66f11f90f86c50c1b7641e558b707ccc3d2bb354daf05c296e58382945e2`,
ran a fresh loopback-only manual installation of the local **0.6.1** candidate.
The runner passed **19 acceptance checks**, including onboarding, URL-independent
CSV upload/mapping/approval, 25 sensors, separate-mosque removal, automatic resource
registration, confirmed Ramadan, Iftar fallback and text-only Taraweeh.

After HA reached RUNNING, restart preserved the approved timetable, staged proposal,
Ramadan settings, entity IDs and single resource registration. Rejection retained
approved Fajr. The actual frontend passed picker/editor, keyboard focus/title,
light/dark themes and phone/tablet checks. Every display setting was changed through
its real editor control and checked after save/page reload. Prayer data and Ramadan
activation remained unchanged. Reports contained only sanitized flags; generated
private configuration and task containers were removed after execution.

The exact locked `pypdf==6.21.1` was explicitly preloaded into the container. This is
not certification of fresh dependency installation through the proxy, an
authenticated HACS installation, physical devices, a full HA backup restore, or
upgrade from a previously published release. Those acceptance items, asset provenance,
hosted checks for the final commit and reviewed release publication remain pending.
No tag or GitHub release was created by this follow-up.


## Repository review and Milestone 7 — candidate 0.6.2

Reviewed the 14 commits between `04af4d0` and baseline main `c9b42f3`, preserving
maintainer changes to rendering, coverage, blueprints, approval/restart tests and
CI. Hosted Validate run [40132027518](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40132027518)
passed for `c9b42f3`. Hosted live run
[40131759984](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40131759984)
passed both HA 2026.10.0 and 2026.10.3 on `80d9eb3`; its tree
`27aa4b9348bed4160550106c37919fe86f9c3bb3` exactly equals baseline main's tree.
This is source-tree evidence, not an exact-commit run for the subsequent local fixes.

### Confirmed fixes and completed acceptance

- Reject datetime rows while retaining date-subclass round-tripping. Previously a
  datetime serialized a full timestamp into a field the storage reader treats as
  an ISO calendar date.
- A legacy Ramadan conflict on a later date could fail coverage calculation and
  disable otherwise valid current sensors. Coverage now stops conservatively at
  the unresolved future date and exposes `unresolved_date`. Real HA tests preserve
  today's Fajr/tomorrow's Next Salah and clear the marker after source selection,
  without changing approved data or entity IDs. Live-window ambiguity still fails.
- Actual HA blueprint validation/substitution and the automation scheduler exercise
  Adhan media/targets/optional volume, changed approved times, successive Friday
  events, pre-midnight Sehri, unavailable times, independent mosques, reload/re-enable
  without catch-up, and health-alert startup/refresh suppression and recovery.
  No production blueprint bug was reproduced in these scenarios.
- Required Validate now reuses the real minimum/current live matrix rather than an
  HTTP-only empty-configuration check. Manual and weekly execution remain available.
  CI requires explicit fresh-dependency proof instead of assuming no-preload means
  the base image lacked the dependency.
- Asset/project/manifest/lock versions advance to 0.6.2 so the maintainer's newer
  rendering code is not served under the earlier 0.6.1 cache token.

### Local results

The full Python suite passed **758 tests**, with **95%** aggregate integration
coverage; **8 blueprint cases** passed again after extending the real reload check.
All **81 Node tests** passed. Required Chromium passed at **320/360/400/900px**,
including editor controls, both time formats, themes and 200% text. Ruff lint/format,
JavaScript syntax, whitespace, offline lock checks and 0.6.2 release-asset preparation
passed. Isolated worker coverage limitations remain unchanged.

The local tree based on `c9b42f3` ran against official HA **2026.10.0** image
`sha256:e5ee66f11f90f86c50c1b7641e558b707ccc3d2bb354daf05c296e58382945e2`
and passed **20 live acceptance checks**. The baseline reported no pypdf metadata
or import. After HA loaded the mosque, both the installed distribution and imported
module reported manifest-pinned **6.21.1**, with
`dependency.fresh_install_verified: true` and `dependency_preloaded: false`.
A session combined CA bundle was mounted read-only for HA's installer; TLS checking
remained enabled, and no package files were supplied.

The runtime created 26 sensors, approved a synthetic CSV, preserved approved/pending
and Ramadan data through restart, kept entity IDs/resource registration stable,
and passed actual picker/editor and per-toggle preview/reload checks. Generated
containers and private configuration were cleaned up. This is a manual installation,
not an authenticated HACS installation or physical-device certification.

The final candidate still needs hosted validation on its own commit, including the
new required live matrix. HACS installation, full HA backup-archive restoration,
physical devices, asset provenance and reviewed release publication remain pending.
No release or tag was created by this review.


## User-confirmed physical-device acceptance — 24 October 2026

After the local 0.6.2 review, the user confirmed: “Physical device checks done,
updated to latest.” Physical-device acceptance is recorded as complete for their
updated installation. Device/browser models, HA/integration version numbers and
individual scenario results were not specified. This confirmation does not by
itself establish the HACS installation route, full backup restoration, a published
0.6.2 release or hosted CI success for a new commit.


## User-confirmed HACS installation and updates — 24 October 2026

The user confirmed installing and updating through Home Assistant's HACS custom
repository route, including the documented restart. HACS installation/restart/update
checks are recorded as complete for their installation. This does not establish
removal/re-addition in a test instance or full HA backup restoration; those remain
separate acceptance work.
