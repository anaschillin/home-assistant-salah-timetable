# Validation and acceptance

Validation evidence is specific to an **exact commit**. The authoritative historical job logs, artifacts and results are on [GitHub Actions](https://github.com/anaschillin/home-assistant-salah-timetable/actions), rather than in an ever-growing per-PR diary.

## Automated checks

The validation workflow covers Python tests and coverage, Ruff, Node frontend tests, Chromium interaction/visual checks, minimum/current pinned Home Assistant compatibility, hassfest, HACS repository validation, package consistency and a disposable Home Assistant Container live smoke run.

The Chromium harness uses test stand-ins for parts of Home Assistant. HACS repository validation is not a real HACS UI installation, and Container archive/restore testing is not a complete HAOS/Supervisor restoration.

For reproducible commands and test boundaries see [Testing](testing.md), [Compatibility](compatibility.md), [Live smoke](live-smoke.md) and [Visual regression](visual-regression.md).

## Manual acceptance

For a release candidate, record real HACS install/update and HAOS usage on the **exact version**; check import/approval, two-mosque isolation, dashboard rendering on mobile/tablet, date boundaries, storage after restart and relevant automation behaviour. Capture environment and results in the release review.

A full HAOS/Supervisor backup restore is optional/deferred, not a prerequisite for every change or release. See [Backup and restore](backup-restore-acceptance.md).

The authoritative sign-off procedure is [Releasing](releasing.md).
