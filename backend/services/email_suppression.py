"""Provider-neutral email suppression and delivery event tracking."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.services.tenant_store import DATABASE_PATH


SUPPRESSION_REASONS = {"permanent_bounce", "complaint", "manual"}
DELIVERY_EVENT_TYPES = {
    "send",
    "delivery",
    "temporary_bounce",
    "permanent_bounce",
    "complaint",
    "reject",
}


class EmailSuppressionStore:
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
                CREATE TABLE IF NOT EXISTS email_suppressions (
                    recipient_email TEXT PRIMARY KEY,
                    reason TEXT NOT NULL CHECK (
                        reason IN (
                            'permanent_bounce', 'complaint', 'manual'
                        )
                    ),
                    source TEXT NOT NULL,
                    provider_message_id TEXT,
                    details TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS email_delivery_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL CHECK (
                        event_type IN (
                            'send', 'delivery', 'temporary_bounce',
                            'permanent_bounce', 'complaint', 'reject'
                        )
                    ),
                    recipient_email TEXT,
                    provider TEXT NOT NULL,
                    provider_message_id TEXT,
                    details_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_email_delivery_event_message
                    ON email_delivery_events(provider_message_id);
                CREATE INDEX IF NOT EXISTS idx_email_delivery_event_recipient
                    ON email_delivery_events(recipient_email, occurred_at);
            """)

    @staticmethod
    def normalize_email(recipient_email: str) -> str:
        return recipient_email.strip().lower()

    def suppress(
        self,
        recipient_email: str,
        *,
        reason: str,
        source: str,
        provider_message_id: str | None = None,
        details: str | None = None,
    ) -> dict:
        if reason not in SUPPRESSION_REASONS:
            raise ValueError("Unsupported email suppression reason.")
        email = self.normalize_email(recipient_email)
        if not email:
            raise ValueError("Recipient email is required.")
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO email_suppressions (
                    recipient_email, reason, source, provider_message_id,
                    details, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (recipient_email) DO UPDATE SET
                    reason = excluded.reason,
                    source = excluded.source,
                    provider_message_id = excluded.provider_message_id,
                    details = excluded.details,
                    updated_at = excluded.updated_at
                """,
                (
                    email,
                    reason,
                    source.strip() or "system",
                    provider_message_id,
                    details,
                    now,
                    now,
                ),
            )
            connection.execute(
                """
                UPDATE email_outbox
                SET status = 'canceled',
                    last_error = 'Recipient is on the suppression list.'
                WHERE recipient_email = ?
                  AND status IN ('queued', 'sending')
                """,
                (email,),
            )
            row = connection.execute(
                """
                SELECT * FROM email_suppressions
                WHERE recipient_email = ?
                """,
                (email,),
            ).fetchone()
        return dict(row)

    def remove(self, recipient_email: str) -> bool:
        email = self.normalize_email(recipient_email)
        with self._connection() as connection:
            result = connection.execute(
                """
                DELETE FROM email_suppressions
                WHERE recipient_email = ?
                """,
                (email,),
            )
        return result.rowcount > 0

    def is_suppressed(self, recipient_email: str) -> bool:
        email = self.normalize_email(recipient_email)
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM email_suppressions
                WHERE recipient_email = ?
                """,
                (email,),
            ).fetchone()
        return row is not None

    def list(self, limit: int = 500) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM email_suppressions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (min(max(limit, 1), 1000),),
            ).fetchall()
        return [dict(row) for row in rows]

    def record_event(
        self,
        *,
        event_type: str,
        recipient_email: str | None,
        provider: str,
        provider_message_id: str | None = None,
        details: dict | None = None,
        occurred_at: str | None = None,
    ) -> dict:
        if event_type not in DELIVERY_EVENT_TYPES:
            raise ValueError("Unsupported email delivery event type.")
        email = (
            self.normalize_email(recipient_email)
            if recipient_email
            else None
        )
        now = datetime.now(timezone.utc).isoformat()
        event_id = str(uuid4())
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO email_delivery_events (
                    id, event_type, recipient_email, provider,
                    provider_message_id, details_json, occurred_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event_type,
                    email,
                    provider.strip().lower(),
                    provider_message_id,
                    json.dumps(details or {}, sort_keys=True),
                    occurred_at or now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM email_delivery_events WHERE id = ?",
                (event_id,),
            ).fetchone()
        if email and event_type in {"permanent_bounce", "complaint"}:
            self.suppress(
                email,
                reason=event_type,
                source=provider,
                provider_message_id=provider_message_id,
                details=json.dumps(details or {}, sort_keys=True),
            )
        result = dict(row)
        result["details"] = json.loads(result.pop("details_json"))
        return result

    def events(self, limit: int = 500) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM email_delivery_events
                ORDER BY occurred_at DESC
                LIMIT ?
                """,
                (min(max(limit, 1), 1000),),
            ).fetchall()
        events = []
        for row in rows:
            event = dict(row)
            event["details"] = json.loads(event.pop("details_json"))
            events.append(event)
        return events


email_suppression_store = EmailSuppressionStore()
email_suppression_store.initialize()
