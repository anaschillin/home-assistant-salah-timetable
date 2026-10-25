# REV-05 — Real Home Assistant backup-archive restore acceptance

**Status:** Reproducible tooling provided; a **full, observed restore on a
disposable HAOS instance** is still required to close REV-05. The existing
migration/per-entry storage tests cannot substitute for this release gate.

Home Assistant Container supports configuration backups and the official
`homeassistant.backup_restore` module; HAOS has a broader full-backup
contract including Supervisor-managed folders/apps. The tests below are
**different scopes** and must be recorded separately.

## Synthetic disposable test setup

Use only a disposable HAOS VM or Home Assistant Container, with synthetic
mosque times. Never target your existing Home Assistant installation.

1. Install the candidate integration on the disposable system; add one or
   preferably two mosques. Approve a synthetic annual source and stage a
   *different* proposal without accepting it. Configure a confirmed Ramadan
   window and a dashboard with the bundled card.
2. Record the test version/commit, config-entry IDs, source metadata,
   registered sensor/calendar IDs, resource count, approved vs pending state
   and any Repairs issues. Use sanitized screenshots/counts only.
3. In **Settings → System → Backups**, create a backup including the Home
   Assistant configuration and database. On HAOS, choose **Full backup**,
   retaining the encryption key securely. Wait for completion before copying
   the file. Do not upload this archive to the GitHub repository or CI
   artifacts: it contains real credentials even with synthetic timetable data.
4. Restore the **actual archive into a different clean disposable HAOS
   instance through the supported onboarding restore flow**. Supply the
   backup's encryption key privately, select all available parts, and let
   Core/apps finish reinstalling. Do not attempt this on the primary HAOS VM.
5. Confirm **same entry IDs, devices, entity unique IDs, registered calendar,
   dashboard/card resource and options**. Confirm approved source bytes and
   source-check timestamps/validators remain unchanged, pending remains
   pending, and no downloaded source becomes approved on restore.
6. Restart the restored HAOS once more. Verify the same results, no duplicate
   resources, no unexpected Repairs items and correct source isolation.
7. Record supported Core version, backup archive format, restore mechanism,
   redacted counts, restart results and any limitations in
   [validation.md](validation.md). Do not commit backups/auth tokens.

## Reproducible Home Assistant Container preflight

For a second disposable Home Assistant **Container**, create a real archive
with **Settings → System → Backups → Create backup** (or the documented
`backup.create` action). Container backups normally live under
`/config/backups`; copy the resulting `.tar` into a temporary private
directory only after backup creation reports completion.

Once you have a backup and the source container's configuration volume (as a
filesystem path), run:

```bash
docker pull ghcr.io/home-assistant/home-assistant:2026.10.3
python -m scripts.disposable_backup_restore \
  --backup /private/synthetic-test-backup.tar \
  --original /private/synthetic-source-config \
  --ha-version 2026.10.3 \
  --confirm-disposable \
  --serve
```

This **does not restore onto the source**. It asks Home Assistant's own
backup restore module to restore the real archive into an ephemeral,
separately mounted configuration, and
`scripts/verify_backup_restore.py` compares config entries, stored
timetables, approved/staged separation, remote metadata, entity/device
registries and card resources **without printing their contents**. A
different, loopback-only test container then starts for an additional UI
check; press Enter to stop/delete the container and restored files. Use
`SALAH_TEST_BACKUP_PASSWORD` in the environment if an encrypted archive
requires a password, not a command-line argument.

Use the same Core patch version as the source for this preflight. For
automation, omit `--serve` to validate the archive and restored files
without booting the UI. The source reference must be a **stopped or
quiescent** disposable HA config immediately after backup creation; live
writes after the archive will otherwise correctly cause a comparison failure.

**Limits:** This helper validates only the HA Container configuration restore
using the official extraction implementation. It does not create the
archive, log into the restored UI, prove HAOS Supervisor/apps recovery,
prove physical hardware behavior, or replace the separate full HAOS
restore/restart acceptance.
