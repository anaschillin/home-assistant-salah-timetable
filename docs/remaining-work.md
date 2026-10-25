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
Adhan controls and media pause/resume. Localization/RTL, import change comparisons
and broader compatibility tests follow separately. Release acceptance below remains
required for each published increment.

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

The live runner is available in `scripts/live_smoke.mjs`. The local 0.7.0 candidate
passed 24 checks on disposable HA 2026.10.0, including fresh dependency installation,
calendar/profile checks, approved/pending/Ramadan restart state, 26 sensors plus
a calendar, real card picker/editor and each display toggle. See the
[latest validation](validation.md#calendar-publication-profiles-and-media--candidate-070).

Historical local 0.7.0 checks and an earlier hosted live run are documented
in [validation.md](validation.md); they do not replace the latest combined
[main Validate run](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40194784544),
which passed all six jobs and 873 Python tests after the REV-04–06 tooling merges.
That run includes automated config-entry removal/re-addition and actual
Home Assistant **Container** archive restoration. HACS UI uninstall/reinstallation
and full **HAOS** archive restore are still unverified release gates.

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
3. Follow the expanded [Milestones 8–17](milestones.md#next-increments): calendar,
   richer Adhan controls, pause/resume media, publication profiles, Arabic/bilingual
   RTL support, broader compatibility tests, calculated night periods, wall-tablet
   display/announcements, published special events and import change comparisons.
   Milestones **8, 9, 12 and 13** are implemented in candidate 0.7.0, with release
   acceptance pending. Next pursue **17** (import change review) and **10**
   (localization/RTL), with **11** continuing in parallel. Milestones 14–16 follow.
4. Consider the HACS default catalogue after the full user workflow and release
   process are established. Custom-repository support is the current route.
