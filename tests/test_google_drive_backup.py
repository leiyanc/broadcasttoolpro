from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from cryptography.fernet import Fernet

from backend.services.google_drive_backup import (
    DAILY_BACKUPS,
    GoogleDriveBackup,
)
from backend.services import google_drive_backup as drive_module


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


def test_connection_check_is_persisted_and_reloaded(monkeypatch):
    with TemporaryDirectory() as directory:
        root = Path(directory)
        token = root / "token.json"
        key = root / "backup.key"
        state = root / "drive-state.json"
        token.write_text("{}", encoding="utf-8")
        key.write_bytes(Fernet.generate_key())
        backup = GoogleDriveBackup(
            token_path=token,
            key_path=key,
            state_path=state,
        )
        monkeypatch.setattr(backup, "_service", lambda: object())
        monkeypatch.setattr(
            backup,
            "_quota",
            lambda _: {"usage": 100, "limit": 1_000},
        )
        monkeypatch.setattr(backup, "_folder", lambda _: "folder-id")
        monkeypatch.setattr(
            backup,
            "_files",
            lambda _service, _folder_id: [
                {
                    "id": "database",
                    "size": "50",
                    "appProperties": {
                        "backup_id": "backup-1",
                        "kind": "encrypted_database",
                    },
                },
                {
                    "id": "manifest",
                    "size": "10",
                    "appProperties": {
                        "backup_id": "backup-1",
                        "kind": "manifest",
                    },
                },
            ],
        )

        result = backup.check_connection()
        restored = GoogleDriveBackup(
            token_path=token,
            key_path=key,
            state_path=state,
        )

        assert result["status"] == "healthy"
        assert result["complete_backup_sets"] == 1
        assert restored.status()["last_check"] == result
        assert restored.health_status() == "healthy"


def test_missing_credentials_are_reported_without_replacing_key():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        key = root / "backup.key"
        original_key = Fernet.generate_key()
        key.write_bytes(original_key)
        backup = GoogleDriveBackup(
            token_path=root / "missing-token.json",
            key_path=key,
            state_path=root / "drive-state.json",
        )

        result = backup.check_connection()

        assert result["status"] == "failed"
        assert "authorization token" in result["error"]
        assert key.read_bytes() == original_key


def test_expired_credentials_work_with_read_only_render_secret(monkeypatch):
    with TemporaryDirectory() as directory:
        root = Path(directory)
        token = root / "token.json"
        key = root / "backup.key"
        token.write_text("{}", encoding="utf-8")
        key.write_bytes(Fernet.generate_key())
        backup = GoogleDriveBackup(token_path=token, key_path=key)

        class CredentialsStub:
            expired = True
            refresh_token = "refresh-token"
            valid = False

            def refresh(self, _request):
                self.expired = False
                self.valid = True

            def to_json(self):
                return '{"token":"refreshed"}'

        credentials = CredentialsStub()
        monkeypatch.setattr(
            drive_module.Credentials,
            "from_authorized_user_file",
            lambda *_args, **_kwargs: credentials,
        )
        original_write_text = Path.write_text

        def read_only_secret(path, *args, **kwargs):
            if path == token:
                raise PermissionError("read-only secret")
            return original_write_text(path, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", read_only_secret)

        result = backup._credentials()

        assert result is credentials
        assert result.valid is True
