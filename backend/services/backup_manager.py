import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.services.tenant_store import DATABASE_PATH


BACKUP_INTERVAL_HOURS = 24
DEFAULT_RETENTION_DAYS = 14


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BackupManager:
    def __init__(
        self,
        database_path: Path = DATABASE_PATH,
        backup_directory: Path | None = None,
        retention_days: int | None = None,
    ):
        configured_directory = os.getenv("BTP_BACKUP_DIR")
        self.database_path = Path(database_path)
        self.backup_directory = Path(
            backup_directory
            or configured_directory
            or self.database_path.parent / "backups"
        )
        self.retention_days = (
            retention_days
            if retention_days is not None
            else int(
                os.getenv(
                    "BTP_BACKUP_RETENTION_DAYS",
                    str(DEFAULT_RETENTION_DAYS),
                )
            )
        )
        self.externally_configured = bool(
            backup_directory or configured_directory
        )
        self._thread_lock = threading.Lock()
        self._last_error: str | None = None

    @property
    def lock_path(self) -> Path:
        return self.backup_directory / ".backup.lock"

    def _acquire_process_lock(self) -> int | None:
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        try:
            return os.open(
                self.lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError:
            try:
                age = (
                    _utc_now().timestamp() - self.lock_path.stat().st_mtime
                )
                if age > 60 * 60:
                    self.lock_path.unlink()
                    return self._acquire_process_lock()
            except FileNotFoundError:
                return self._acquire_process_lock()
            return None

    def _release_process_lock(self, descriptor: int) -> None:
        os.close(descriptor)
        self.lock_path.unlink(missing_ok=True)

    @staticmethod
    def _checksum(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _verify_database(path: Path) -> None:
        with sqlite3.connect(path) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
        if result is None or result[0] != "ok":
            detail = result[0] if result else "No integrity result returned."
            raise RuntimeError(f"Backup integrity check failed: {detail}")

    def _manifest_paths(self) -> list[Path]:
        if not self.backup_directory.exists():
            return []
        return sorted(
            self.backup_directory.glob("broadcast-tool-pro-*.json"),
            reverse=True,
        )

    def _read_manifest(self, path: Path) -> dict[str, Any] | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def latest(self) -> dict[str, Any] | None:
        for path in self._manifest_paths():
            manifest = self._read_manifest(path)
            if manifest:
                return manifest
        return None

    def is_due(self) -> bool:
        latest = self.latest()
        if latest is None:
            return True
        try:
            created_at = datetime.fromisoformat(latest["created_at"])
        except (KeyError, TypeError, ValueError):
            return True
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return _utc_now() - created_at >= timedelta(
            hours=BACKUP_INTERVAL_HOURS
        )

    def create_if_due(self) -> dict[str, Any] | None:
        if not self.is_due():
            return None
        return self.create_backup()

    def create_backup(self) -> dict[str, Any] | None:
        if not self.database_path.exists():
            self._last_error = "The application database does not exist."
            return None
        with self._thread_lock:
            descriptor = self._acquire_process_lock()
            if descriptor is None:
                return None
            try:
                now = _utc_now()
                timestamp = now.strftime("%Y%m%dT%H%M%S%fZ")
                stem = f"broadcast-tool-pro-{timestamp}"
                final_database = self.backup_directory / f"{stem}.sqlite3"
                temporary_database = self.backup_directory / f".{stem}.tmp"
                manifest_path = self.backup_directory / f"{stem}.json"

                with sqlite3.connect(self.database_path) as source:
                    with sqlite3.connect(temporary_database) as destination:
                        source.backup(destination)
                self._verify_database(temporary_database)
                temporary_database.replace(final_database)

                manifest = {
                    "filename": final_database.name,
                    "created_at": now.isoformat(),
                    "size_bytes": final_database.stat().st_size,
                    "sha256": self._checksum(final_database),
                    "integrity": "ok",
                }
                manifest_path.write_text(
                    json.dumps(manifest, indent=2),
                    encoding="utf-8",
                )
                self._last_error = None
                self.prune()
                return manifest
            except Exception as exc:
                self._last_error = str(exc)
                raise
            finally:
                self._release_process_lock(descriptor)

    def prune(self) -> int:
        cutoff = _utc_now() - timedelta(days=self.retention_days)
        removed = 0
        manifests = self._manifest_paths()
        for path in manifests[1:]:
            manifest = self._read_manifest(path)
            if not manifest:
                continue
            try:
                created_at = datetime.fromisoformat(manifest["created_at"])
            except (KeyError, TypeError, ValueError):
                continue
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if created_at >= cutoff:
                continue
            database_file = self.backup_directory / manifest["filename"]
            database_file.unlink(missing_ok=True)
            path.unlink(missing_ok=True)
            removed += 1
        return removed

    def verify_latest(self) -> dict[str, Any] | None:
        manifest = self.latest()
        if manifest is None:
            return None
        database_file = self.backup_directory / manifest["filename"]
        self._verify_database(database_file)
        checksum_matches = (
            self._checksum(database_file) == manifest["sha256"]
        )
        if not checksum_matches:
            raise RuntimeError("The latest backup checksum does not match.")
        return {
            **manifest,
            "checksum_verified": True,
        }

    def status(self) -> dict[str, Any]:
        latest = self.latest()
        state = "healthy"
        if self._last_error:
            state = "error"
        elif latest is None or self.is_due():
            state = "warning"
        return {
            "status": state,
            "latest_backup": latest,
            "retention_days": self.retention_days,
            "automatic_interval_hours": BACKUP_INTERVAL_HOURS,
            "external_storage_configured": self.externally_configured,
            "last_error": self._last_error,
        }


backup_manager = BackupManager()
