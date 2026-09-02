import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DATA_DIR = Path(
    os.getenv(
        "BTP_DATA_DIR",
        str(Path(__file__).resolve().parents[1] / "data"),
    )
).expanduser()
DATABASE_PATH = DATA_DIR / "broadcast_tool_pro.db"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if len(slug) < 2:
        raise ValueError("A valid name or slug is required.")
    return slug[:80]


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f'Unknown time zone: "{value}".') from exc
    return value


class TenantStore:
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
                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    plan TEXT NOT NULL CHECK (
                        plan IN ('starter', 'professional', 'enterprise')
                    ),
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    default_timezone TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (organization_id)
                        REFERENCES organizations(id) ON DELETE CASCADE,
                    UNIQUE (organization_id, slug)
                );

                CREATE TABLE IF NOT EXISTS channels (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    channel_code TEXT,
                    timezone TEXT NOT NULL,
                    primary_language TEXT NOT NULL,
                    stream_monitoring INTEGER NOT NULL DEFAULT 0,
                    deactivation_scheduled_at TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (workspace_id)
                        REFERENCES workspaces(id) ON DELETE CASCADE,
                    UNIQUE (workspace_id, slug)
                );

                CREATE INDEX IF NOT EXISTS idx_workspaces_organization
                    ON workspaces(organization_id);
                CREATE INDEX IF NOT EXISTS idx_channels_workspace
                    ON channels(workspace_id);

                UPDATE organizations
                SET plan = 'professional'
                WHERE plan = 'starter';
            """)
            channel_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(channels)"
                ).fetchall()
            }
            if "stream_monitoring" not in channel_columns:
                connection.execute(
                    "ALTER TABLE channels ADD COLUMN "
                    "stream_monitoring INTEGER NOT NULL DEFAULT 0"
                )
            if "deactivation_scheduled_at" not in channel_columns:
                connection.execute(
                    "ALTER TABLE channels ADD COLUMN "
                    "deactivation_scheduled_at TEXT"
                )

    def create_organization(
        self,
        *,
        name: str,
        slug: str | None,
        plan: str,
    ) -> dict:
        organization_id = str(uuid4())
        timestamp = _utc_now()
        organization_slug = slug or _slugify(name)
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO organizations (
                        id, name, slug, plan, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        organization_id,
                        name.strip(),
                        organization_slug,
                        plan,
                        timestamp,
                        timestamp,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f'Organization slug "{organization_slug}" is already in use.'
            ) from exc
        return self.get_organization(organization_id)

    def list_organizations(self) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM organizations ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_organization(self, organization_id: str) -> dict:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM organizations WHERE id = ?",
                (organization_id,),
            ).fetchone()
        if row is None:
            raise KeyError("Organization not found.")
        return dict(row)

    def create_workspace(
        self,
        *,
        organization_id: str,
        name: str,
        slug: str | None,
        default_timezone: str,
    ) -> dict:
        self.get_organization(organization_id)
        workspace_id = str(uuid4())
        timestamp = _utc_now()
        workspace_slug = slug or _slugify(name)
        timezone_name = _validate_timezone(default_timezone)
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO workspaces (
                        id, organization_id, name, slug, default_timezone,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        workspace_id,
                        organization_id,
                        name.strip(),
                        workspace_slug,
                        timezone_name,
                        timestamp,
                        timestamp,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f'Workspace slug "{workspace_slug}" is already in use.'
            ) from exc
        return self.get_workspace(workspace_id)

    def list_workspaces(self, organization_id: str) -> list[dict]:
        self.get_organization(organization_id)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM workspaces
                WHERE organization_id = ?
                ORDER BY name
                """,
                (organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_workspace(self, workspace_id: str) -> dict:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,),
            ).fetchone()
        if row is None:
            raise KeyError("Workspace not found.")
        return dict(row)

    def create_channel(
        self,
        *,
        workspace_id: str,
        name: str,
        slug: str | None,
        channel_code: str | None,
        timezone: str,
        primary_language: str,
        stream_monitoring: bool = False,
    ) -> dict:
        self.get_workspace(workspace_id)
        channel_id = str(uuid4())
        timestamp = _utc_now()
        channel_slug = slug or _slugify(name)
        timezone_name = _validate_timezone(timezone)
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO channels (
                        id, workspace_id, name, slug, channel_code, timezone,
                        primary_language, stream_monitoring, active,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        channel_id,
                        workspace_id,
                        name.strip(),
                        channel_slug,
                        channel_code.strip() if channel_code else None,
                        timezone_name,
                        primary_language,
                        int(stream_monitoring),
                        timestamp,
                        timestamp,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f'Channel slug "{channel_slug}" is already in use.'
            ) from exc
        return self.get_channel(channel_id)

    def list_channels(self, workspace_id: str) -> list[dict]:
        self.get_workspace(workspace_id)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM channels
                WHERE workspace_id = ?
                ORDER BY name
                """,
                (workspace_id,),
            ).fetchall()
        return [self._channel(row) for row in rows]

    def update_channel_primary_language(
        self,
        channel_id: str,
        primary_language: str,
    ) -> dict:
        self.get_channel(channel_id)
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE channels
                SET primary_language = ?, updated_at = ?
                WHERE id = ?
                """,
                (primary_language, _utc_now(), channel_id),
            )
        return self.get_channel(channel_id)

    def list_organization_channels(self, organization_id: str) -> list[dict]:
        self.get_organization(organization_id)
        self.deactivate_due_channels(organization_id)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT channels.*
                FROM channels
                JOIN workspaces ON workspaces.id = channels.workspace_id
                WHERE workspaces.organization_id = ?
                ORDER BY channels.active DESC, channels.name
                """,
                (organization_id,),
            ).fetchall()
        return [self._channel(row) for row in rows]

    def included_channel_id(self, organization_id: str) -> str | None:
        """Return the organization's original channel, which is plan-included."""
        self.get_organization(organization_id)
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT channels.id
                FROM channels
                JOIN workspaces ON workspaces.id = channels.workspace_id
                WHERE workspaces.organization_id = ?
                ORDER BY channels.created_at ASC, channels.id ASC
                LIMIT 1
                """,
                (organization_id,),
            ).fetchone()
        return row["id"] if row is not None else None

    def schedule_channel_deactivation(
        self,
        channel_id: str,
        *,
        effective_at: str,
    ) -> dict:
        self.get_channel(channel_id)
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE channels
                SET deactivation_scheduled_at = ?, updated_at = ?
                WHERE id = ? AND active = 1
                """,
                (effective_at, _utc_now(), channel_id),
            )
        return self.get_channel(channel_id)

    def cancel_channel_deactivation(self, channel_id: str) -> dict:
        self.get_channel(channel_id)
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE channels
                SET deactivation_scheduled_at = NULL, updated_at = ?
                WHERE id = ? AND active = 1
                """,
                (_utc_now(), channel_id),
            )
        return self.get_channel(channel_id)

    def deactivate_due_channels(self, organization_id: str) -> int:
        now = _utc_now()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE channels
                SET active = 0, deactivation_scheduled_at = NULL,
                    updated_at = ?
                WHERE active = 1
                  AND deactivation_scheduled_at IS NOT NULL
                  AND deactivation_scheduled_at <= ?
                  AND workspace_id IN (
                      SELECT id FROM workspaces WHERE organization_id = ?
                  )
                """,
                (now, now, organization_id),
            )
        return cursor.rowcount

    def get_channel(self, channel_id: str) -> dict:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM channels WHERE id = ?",
                (channel_id,),
            ).fetchone()
        if row is None:
            raise KeyError("Channel not found.")
        return self._channel(row)

    @staticmethod
    def _channel(row: sqlite3.Row) -> dict:
        result = dict(row)
        result["active"] = bool(result["active"])
        result["stream_monitoring"] = bool(result["stream_monitoring"])
        return result


tenant_store = TenantStore()
tenant_store.initialize()
