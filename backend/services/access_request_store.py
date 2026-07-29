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
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (
                        status IN ('pending', 'approved', 'rejected')
                    ),
                    assigned_plan TEXT CHECK (
                        assigned_plan IN ('professional', 'enterprise')
                    ),
                    organization_id TEXT,
                    user_id TEXT,
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

    def create(
        self,
        *,
        organization_name: str,
        contact_name: str,
        email: str,
        message: str | None,
    ) -> dict:
        email = email.strip().lower()
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            existing_user = connection.execute(
                "SELECT 1 FROM users WHERE email = ?",
                (email,),
            ).fetchone()
            if existing_user:
                raise ValueError(
                    "An account with this email address already exists."
                )
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
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    request_id,
                    organization_name.strip(),
                    contact_name.strip(),
                    email,
                    message.strip() if message else None,
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
        return dict(row)

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
        return [dict(row) for row in rows]

    def approve(
        self,
        request_id: str,
        *,
        plan: str,
        organization_id: str,
        user_id: str,
    ) -> dict:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE access_requests
                SET status = 'approved', assigned_plan = ?,
                    organization_id = ?, user_id = ?, updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (
                    plan,
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
