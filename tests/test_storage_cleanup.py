import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.services.backup_manager import BackupManager
from backend.services.storage_cleanup import StorageCleanup
from tools.recovery_drill import run_recovery_drill


def _set_age(path: Path, observed_at: datetime, hours: int) -> None:
    timestamp = (observed_at - timedelta(hours=hours)).timestamp()
    os.utime(path, (timestamp, timestamp))


def test_cleanup_removes_only_expired_technical_files():
    with TemporaryDirectory() as directory:
        data_directory = Path(directory) / "data"
        temporary_directory = data_directory / "tmp"
        backup_directory = data_directory / "backups"
        temporary_directory.mkdir(parents=True)
        backup_directory.mkdir(parents=True)
        observed_at = datetime(2026, 8, 3, tzinfo=timezone.utc)

        expired = temporary_directory / "expired.upload"
        recent = temporary_directory / "recent.upload"
        incomplete_backup = backup_directory / ".backup.tmp"
        verified_backup = backup_directory / "verified.sqlite3"
        customer_report = data_directory / "reports" / "report.pdf"
        customer_report.parent.mkdir()
        for path in (
            expired,
            recent,
            incomplete_backup,
            verified_backup,
            customer_report,
        ):
            path.write_bytes(b"content")
        _set_age(expired, observed_at, 25)
        _set_age(recent, observed_at, 1)
        _set_age(incomplete_backup, observed_at, 25)
        _set_age(verified_backup, observed_at, 25)
        _set_age(customer_report, observed_at, 25)

        result = StorageCleanup(
            data_directory=data_directory,
            temporary_directory=temporary_directory,
            retention_hours=24,
        ).run(observed_at)

        assert result["last_removed"] == 2
        assert expired.exists() is False
        assert incomplete_backup.exists() is False
        assert recent.is_file()
        assert verified_backup.is_file()
        assert customer_report.is_file()


def test_recovery_drill_restores_backup_without_live_database():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        database_path = root / "live.db"
        backup_directory = root / "backups"
        with sqlite3.connect(database_path) as connection:
            connection.execute("CREATE TABLE records (id INTEGER PRIMARY KEY)")
            connection.execute("INSERT INTO records DEFAULT VALUES")
        backup = BackupManager(
            database_path=database_path,
            backup_directory=backup_directory,
        ).create_backup()
        assert backup is not None
        before = database_path.read_bytes()

        result = run_recovery_drill(
            backup_directory / backup["filename"]
        )

        assert result["status"] == "passed"
        assert result["integrity"] == "ok"
        assert result["restored_table_count"] == 1
        assert result["pre_restore_copy_created"] is True
        assert result["live_database_touched"] is False
        assert database_path.read_bytes() == before
