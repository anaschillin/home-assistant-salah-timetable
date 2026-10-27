# Remaining development work

This is the **feature and engineering backlog**, not a second release checklist.
The current integration candidate is **0.9.3**. For release blockers,
sign-offs and version-specific manual acceptance, use the
[release readiness checklist](releasing.md#current-release-readiness).
For completed milestones and future scope, see the
[implementation plan](milestones.md); dated test evidence is preserved in
[validation](validation.md).

## Current engineering status

On 27 October 2026, [main commit `78c1a9f`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/78c1a9f018f9676a56b1657865bcdef40a5f8175)
passed [Validate 40578293746](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40578293746)
(**7/7 jobs**) and [CodeQL 40578293664](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40578293664).
The root and both pinned Home Assistant 2026.10.0 / 2026.10.3 unit suites
each passed **904 Python tests**, with **95% rounded line coverage** (3,142
statements, 163 missed). Frontend/Chromium, hassfest, HACS and the single
supported-current live Container acceptance job also passed.

The seven-job workflow replaces the former 12-job matrix. Both compatibility
lanes now execute the full suite without sharding; the original October 26
single-process hang remains an historical incident, not an active five-shard
configuration. See [compatibility](compatibility.md) and the dated
[validation log](validation.md) for evidence and limitations.

Green CI does **not** establish a published release, full HAOS restore,
redistribution rights, or complete manual HACS/physical-device acceptance.
Those decisions remain in [releasing.md](releasing.md).

## 27 October code-review follow-up (completed)

Baseline: [main at 7913789](https://github.com/anaschillin/home-assistant-salah-timetable/commit/791378940435d2f97117d06b158ce100adcaf0eb). Findings are hypotheses until reproduced; preserve approved data, multi-instance isolation and existing security boundaries. Work in small PRs with regression tests.

- [x] **CR27-01 (P1):** Reproduce source-check timer behaviour when remote profiles are added or removed. Fix rescheduling and status notification if tests expose stale scheduling.
- [x] **CR27-02 (P1):** Test calendar next-event cache across approval, rejection, source replacement, midnight, year rollover and empty future coverage. Correct confirmed stale state without changing published instants.
- [x] **CR27-03 (P2):** Audit frontend component-loaded listener lifetime and cleanup across repeated setup, unload and re-addition; add lifecycle tests before changing global registration.
- [x] **CR27-04 (P2):** Measure coordinator minute refresh against event-boundary scheduling. Preserve clock-correction, DST and restart recovery; change cadence only with evidence.
- [x] **CR27-05 (P2):** Extract shared PDF/CSV/URL import preparation from options flows without changing approval semantics or user-facing steps.
- [x] **CR27-06 (P3):** Audit callers of legacy storage helpers (including `for_date`); remove dead code or correct stale documentation with tests.
- [x] **CR27-07 (P3):** Document import, source-update, storage, coordinator and frontend responsibilities and cross-module state-change contracts.

**CR27-07:** Module responsibilities and change-propagation contracts documented in [integration architecture](integration-architecture.md).

**CR27-06:** Audited the annual-only `TimetableStorage.for_date` lookup. It remains in place for regression-test compatibility (24 tests depend on it); its docstring explicitly distinguishes it from effective Ramadan resolution through `ramadan.resolve_day`. No runtime caller was changed. The full validation workflow passed after restoring this test-supported helper.

**CR27-05:** Shared the PDF/CSV source inspection path between uploaded PDF and remote URL imports without changing staged review, explicit approval, or download safeguards. The existing import-flow regression suites and CI passed after the follow-up fixes.

**CR27-04 review (27 October):** Scheduling design audited; no performance benchmark was collected, so optimisation remains a separate potential task. Keep both scheduling mechanisms. Event-boundary callbacks provide timely transitions, while the one-minute coordinator fallback recovers from clock changes, delayed callbacks and other timing drift. Coverage is cached by day, approved tables and Ramadan settings. No cadence change without performance measurements and boundary/DST regression evidence; the audit is complete, but optimisation remains conditional.

**First implementation batch:** CR27-01, CR27-02 and CR27-03 implemented in [PR #66](https://github.com/anaschillin/home-assistant-salah-timetable/pull/66). Source removal now explicitly recalculates the check timer, with a regression test. Calendar cache behaviour was verified by existing tests and an added replacement/year-rollover regression test; no production cache change was needed. Frontend component-loaded listener now unregisters on Home Assistant shutdown, covered by a lifecycle regression test. Maintainer reports CI passed after Ruff formatting correction. This does not replace manual HA acceptance.

## Next development priorities

1. **Milestone 10B — Home Assistant integration translations.**
   Translate setup/options forms, entity labels and generated summaries through
   Home Assistant translation facilities. Arrange fluent review of draft Arabic
   wording before claiming linguistic sign-off; retain stable entity IDs,
   canonical prayer values and storage formats.
2. **Support additional verified publications.**
   Check a public HTTPS source for the Mosque A timetable;
   retain HTTPS-only downloads. Add a fully inspected MOSQUE_A Ramadan edition and
   additional annual/monthly/Ramadan adapters only when the printed source
   and independent expected results can be reviewed. Support cross-Gregorian-year
   Ramadan publications without altering printed dates.
3. **Milestones 14–16 — optional features.**
   Investigate calculated night midpoint/last third, mosque wall/tablet
   display and explicitly approved special prayer events. Label calculations
   distinctly and never invent missing or disputed prayer-event dates.
4. **Milestone 18 — Islamic history research, not runtime data.**
   Review [Sunni-source candidates](islamic-history-source-audit.md) for
   attribution, disputed dates and date precision. Editorial approval is
   required before any optional offline dashboard/history companion is added.
5. **Potential HACS catalogue submission.**
   Consider the default catalogue once the release workflow and user acceptance
   have been completed; custom-repository installation remains supported.

## Historical implementation evidence

Milestones 1–5, 7A/7B, 8, 10A, 11, 12, 13 and 17 have implemented
features or tests. Their exact scopes remain in [milestones.md](milestones.md).
Original 0.7.0–0.9.0 acceptance runs, earlier failed CI attempts and
manual-install evidence remain in [validation.md](validation.md).
The [25 October review action plan](archive/review-action-plan-2026-10-25.md)
is historical, not an active task list. The
[import review guide](import_review.md) is the authoritative explanation of
source comparison and approval; historical links to `import_comparison.md`
continue to resolve.
