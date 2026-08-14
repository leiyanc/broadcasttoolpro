# Backup and Recovery Runbook

## Purpose

Broadcast Tool Pro creates a verified SQLite backup every 24 hours while the
application is running. A Super Admin can also create and verify a backup from
the Control Panel.

Each backup consists of:

- A `.sqlite3` database snapshot produced through SQLite's online backup API
- A `.json` manifest containing its creation time, size, SHA-256 checksum, and
  integrity result

The default local retention period is 14 days.

The Stage 1 off-server copy is stored in the personal Google Drive folder
`Broadcast Tool Pro Backups`. Database files are encrypted before upload and
are accompanied by a checksum manifest. Google receives only the encrypted
database artifact.

Remote retention is automatic:

- The seven most recent daily backup sets are retained.
- Four additional weekly recovery points are retained.
- Older Broadcast Tool Pro backup sets are permanently recycled.
- The newest verified recovery point is never removed by capacity recycling.
- Total Drive usage targets 4 GB and may never exceed the configured 5 GB hard
  ceiling as a result of a new Broadcast Tool Pro backup.

## Production Configuration

The default local backup directory is intended only for development. Before
the first commercial deployment, mount a persistent directory that is
independent of the application filesystem and set:

```text
BTP_BACKUP_DIR=/mounted-backup-location/broadcast-tool-pro
BTP_BACKUP_RETENTION_DAYS=14
BTP_GOOGLE_DRIVE_TOKEN=/mounted-data/google-drive/google-drive-token.json
BTP_BACKUP_ENCRYPTION_KEY=/mounted-data/google-drive/backup-encryption.key
BTP_GOOGLE_DRIVE_STATE=/mounted-data/google-drive/google-drive-state.json
BTP_REQUIRE_REMOTE_BACKUP=true
```

The Control Panel must display `External backup location configured` before
commercial launch. If it displays a local-development warning, the backups can
be lost with the application server and are not production-ready.

The local configured directory may be:

- A low-cost persistent disk mounted separately from the application
- A synchronized backup volume
- Another protected filesystem location with independent retention

Google Drive authorization files and the backup encryption key live outside
the repository under the protected user configuration directory. They must
never be committed or copied into the application source.

The Super Admin control panel checks the remote connection on demand, and the
application records a persistent connection check at least once every 24
hours. When `BTP_REQUIRE_REMOTE_BACKUP=true`, a missing, failed, or stale
remote check reports `remote_backup=error` from `/health` so external
monitoring can open an incident.

The encryption key is required for disaster recovery. Keep a protected copy
in the owner's password manager or offline recovery vault. Do not store that
copy in the same Google Drive folder as the encrypted backups.

## Daily Operation

The application checks once per hour whether a backup is due. It creates no
more than one scheduled backup every 24 hours.

Every created backup is:

1. Generated from the live SQLite database using the SQLite backup API.
2. Checked with `PRAGMA integrity_check`.
3. Hashed with SHA-256.
4. Recorded in a manifest.
5. Subject to the configured retention policy.
6. Encrypted locally and uploaded to Google Drive when authorization is
   configured.
7. Verified after upload and recycled according to the remote retention and
   capacity policy.

Super Admins can inspect the latest backup and run an immediate verified backup
from `Control Panel → Backup & Recovery`.

## Recovery Procedure

Restoration is deliberately unavailable through the web interface. This
prevents an account or browser session from overwriting the production
database.

Only restore during a maintenance window:

1. Stop the Broadcast Tool Pro application.
2. Download and decrypt the newest complete Google Drive recovery point:

```text
python -m tools.download_google_drive_backup \
  --destination /protected-recovery-location
```

3. Identify the recovered `.sqlite3` backup and matching `.json` manifest.
4. Run the protected restore tool:

```text
python tools/restore_database.py \
  --database backend/data/broadcast_tool_pro.db \
  --backup /mounted-backup-location/broadcast-tool-pro/backup.sqlite3 \
  --confirm RESTORE_DATABASE
```

5. The tools verify encryption, manifests, checksums, and SQLite integrity.
6. The restore preserves the current database as a timestamped pre-restore
   copy.
7. Start the application.
8. Confirm `/health`, account login, organization access, and recent records.

## Required Recovery Test

At least once before commercial launch, and quarterly afterward:

1. Copy a production-style backup into an isolated environment.
2. Restore it using the documented tool.
3. Start the isolated application.
4. Confirm users, organizations, subscriptions, support requests, and report
   history.
5. Record the date, operator, backup used, result, and recovery time.

A backup is not considered operationally reliable until restoration has been
tested successfully.

The staging recovery drill completed successfully on August 13, 2026. The
latest encrypted Google Drive recovery point was downloaded, decrypted,
checksum-verified, restored into an isolated temporary database, and verified
with 24 tables. The live database was not touched and the temporary recovery
files were removed afterward.
