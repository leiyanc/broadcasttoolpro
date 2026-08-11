import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.services.tenant_store import DATABASE_PATH


class AccessRequestStore:
    def __init__(self, database_path: Path = DATABASE_PATH):
        self.database_path = database_path

    def _connection(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS access_requests (
                    id TEXT PRIMARY KEY,
                    organization_name TEXT NOT NULL,
                    contact_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    message TEXT,
                    requested_plan TEXT NOT NULL DEFAULT 'professional' CHECK (
                        requested_plan IN (
                            'programming_suite', 'professional', 'enterprise'
                        )
                    ),
                    include_stream_monitoring INTEGER NOT NULL DEFAULT 0,
                    billing_cycle TEXT NOT NULL DEFAULT 'monthly' CHECK (
                        billing_cycle IN ('monthly')
                    ),
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (
                        status IN ('pending', 'approved', 'rejected')
                    ),
                    assigned_plan TEXT CHECK (
                        assigned_plan IN (
                            'programming_suite', 'professional', 'enterprise'
                        )
                    ),
                    assigned_stream_monitoring INTEGER,
                    organization_id TEXT,
                    user_id TEXT,
                    existing_account INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (organization_id)
                        REFERENCES organizations(id) ON DELETE SET NULL,
                    FOREIGN KEY (user_id)
                        REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_access_requests_status
                    ON access_requests(status, created_at);
            """)
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(access_requests)"
                ).fetchall()
            }
            if "existing_account" not in columns:
                connection.execute(
                    """
                    ALTER TABLE access_requests
                    ADD COLUMN existing_account INTEGER NOT NULL DEFAULT 0
                    """
                )
            migrations = {
                "requested_plan": (
                    "ALTER TABLE access_requests ADD COLUMN "
                    "requested_plan TEXT NOT NULL DEFAULT 'professional'"
                ),
                "include_stream_monitoring": (
                    "ALTER TABLE access_requests ADD COLUMN "
                    "include_stream_monitoring INTEGER NOT NULL DEFAULT 0"
                ),
                "billing_cycle": (
                    "ALTER TABLE access_requests ADD COLUMN "
                    "billing_cycle TEXT NOT NULL DEFAULT 'monthly'"
                ),
                "assigned_stream_monitoring": (
                    "ALTER TABLE access_requests ADD COLUMN "
                    "assigned_stream_monitoring INTEGER"
                ),
            }
            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)

            table_sql = connection.execute(
                """
                SELECT sql FROM sqlite_master
                WHERE type = 'table' AND name = 'access_requests'
                """
            ).fetchone()["sql"]
            if "'programming_suite', 'professional', 'enterprise'" not in table_sql:
                connection.executescript("""
                    DROP INDEX IF EXISTS idx_access_requests_status;
                    CREATE TABLE access_requests_v2 (
                        id TEXT PRIMARY KEY,
                        organization_name TEXT NOT NULL,
                        contact_name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        message TEXT,
                        requested_plan TEXT NOT NULL DEFAULT 'professional',
                        include_stream_monitoring INTEGER NOT NULL DEFAULT 0,
                        billing_cycle TEXT NOT NULL DEFAULT 'monthly',
                        status TEXT NOT NULL DEFAULT 'pending' CHECK (
                            status IN ('pending', 'approved', 'rejected')
                        ),
                        assigned_plan TEXT CHECK (
                            assigned_plan IN (
                                'programming_suite', 'professional', 'enterprise'
                            )
                        ),
                        assigned_stream_monitoring INTEGER,
                        organization_id TEXT,
                        user_id TEXT,
                        existing_account INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        FOREIGN KEY (organization_id)
                            REFERENCES organizations(id) ON DELETE SET NULL,
                        FOREIGN KEY (user_id)
                            REFERENCES users(id) ON DELETE SET NULL
                    );
                    INSERT INTO access_requests_v2 (
                        id, organization_name, contact_name, email, message,
                        requested_plan, include_stream_monitoring, billing_cycle,
                        status, assigned_plan, assigned_stream_monitoring,
                        organization_id, user_id,
                        existing_account, created_at, updated_at
                    )
                    SELECT
                        id, organization_name, contact_name, email, message,
                        requested_plan, include_stream_monitoring, billing_cycle,
                        status, assigned_plan, assigned_stream_monitoring,
                        organization_id, user_id,
                        existing_account, created_at, updated_at
                    FROM access_requests;
                    DROP TABLE access_requests;
                    ALTER TABLE access_requests_v2 RENAME TO access_requests;
                    CREATE INDEX idx_access_requests_status
                        ON access_requests(status, created_at);
                """)

    def create(
        self,
        *,
        organization_name: str,
        contact_name: str,
        email: str,
        requested_plan: str = "professional",
        include_stream_monitoring: bool = False,
        billing_cycle: str = "monthly",
        message: str | None = None,
    ) -> dict:
        email = email.strip().lower()
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            existing_user = connection.execute(
                "SELECT 1 FROM users WHERE email = ?",
                (email,),
            ).fetchone()
            pending = connection.execute(
                """
                SELECT 1 FROM access_requests
                WHERE email = ? AND status = 'pending'
                """,
                (email,),
            ).fetchone()
            if pending:
                raise ValueError(
                    "An access request for this email is already pending."
                )
            request_id = f"REQ-{uuid4().hex[:10].upper()}"
            connection.execute(
                """
                INSERT INTO access_requests (
                    id, organization_name, contact_name, email, message,
                    requested_plan, include_stream_monitoring, billing_cycle,
                    status, existing_account, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                """,
                (
                    request_id,
                    organization_name.strip(),
                    contact_name.strip(),
                    email,
                    message.strip() if message else None,
                    requested_plan,
                    int(include_stream_monitoring),
                    billing_cycle,
                    int(bool(existing_user)),
                    now,
                    now,
                ),
            )
        return self.get(request_id)

    def get(self, request_id: str) -> dict:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM access_requests WHERE id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise KeyError("Access request not found.")
        result = dict(row)
        result["existing_account"] = bool(result["existing_account"])
        result["include_stream_monitoring"] = bool(
            result["include_stream_monitoring"]
        )
        if result.get("assigned_stream_monitoring") is not None:
            result["assigned_stream_monitoring"] = bool(
                result["assigned_stream_monitoring"]
            )
        return result

    def list(self, limit: int = 100) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM access_requests
                ORDER BY
                    CASE status WHEN 'pending' THEN 0 ELSE 1 END,
                    created_at DESC
                LIMIT ?
                """,
                (min(max(limit, 1), 500),),
            ).fetchall()
        results = []
        for row in rows:
            result = dict(row)
            result["existing_account"] = bool(result["existing_account"])
            result["include_stream_monitoring"] = bool(
                result["include_stream_monitoring"]
            )
            if result.get("assigned_stream_monitoring") is not None:
                result["assigned_stream_monitoring"] = bool(
                    result["assigned_stream_monitoring"]
                )
            results.append(result)
        return results

    def approved_for_organization(
        self,
        organization_id: str,
    ) -> dict | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM access_requests
                WHERE organization_id = ? AND status = 'approved'
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (organization_id,),
            ).fetchone()
        return self.get(row["id"]) if row else None

    def approve(
        self,
        request_id: str,
        *,
        plan: str,
        organization_id: str,
        user_id: str,
        include_stream_monitoring: bool = False,
    ) -> dict:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE access_requests
                SET status = 'approved', assigned_plan = ?,
                    assigned_stream_monitoring = ?,
                    organization_id = ?, user_id = ?, updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (
                    plan,
                    int(include_stream_monitoring),
                    organization_id,
                    user_id,
                    datetime.now(timezone.utc).isoformat(),
                    request_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError(
                    "Only a pending access request can be approved."
                )
        return self.get(request_id)

    def reject(self, request_id: str) -> dict:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE access_requests
                SET status = 'rejected', updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (datetime.now(timezone.utc).isoformat(), request_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(
                    "Only a pending access request can be rejected."
                )
        return self.get(request_id)


access_request_store = AccessRequestStore()
access_request_store.initialize()
