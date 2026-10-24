# Remaining work

Milestones 1–5 are implemented. Release hardening is in progress; an item below is
complete only when its stated evidence exists. See [recorded validation](validation.md).

## Before a tested public release

| Work | Status | Completion evidence |
| --- | --- | --- |
| Hosted validation | Passed for `9642db3` ([run](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/39998754702)); rerun for the final release commit | Successful Validate run for the exact release commit, including HACS and hassfest |
| Minimum HA version | HA 2026.10.0 setup/import work; restart acceptance is unresolved | HA 2026.10.0 configuration, import, persistence, card and real editor checks pass |
| HACS custom-repository installation | Pending | Install with a maintainer's GitHub authorization in disposable HA; verify bundled assets, restart, update and removal |
| Physical mobile/tablet checks | Pending | Test narrow displays, themes, text scaling, touch and keyboard access on real devices |
| Complete backup restoration | Pending | Restore a full HA backup archive, including configuration entries and timetable storage, then verify identities and approved/pending data |
| Asset provenance | Maintainer review needed | Confirm redistribution rights for contributed branding and real NMS/Zakariyya PDF fixtures; publications are excluded from integration release archives |
| Release publication | Pending | Review release notes, validation and checklist, then publish the prepared draft |

HACS does not require an existing public release for a custom repository: its
[source implementation](https://github.com/hacs/integration/blob/a15e87ec0d1c82e58f1ddbaf17669d3eaa261eb8/custom_components/hacs/repositories/base.py#L1313)
falls back to the default branch when no release is available. This source review
establishes the expected packaging contract; it does not certify an authenticated
HACS installation of this repository.

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
- A manual draft-release workflow that requires an existing reviewed tag and green
  validation for its exact commit on main; it neither creates tags nor publishes
  or overwrites releases.

The experimental repeatable live runner is available in `scripts/live_smoke.mjs`
with startup/readiness gates and privacy-safe restart state flags. Docker execution
is currently blocked by the workspace sandbox; these improvements have unit coverage
but do not establish live acceptance. The original runner is preserved on the
[`codex/live-smoke-runner` branch](https://github.com/anaschillin/home-assistant-salah-timetable/tree/codex/live-smoke-runner).
It reached configuration, import, Ramadan and two-mosque checks on HA 2026.10.0,
but did not confirm the expected prayer state after restart. Complete startup/state
diagnostics before treating that result as a storage defect or claiming minimum-version
acceptance. The validated HA 2026.10.2 checks remain recorded separately.

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
3. Expand language translations and test additional accessibility combinations.
4. Consider the HACS default catalogue after the full user workflow and release
   process are established. Custom-repository support is the current route.
