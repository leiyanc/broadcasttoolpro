import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from backend.services.tenant_store import DATABASE_PATH


TRIAL_EMAILS = (
    {
        "code": "trial_welcome",
        "days_before_end": 7,
        "subject": "Welcome to your Broadcast Tool Pro trial",
        "body": (
            "Your 7-day trial is active. You can use XMLTV Validator, "
            "Pre-Logs, and HLS Validator. Trial reports are branded PDF files."
        ),
    },
    {
        "code": "trial_three_days_remaining",
        "days_before_end": 3,
        "subject": "Three days remain in your Broadcast Tool Pro trial",
        "body": (
            "Your Broadcast Tool Pro trial ends in three days. Review the "
            "available plans if you want uninterrupted access."
        ),
    },
    {
        "code": "trial_one_day_remaining",
        "days_before_end": 1,
        "subject": "Your Broadcast Tool Pro trial ends tomorrow",
        "body": (
            "Your Broadcast Tool Pro trial ends tomorrow. Choose a plan to "
            "keep access to your workflows and reports."
        ),
    },
    {
        "code": "trial_expired",
        "days_before_end": 0,
        "subject": "Your Broadcast Tool Pro trial has ended",
        "body": (
            "Your Broadcast Tool Pro trial has ended. Your account and "
            "history remain available when you activate a plan."
        ),
    },
)


class EmailOutboxStore:
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
                CREATE TABLE IF NOT EXISTS email_outbox (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    recipient_email TEXT NOT NULL,
                    template_code TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body_text TEXT NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued' CHECK (
                        status IN (
                            'queued', 'sending', 'sent', 'failed', 'canceled'
                        )
                    ),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    sent_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (organization_id)
                        REFERENCES organizations(id) ON DELETE CASCADE,
                    UNIQUE (organization_id, template_code)
                );

                CREATE INDEX IF NOT EXISTS idx_email_outbox_delivery
                    ON email_outbox(status, scheduled_for);
            """)

    def schedule_trial_lifecycle(
        self,
        *,
        organization_id: str,
        recipient_email: str,
        trial_ends_at: str,
    ) -> list[dict]:
        trial_end = datetime.fromisoformat(trial_ends_at)
        if trial_end.tzinfo is None:
            trial_end = trial_end.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        created_at = now.isoformat()
        with self._connection() as connection:
            for message in TRIAL_EMAILS:
                if message["code"] == "trial_welcome":
                    scheduled_for = now
                else:
                    scheduled_for = trial_end - timedelta(
                        days=message["days_before_end"]
                    )
                connection.execute(
                    """
                    INSERT INTO email_outbox (
                        id, organization_id, recipient_email, template_code,
                        subject, body_text, scheduled_for, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)
                    ON CONFLICT (organization_id, template_code) DO NOTHING
                    """,
                    (
                        str(uuid4()),
                        organization_id,
                        recipient_email.strip().lower(),
                        message["code"],
                        message["subject"],
                        message["body"],
                        max(scheduled_for, now).isoformat(),
                        created_at,
                    ),
                )
        return self.list_for_organization(organization_id)

    def schedule_password_reset(
        self,
        *,
        organization_id: str,
        recipient_email: str,
        reset_url: str,
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        message_id = str(uuid4())
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO email_outbox (
                    id, organization_id, recipient_email, template_code,
                    subject, body_text, scheduled_for, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)
                """,
                (
                    message_id,
                    organization_id,
                    recipient_email.strip().lower(),
                    f"password_reset_{message_id}",
                    "Reset your Broadcast Tool Pro password",
                    (
                        "A password reset was requested for your Broadcast "
                        f"Tool Pro account. Use this secure link within 30 "
                        f"minutes: {reset_url}\n\nIf you did not request "
                        "this change, ignore this message."
                    ),
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM email_outbox WHERE id = ?",
                (message_id,),
            ).fetchone()
        return dict(row)

    def schedule_account_activation(
        self,
        *,
        organization_id: str,
        recipient_email: str,
        organization_name: str,
        plan: str,
        activation_url: str,
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        message_id = str(uuid4())
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO email_outbox (
                    id, organization_id, recipient_email, template_code,
                    subject, body_text, scheduled_for, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)
                """,
                (
                    message_id,
                    organization_id,
                    recipient_email.strip().lower(),
                    f"account_activation_{message_id}",
                    "Activate your Broadcast Tool Pro account",
                    (
                        f"{organization_name} has been approved for the "
                        f"{plan.title()} plan. Create your password within "
                        f"seven days: {activation_url}"
                    ),
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM email_outbox WHERE id = ?",
                (message_id,),
            ).fetchone()
        return dict(row)

    def list_for_organization(self, organization_id: str) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM email_outbox
                WHERE organization_id = ?
                ORDER BY scheduled_for
                """,
                (organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def pending(self, limit: int = 100) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM email_outbox
                WHERE status = 'queued' AND scheduled_for <= ?
                ORDER BY scheduled_for
                LIMIT ?
                """,
                (datetime.now(timezone.utc).isoformat(), limit),
            ).fetchall()
        return [dict(row) for row in rows]


email_outbox_store = EmailOutboxStore()
email_outbox_store.initialize()
