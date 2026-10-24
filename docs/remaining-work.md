# Remaining work

Milestones 1–5 are implemented. Release hardening is in progress; an item below is
complete only when its stated evidence exists. See [recorded validation](validation.md).

The next feature increments are specified in the [implementation plan](milestones.md#next-increments).
Milestone 7 now has implemented prayer automation blueprints, approved-date coverage
monitoring and real automation-engine acceptance tests. Calendar support, source
profiles, localization/RTL and broader compatibility tests follow separately. Release acceptance below remains required
for each published increment.

## Before a tested public release

| Work | Status | Completion evidence |
| --- | --- | --- |
| Hosted validation | Passed for `b7b0c74` ([run](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40138323440)); rerun if the release commit changes | Successful Validate run for the exact release commit, including HACS and hassfest |
| Minimum HA version | Passed 20 disposable HA 2026.10.0 checks for the local 0.6.2 candidate, including fresh dependency, import, restart and actual editor | Rerun configuration, import, persistence, card and real editor checks for the final candidate |
| Fresh runtime dependency installation | Passed locally on HA 2026.10.0: absent baseline and imported/installed `6.21.1` verified, no preload; trusted CA bundle supplied for the session proxy | Start clean supported HA without `--preload-pypdf`; verify HA installs the exact manifest-pinned dependency, rather than using a supplied copy |
| HACS custom-repository installation | Installation, restart and updates user-confirmed complete; test-instance removal/re-addition pending | Verify removal/re-addition preserves expected behavior without affecting another mosque |
| Physical mobile/tablet checks | Complete — user-confirmed on 24 October 2026 after updating to latest | User-reported completion; hardware, browser and exact version details were not recorded ([record](validation.md#user-confirmed-physical-device-acceptance--24-october-2026)) |
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

The live runner is available in `scripts/live_smoke.mjs`. The local 0.6.2 candidate
passed 20 checks on disposable HA 2026.10.0, including fresh dependency installation,
RUNNING/config-entry readiness, approved/pending/Ramadan restart state, 26 entities,
real card picker/editor and each display toggle. See the
[latest validation](validation.md#repository-review-and-milestone-7--candidate-062).

An earlier hosted live run passed HA 2026.10.0 and 2026.10.3 on the same source tree
as baseline main `c9b42f3`; that result does not certify the subsequent local fixes.
Validate now requires the reusable minimum/current live matrix, with explicit
fresh-dependency proof; the live matrix also runs weekly. Validate passed for the
pushed `b7b0c74` commit. HACS installation, restart and updates are user-confirmed;
removal/re-addition remains to be checked in a test instance.

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
   Recommended next sequence: **8 → 12 → 13 → 9**, with 11 continuing in parallel
   and 17 available as an independent approval-workflow improvement. These additions
   are planned, not currently implemented.
4. Consider the HACS default catalogue after the full user workflow and release
   process are established. Custom-repository support is the current route.
