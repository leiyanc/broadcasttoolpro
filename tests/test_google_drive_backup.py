from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from cryptography.fernet import Fernet

from backend.services.google_drive_backup import (
    DAILY_BACKUPS,
    GoogleDriveBackup,
)


def test_backup_encryption_key_round_trip():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        token = root / "token.json"
        key = root / "backup.key"
        token.write_text("{}", encoding="utf-8")
        key.write_bytes(Fernet.generate_key())
        backup = GoogleDriveBackup(token_path=token, key_path=key)
        content = b"verified SQLite backup"

        encrypted = backup._fernet().encrypt(content)

        assert encrypted != content
        assert backup._fernet().decrypt(encrypted) == content
        assert backup.is_authorized() is True


def test_retention_keeps_recent_daily_and_older_weekly_sets():
    now = datetime.now(timezone.utc)
    groups = [
        {
            "backup_id": f"backup-{day}",
            "created_at": (now - timedelta(days=day)).isoformat(),
            "files": [],
            "size": 1,
        }
        for day in range(45)
    ]

    retained = GoogleDriveBackup.retention_ids(groups)

    assert {
        f"backup-{day}" for day in range(DAILY_BACKUPS)
    }.issubset(retained)
    assert len(retained) <= DAILY_BACKUPS + 4
