import argparse
import json
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.restore_database import restore, verify_database


def run_recovery_drill(backup_path: Path) -> dict:
    """Restores into an isolated temporary database, never the live path."""
    backup_path = Path(backup_path).resolve()
    with TemporaryDirectory(prefix="btp-recovery-drill-") as directory:
        drill_root = Path(directory)
        isolated_database = drill_root / "restored.db"
        with sqlite3.connect(isolated_database) as connection:
            connection.execute(
                "CREATE TABLE recovery_drill_placeholder (id INTEGER)"
            )

        safety_copy = restore(
            database_path=isolated_database,
            backup_path=backup_path,
            confirmation="RESTORE_DATABASE",
        )
        verify_database(isolated_database)
        with sqlite3.connect(isolated_database) as connection:
            table_count = connection.execute(
                """
                SELECT COUNT(*) FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                """
            ).fetchone()[0]

        return {
            "status": "passed",
            "backup_filename": backup_path.name,
            "integrity": "ok",
            "restored_table_count": table_count,
            "pre_restore_copy_created": safety_copy.is_file(),
            "live_database_touched": False,
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run an isolated restoration drill against a verified backup."
        )
    )
    parser.add_argument("--backup", required=True, type=Path)
    arguments = parser.parse_args()
    print(json.dumps(run_recovery_drill(arguments.backup), indent=2))


if __name__ == "__main__":
    main()
