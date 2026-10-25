# Remaining work

Milestones 1–5 are implemented. Release hardening is in progress; an item below is
complete only when its stated evidence exists. See [recorded validation](validation.md).

The implementation fixes from the 25 October review (REV-01–03) and
supporting acceptance tooling (REV-04–06) are merged. The original
[review action plan](archive/review-action-plan-2026-10-25.md) is retained
as a **historical archive**, not another active checklist. The
[release guide](releasing.md#current-release-readiness--25-october-2026) is
the **single source of truth** for outstanding redistribution rights, full
HAOS restore, HACS UI uninstall/re-addition, and other release sign-offs.

The next feature increments are specified in the [implementation plan](milestones.md#next-increments).
Milestone 7 now has implemented prayer automation blueprints, approved-date coverage
monitoring and real automation-engine acceptance tests. Candidate 0.7.0 adds
Milestones 8, 9, 12 and 13: native calendar, inspected publication profiles, richer
Adhan controls and media pause/resume. Milestone 17 now adds read-only
paginated import-change comparisons (pending release acceptance). Localization/RTL
and broader compatibility tests follow separately. Applicable release acceptance
is tracked in [the release guide](releasing.md), not in this feature backlog.

## Release readiness

For the current release gates, their actual evidence, and outstanding sign-offs
see [Building and accepting a release](releasing.md#current-release-readiness--25-october-2026).
The [validation record](validation.md) contains dated test outcomes. Do not use
this feature backlog as a separate release acceptance checklist.

## Completed hardening

- Persistent Repairs for invalid structured timetable records, with safe guidance
  and cleanup after recovery/removal.
- Independent, frozen schema-1/schema-2 fixtures and real HA migration tests,
  including pending approval, failed writes, retries and future-schema rejection.
- Complete timetable-store backup restoration tests, preserving approved sources,
  Ramadan settings, pending proposals and entity IDs while clearing Repairs.
- Accurate diagnostic entry state and allowlisted row/event availability summaries;
  no source identities, imported values, dates, times or URLs are exposed.
- Reproducible manual-install archives, SHA-256 checksums, required-asset/version
  checks and tested release-note preparation.
- A manual draft-release workflow that requires an existing reviewed tag,
  a green run for the exact commit, and cleared public-asset redistribution
  rights; it neither creates tags nor publishes or overwrites releases.
- Calendar presentation-interval overlap/trigger fixes, coordinator teardown
  cleanup, and rejected-versus-approved source status (REV-01–03).
- Public asset inventory and fail-closed release audit (REV-04 tooling);
  full Container archive restore into a second disposable configuration
  (REV-05 tooling); two-mosque remove/re-add isolation (REV-06 tooling).
  Their **separate release acceptance gates** remain open in
  [releasing.md](releasing.md#current-release-readiness--25-october-2026).

The live runner is available in `scripts/live_smoke.mjs`. An earlier local 0.7.0
candidate passed 24 checks on disposable HA 2026.10.0, including fresh dependency
installation, calendar/profile checks, approved/pending/Ramadan restart state, 26
sensors plus a calendar, and real card picker/editor toggles. See the
[historical local validation](validation.md#calendar-publication-profiles-and-media--candidate-070).

Historical local 0.7.0 checks are documented in [validation.md](validation.md).
The latest recorded [main Validate run](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40195818111)
passed all six jobs and 873 Python tests on **attempt 2**. Attempt 1 encountered
one calendar-trigger timing failure, now tracked in
[issue #13](https://github.com/anaschillin/home-assistant-salah-timetable/issues/13).
Hosted acceptance includes automated config-entry removal/re-addition and actual
Home Assistant **Container** archive restoration. HACS UI uninstall/reinstallation
and full **HAOS** archive restoration remain unverified release gates.

## Subsequent additions

Ramadan import review now checks adjusted confirmed-window coverage, inherited and
unavailable values, advisory time ordering and approval-time source ambiguity. The
real NMS May–June 2022 and Zakariyya 2026 annual/Ramadan fixtures have strict
adapters and independent expected-value comparisons. See [Ramadan validation](ramadan_validation.md).

1. Verify the NMS website's public HTTPS timetable URL and scheduled changes on a
   network that can access it. Its supplied HTTP URL remains intentionally rejected;
   manual import of the attached NMS PDF is tested.
2. Add a complete NMS Ramadan publication and additional inspected mosque editions.
   Support native cross-year Ramadan publications without changing printed dates; current imports use one
   Gregorian year per source. Add further adapters only after obtaining inspectable,
   redistributable fixtures and an independent expected-results comparison. Unknown
   layouts and scanned/encrypted PDFs remain unsupported.
3. Follow [the feature roadmap](milestones.md#next-increments). Milestones **8,
   9, 12, 13 and 17** are implemented in the candidate (release acceptance pending).
   Next pursue **10** (localization and RTL),
   with **11** (expanded compatibility and the
   [calendar-trigger CI follow-up](https://github.com/anaschillin/home-assistant-salah-timetable/issues/13))
   continuing in parallel. Milestones **14–16** (night periods, wall-tablet
   display and published special events) are subsequent additions.
4. Consider the HACS default catalogue after the full user workflow and release
   process are established. Custom-repository support is the current route.
