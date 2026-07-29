import asyncio
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.services.backup_manager import BackupManager
from backend.main import app, health, lifespan
from tools.restore_database import restore


def _database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT)"
        )
        connection.execute(
            "INSERT INTO records (value) VALUES ('original')"
        )


def test_backup_is_created_verified_and_reported():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        database_path = root / "application.db"
        backup_directory = root / "off-server"
        _database(database_path)
        manager = BackupManager(
            database_path,
            backup_directory,
            retention_days=7,
        )

        backup = manager.create_backup()
        verification = manager.verify_latest()
        status = manager.status()

        assert backup is not None
        assert backup["integrity"] == "ok"
        assert verification is not None
        assert verification["checksum_verified"] is True
        assert status["status"] == "healthy"
        assert status["external_storage_configured"] is True
        assert manager.create_if_due() is None


def test_restore_requires_confirmation_and_preserves_current_database():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        database_path = root / "application.db"
        backup_directory = root / "backups"
        _database(database_path)
        manager = BackupManager(database_path, backup_directory)
        backup = manager.create_backup()
        assert backup is not None
        backup_path = backup_directory / backup["filename"]

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "UPDATE records SET value = 'changed' WHERE id = 1"
            )

        try:
            restore(
                database_path=database_path,
                backup_path=backup_path,
                confirmation="wrong",
            )
            raise AssertionError("Restore should require confirmation.")
        except ValueError:
            pass

        safety_copy = restore(
            database_path=database_path,
            backup_path=backup_path,
            confirmation="RESTORE_DATABASE",
        )
        assert safety_copy.is_file()

        with sqlite3.connect(database_path) as connection:
            value = connection.execute(
                "SELECT value FROM records WHERE id = 1"
            ).fetchone()[0]
        assert value == "original"


def test_application_lifespan_exposes_backup_health():
    async def check():
        async with lifespan(app):
            result = health()
            assert result["status"] == "healthy"
            assert result["backup"] in {"healthy", "warning"}

    asyncio.run(check())
