import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


CONFIRMATION = "RESTORE_DATABASE"


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()
    if result is None or result[0] != "ok":
        raise RuntimeError("The backup database failed its integrity check.")


def restore(
    *,
    database_path: Path,
    backup_path: Path,
    confirmation: str,
) -> Path:
    if confirmation != CONFIRMATION:
        raise ValueError(
            f'Confirmation must be exactly "{CONFIRMATION}".'
        )
    if not backup_path.is_file():
        raise FileNotFoundError("The selected backup file does not exist.")
    manifest_path = backup_path.with_suffix(".json")
    if not manifest_path.is_file():
        raise FileNotFoundError("The backup manifest does not exist.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("filename") != backup_path.name:
        raise RuntimeError("The backup manifest filename does not match.")
    if checksum(backup_path) != manifest.get("sha256"):
        raise RuntimeError("The backup checksum does not match its manifest.")
    verify_database(backup_path)

    database_path.parent.mkdir(parents=True, exist_ok=True)
    safety_copy = database_path.with_name(
        f"{database_path.stem}-before-restore-"
        f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
        f"{database_path.suffix}"
    )
    if database_path.exists():
        shutil.copy2(database_path, safety_copy)

    temporary_path = database_path.with_suffix(
        f"{database_path.suffix}.restore"
    )
    shutil.copy2(backup_path, temporary_path)
    verify_database(temporary_path)
    temporary_path.replace(database_path)
    return safety_copy


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Restore a verified Broadcast Tool Pro SQLite backup. "
            "The application must be stopped first."
        )
    )
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--backup", required=True, type=Path)
    parser.add_argument("--confirm", required=True)
    arguments = parser.parse_args()
    safety_copy = restore(
        database_path=arguments.database,
        backup_path=arguments.backup,
        confirmation=arguments.confirm,
    )
    print(f"Restore completed. Pre-restore copy: {safety_copy}")


if __name__ == "__main__":
    main()
