import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.services.tenant_store import DATA_DIR, DATABASE_PATH

REPORTS_DIR = DATA_DIR / "reports"


def _connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS report_history (
            id TEXT PRIMARY KEY,
            report_type TEXT NOT NULL,
            client_name TEXT,
            channel_name TEXT NOT NULL,
            product TEXT,
            agency TEXT,
            asset_ids TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            output_format TEXT NOT NULL,
            filename TEXT NOT NULL,
            media_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            organization_id TEXT,
            workspace_id TEXT,
            created_by TEXT
        )
    """)
    return connection


def record_report(
    *,
    report_type: str,
    client_name: str | None,
    channel_name: str,
    product: str | None,
    agency: str | None,
    asset_ids: list[str],
    start_date: str | None,
    end_date: str | None,
    output_format: str,
    filename: str,
    media_type: str,
    content: bytes,
    organization_id: str | None = None,
    workspace_id: str | None = None,
    created_by: str | None = None,
) -> str:
    report_id = str(uuid4())
    extension = Path(filename).suffix.lower()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = REPORTS_DIR / f"{report_id}{extension}"
    file_path.write_bytes(content)
    created_at = datetime.now(timezone.utc).isoformat()

    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO report_history (
                id, report_type, client_name, channel_name, product,
                agency, asset_ids, start_date, end_date, output_format,
                filename, media_type, file_path, created_at, created_by,
                organization_id, workspace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                report_type,
                client_name,
                channel_name,
                product,
                agency,
                json.dumps(sorted(set(asset_ids))),
                start_date,
                end_date,
                output_format,
                filename,
                media_type,
                str(file_path),
                created_at,
                created_by,
                organization_id,
                workspace_id,
            ),
        )
    return report_id


def list_reports(organization_id: str, limit: int = 100) -> list[dict]:
    safe_limit = min(max(limit, 1), 500)
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM report_history
            WHERE organization_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (organization_id, safe_limit),
        ).fetchall()

    private_fields = {
        "file_path",
        "organization_id",
        "workspace_id",
        "created_by",
    }
    return [
        {
            **{
                key: value
                for key, value in dict(row).items()
                if key not in private_fields
            },
            "asset_ids": json.loads(row["asset_ids"]),
        }
        for row in rows
    ]


def get_report(report_id: str, organization_id: str) -> dict | None:
    with _connection() as connection:
        row = connection.execute(
            """
            SELECT * FROM report_history
            WHERE id = ? AND organization_id = ?
            """,
            (report_id, organization_id),
        ).fetchone()
    if row is None:
        return None

    result = dict(row)
    result["asset_ids"] = json.loads(result["asset_ids"])
    return result
