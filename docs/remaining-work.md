# Remaining development work

This is the **feature and engineering backlog**, not a second release checklist.
The current integration candidate is **0.9.1**. For release blockers,
sign-offs and version-specific manual acceptance, use the
[release readiness checklist](releasing.md#current-release-readiness).
For completed milestones and future scope, see the
[implementation plan](milestones.md); dated test evidence is preserved in
[validation](validation.md).

## Current engineering status

The minimum/current Home Assistant unit lanes, complete
`test_source_flow.py` compatibility suite, live Container acceptance,
HACS, hassfest, frontend/Chromium and CodeQL all passed on the
[26 October 2026 main commit `b6dbe14`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/b6dbe14bb75b791fbb1171e981494d2a21dbe07e).
[Validate run 40337238065](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40337238065)
finished **12/12 jobs successfully**; [CodeQL 40337238192](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40337238192)
also passed. CI simplification and diagnostics were squash-merged in
[PR #26](https://github.com/anaschillin/home-assistant-salah-timetable/pull/26)
and [PR #27](https://github.com/anaschillin/home-assistant-salah-timetable/pull/27).
Calendar test timing [#13](https://github.com/anaschillin/home-assistant-salah-timetable/issues/13)
and minimum-HA hosted cancellation [#24](https://github.com/anaschillin/home-assistant-salah-timetable/issues/24)
are **closed**. The original unsharded minimum-HA hang was not conclusively
diagnosed; the maintained five-group approach remains documented in
[compatibility](compatibility.md).

Green CI is **not** a published release or proof of full HAOS restore,
rights clearance, authenticated HACS UI acceptance or manual/device checks.
Those decisions are owned by [releasing.md](releasing.md).

## 27 October code-review follow-up (active)

Baseline: [main at 7913789](https://github.com/anaschillin/home-assistant-salah-timetable/commit/791378940435d2f97117d06b158ce100adcaf0eb). Findings are hypotheses until reproduced; preserve approved data, multi-instance isolation and existing security boundaries. Work in small PRs with regression tests.

- [x] **CR27-01 (P1):** Reproduce source-check timer behaviour when remote profiles are added or removed. Fix rescheduling and status notification if tests expose stale scheduling.
- [x] **CR27-02 (P1):** Test calendar next-event cache across approval, rejection, source replacement, midnight, year rollover and empty future coverage. Correct confirmed stale state without changing published instants.
- [ ] **CR27-03 (P2):** Audit frontend component-loaded listener lifetime and cleanup across repeated setup, unload and re-addition; add lifecycle tests before changing global registration.
- [ ] **CR27-04 (P2):** Measure coordinator minute refresh against event-boundary scheduling. Preserve clock-correction, DST and restart recovery; change cadence only with evidence.
- [ ] **CR27-05 (P2):** Extract shared PDF/CSV/URL import preparation from options flows without changing approval semantics or user-facing steps.
- [ ] **CR27-06 (P3):** Audit callers of legacy storage helpers (including `for_date`); remove dead code or correct stale documentation with tests.
- [ ] **CR27-07 (P3):** Document import, source-update, storage, coordinator and frontend responsibilities and cross-module state-change contracts.

**First implementation batch:** CR27-01 and CR27-02 implemented in [PR #66](https://github.com/anaschillin/home-assistant-salah-timetable/pull/66). Source removal now explicitly recalculates the check timer, with a regression test. Calendar cache behaviour was verified by existing tests and an added replacement/year-rollover regression test; no production cache change was needed. Maintainer reports CI passed after Ruff formatting correction. This does not replace manual HA acceptance.

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
