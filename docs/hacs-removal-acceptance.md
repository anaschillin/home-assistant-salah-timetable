# REV-06 — HACS removal/re-addition and two-mosque acceptance

**Scope:** HACS repository validation and real Home Assistant Container lifecycle
checks run in CI for pull requests. The maintainer also reports HACS/HAOS checks
after completed PRs. The longer HACS UI remove/re-add procedure below remains an
optional *release-level* acceptance checklist; passing CI does not prove that UI
sequence occurred. Record versions and outcomes if that sequence is used.

## Reported HACS remove/reinstall outcome — 25 October 2026

**User-confirmed:** Removing and reinstalling the integration worked correctly
in the user's installation. This is positive manual feedback covering the
observed **removal/reinstallation outcome**; it is not merely the HACS
repository-validation result.

**Evidence details not yet recorded:** whether removal/reinstall was carried
out specifically through the HACS UI, HA/HACS/integration versions, browser,
a disposable installation, two independent mosque entries, preservation of
the unaffected mosque, deleted entry storage and registry cleanup, resource
uniqueness, and repeat-restart behavior. Do **not** infer passes for those
checks from a general report that reinstall works. The complete acceptance
sequence below remains the criterion for closing REV-06. Record the exact
environment and checks when known.

## Automated preflight

The live Home Assistant smoke matrix uses the actual integration and registry,
not mocked storage. On both supported HA versions, it now:

1. Creates separate mosque entries with the same date but different synthetic Fajr
   times (06:00 and 06:22) and verifies no cross-contamination.
2. Deletes the second config entry and checks that its live entities disappear,
   the first mosque's entities and data remain unchanged, and the integration's
   per-entry storage cleanup takes effect.
3. Creates a replacement for the second mosque ID and verifies the deleted
   timetable does not come back. Removes it again and confirms the bundled
   frontend resource has not been registered twice.
4. Restarts/reloads the first mosque and verifies its data, entities and card
   remain present.

These checks exercise **Home Assistant config-entry removal/re-addition** with the
custom component bind-mounted into a disposable HA Container. They do **not**
exercise the HACS frontend or HACS's package file removal.

## HACS acceptance in a disposable installation

Do not carry this out on your primary Home Assistant or on a device with data
you need to retain. Record the **actual** Home Assistant version, HACS version,
integration commit/tag, browser, and timestamp. Never upload auth tokens,
credentials, backup decryption keys, or real mosque timetable contents.

1. Create a clean disposable HAOS instance with HACS configured. Add this repo
   as a custom **Integration** repository in HACS, install the tested candidate,
   and restart Home Assistant. Confirm the installed custom component version.
2. Add Mosque A (`acceptance_a`) and Mosque B (`acceptance_b`), using only
   independent synthetic test timetables with visibly different Fajr values.
   Verify distinct config entry IDs, devices, sensor and calendar identities,
   source provenance and dashboard selection; save screenshots of safe, synthetic
   states only.
3. Stage a pending *different* import for A while B stays approved; verify B
   cannot see or approve A's proposal. Restart and confirm the pending/approved
   separation, per-entry source metadata and settings.
4. **Remove B's config entry through Settings → Devices & services first.**
   This intentionally deletes B's per-entry timetable store; it is not a way
   to preserve B's data. Confirm A remains, B's entities are removed, and
   any A-only Repairs issues remain scoped to A. Re-add B and confirm it starts
   empty, with no stale sensors or duplicate device.
5. Remove the remaining config entries and remove the integration through
   HACS. Follow HACS's restart instruction. Confirm the integration is no
   longer installed and any stale dashboard custom-card resource is identified
   rather than silently treated as functional; delete stale test dashboards
   manually if HACS cannot manage Lovelace resources.
6. Re-add the candidate from HACS and restart. Configure two synthetic mosques
   again, verify the card resources, options flows, dashboard/editor, and
   all sensors/calendars. Check that there is **one** active card resource and no
   unexpected duplicate entities/devices. Reinstalling code alone must **not**
   be claimed to have restored previously deleted config-entry storage.
7. Upgrade from an actual earlier published integration release if one exists.
   If none exists, mark the upgrade-path check **not applicable / not tested**
   rather than inventing a result.

## Evidence to append to `docs/validation.md`

Record pass/fail separately for HACS installation, removal, re-addition, two
mosques with different approved values, per-entry deletion semantics, pending
proposal isolation, frontend resource uniqueness, old-release upgrade (if
applicable), and restart. Include failures and exact reproducible steps;
only redact private information from any saved evidence.

**Evidence rule:** Mark the HACS UI lifecycle as passed only when the full sequence
is actually observed and recorded. Routine PR CI proves HACS repository validity
and Container config-entry lifecycle, not authenticated HACS uninstall/reinstall.
