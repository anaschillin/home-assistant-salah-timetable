# Validation record

This is a **dated evidence log**, not the live feature backlog or the release
acceptance checklist. See [remaining work](remaining-work.md) for engineering
priorities and [release readiness](releasing.md#current-release-readiness) for
blocking manual sign-offs.

## 0.9.18 dashboard redesign — 28 October 2026 (merged)

The maintainer reviewed the revised liquid-glass timetable and photo
background in Home Assistant and explicitly approved merging
[PR #88](https://github.com/anaschillin/home-assistant-salah-timetable/pull/88).
The PR was **squash-merged** into `main` at
[`80b8017`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/80b80173bc45257cc46fd31e81dcbaff87ab97ed).
At its final head (`e8ab5dba`),
[Validate 40744012961](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40744012961)
and [CodeQL 40744012733](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40744012733)
passed. Validation included the frontend Chromium screenshot/layout checks,
Python tests, HACS, Hassfest, pinned Home Assistant compatibility and
disposable live Home Assistant acceptance.

The shipped 0.9.18 card combines mosque name, Gregorian/Hijri dates,
the inline Hijri-month description and both contextual countdowns in one
glass summary, with a separate equally styled timetable and footer
Yesterday/Today/Tomorrow navigation. It supports multi-mosque header
selection, responsive layouts, a full-viewport local photo, stable photo
framing across day changes, no photo-opacity control and accessibility
fallbacks. The maintainer's visual sign-off does **not** establish every
physical mobile/tablet, RTL, HACS uninstall or full HAOS/Supervisor
restore case; release gates are tracked in [releasing](releasing.md).

## PR #82 CSS module verification — 27 October 2026 (historical pre-merge)

The [CSS module PR #82](https://github.com/anaschillin/home-assistant-salah-timetable/pull/82)
passed [Validate 40594333792](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40594333792)
(**7/7 jobs**) and [CodeQL 40594333630](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40594333630).
The root and pinned HA 2026.10.0/2026.10.3 Python suites each passed
**957 tests**, with **95.37% line coverage**. Real Chromium checked sixteen
mobile/tablet/English/Arabic/bilingual combinations, and Home Assistant
Container live acceptance passed. The new module is included in runtime
asset and release-package tests. No screenshot golden comparison was made.
This was provisional CI evidence **at the time**; PR #82 was
subsequently merged and superseded by the 0.9.18 redesign. The original
branch-only steps are archived in [CSS acceptance](css-acceptance.md).

## 0.9.3 main-branch CI evidence — 27 October 2026

On main commit [`78c1a9f018f9676a56b1657865bcdef40a5f8175`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/78c1a9f018f9676a56b1657865bcdef40a5f8175),
[Validate 40578293746](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40578293746)
passed all **seven** jobs, and
[CodeQL 40578293664](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40578293664)
passed. The locked root suite and both separate Home Assistant
2026.10.0/2026.10.3 compatibility lanes each passed **904 Python tests**.
Root coverage measured **3,142 statements, 163 missed, 95% after rounding**
(actual line ratio approximately **94.81%**). The isolated
`pdf_worker.py` subprocess accounts for 47 uncovered statements in this
combined-process report; its worker behaviour is exercised through separate
black-box parser tests, not instrumented in the same coverage process.

Frontend/Chromium, hassfest, HACS and the HA 2026.10.3 live Container job
succeeded. This is exact-commit CI evidence, **not** confirmation of a
published release, full HAOS/Supervisor restore, redistribution rights or
complete manual/device/HACS UI acceptance. Branch coverage is not enabled;
line coverage must not be presented as branch coverage.

## Validation workflow simplification — 27 October 2026

PR #35 reduces the prospective Validate workflow from 12 jobs to **seven**:
locked Python tests, frontend/Chromium, HACS, hassfest, full-suite pinned HA
2026.10.0 compatibility, full-suite pinned HA 2026.10.3 compatibility,
and one real Container/live-frontend acceptance run on HA 2026.10.3.
The former shard selector and its dedicated tests have been removed.
All test modules still run in each pinned compatibility lane; the usual
per-test and process timeouts are unchanged.

This is a CI configuration change, not evidence of a release. The previous
12-job results below are retained as historical, exact-commit records.
The simplified workflow later passed on main at `78c1a9f`; see the
0.9.3 evidence above. The original note is retained as a historical record.

## 0.9.1 acceptance report — 26 October 2026

The maintainer reports successfully **removing and reinstalling Salah
Timetable completely** and subsequently creating/configuring a second
independent mosque instance in their Home Assistant installation. These
are user-reported observations, not independently captured test logs.
The second mosque was **not obvious as a separate dashboard card**.

The 0.9.1 change removes the inspected-publication-profile menu and
catalogue, and makes the existing card editor list each mosque's own
dashboard sensor by name. One custom card **type** is registered with
Home Assistant; add another instance of that card in the dashboard
and choose the second mosque to display its timetable. The integration
does not silently add cards to user dashboards. The bundled resource
cache version is updated. Tests cover independent instances, preserved
entity references and legacy profile metadata, and the disposable
HA live runner now saves a two-card dashboard.

This work does not itself certify a full HAOS/Supervisor restore,
public asset redistribution permission or all manual HACS acceptance
gates. Exact-commit PR and post-merge hosted validation are required;
see the associated 0.9.1 pull request and CI evidence.

## Latest merged CI evidence — 26 October 2026

On code commit `b6dbe14bb75b791fbb1171e981494d2a21dbe07e`,
[Validate 40337238065](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40337238065)
passed **12 of 12 jobs on the first attempt**, and
[CodeQL 40337238192](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40337238192)
passed. Validation covers the locked development Python suite, frontend/Chromium,
HACS, hassfest, all five exhaustive HA 2026.10.0 minimum-compatibility groups,
the unsharded 2026.10.3 supported-current suite, and both real Container live
smoke checks (including fresh dependency and backup/restore coverage).

[PR #23](https://github.com/anaschillin/home-assistant-salah-timetable/pull/23)
corrected the frozen-router test fixture and invalid-PDF lifecycle.
[PR #26](https://github.com/anaschillin/home-assistant-salah-timetable/pull/26)
simplified the compatibility test matrix; [PR #27](https://github.com/anaschillin/home-assistant-salah-timetable/pull/27)
removed redundant CI setup and improved disposable HA startup diagnostics.
[Calendar issue #13](https://github.com/anaschillin/home-assistant-salah-timetable/issues/13)
and [minimum-HA CI issue #24](https://github.com/anaschillin/home-assistant-salah-timetable/issues/24)
are **closed**, though the root cause of the *original unsharded*
minimum-HA hang was never conclusively identified. Five bounded minimum
groups are retained rather than claiming the old single-process run is reliable.

This evidence applies to the exact code commit above, not a future release
tag. No draft/published release or full HAOS/Supervisor restore was verified by
these CI runs, and manual HACS UI acceptance and redistribution rights remain
tracked in [releasing.md](releasing.md).

## 0.9.0 candidate validation — 26 October 2026

Candidate **0.9.0** combines the merged 0.8.1 Hijri-first/import changes with
Milestone **10A**: automatic or explicit English/Arabic card and editor labels,
bilingual prayer names and RTL layouts. Review removed the remaining PDF layout
selector and extended monthly date-window protection to CSV URL updates as well
as PDFs. Stored concrete parsers remain compatible with existing sources.

Local validation of the combined candidate passed **970 Python tests** (**95%**
coverage), **109 Node tests**, Ruff lint/formatting, the frozen lock consistency
check, release packaging and **16 native Chromium fixtures** (four widths × two
languages × both bilingual modes; 17 runner tests including their parent).
The fixtures include independent Gregorian/Hijri controls, mosque-level Hijri
authority, named Islamic months, 200% text, keyboard focus, RTL scrolling and
configuration round trips. The larger browser matrix now loads fixtures
sequentially to avoid starving debugger requests. Local evidence files are
`/tmp/salah-m10-final-python.log`, `/tmp/salah-m10-final-node.log` and
`/tmp/salah-m10-browser-final.log`; these ephemeral paths are not repository assets.

The base 0.8.1 main commit `10f63c8ed80f5419379a194f4fec494a37ef4e7a` passed
[Validate 40243730141](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40243730141).
That result does not validate the later 0.9.0 changes.

The clean 0.9.0 source commit `5942654` subsequently passed **29 live checks**
on official HA **2026.10.0**, including fresh `pypdf==6.21.1` installation,
real Container backup archive restore, two-mosque isolation, paged import review
and the actual HA graphical editor. The browser exercised English and Arabic,
both bilingual modes, four widths, 200% text, keyboard focus, theme changes,
saved configuration after reload and automatic HA language changes en → ar → en.
`/tmp/salah-live-0.9.0/results.json` records status `passed` and
`working_tree_dirty: false`. This is Container/browser acceptance, not a full
HAOS restore or physical-device sign-off. Exact final-commit hosted CI remains
required.
Arabic wording remains a draft awaiting fluent-language review; physical-device
acceptance and the external release gates remain open. No tag or release was
published.

### Hosted 0.9.0 and compatibility expansion

[Validate 40293428430](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40293428430)
passed all six jobs on main commit `27ede6e5a0bc7a0c1249076bb5c38833d6d92413`:
locked Python tests, frontend/Chromium, hassfest, HACS and live HA 2026.10.0 /
2026.10.3. This establishes hosted acceptance for the 0.9.0 feature checkpoint.

Milestone **11** now adds separately locked unit-test projects for minimum
HA **2026.10.0** / test plugin **0.13.371** and supported-current HA
**2026.10.3** / plugin **0.13.374**, leaving the development/release lock on
HA 2026.10.2. Both complete suites passed **978 tests** at **95%** coverage
with Python **3.14.8**, including the eight new environment-guard tests.
Distribution metadata, imported HA code, plugin, interpreter prefix and package
compatibility were checked before execution. Local logs are
`/tmp/salah-m11-minimum-final.log` and `/tmp/salah-m11-current-final.log`;
version evidence is in `/tmp/salah-m11-minimum-environment.json` and
`/tmp/salah-m11-current-environment.json`. Initial parallel runs collided in
HA's shared temporary upload directory; per-lane temporary directories removed
that interference, and the workflow/local guide now isolate these directories.

The new reusable unit workflow runs on Validate, weekly and manually, with version,
JUnit and coverage artifacts. Its first hosted submission on `116498e` was rejected
before job execution because `runner.temp` was used in job-level `env`. Path
configuration now occurs in a runtime setup step, and actionlint 1.7.7 validates
the workflow expressions. The corrected commit still requires hosted validation. HA 2026.10.3 is the reviewed support target; these checks do not claim
compatibility with every newer HA release. See [the compatibility guide](compatibility.md).
The historical-events branch was also reviewed and merged as **research-only**
documentation: twelve candidates, explicit date precision and future editorial
criteria. It adds no runtime feed, calendar events or dashboard panel.

## Recorded status — 25 October 2026

The current integration candidate is **0.8.1**, developed in
[PR #21](https://github.com/anaschillin/home-assistant-salah-timetable/pull/21).
It adds a Hijri-first dashboard with an independent Gregorian visibility switch,
strict automatic recognition of supported PDF editions, user-facing
Annual/Monthly/Ramadan choices and separate, nonoverlapping monthly date-span
sources. Historical 0.8.0 evidence below remains limited to that earlier tree.
The local branch at `0850ca6` passed **902 Python tests** (95% coverage), **81 Node
tests** and **25 disposable HA 2026.10.0 checks** before merging the later
`origin/main` work. The [0.8.0 record](#paged-import-review--candidate-080) below
describes that pre-merge evidence; those counts do not validate the combined tree.

The combined candidate based on `0850ca6` and `ffc56c6` now passes **936 Python
tests** (95% coverage), **83 Node tests**, required native Chromium, **29 live
HA 2026.10.0 checks** (including a real Container backup restore), and the
[calendar synchronization regression](#combined-080-review-and-calendar-synchronization)
below. Those local results preceded the merged-tree hosted result recorded next.

**Merged 0.8.0 evidence:** [Validate run
40229412033](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40229412033)
passed on main commit `f34682a34ab625dcec0008357308a1fd435df93f`:
**936 Python tests** plus all six jobs, including frontend/Chromium,
hassfest, HACS and live HA 2026.10.0 / 2026.10.3.

**0.8.1 feature branch evidence:** [PR #21 Validate run
40242996936](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40242996936)
passed on source `888e4cd46c7be82abd2a2e90512d61c98356117e` on
the first attempt: **955 Python tests**, frontend/Chromium, hassfest, HACS
and both live Home Assistant jobs. This covers the January/February source
isolation regression and strict PDF recognition tests. A subsequent
documentation-only commit and the eventual merge commit must each receive
their own exact-SHA CI validation. Hosted smoke acceptance does **not**
establish physical-dashboard, full HAOS/Supervisor restore, HACS UI
uninstallation or asset redistribution permission. Required Validate includes
the minimum/current HA live matrix with strict dependency proof and also runs
weekly.

REV-01–03 runtime fixes and REV-04–06 release-assurance tooling were merged through PRs
[#6](https://github.com/anaschillin/home-assistant-salah-timetable/pull/6),
[#7](https://github.com/anaschillin/home-assistant-salah-timetable/pull/7),
[#8](https://github.com/anaschillin/home-assistant-salah-timetable/pull/8),
[#9](https://github.com/anaschillin/home-assistant-salah-timetable/pull/9),
[#10](https://github.com/anaschillin/home-assistant-salah-timetable/pull/10)
and [#11](https://github.com/anaschillin/home-assistant-salah-timetable/pull/11).

The first combined [Validate run **40194784544**](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40194784544)
for **main commit `12f6ae52e249ed2a4ba6d80b17989b0c5e781753`** completed
successfully on 25 October 2026:

- **873 Python tests passed**, with Ruff lint and formatting checks.
- Frontend/Chromium tests, hassfest and HACS repository validation succeeded.
- Live Home Assistant tests succeeded on **2026.10.0** and **2026.10.3**.
- The live HA matrix exercised two independently approved synthetic mosque
  timetables, config-entry removal/re-addition and isolation, and creation
  and restoration of a **real Home Assistant Container backup archive** into
  a second disposable configuration using Home Assistant's restore module.
  The backup audit compared stored approved and pending imports, source
  metadata, config entries and registry/card identities without exporting
  contents. This was **not a full HAOS/Supervisor restoration**.

**User-reported HACS removal/reinstallation — 25 October 2026:**
The maintainer confirmed that removing and reinstalling the integration
**works correctly** in their installation. This records a successful
**manual removal/reinstall outcome**, rather than a simulated config-entry
removal or a HACS repository lint result. The exact HA/HACS/integration
versions, route used, disposable-instance status, two-mosque coexistence,
registry/resource cleanup and post-restart checks were not supplied.
Treat these subchecks as **not yet independently evidenced**; the
[REV-06 acceptance procedure](hacs-removal-acceptance.md) and
[release checklist](releasing.md) remain authoritative. Do not invent
screenshots, test durations or version information.

**Outstanding release sign-offs:** Public redistribution permission for the
contributed PDF fixtures/derived oracles, brand icon and screenshots
(REV-04); full HAOS backup-archive restore, restart, Repairs and resource
checks in another disposable HAOS (REV-05); and full HACS **UI**
uninstall/reinstallation with coexistence and cleanup evidence beyond the
user-confirmed removal/reinstall result above (REV-06).
A passed HACS *repository check* or a Container config-entry lifecycle test
is not evidence of HACS UI reinstallation. All three remain **open**, with
the current decision criteria in the
[single release checklist](releasing.md#current-release-readiness)
and executable evidence procedures in
[asset provenance](asset-provenance.md),
[backup restore](backup-restore-acceptance.md) and
[HACS lifecycle acceptance](hacs-removal-acceptance.md).
The strict asset-provenance release check deliberately fails until rights
are established. No draft or published GitHub release was created.

**Earlier merged documentation validation:** [Validate run **40195818111**](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40195818111)
for main commit `f962fdbd1f9ecf6d27c30eda94c432d7552bfba3`
(doc archive/cleanup [PR #12](https://github.com/anaschillin/home-assistant-salah-timetable/pull/12))
completed successfully on **attempt 2**, with all six jobs green and **873 Python
tests passed**. On **attempt 1**, the Python job reported **872 passed,
1 failed, 1 error**, with the observed failure in
`tests/test_calendar.py::test_calendar_trigger_offset_before_local_midnight_uses_next_date`:
the start-offset event fired, but the expected calendar presentation-end event
was not observed at frozen time `2026-10-23T23:06:00Z` (actual event count 1,
expected 2). The same source passed without changes on rerun. The cause and
reproducibility are **not established**, and the pass is not a fix. Investigation
is open in [issue #13](https://github.com/anaschillin/home-assistant-salah-timetable/issues/13)
under Milestone 11. The separate later-documentation and release CI must still
pass for its own exact commit.

**Later merged-main acceptance (Milestone 17):** [run
40208986292](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40208986292)
completed on main commit `e48463d53417909809ff30c1708127d9917f1786`
([PR #15](https://github.com/anaschillin/home-assistant-salah-timetable/pull/15)):
**880 Python tests passed**, plus frontend/Chromium, HACS, hassfest and
disposable live Home Assistant 2026.10.0 / 2026.10.3, all green. This
includes pure source-scoped date/time import comparison and Home Assistant
Options-flow pagination/reject/approval tests. The first branch run failed
Ruff formatting, the next found three incorrect Markdown-label test
assertions; both were corrected. One Chromium-startup timeout occurred on a
later branch attempt, and its failed job passed on rerun. The final
**merged-main** run succeeded without those errors.

**Dashboard enhancement evidence (not release sign-off):** [PR
#16](https://github.com/anaschillin/home-assistant-salah-timetable/pull/16)
adds a Fajr end display using the explicitly published Sunrise, MOSQUE_A annual
and monthly **second khutbah** footer extraction as Friday-only metadata,
and a full calculated Hijri date visibility option at initial mosque setup
and in later Options settings. The published Fajr, Dhuhr, Jumu’ah and
Jamaat timestamps are unchanged; khutbah is **not** inserted into the event
engine. The user-facing card retains its independent per-card hide switch.

The [PR validation run **40212080948**](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40212080948)
succeeded for source commit `ed6733cc03a9c354dba6f233e37431140c8eda30`:
**884 Python tests passed**, frontend Chromium, HACS, hassfest and disposable
live HA 2026.10.0/2026.10.3 all passed. Early branch iterations caught
Python formatting, browser DOM selection and the new MOSQUE_A fixture's CSV
header/column-count mismatches. These were corrected and not silently
dismissed. Manual real-publication display, physical-device/card-editor
and restart acceptance remain **unverified** and must be recorded against
the final release candidate. The live matrix does not establish full HAOS
restore or HACS UI uninstall/reinstallation.

**Dashboard post-merge `main` evidence:** [Validate run
**40212875119**](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40212875119)
completed on **25 October 2026**, on squash-merge commit
`c8e65bd01250af0b892782c0e1ef04b99072e37a`
([PR #16](https://github.com/anaschillin/home-assistant-salah-timetable/pull/16)).
**All six jobs passed on the first attempt**, including **884 Python tests**,
Ruff, Node/Chromium frontend, hassfest, HACS and disposable live Home Assistant
**2026.10.0 / 2026.10.3** checks. This validates the merged dashboard changes
in the recorded automated environments. It **does not** certify the physical
dashboard, full HAOS/Supervisor recovery, actual HACS UI remove/reinstall or
asset redistribution rights. The next documentation commit and any eventual
release commit must also pass their own exact-commit CI.

**Previously user-confirmed acceptance:** Physical-device checks and HACS
custom-repository installation, restart and updates were reported complete
on 24 October 2026 for the latest installed candidate. Their exact device,
browser and installation version were not recorded. This confirmation predates
0.7.0 and does not establish physical testing of the new calendar, publication
profiles, speaker controls, paged review or dashboard additions, or the three
outstanding release sign-offs.

The original [25 October review plan](archive/review-action-plan-2026-10-25.md)
is archived as implementation history. Dated sections below retain the
actual results and limitations observed when they ran, including earlier
0.5.x, 0.6.x, 0.7.0 and pre-merge 0.8.0 candidates; they must not be interpreted as the
latest source or current release gates.

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
- The supplied Mosque A 2026 PDF passed authenticated upload,
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
real mobile/tablet devices. The MOSQUE_A website's live HTTPS availability is unverified;
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

- MOSQUE_A `mosque_a_monthly_2022.pdf` is May–June **2022**, not a complete Ramadan-only file.
  The strict monthly adapter produces 61 exact dates and 854 event values.
- Mosque B `mosque_b_2026.pdf` is the 2026 annual calendar plus a final Ramadan page. The new
  adapter imports only that page: February 18–March 20, 31 dates and 341 published
  values. Its final post-Ramadan Hijri-1 row does not activate Ramadan.
- Every date and event value matched separately constructed Poppler spatial-text
  CSV oracles, independently of production pypdf extraction and layout helpers.
- Actual isolated extraction and native HA authenticated upload/map/review/approve
  flows passed for both real PDFs. Source binary/checksum and parsed provenance
  round-trip through persistence and config-entry reload without activation.
- Explicit confirmation in the example February 18–March 19 window enables
  Mosque B's permitted default Iftar and text-only Taraweeh; March 20 stays inactive.
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

The complete MOSQUE_A Ramadan publication, full Mosque B annual parsing and native
cross-Gregorian-year PDF imports remain outside this change. See
[Ramadan validation](ramadan_validation.md) and [remaining work](remaining-work.md).


## Mosque B annual tables and README badges — candidate 0.5.4

The same maintainer-supplied `mosque_b_2026.pdf` now has a separate annual adapter:
`mosque_b_annual_v1`. It imports twelve complete monthly tables and excludes the
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

Pulled the maintainer's Chrome diagnostic step, MOSQUE_A monthly confirmation test and
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
the maintainer's MOSQUE_A flow and frontend/packaging/release preparation also passed,
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
updated installation at that time, before 0.7.0. Device/browser models,
HA/integration version numbers and
individual scenario results were not specified. This confirmation does not by
itself establish the HACS installation route, full backup restoration, a published
0.6.2 release, hosted CI success for a new commit or physical testing of subsequent
calendar, publication-profile, speaker, paged-review and dashboard additions.


## User-confirmed HACS installation and updates — 24 October 2026

The user confirmed installing and updating through Home Assistant's HACS custom
repository route, including the documented restart. HACS installation/restart/update
checks are recorded as complete for their installation. This does not establish
removal/re-addition in a test instance or full HA backup restoration; those remain
separate acceptance work.


## Calendar, publication profiles and media — candidate 0.7.0

Tested the local candidate based on `79aa7c4` on 25 October 2026, before commit.
This is manual-install evidence; it does not establish HACS removal/re-addition or
new physical-speaker/device acceptance.

- **853 Python tests passed**, with 95% aggregate integration line coverage.
  The focused feature suites include 23 calendar, 24 publication-profile, 22 Adhan
  control and 26 pause/resume cases; existing blueprint cases remain covered.
- Native calendar tests cover approved/pending data, distinct zero-duration events,
  multiple Jumuah, derived Iftar labelling, missing dates, later approved years,
  leap-day/year boundaries, DST ambiguity, stable IDs, authenticated APIs, reload,
  mosque isolation and an actual HA calendar-trigger offset before local midnight.
  These historical results predate REV-01's one-minute presentation-interval fix;
  [current calendar behavior](calendar.md) preserves exact prayer instants.
- Publication-profile tests cover all four inspected editions, exact year/date
  spans, immutable defaults, unchanged original rows/warnings, optional omitted
  fields, versioned provenance persistence, actual upload/review/approval/rejection
  and timezone changes between selection, mapping and approval.
- Real HA scheduler tests cover Fajr audio, per-prayer volume, disabled prayers,
  quiet-hour boundaries/DST, unavailable players, delayed speaker acknowledgement,
  guarded restoration, manual interference, media ownership, missing anchors,
  overlapping operations and cancellation. Incremental reload retains unchanged
  automations; disabling or reloading changed settings cancels their pending work.
- **81 Node tests passed**. Native Chromium passed all four widths, light/dark
  themes, 200% text, keyboard focus, selection and graphical editor persistence.
- **24 disposable HA 2026.10.0 checks passed**, including the new calendar and
  profile guard checks, import/approval, restart/pending/rejection and real editor.
  `pypdf` metadata/module were absent before setup and both reported pinned
  **6.21.1** afterward. No preload; the session's trusted CA bundle was mounted
  read-only with TLS verification enabled. Results: `/tmp/salah-live-0.7.0/results.json`.
- Ruff, formatting, whitespace, offline lock consistency and 0.7.0 release archive,
  checksum and notes preparation passed. Release publication remains separate.

Pushed 0.7.0 commit `737b636` subsequently passed hosted Validate, including both
HA live lanes. Later increments require their own result. Existing user-confirmed
device/HACS checks predate these new controls and are recorded
separately above. Full HA backup restoration, HACS removal/re-addition and asset
provenance remain release acceptance work.


## Paged import review — candidate 0.8.0

Tested the local candidate based on `737b636` on 25 October 2026, subsequently
committed as `0850ca6`, before merging the later `origin/main` runtime, dashboard
and canonical-comparison changes. These are pre-merge results, not validation of
the combined candidate.
The comparison uses only the exact approved source ID being replaced, including
all legacy years. It distinguishes canonical prayer values, original source cells
and provenance changes without treating a new checksum as changed prayer times.

- **902 Python tests passed**, with 95% aggregate integration line coverage,
  after the three Adhan regression cases described below (the earlier run passed 899).
- **46 focused comparison tests passed**: 31 pure model/rendering cases and 15 real
  HA flow/storage cases. These cover every page of large/whole-year comparisons,
  added/removed dates and fields, all Jumuah slots, ditto/12-hour original tokens,
  unmapped annotations and blank cells on new/removed dates, legacy provenance,
  private-URL redaction, escaped/truncated labels, explicit decisions, restart,
  two mosques and another storage instance changing the approved baseline.
- Navigation leaves the staged identity and approved records unchanged. Stale
  baseline approval resets the comparison and requires another explicit click;
  profile timezone checks use the freshly loaded staged candidate.
- **81 Node tests passed**. No dashboard behavior was changed in this increment;
  metadata and JavaScript cache versions advance together to 0.8.0.
- **25 live HA 2026.10.0 checks passed** on the pre-merge integration candidate, with
  `pypdf` absent before setup and pinned 6.21.1 installed/imported afterward. No
  preload; trusted CA mounted read-only with TLS verification enabled. The new
  check navigates comparison pages while approved Fajr remains unavailable until
  explicit approval. Calendar, restart, rejection, actual card/editor, four widths,
  themes and 200% text remain covered. Results: `/tmp/salah-live-0.8.0-final/results.json`.
- Broad peer review reproduced two Adhan restoration failures: removing a player
  during acknowledgement interrupted healthy players, and same-context hardware
  changes away and back were overwritten. Missing-player guards and a conservative
  last-update ownership check fix both. Three new scheduler cases prove the failures
  before the fix and the expected behavior afterward; ordinary player updates may
  intentionally skip restoration. The release checklist now covers all new controls.
- Ruff, formatting, whitespace, offline lock checks and 0.8.0 archive/checksum/notes
  preparation passed. Exact-commit hosted validation remains required.

The integration remains an unreleased candidate. Earlier user-confirmed physical
and HACS installation checks are separate from new-feature release acceptance.


## Combined 0.8.0 review and calendar synchronization

Combined local `0850ca6` with the later main work through `ffc56c6`. Retained the
one-minute calendar presentation interval and overlap semantics, coordinator
lifecycle cleanup, rejected-source status, Fajr-end/Friday-khutbah/Hijri dashboard
settings, asset gate, Container archive restore and two-mosque lifecycle checks.
The existing **Compare changes** route now shows all rich ten-entry source pages
and returns to review before explicit approval/rejection. Canonical comparison API
compatibility remains covered separately.

- **936 Python tests passed**, 95% integration coverage.
- **113 focused comparison/import/profile tests passed** during merge verification.
- **83 Node tests passed**; native Chromium passed 320/360/400/900px, theme,
  keyboard/focus, selection and 200% text checks.
- Ruff, formatting, whitespace, offline dependency lock consistency, local links,
  version checks and local 0.8.0 ZIP/checksum/release-note preparation passed.
  The ordinary asset inventory audit passed and reports ten unresolved rights
  records. The strict public-release gate remains intentionally blocked.

For [issue #13](https://github.com/anaschillin/home-assistant-salah-timetable/issues/13),
the unchanged timing test failed once in ten local runs, with the same missing
end event and delayed timer as CI. Home Assistant's 15-minute calendar refresh
and its executor query run as background tasks; the test's default drain excluded
them before advancing to the end instant. A forced delayed-refresh variant
reproduced the failure. The fixed test explicitly processes the 23:00 polling
boundary and drains background work before its unchanged exact start/end assertions.
Normal and delayed variants then passed **20/20** repeated cases; all **27 calendar
tests passed**. This is a test synchronization correction; production event timing
and the calendar presentation interval are unchanged. Hosted evidence for this
fix is still required before treating the issue as closed.


The combined candidate also passed **29 disposable HA 2026.10.0 checks** with
fresh pinned dependency installation and `--verify-backup-restore`. Home Assistant
created an actual Container archive; its restore module extracted it into another
disposable configuration, and the private audit matched approved/pending imports,
source metadata, config entries, devices, entities and card resources. Two-mosque
approval/removal/re-addition remained isolated. The new Compare screen navigation
left active data unchanged, and calendar intervals, source-profile guard, restart,
rejection and the actual card/editor remained covered. Results:
`/tmp/salah-live-merged-0.8.0/results.json`. This remains Container archive evidence;
full HAOS restore and authenticated HACS UI reinstall remain release gates.
