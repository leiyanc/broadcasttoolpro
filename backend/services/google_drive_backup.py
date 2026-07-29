import hashlib
import io
import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
DEFAULT_CONFIG_DIRECTORY = Path.home() / ".config" / "broadcasttoolpro"
DEFAULT_TOKEN_PATH = DEFAULT_CONFIG_DIRECTORY / "google-drive-token.json"
DEFAULT_KEY_PATH = DEFAULT_CONFIG_DIRECTORY / "backup-encryption.key"
DEFAULT_FOLDER_NAME = "Broadcast Tool Pro Backups"
TARGET_TOTAL_USAGE_BYTES = 4_000_000_000
HARD_TOTAL_USAGE_BYTES = 5_000_000_000
DAILY_BACKUPS = 7
WEEKLY_BACKUPS = 4


class GoogleDriveBackup:
    def __init__(
        self,
        *,
        token_path: Path | None = None,
        key_path: Path | None = None,
        folder_name: str | None = None,
    ):
        self.token_path = Path(
            token_path
            or os.getenv("BTP_GOOGLE_DRIVE_TOKEN")
            or DEFAULT_TOKEN_PATH
        )
        self.key_path = Path(
            key_path
            or os.getenv("BTP_BACKUP_ENCRYPTION_KEY")
            or DEFAULT_KEY_PATH
        )
        self.folder_name = (
            folder_name
            or os.getenv("BTP_GOOGLE_DRIVE_FOLDER")
            or DEFAULT_FOLDER_NAME
        )
        self._last_error: str | None = None
        self._last_upload: dict[str, Any] | None = None

    def is_authorized(self) -> bool:
        return self.token_path.is_file() and self.key_path.is_file()

    def _credentials(self) -> Credentials:
        if not self.token_path.is_file():
            raise RuntimeError("Google Drive authorization is not configured.")
        credentials = Credentials.from_authorized_user_file(
            self.token_path,
            [DRIVE_SCOPE],
        )
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            self.token_path.write_text(
                credentials.to_json(),
                encoding="utf-8",
            )
            self.token_path.chmod(0o600)
        if not credentials.valid:
            raise RuntimeError("Google Drive authorization is invalid.")
        return credentials

    def _service(self):
        return build(
            "drive",
            "v3",
            credentials=self._credentials(),
            cache_discovery=False,
        )

    def _fernet(self) -> Fernet:
        if not self.key_path.is_file():
            raise RuntimeError("The backup encryption key is not configured.")
        return Fernet(self.key_path.read_bytes().strip())

    @staticmethod
    def _verify_database(path: Path) -> None:
        with sqlite3.connect(path) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
        if result is None or result[0] != "ok":
            raise RuntimeError(
                "The downloaded backup failed its integrity check."
            )

    @staticmethod
    def _md5(path: Path) -> str:
        digest = hashlib.md5(usedforsecurity=False)
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _quota(self, service) -> dict[str, int]:
        result = service.about().get(fields="storageQuota").execute()
        quota = result.get("storageQuota", {})
        return {
            "usage": int(quota.get("usage", 0)),
            "limit": int(quota.get("limit", 0)),
        }

    def _folder(self, service) -> str:
        result = service.files().list(
            q=(
                "mimeType = 'application/vnd.google-apps.folder' "
                "and trashed = false "
                "and appProperties has { key='btp_backup_folder' "
                "and value='true' }"
            ),
            spaces="drive",
            fields="files(id,name)",
            pageSize=10,
        ).execute()
        folders = result.get("files", [])
        if folders:
            return folders[0]["id"]
        folder = service.files().create(
            body={
                "name": self.folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "appProperties": {"btp_backup_folder": "true"},
            },
            fields="id",
        ).execute()
        return folder["id"]

    def _files(self, service, folder_id: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        page_token = None
        while True:
            response = service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                spaces="drive",
                fields=(
                    "nextPageToken,files("
                    "id,name,size,createdTime,md5Checksum,appProperties)"
                ),
                pageSize=1000,
                pageToken=page_token,
            ).execute()
            result.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                return result

    @staticmethod
    def _backup_groups(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"files": [], "size": 0}
        )
        for file in files:
            properties = file.get("appProperties") or {}
            backup_id = properties.get("backup_id")
            if not backup_id:
                continue
            group = groups[backup_id]
            group["backup_id"] = backup_id
            group["created_at"] = properties.get(
                "created_at",
                file.get("createdTime"),
            )
            group["files"].append(file)
            group["size"] += int(file.get("size", 0))
        return sorted(
            groups.values(),
            key=lambda item: item.get("created_at") or "",
            reverse=True,
        )

    @staticmethod
    def retention_ids(groups: list[dict[str, Any]]) -> set[str]:
        keep = {
            group["backup_id"]
            for group in groups[:DAILY_BACKUPS]
        }
        weeks: set[tuple[int, int]] = set()
        for group in groups[DAILY_BACKUPS:]:
            try:
                created_at = datetime.fromisoformat(group["created_at"])
            except (TypeError, ValueError):
                continue
            week = created_at.isocalendar()[:2]
            if week in weeks:
                continue
            weeks.add(week)
            keep.add(group["backup_id"])
            if len(weeks) >= WEEKLY_BACKUPS:
                break
        return keep

    @staticmethod
    def _delete_group(service, group: dict[str, Any]) -> int:
        removed = 0
        for file in group["files"]:
            service.files().delete(fileId=file["id"]).execute()
            removed += int(file.get("size", 0))
        return removed

    def _recycle(
        self,
        service,
        folder_id: str,
        *,
        incoming_bytes: int = 0,
    ) -> dict[str, int]:
        files = self._files(service, folder_id)
        groups = self._backup_groups(files)
        keep_ids = self.retention_ids(groups)
        quota = self._quota(service)
        estimated_usage = quota["usage"]
        deleted = 0

        for group in reversed(groups):
            if group["backup_id"] in keep_ids:
                continue
            estimated_usage -= self._delete_group(service, group)
            deleted += 1

        remaining = [
            group for group in groups if group["backup_id"] in keep_ids
        ]
        for group in reversed(remaining[1:]):
            if estimated_usage + incoming_bytes <= TARGET_TOTAL_USAGE_BYTES:
                break
            estimated_usage -= self._delete_group(service, group)
            deleted += 1

        if estimated_usage + incoming_bytes > HARD_TOTAL_USAGE_BYTES:
            raise RuntimeError(
                "Google Drive does not have enough protected backup capacity."
            )
        return {
            "deleted_backup_sets": deleted,
            "estimated_usage_bytes": max(0, estimated_usage),
        }

    def upload(
        self,
        *,
        backup_directory: Path,
        manifest: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.is_authorized():
            raise RuntimeError("Google Drive backup is not authorized.")
        source = Path(backup_directory) / manifest["filename"]
        if not source.is_file():
            raise FileNotFoundError("The verified local backup is missing.")

        encrypted_content = self._fernet().encrypt(source.read_bytes())
        backup_id = source.stem
        created_at = manifest["created_at"]
        encrypted_name = f"{source.name}.encrypted"
        remote_manifest_name = f"{backup_id}.drive.json"
        with NamedTemporaryFile(suffix=".encrypted") as encrypted_file:
            encrypted_file.write(encrypted_content)
            encrypted_file.flush()
            encrypted_path = Path(encrypted_file.name)
            remote_manifest = {
                **manifest,
                "backup_id": backup_id,
                "encrypted_filename": encrypted_name,
                "encryption": "Fernet AES-128-CBC + HMAC-SHA256",
                "encrypted_sha256": hashlib.sha256(
                    encrypted_content
                ).hexdigest(),
            }
            manifest_bytes = json.dumps(
                remote_manifest,
                indent=2,
            ).encode("utf-8")

            service = self._service()
            folder_id = self._folder(service)
            recycle = self._recycle(
                service,
                folder_id,
                incoming_bytes=len(encrypted_content) + len(manifest_bytes),
            )
            properties = {
                "btp_backup": "true",
                "backup_id": backup_id,
                "created_at": created_at,
            }
            uploaded = service.files().create(
                body={
                    "name": encrypted_name,
                    "parents": [folder_id],
                    "appProperties": {
                        **properties,
                        "kind": "encrypted_database",
                    },
                },
                media_body=MediaFileUpload(
                    encrypted_path,
                    mimetype="application/octet-stream",
                    resumable=False,
                ),
                fields="id,name,size,md5Checksum",
            ).execute()
            if uploaded.get("md5Checksum") != self._md5(encrypted_path):
                service.files().delete(fileId=uploaded["id"]).execute()
                raise RuntimeError("Google Drive upload verification failed.")

            with NamedTemporaryFile(suffix=".json") as manifest_file:
                manifest_file.write(manifest_bytes)
                manifest_file.flush()
                service.files().create(
                    body={
                        "name": remote_manifest_name,
                        "parents": [folder_id],
                        "appProperties": {
                            **properties,
                            "kind": "manifest",
                        },
                    },
                    media_body=MediaFileUpload(
                        manifest_file.name,
                        mimetype="application/json",
                        resumable=False,
                    ),
                    fields="id",
                ).execute()

            post_upload_recycle = self._recycle(service, folder_id)
            quota = self._quota(service)
            result = {
                "status": "uploaded",
                "folder_name": self.folder_name,
                "filename": encrypted_name,
                "uploaded_bytes": int(uploaded.get("size", 0)),
                "drive_usage_bytes": quota["usage"],
                "target_usage_bytes": TARGET_TOTAL_USAGE_BYTES,
                "hard_limit_bytes": HARD_TOTAL_USAGE_BYTES,
                "deleted_backup_sets": (
                    recycle["deleted_backup_sets"]
                    + post_upload_recycle["deleted_backup_sets"]
                ),
            }
            self._last_upload = result
            self._last_error = None
            return result

    def upload_safely(
        self,
        *,
        backup_directory: Path,
        manifest: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            return self.upload(
                backup_directory=backup_directory,
                manifest=manifest,
            )
        except Exception as exc:
            self._last_error = str(exc)
            return {
                "status": "failed",
                "error": self._last_error,
            }

    @staticmethod
    def _download_file(service, file_id: str) -> bytes:
        stream = io.BytesIO()
        request = service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(stream, request)
        complete = False
        while not complete:
            _, complete = downloader.next_chunk()
        return stream.getvalue()

    def download_latest(self, destination: Path) -> dict[str, Any]:
        if not self.is_authorized():
            raise RuntimeError("Google Drive backup is not authorized.")
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        service = self._service()
        folder_id = self._folder(service)
        groups = self._backup_groups(self._files(service, folder_id))
        for group in groups:
            by_kind = {
                (item.get("appProperties") or {}).get("kind"): item
                for item in group["files"]
            }
            encrypted = by_kind.get("encrypted_database")
            manifest_file = by_kind.get("manifest")
            if encrypted and manifest_file:
                break
        else:
            raise RuntimeError(
                "No complete Google Drive backup set is available."
            )

        manifest_bytes = self._download_file(
            service,
            manifest_file["id"],
        )
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        encrypted_bytes = self._download_file(service, encrypted["id"])
        if hashlib.sha256(encrypted_bytes).hexdigest() != manifest.get(
            "encrypted_sha256"
        ):
            raise RuntimeError(
                "The encrypted Google Drive backup checksum does not match."
            )
        database_bytes = self._fernet().decrypt(encrypted_bytes)
        if hashlib.sha256(database_bytes).hexdigest() != manifest.get(
            "sha256"
        ):
            raise RuntimeError(
                "The decrypted Google Drive backup checksum does not match."
            )

        database_path = destination / manifest["filename"]
        manifest_path = database_path.with_suffix(".json")
        database_path.write_bytes(database_bytes)
        database_path.chmod(0o600)
        self._verify_database(database_path)
        local_manifest = {
            key: manifest[key]
            for key in (
                "filename",
                "created_at",
                "size_bytes",
                "sha256",
                "integrity",
            )
        }
        manifest_path.write_text(
            json.dumps(local_manifest, indent=2),
            encoding="utf-8",
        )
        manifest_path.chmod(0o600)
        return {
            "status": "downloaded_and_verified",
            "database_path": str(database_path),
            "manifest_path": str(manifest_path),
            "created_at": manifest["created_at"],
        }

    def status(self) -> dict[str, Any]:
        result = {
            "authorized": self.is_authorized(),
            "folder_name": self.folder_name,
            "target_usage_bytes": TARGET_TOTAL_USAGE_BYTES,
            "hard_limit_bytes": HARD_TOTAL_USAGE_BYTES,
            "last_upload": self._last_upload,
            "last_error": self._last_error,
        }
        if not self.is_authorized():
            return result
        try:
            quota = self._quota(self._service())
            result["drive_usage_bytes"] = quota["usage"]
            result["drive_limit_bytes"] = quota["limit"]
        except Exception as exc:
            self._last_error = str(exc)
            result["last_error"] = self._last_error
        return result


google_drive_backup = GoogleDriveBackup()
