# Backup and Recovery Runbook

## Purpose

Broadcast Tool Pro creates a verified SQLite backup every 24 hours while the
application is running. A Super Admin can also create and verify a backup from
the Control Panel.

Each backup consists of:

- A `.sqlite3` database snapshot produced through SQLite's online backup API
- A `.json` manifest containing its creation time, size, SHA-256 checksum, and
  integrity result

The default retention period is 14 days.

## Production Configuration

The default local backup directory is intended only for development. Before
the first commercial deployment, mount a persistent directory that is
independent of the application filesystem and set:

```text
BTP_BACKUP_DIR=/mounted-backup-location/broadcast-tool-pro
BTP_BACKUP_RETENTION_DAYS=14
```

The Control Panel must display `External backup location configured` before
commercial launch. If it displays a local-development warning, the backups can
be lost with the application server and are not production-ready.

No storage vendor is required. The configured directory may be:

- A low-cost persistent disk mounted separately from the application
- A synchronized backup volume
- Another protected filesystem location with independent retention

## Daily Operation

The application checks once per hour whether a backup is due. It creates no
more than one scheduled backup every 24 hours.

Every created backup is:

1. Generated from the live SQLite database using the SQLite backup API.
2. Checked with `PRAGMA integrity_check`.
3. Hashed with SHA-256.
4. Recorded in a manifest.
5. Subject to the configured retention policy.

Super Admins can inspect the latest backup and run an immediate verified backup
from `Control Panel → Backup & Recovery`.

## Recovery Procedure

Restoration is deliberately unavailable through the web interface. This
prevents an account or browser session from overwriting the production
database.

Only restore during a maintenance window:

1. Stop the Broadcast Tool Pro application.
2. Identify the `.sqlite3` backup and its matching `.json` manifest.
3. Run the protected restore tool:

```text
python tools/restore_database.py \
  --database backend/data/broadcast_tool_pro.db \
  --backup /mounted-backup-location/broadcast-tool-pro/backup.sqlite3 \
  --confirm RESTORE_DATABASE
```

4. The tool verifies the manifest, checksum, and SQLite integrity.
5. It preserves the current database as a timestamped pre-restore copy.
6. Start the application.
7. Confirm `/health`, account login, organization access, and recent records.

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
