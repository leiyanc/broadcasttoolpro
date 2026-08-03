import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.services.tenant_store import DATA_DIR


DEFAULT_TEMP_RETENTION_HOURS = 24


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StorageCleanup:
    """Removes only expired, application-owned technical working files."""

    def __init__(
        self,
        data_directory: Path = DATA_DIR,
        temporary_directory: Path | None = None,
        retention_hours: int | None = None,
    ):
        configured_directory = os.getenv("BTP_TEMP_DIR")
        self.data_directory = Path(data_directory)
        self.temporary_directory = Path(
            temporary_directory
            or configured_directory
            or self.data_directory / "tmp"
        )
        self.retention_hours = (
            retention_hours
            if retention_hours is not None
            else int(
                os.getenv(
                    "BTP_TEMP_RETENTION_HOURS",
                    str(DEFAULT_TEMP_RETENTION_HOURS),
                )
            )
        )
        if self.retention_hours < 1:
            raise ValueError("Temporary retention must be at least one hour.")
        self._lock = threading.Lock()
        self._last_cleanup_at: str | None = None
        self._last_removed = 0
        self._last_error: str | None = None

    def _expired(self, path: Path, cutoff: datetime) -> bool:
        modified_at = datetime.fromtimestamp(
            path.lstat().st_mtime,
            tz=timezone.utc,
        )
        return modified_at < cutoff

    def _temporary_candidates(self) -> list[Path]:
        if not self.temporary_directory.exists():
            return []
        return [
            path
            for path in self.temporary_directory.rglob("*")
            if path.is_file() or path.is_symlink()
        ]

    def _incomplete_database_candidates(self) -> list[Path]:
        if not self.data_directory.exists():
            return []
        candidates: list[Path] = []
        backup_directory = self.data_directory / "backups"
        if backup_directory.exists():
            candidates.extend(backup_directory.glob(".*.tmp"))
        candidates.extend(self.data_directory.glob("*.restore"))
        return candidates

    def run(self, now: datetime | None = None) -> dict:
        observed_at = now or _utc_now()
        cutoff = observed_at - timedelta(hours=self.retention_hours)
        removed = 0
        with self._lock:
            try:
                candidates = (
                    self._temporary_candidates()
                    + self._incomplete_database_candidates()
                )
                for path in candidates:
                    try:
                        if self._expired(path, cutoff):
                            path.unlink(missing_ok=True)
                            removed += 1
                    except FileNotFoundError:
                        continue

                if self.temporary_directory.exists():
                    directories = sorted(
                        (
                            path
                            for path in self.temporary_directory.rglob("*")
                            if path.is_dir()
                        ),
                        key=lambda path: len(path.parts),
                        reverse=True,
                    )
                    for directory in directories:
                        try:
                            directory.rmdir()
                        except OSError:
                            continue

                self._last_cleanup_at = observed_at.isoformat()
                self._last_removed = removed
                self._last_error = None
            except Exception as exc:
                self._last_error = str(exc)
                raise
        return self.status()

    def status(self) -> dict:
        return {
            "status": "error" if self._last_error else "healthy",
            "temporary_directory": str(self.temporary_directory),
            "retention_hours": self.retention_hours,
            "last_cleanup_at": self._last_cleanup_at,
            "last_removed": self._last_removed,
            "last_error": self._last_error,
        }


storage_cleanup = StorageCleanup()
