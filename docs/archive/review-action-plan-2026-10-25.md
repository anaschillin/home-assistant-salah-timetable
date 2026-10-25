# Archived code review follow-up action plan — 25 October 2026

**Status:** Archived after the 25 October 2026 implementation sweep; REV-01–03 fixes and REV-04–06 test/tooling PRs are merged. Release sign-offs and later enhancements remain open. This file preserves historical review decisions, **not** a second live checklist. For current release gates use [Building and accepting a release](../releasing.md); for later development use [Remaining work](../remaining-work.md).
**Review baseline:** [`main` at `737b636`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/737b636dfc5ce934625dec0afc6eb5291ee43091) (candidate 0.7.0).
**Purpose:** A durable, prioritized backlog from the 25 October repository review. This supplements [remaining work](../remaining-work.md), [validation evidence](../validation.md), and the [release checklist](../releasing.md); it does not replace the feature [milestones](../milestones.md).

Keep changes small, add regression tests, and link the implementing commit/PR and test run beside each item when complete. A green pre-change CI run does **not** prove any task below has been resolved. For changes to runtime behaviour, review the user-visible semantics before implementation.

## Priority summary

| ID | Priority | State | Action | Target |
| --- | --- | --- | --- | --- |
| REV-01 | P1 | [x] Merged ([PR #7](https://github.com/anaschillin/home-assistant-salah-timetable/pull/7), [`bbf4f1d`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/bbf4f1dddae4578dd9f00d8aee0d9526c9eab0bf)) | Resolve zero-duration calendar event compatibility | Before next public release |
| REV-02 | P1 | [x] Merged ([PR #6](https://github.com/anaschillin/home-assistant-salah-timetable/pull/6), [`b175f89`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/b175f89c8dea466103e4b654cd5e98c89b0c674e)) | Ensure coordinator boundary timer is stopped on unload/reload | Before next public release |
| REV-03 | P2 | [x] Merged ([PR #8](https://github.com/anaschillin/home-assistant-salah-timetable/pull/8), [`423f4b8`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/423f4b8cf34ec6e6ada054310ed7922efbab2e39)) | Make rejected-source status distinguishable from approved/up-to-date data | Before next public release |
| REV-04 | P2 | [ ] Rights pending; tooling merged ([PR #9](https://github.com/anaschillin/home-assistant-salah-timetable/pull/9), [`44b102a`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/44b102ae6edd83c242b6026efda34cddcbda3a96)) | Verify redistribution rights of fixtures and branding | Release gate |
| REV-05 | P2 | [ ] Full HAOS restore evidence pending; Container test merged ([PR #11](https://github.com/anaschillin/home-assistant-salah-timetable/pull/11), [`12f6ae5`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/12f6ae52e249ed2a4ba6d80b17989b0c5e781753)) | Restore a full Home Assistant backup archive in a disposable instance | Release gate |
| REV-06 | P2 | [ ] HACS UI evidence pending; test merged ([PR #10](https://github.com/anaschillin/home-assistant-salah-timetable/pull/10), [`d335a4c`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/d335a4c52740a41dadcce57c63a65a28a81105bb)) | Verify HACS removal/re-addition and multi-mosque isolation | Release gate |
| REV-07 | P3 | [ ] Open | Expand version/upgrade compatibility evidence | Follow-up |
| REV-08 | P3 | [ ] Open | Track localization/RTL and import change-diff usability | Subsequent milestones |

**Implementation tracking (25 October):** REV-02 was squash-merged as [`b175f89`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/b175f89c8dea466103e4b654cd5e98c89b0c674e) and REV-01 as [`bbf4f1d`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/bbf4f1dddae4578dd9f00d8aee0d9526c9eab0bf); maintainer confirms both CI suites passed. REV-03 was squash-merged as [`423f4b8`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/423f4b8cf34ec6e6ada054310ed7922efbab2e39) after green CI. REV-04/05/06 tooling was subsequently squash-merged in PRs #9, #11 and #10, respectively. Final combined [main validation run 40194784544](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40194784544) passed (873 Python tests and both Home Assistant 2026.10 live jobs). These runs do **not** establish redistribution permission, full HAOS/Supervisor restore, or HACS UI uninstall/reinstallation, so those three gates remain open in the [current release checklist](../../releasing.md).

## REV-01 — CalendarEvent start/end semantics

**Evidence:** [`calendar.py`](../../custom_components/salah_timetable/calendar.py) in `_day_events()` sets `end=stamp`. [`test_calendar.py`](../../tests/test_calendar.py) explicitly asserts that `start == end`. The [Home Assistant calendar entity developer documentation](https://contributors.home-assistant.io/core/entities/calendar/) treats event starts as inclusive and ends as exclusive; verify the contract against the supported Core versions before changing behaviour.

**Risk:** Zero-length events have no active interval. UI rendering, calendar integrations, overlapping range queries and start/end-trigger semantics may be inconsistent even if current API smoke tests succeed. Prayer/Jamaat times themselves must remain exact instants—an event's display interval must not be presented as a religious or congregational duration.

**Tasks**
- [x] Confirm the precise `CalendarEvent` invariants and consumer behaviour on supported HA versions.
- [x] Choose and document an explicit *calendar presentation interval* (e.g. 60 seconds), or a standards-compatible alternative. Do not infer prayer duration.
- [x] Update `_day_events()` and affected calendar descriptions/docs.
- [x] Audit `calendar_events()` for the Home Assistant range contract (overlap with the requested interval, not only start-within-range), including midnight boundaries and next-day indexing.
- [x] Recheck `PrayerCalendar.event` transitions and calendar start/end automation triggers.
- [x] Replace zero-length assertions with regression tests covering multiple Jumu'ah slots, precise start timestamps, DST, midnight and interval overlap.

**Done when:** Calendar UI/API and start triggers work on the minimum/current supported Core versions, no published start time shifts, and the chosen representation is documented.

## REV-02 — Cancel coordinator boundary scheduling on unload/reload

**Evidence:** [`coordinator.py`](../../custom_components/salah_timetable/coordinator.py) registers `_boundary_unsub` through `async_track_point_in_utc_time` and cancels it in `async_shutdown()`. [`__init__.py`](../../custom_components/salah_timetable/__init__.py) calls `source_updates.async_stop()` on successful unload but does not explicitly call `coordinator.async_shutdown()`.

**Risk / hypothesis to verify:** A callback registered independently of platform update listeners may survive unload and keep refreshing an obsolete coordinator after a reload.

**Tasks**
- [x] Add a failing integration regression test: populate a schedule, unload, advance time across a boundary, and confirm the old coordinator does not refresh or reschedule.
- [x] On a successful unload, stop both the source-update manager and coordinator; preserve failure semantics when unloading platforms fails.
- [x] Check teardown on partial setup failure and repeated reloads; ensure no duplicate scheduled callbacks remain.
- [x] Verify normal boundary-based state changes still occur exactly once after reloading.

**Done when:** No stale timer is left after unload or reload, with tested cleanup on supported Core versions.

## REV-03 — Distinguish rejected content from approved source freshness

**Evidence:** [`source_updates.py`](../../custom_components/salah_timetable/source_updates.py) returns `up_to_date` when checks have `last_success`, even if content was staged and rejected. [`test_source_updates.py`](../../tests/test_source_updates.py) intentionally asserts `up_to_date` for a rejected, unchanged source with no approved table.

**Risk:** Users may read “up to date” as “the current publication has been approved and is active,” whereas it can mean only “the last download was successful.” The existing checksum suppression after a rejection is valuable and should be retained.

**Tasks**
- [x] Define separate concepts: source reachable/checked, latest seen digest, approved digest and explicitly rejected digest.
- [x] Decide user-visible status wording (e.g. `rejected_version` / `differs_from_approved`), without exposing URLs or source content in public sensors/diagnostics.
- [x] Preserve the no-reprompt-until-content-changes rule and all approval safeguards.
- [x] Update status sensor translations/documentation and tests for new, unchanged, approved, rejected, pending and failed sources; verify persistence across restart.

**Done when:** Freshness never implies approval incorrectly, and rejected identical bytes remain suppressed until the published content changes.

## REV-04 — Asset provenance and redistribution

**Evidence:** [`tests/fixtures/pdf/`](../../tests/fixtures/pdf) includes real NMS/Zakariyya PDFs; [`brand/icon.png`](../../custom_components/salah_timetable/brand/icon.png) and other contributed assets need provenance checks. The runtime release archive excludes published PDFs, but they remain public in repository history.

**Tasks**
- [ ] Record source, owner, licence/permission and intended distribution for each real fixture and logo.
- [ ] Obtain explicit redistribution permission where required; otherwise replace publicly shipped fixture content with suitable synthetic, independently asserted equivalents.
- [ ] Keep original evidence privately where redistribution is not authorized; review history-removal implications separately if needed.
- [ ] Document the outcome in the release checklist.

**Done when:** Every published non-code asset has a recorded distribution basis.

## REV-05 — Full Home Assistant backup restoration

**Evidence:** Timetable-store migration/restore tests exist, but [remaining-work.md](../remaining-work.md) distinguishes them from full HA *backup-archive* restoration.

**Tasks**
- [ ] Create a disposable instance with a configured mosque, approved source, pending proposal, Ramadan settings and registered entities.
- [ ] Create a complete Home Assistant backup archive; restore into a second disposable instance.
- [ ] Verify config entries, IDs, source provenance, pending/approved separation, calendar/card registration and remote-check metadata.
- [ ] Verify no source is automatically approved; repeat a restart and check Repairs and duplicate resources.
- [ ] Record Core version, backup/restore method, anonymized results and limitations in [validation.md](../validation.md).

**Done when:** An actual full-backup restore succeeds and the recorded evidence is reproducible.

## REV-06 — HACS remove/re-add and coexistence

**Evidence:** User-confirmed HACS custom-repository install/restart/update already exists; removal/re-addition remains unverified.

**Tasks**
- [ ] Use a disposable Home Assistant instance, not the primary deployment.
- [ ] Install through HACS, add two separately identified mosques and import different timetables.
- [ ] Remove/re-add the integration as appropriate and document whether config-entry removal intentionally deletes per-entry storage.
- [ ] Confirm no stale card resources, timers, entities or unexpected cross-mosque effects; test upgrade to the candidate.
- [ ] Record each scenario and any recovery instructions in [validation.md](../validation.md).

**Done when:** The expected uninstall/reinstallation behaviour is documented and the other mosque remains unaffected where applicable.

## REV-07 — Extended compatibility evidence (not a substitute for release gates)

- [ ] Keep the minimum/current supported Home Assistant smoke matrix green, including fresh dependency installation.
- [ ] Add an upgrade-path scenario from the last published version once a release exists.
- [ ] Revisit the supported patch matrix when Home Assistant versions advance; avoid claiming support for untested versions.
- [ ] Record hardware browser behaviour and results separately from mocked browser tests.

## REV-08 — Subsequent UX and localization work

- [ ] Track Arabic/bilingual display and right-to-left card accessibility against [milestones.md](../milestones.md), with actual mobile/tablet acceptance.
- [ ] Add a field-by-field import-change comparison (added, removed and changed dates/times) before approving replacement sources.
- [ ] Keep these enhancements separate from the targeted release fixes above unless a regression requires them.

## Implementation order and evidence

1. **First:** REV-01 and REV-02, each in a focused PR with a regression test that fails before the fix.
2. **Then:** REV-03, including a deliberate UX decision and translation updates.
3. **Before release:** REV-04, REV-05, REV-06 and all required [release checklist](../releasing.md) items.
4. **After stabilization:** REV-07 and REV-08.

Local validation commands, matching [`validate.yml`](../../.github/workflows/validate.yml):

```bash
uv sync --frozen --group dev
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pytest
npm test
npm run test:browser
uv run --frozen python scripts/build_release.py --check
```

Also inspect the required hosted hassfest, HACS and Home Assistant live-acceptance jobs; local unit tests alone are insufficient.

### Final release gate

- [ ] P1 fixes implemented, verified on minimum/current supported Home Assistant versions and reflected in calendar/user documentation.
- [ ] P2 semantics and asset/backup/HACS acceptance tasks completed or explicitly documented as release blockers with an approved decision.
- [ ] Exact proposed release commit has all required green CI jobs.
- [ ] `manifest.json`, `pyproject.toml`, bundled frontend asset versions, release notes and changelog agree.
- [ ] Release documentation and validation evidence updated; manual draft release reviewed before publishing.

**Tracking:** When completing a checkbox, replace “Open” with the actual state and link the implementing PR/commit and test evidence. Do not treat this plan itself as confirmation that a fix or acceptance test has run.
