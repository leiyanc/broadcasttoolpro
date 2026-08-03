import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.services.tenant_store import DATABASE_PATH


class AdminStore:
    def __init__(self, database_path: Path = DATABASE_PATH):
        self.database_path = database_path

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT,
                    module TEXT NOT NULL,
                    severity TEXT NOT NULL CHECK (
                        severity IN ('info', 'warning', 'critical')
                    ),
                    status TEXT NOT NULL DEFAULT 'open' CHECK (
                        status IN ('open', 'investigating', 'resolved')
                    ),
                    summary TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    FOREIGN KEY (organization_id)
                        REFERENCES organizations(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_incidents_status
                    ON incidents(status, created_at);
            """)
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(incidents)"
                ).fetchall()
            }
            migrations = {
                "reporter_user_id": "TEXT",
                "category": "TEXT",
                "priority": "TEXT",
                "request_type": "TEXT",
                "error_message": "TEXT",
                "resolution": "TEXT",
            }
            for column, definition in migrations.items():
                if column not in columns:
                    connection.execute(
                        f"ALTER TABLE incidents "
                        f"ADD COLUMN {column} {definition}"
                    )
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS incident_messages (
                    id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    author_user_id TEXT NOT NULL,
                    visibility TEXT NOT NULL CHECK (
                        visibility IN ('customer', 'internal')
                    ),
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (incident_id)
                        REFERENCES incidents(id) ON DELETE CASCADE,
                    FOREIGN KEY (author_user_id)
                        REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS incident_activity (
                    id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    actor_user_id TEXT,
                    event_type TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (incident_id)
                        REFERENCES incidents(id) ON DELETE CASCADE,
                    FOREIGN KEY (actor_user_id)
                        REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_incident_messages_incident
                    ON incident_messages(incident_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_incident_activity_incident
                    ON incident_activity(incident_id, created_at);
            """)

    def overview(self) -> dict:
        with self._connection() as connection:
            organizations = connection.execute(
                "SELECT COUNT(*) FROM organizations"
            ).fetchone()[0]
            active_organizations = connection.execute(
                """
                SELECT COUNT(*) FROM organizations
                WHERE status = 'active'
                """
            ).fetchone()[0]
            users = connection.execute(
                "SELECT COUNT(*) FROM users WHERE status = 'active'"
            ).fetchone()[0]
            channels = connection.execute(
                "SELECT COUNT(*) FROM channels WHERE active = 1"
            ).fetchone()[0]
            open_incidents = connection.execute(
                """
                SELECT COUNT(*) FROM incidents
                WHERE status != 'resolved'
                """
            ).fetchone()[0]
        return {
            "organizations": organizations,
            "active_organizations": active_organizations,
            "users": users,
            "channels": channels,
            "open_incidents": open_incidents,
        }

    def organizations(self) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute("""
                SELECT organizations.*,
                    COUNT(DISTINCT workspaces.id) AS workspace_count,
                    COUNT(DISTINCT channels.id) AS channel_count,
                    COUNT(DISTINCT organization_memberships.user_id)
                        AS member_count,
                    (
                        SELECT users.display_name
                        FROM organization_memberships AS owner_membership
                        JOIN users
                          ON users.id = owner_membership.user_id
                        WHERE owner_membership.organization_id =
                              organizations.id
                        ORDER BY
                            CASE owner_membership.role
                                WHEN 'owner' THEN 0 ELSE 1
                            END,
                            owner_membership.created_at
                        LIMIT 1
                    ) AS owner_name,
                    (
                        SELECT users.email
                        FROM organization_memberships AS owner_membership
                        JOIN users
                          ON users.id = owner_membership.user_id
                        WHERE owner_membership.organization_id =
                              organizations.id
                        ORDER BY
                            CASE owner_membership.role
                                WHEN 'owner' THEN 0 ELSE 1
                            END,
                            owner_membership.created_at
                        LIMIT 1
                    ) AS owner_email
                FROM organizations
                LEFT JOIN workspaces
                    ON workspaces.organization_id = organizations.id
                LEFT JOIN channels
                    ON channels.workspace_id = workspaces.id
                LEFT JOIN organization_memberships
                    ON organization_memberships.organization_id =
                       organizations.id
                GROUP BY organizations.id
                ORDER BY organizations.created_at DESC
            """).fetchall()
        return [dict(row) for row in rows]

    def update_organization(
        self,
        organization_id: str,
        *,
        plan: str | None,
        status: str | None,
    ) -> dict:
        assignments = []
        values = []
        if plan is not None:
            assignments.append("plan = ?")
            values.append(plan)
        if status is not None:
            assignments.append("status = ?")
            values.append(status)
        if not assignments:
            raise ValueError("At least one organization field is required.")
        assignments.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(organization_id)
        with self._connection() as connection:
            cursor = connection.execute(
                f"""
                UPDATE organizations
                SET {", ".join(assignments)}
                WHERE id = ?
                """,
                values,
            )
            if cursor.rowcount == 0:
                raise KeyError("Organization not found.")
            row = connection.execute(
                "SELECT * FROM organizations WHERE id = ?",
                (organization_id,),
            ).fetchone()
        return dict(row)

    def record_incident(
        self,
        *,
        organization_id: str | None,
        reporter_user_id: str | None = None,
        module: str,
        category: str | None = None,
        severity: str,
        priority: str | None = None,
        request_type: str | None = None,
        summary: str,
        details: str | None = None,
        error_message: str | None = None,
    ) -> str:
        incident_id = f"INC-{datetime.now():%Y%m%d}-{uuid4().hex[:8].upper()}"
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO incidents (
                    id, organization_id, reporter_user_id, module, category,
                    severity, priority, request_type, status, summary, details,
                    error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)
                """,
                (
                    incident_id,
                    organization_id,
                    reporter_user_id,
                    module,
                    category,
                    severity,
                    priority,
                    request_type,
                    summary,
                    details,
                    error_message,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.execute(
                """
                INSERT INTO incident_activity (
                    id, incident_id, actor_user_id, event_type,
                    details, created_at
                ) VALUES (?, ?, ?, 'created', ?, ?)
                """,
                (
                    str(uuid4()),
                    incident_id,
                    reporter_user_id,
                    summary,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return incident_id

    def list_incidents(self, limit: int = 100) -> list[dict]:
        safe_limit = min(max(limit, 1), 500)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT incidents.*, organizations.name AS organization_name,
                       users.display_name AS reporter_name,
                       users.email AS reporter_email
                FROM incidents
                LEFT JOIN organizations
                    ON organizations.id = incidents.organization_id
                LEFT JOIN users
                    ON users.id = incidents.reporter_user_id
                ORDER BY incidents.created_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_user_incidents(
        self,
        user_id: str,
        limit: int = 100,
    ) -> list[dict]:
        safe_limit = min(max(limit, 1), 500)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, module, category, priority, severity, status,
                       summary, created_at, resolved_at
                FROM incidents
                WHERE reporter_user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, safe_limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_incident_status(
        self,
        incident_id: str,
        status: str,
        *,
        actor_user_id: str | None = None,
        resolution: str | None = None,
    ) -> dict:
        if status == "resolved" and not (resolution or "").strip():
            raise ValueError(
                "A resolution is required before resolving the ticket."
            )
        resolved_at = (
            datetime.now(timezone.utc).isoformat()
            if status == "resolved"
            else None
        )
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE incidents
                SET status = ?, resolved_at = ?, resolution = ?
                WHERE id = ?
                """,
                (
                    status,
                    resolved_at,
                    resolution.strip() if resolution else None,
                    incident_id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError("Incident not found.")
            row = connection.execute(
                "SELECT * FROM incidents WHERE id = ?",
                (incident_id,),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO incident_activity (
                    id, incident_id, actor_user_id, event_type,
                    details, created_at
                ) VALUES (?, ?, ?, 'status_changed', ?, ?)
                """,
                (
                    str(uuid4()),
                    incident_id,
                    actor_user_id,
                    status,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return dict(row)

    def get_incident(
        self,
        incident_id: str,
        *,
        reporter_user_id: str | None = None,
        customer_view: bool = False,
    ) -> dict:
        conditions = ["incidents.id = ?"]
        values: list[object] = [incident_id]
        if reporter_user_id is not None:
            conditions.append("incidents.reporter_user_id = ?")
            values.append(reporter_user_id)
        with self._connection() as connection:
            incident = connection.execute(
                f"""
                SELECT incidents.*, organizations.name AS organization_name,
                       users.display_name AS reporter_name,
                       users.email AS reporter_email
                FROM incidents
                LEFT JOIN organizations
                    ON organizations.id = incidents.organization_id
                LEFT JOIN users
                    ON users.id = incidents.reporter_user_id
                WHERE {" AND ".join(conditions)}
                """,
                values,
            ).fetchone()
            if incident is None:
                raise KeyError("Incident not found.")
            message_condition = (
                "AND incident_messages.visibility = 'customer'"
                if customer_view
                else ""
            )
            messages = connection.execute(
                f"""
                SELECT incident_messages.*, users.display_name AS author_name
                FROM incident_messages
                JOIN users ON users.id = incident_messages.author_user_id
                WHERE incident_messages.incident_id = ?
                {message_condition}
                ORDER BY incident_messages.created_at
                """,
                (incident_id,),
            ).fetchall()
            activity = connection.execute(
                """
                SELECT incident_activity.*, users.display_name AS actor_name
                FROM incident_activity
                LEFT JOIN users
                    ON users.id = incident_activity.actor_user_id
                WHERE incident_activity.incident_id = ?
                ORDER BY incident_activity.created_at
                """,
                (incident_id,),
            ).fetchall()
        return {
            "incident": dict(incident),
            "messages": [dict(row) for row in messages],
            "activity": [dict(row) for row in activity],
        }

    def add_incident_message(
        self,
        incident_id: str,
        *,
        author_user_id: str,
        visibility: str,
        message: str,
    ) -> dict:
        message_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            exists = connection.execute(
                "SELECT id FROM incidents WHERE id = ?",
                (incident_id,),
            ).fetchone()
            if exists is None:
                raise KeyError("Incident not found.")
            connection.execute(
                """
                INSERT INTO incident_messages (
                    id, incident_id, author_user_id, visibility,
                    message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    incident_id,
                    author_user_id,
                    visibility,
                    message.strip(),
                    created_at,
                ),
            )
            connection.execute(
                """
                INSERT INTO incident_activity (
                    id, incident_id, actor_user_id, event_type,
                    details, created_at
                ) VALUES (?, ?, ?, 'message_added', ?, ?)
                """,
                (
                    str(uuid4()),
                    incident_id,
                    author_user_id,
                    visibility,
                    created_at,
                ),
            )
        return {
            "id": message_id,
            "incident_id": incident_id,
            "author_user_id": author_user_id,
            "visibility": visibility,
            "message": message.strip(),
            "created_at": created_at,
        }


admin_store = AdminStore()
admin_store.initialize()
