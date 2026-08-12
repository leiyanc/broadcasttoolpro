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
                    provider_message_id TEXT,
                    sent_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (organization_id)
                        REFERENCES organizations(id) ON DELETE CASCADE,
                    UNIQUE (organization_id, template_code)
                );

                CREATE INDEX IF NOT EXISTS idx_email_outbox_delivery
                    ON email_outbox(status, scheduled_for);

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

                CREATE TABLE IF NOT EXISTS email_preferences (
                    recipient_email TEXT PRIMARY KEY,
                    trial_reminders INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );
            """)
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(email_outbox)"
                ).fetchall()
            }
            if "provider_message_id" not in columns:
                connection.execute(
                    "ALTER TABLE email_outbox "
                    "ADD COLUMN provider_message_id TEXT"
                )

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
        payment_required: bool = False,
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
                        f"{plan.replace('_', ' ').title()} plan. Create "
                        f"your password within seven days: {activation_url}"
                        + (
                            "\n\nAfter activation, open Billing and complete "
                            "secure Stripe Checkout. Product access begins "
                            "only after Stripe confirms the subscription."
                            if payment_required
                            else ""
                        )
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

    def schedule_access_request_received(
        self,
        *,
        notification_organization_id: str,
        request_id: str,
        organization_name: str,
        contact_name: str,
        requester_email: str,
        request_message: str | None,
        administrator_emails: list[str],
        requested_plan: str = "professional",
        include_stream_monitoring: bool = False,
        billing_cycle: str = "monthly",
    ) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        messages = [
            {
                "recipient": requester_email,
                "code": f"access_request_requester_{request_id}",
                "subject": "We received your Broadcast Tool Pro request",
                "body": (
                    f"Hello {contact_name},\n\n"
                    "Your Broadcast Tool Pro access request has been "
                    f"received. Reference: {request_id}.\n\n"
                    "Our team will review your request and contact you "
                    "with activation instructions.\n\n"
                    f"Requested plan: {requested_plan.replace('_', ' ').title()}\n"
                    f"Billing cycle: {billing_cycle.title()}\n"
                    "Stream Monitoring add-on: "
                    f"{'Requested' if include_stream_monitoring else 'No'}\n\n"
                    "No payment has been collected."
                ),
            }
        ]
        request_details = (
            request_message.strip()
            if request_message and request_message.strip()
            else "No additional workflow details were provided."
        )
        for position, email in enumerate(
            dict.fromkeys(
                address.strip().lower()
                for address in administrator_emails
                if address.strip()
            )
        ):
            messages.append(
                {
                    "recipient": email,
                    "code": (
                        f"access_request_admin_{request_id}_{position}"
                    ),
                    "subject": (
                        f"New access request: {organization_name}"
                    ),
                    "body": (
                        "A new paid-account access request is ready for "
                        "review in the Control Panel.\n\n"
                        f"Reference: {request_id}\n"
                        f"Organization: {organization_name}\n"
                        f"Contact: {contact_name}\n"
                        f"Email: {requester_email}\n"
                        "Requested plan: "
                        f"{requested_plan.replace('_', ' ').title()}\n"
                        f"Billing cycle: {billing_cycle.title()}\n"
                        "Stream Monitoring add-on: "
                        f"{'Requested' if include_stream_monitoring else 'No'}\n"
                        f"Workflow: {request_details}"
                    ),
                }
            )
        created: list[dict] = []
        with self._connection() as connection:
            for message in messages:
                message_id = str(uuid4())
                connection.execute(
                    """
                    INSERT INTO email_outbox (
                        id, organization_id, recipient_email, template_code,
                        subject, body_text, scheduled_for, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)
                    """,
                    (
                        message_id,
                        notification_organization_id,
                        message["recipient"].strip().lower(),
                        message["code"],
                        message["subject"],
                        message["body"],
                        now,
                        now,
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM email_outbox WHERE id = ?",
                    (message_id,),
                ).fetchone()
                created.append(dict(row))
        return created

    def schedule_account_reactivated(
        self,
        *,
        organization_id: str,
        recipient_email: str,
        organization_name: str,
        plan: str,
        sign_in_url: str,
        payment_required: bool = False,
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
                    f"account_reactivated_{message_id}",
                    "Your Broadcast Tool Pro access was approved",
                    (
                        f"{organization_name} has been approved for the "
                        f"{plan.replace('_', ' ').title()} plan. Your "
                        f"existing account remains valid. Sign in here: "
                        f"{sign_in_url}"
                        + (
                            "\n\nOpen Billing and complete secure Stripe "
                            "Checkout. Product access begins only after "
                            "Stripe confirms the subscription."
                            if payment_required
                            else ""
                        )
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

    def schedule_payment_failure_lifecycle(
        self,
        *,
        organization_id: str,
        recipient_email: str,
        grace_ends_at: str,
        grace_hours: int = 72,
        hosted_invoice_url: str | None = None,
    ) -> list[dict]:
        grace_end = datetime.fromisoformat(grace_ends_at)
        if grace_end.tzinfo is None:
            grace_end = grace_end.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        payment_link = (
            f"\n\nUpdate payment details: {hosted_invoice_url}"
            if hosted_invoice_url else ""
        )
        cycle_key = str(int(grace_end.timestamp()))
        messages = (
            (
                f"payment_failed_{cycle_key}",
                f"Payment failed — {grace_hours}-hour access grace period",
                (
                    "We could not renew your Broadcast Tool Pro subscription. "
                    f"Access remains available until {grace_end.isoformat()}. "
                    "Update your payment method to prevent suspension."
                    f"{payment_link}"
                ),
                now,
            ),
            (
                f"payment_grace_24h_{cycle_key}",
                "24 hours remain before subscription suspension",
                (
                    "Your Broadcast Tool Pro payment remains past due. "
                    "Approximately 24 hours of access remain before automatic "
                    f"suspension at {grace_end.isoformat()}."
                    f"{payment_link}"
                ),
                grace_end - timedelta(hours=24),
            ),
            (
                f"payment_suspended_{cycle_key}",
                "Broadcast Tool Pro access suspended",
                (
                    f"The {grace_hours}-hour payment grace period has ended "
                    "and product "
                    "access is now suspended. Your files, history, and settings "
                    "have not been deleted. Restore payment to reactivate access."
                    f"{payment_link}"
                ),
                grace_end,
            ),
        )
        created: list[dict] = []
        with self._connection() as connection:
            for code, subject, body, scheduled_for in messages:
                message_id = str(uuid4())
                connection.execute(
                    """
                    INSERT OR IGNORE INTO email_outbox (
                        id, organization_id, recipient_email, template_code,
                        subject, body_text, scheduled_for, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)
                    """,
                    (
                        message_id, organization_id,
                        recipient_email.strip().lower(), code, subject, body,
                        max(scheduled_for, now).isoformat(), now.isoformat(),
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM email_outbox WHERE id = ?",
                    (message_id,),
                ).fetchone()
                if row is not None:
                    created.append(dict(row))
        return created

    def cancel_payment_failure_lifecycle(
        self,
        *,
        organization_id: str,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE email_outbox
                SET status = 'canceled',
                    last_error = 'Payment recovered before notification.'
                WHERE organization_id = ? AND status = 'queued'
                  AND (
                      template_code LIKE 'payment_grace_24h_%'
                      OR template_code LIKE 'payment_suspended_%'
                  )
                """,
                (organization_id,),
            )

    def schedule_payment_recovered(
        self,
        *,
        organization_id: str,
        recipient_email: str,
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
                    message_id, organization_id,
                    recipient_email.strip().lower(),
                    f"payment_recovered_{message_id}",
                    "Payment received — access restored",
                    (
                        "Your Broadcast Tool Pro payment was received. Your "
                        "subscription is active and full product access has "
                        "been restored automatically."
                    ),
                    now, now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM email_outbox WHERE id = ?",
                (message_id,),
            ).fetchone()
        return dict(row)

    def schedule_subscription_change_notifications(
        self,
        *,
        organization_id: str,
        recipient_email: str,
        administrator_emails: list[str],
        previous_plan: str,
        new_plan: str,
        include_stream_monitoring: bool,
        effective: str,
        effective_at: str | None,
        recurring_monthly_cents: int,
        billing_url: str,
    ) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        change_id = str(uuid4())
        plan_names = {
            "programming_suite": "Programming Suite",
            "professional": "Professional",
            "enterprise": "Enterprise",
        }
        previous_name = plan_names.get(previous_plan, previous_plan)
        new_name = plan_names.get(new_plan, new_plan)
        monitoring = "Included" if (
            new_plan == "enterprise" or include_stream_monitoring
        ) else "Not included"
        effective_label = None
        if effective_at:
            effective_date = datetime.fromisoformat(effective_at)
            if effective_date.tzinfo is None:
                effective_date = effective_date.replace(tzinfo=timezone.utc)
            effective_label = effective_date.astimezone(timezone.utc).strftime(
                "%B %d, %Y at %H:%M UTC"
            ).replace(" 0", " ")
        timing = {
            "immediately": "The change is effective immediately.",
            "pending_payment": (
                "The current plan remains active until Stripe confirms payment."
            ),
            "period_end": f"The change is scheduled for {effective_label}.",
        }[effective]
        with self._connection() as connection:
            organization = connection.execute(
                "SELECT name FROM organizations WHERE id = ?",
                (organization_id,),
            ).fetchone()
        organization_name = (
            organization["name"] if organization else organization_id
        )
        charged_today = (
            "$0.00" if effective == "period_end"
            else "See your Stripe payment receipt"
        )
        summary = (
            f"Organization: {organization_name}\n"
            f"Previous plan: {previous_name}\n"
            f"New plan: {new_name}\n"
            f"Stream Monitoring: {monitoring}\n"
            f"New monthly total: ${recurring_monthly_cents / 100:.2f}\n"
            f"Charged today: {charged_today}\n"
            f"{timing}"
        )
        messages = [{
            "recipient": recipient_email,
            "code": f"subscription_change_customer_{change_id}",
            "subject": "Your Broadcast Tool Pro subscription change",
            "body": (
                "Your subscription change request was received.\n\n"
                f"{summary}\n\n"
                f"Open Billing: {billing_url}"
            ),
        }]
        for position, email in enumerate(dict.fromkeys(
            address.strip().lower()
            for address in administrator_emails
            if address.strip()
        )):
            messages.append({
                "recipient": email,
                "code": f"subscription_change_admin_{change_id}_{position}",
                "subject": "Customer subscription change recorded",
                "body": (
                    "A customer subscription change was recorded.\n\n"
                    f"{summary}"
                ),
            })
        created: list[dict] = []
        with self._connection() as connection:
            for message in messages:
                message_id = str(uuid4())
                connection.execute(
                    """
                    INSERT INTO email_outbox (
                        id, organization_id, recipient_email, template_code,
                        subject, body_text, scheduled_for, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)
                    """,
                    (
                        message_id, organization_id,
                        message["recipient"].strip().lower(), message["code"],
                        message["subject"], message["body"], now, now,
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM email_outbox WHERE id = ?", (message_id,)
                ).fetchone()
                created.append(dict(row))
        return created

    def schedule_subscription_renewal_notice(
        self,
        *,
        organization_id: str,
        recipient_email: str,
        administrator_emails: list[str],
        cancel: bool,
        effective_at: str | None,
    ) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        message_id = str(uuid4())
        subject = (
            "Your Broadcast Tool Pro cancellation is scheduled"
            if cancel else "Your Broadcast Tool Pro renewal was resumed"
        )
        body = (
            "Your subscription will not renew. Product access remains active "
            f"through {effective_at}."
            if cancel else
            "Automatic renewal has been resumed for your subscription."
        )
        messages = [(recipient_email, subject, body)]
        admin_action = "scheduled cancellation" if cancel else "resumed renewal"
        for email in dict.fromkeys(
            address.strip().lower()
            for address in administrator_emails
            if address.strip()
        ):
            messages.append((
                email,
                f"Customer subscription {admin_action}",
                f"Organization ID: {organization_id}\n{body}",
            ))
        created: list[dict] = []
        with self._connection() as connection:
            for position, (email, message_subject, message_body) in enumerate(messages):
                row_id = message_id if position == 0 else str(uuid4())
                connection.execute(
                    """
                    INSERT INTO email_outbox (
                        id, organization_id, recipient_email, template_code,
                        subject, body_text, scheduled_for, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)
                    """,
                    (
                        row_id, organization_id, email.strip().lower(),
                        f"subscription_renewal_{message_id}_{position}",
                        message_subject, message_body, now, now,
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM email_outbox WHERE id = ?", (row_id,)
                ).fetchone()
                created.append(dict(row))
        return created

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

    def recent_delivery_attempts(self, limit: int = 100) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT id, organization_id, recipient_email, template_code,
                       subject, scheduled_for, status, attempts, last_error,
                       provider_message_id, sent_at, created_at
                FROM email_outbox
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (min(max(limit, 1), 500),),
            ).fetchall()
        return [dict(row) for row in rows]

    def subscription_message_detail(self, message_id: str) -> dict:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT id, recipient_email, template_code, subject, body_text,
                       status, attempts, last_error, created_at, sent_at
                FROM email_outbox WHERE id = ?
                """,
                (message_id,),
            ).fetchone()
        if row is None:
            raise KeyError("Email message not found.")
        if not row["template_code"].startswith((
            "subscription_change_", "subscription_renewal_"
        )):
            raise ValueError(
                "Message details are available only for subscription notices."
            )
        return dict(row)

    def retry_delivery(self, message_id: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM email_outbox WHERE id = ?",
                (message_id,),
            ).fetchone()
            if row is None:
                raise KeyError("Email message not found.")
            if row["status"] not in {"queued", "failed"}:
                raise ValueError(
                    "Only queued or failed messages can be retried."
                )
            suppression = connection.execute(
                """
                SELECT reason FROM email_suppressions
                WHERE recipient_email = ?
                """,
                (row["recipient_email"],),
            ).fetchone()
            if suppression is not None:
                raise ValueError(
                    "Remove the recipient suppression before retrying."
                )
            connection.execute(
                """
                UPDATE email_outbox
                SET status = 'queued', attempts = 0, scheduled_for = ?,
                    last_error = NULL, provider_message_id = NULL,
                    sent_at = NULL
                WHERE id = ?
                """,
                (now, message_id),
            )
            retried = connection.execute(
                "SELECT * FROM email_outbox WHERE id = ?",
                (message_id,),
            ).fetchone()
        return dict(retried)

    def preferences_for(self, recipient_email: str) -> dict:
        normalized = recipient_email.strip().lower()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT trial_reminders, updated_at
                FROM email_preferences
                WHERE recipient_email = ?
                """,
                (normalized,),
            ).fetchone()
        return {
            "recipient_email": normalized,
            "trial_reminders": (
                bool(row["trial_reminders"]) if row is not None else True
            ),
            "updated_at": row["updated_at"] if row is not None else None,
        }

    def update_preferences(
        self,
        recipient_email: str,
        *,
        trial_reminders: bool,
    ) -> dict:
        normalized = recipient_email.strip().lower()
        updated_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO email_preferences (
                    recipient_email, trial_reminders, updated_at
                ) VALUES (?, ?, ?)
                ON CONFLICT (recipient_email) DO UPDATE SET
                    trial_reminders = excluded.trial_reminders,
                    updated_at = excluded.updated_at
                """,
                (normalized, int(trial_reminders), updated_at),
            )
            if not trial_reminders:
                connection.execute(
                    """
                    UPDATE email_outbox
                    SET status = 'canceled',
                        last_error = 'Disabled by recipient preference.'
                    WHERE recipient_email = ?
                      AND status = 'queued'
                      AND template_code IN (
                          'trial_three_days_remaining',
                          'trial_one_day_remaining'
                      )
                    """,
                    (normalized,),
                )
        return self.preferences_for(normalized)

    def pending(self, limit: int = 100) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM email_outbox
                WHERE status = 'queued' AND scheduled_for <= ?
                  AND NOT EXISTS (
                      SELECT 1 FROM email_suppressions
                      WHERE email_suppressions.recipient_email =
                            email_outbox.recipient_email
                  )
                  AND (
                      template_code NOT IN (
                          'trial_three_days_remaining',
                          'trial_one_day_remaining'
                      )
                      OR NOT EXISTS (
                          SELECT 1 FROM email_preferences
                          WHERE email_preferences.recipient_email =
                                email_outbox.recipient_email
                            AND email_preferences.trial_reminders = 0
                      )
                  )
                ORDER BY scheduled_for
                LIMIT ?
                """,
                (datetime.now(timezone.utc).isoformat(), limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def claim_pending(self, limit: int = 25) -> list[dict]:
        """Atomically reserve due messages for one delivery worker."""
        now = datetime.now(timezone.utc).isoformat()
        claimed: list[dict] = []
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT * FROM email_outbox
                WHERE status = 'queued' AND scheduled_for <= ?
                  AND NOT EXISTS (
                      SELECT 1 FROM email_suppressions
                      WHERE email_suppressions.recipient_email =
                            email_outbox.recipient_email
                  )
                  AND (
                      template_code NOT IN (
                          'trial_three_days_remaining',
                          'trial_one_day_remaining'
                      )
                      OR NOT EXISTS (
                          SELECT 1 FROM email_preferences
                          WHERE email_preferences.recipient_email =
                                email_outbox.recipient_email
                            AND email_preferences.trial_reminders = 0
                      )
                  )
                ORDER BY scheduled_for
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()
            for row in rows:
                updated = connection.execute(
                    """
                    UPDATE email_outbox
                    SET status = 'sending', attempts = attempts + 1,
                        last_error = NULL
                    WHERE id = ? AND status = 'queued'
                    """,
                    (row["id"],),
                )
                if updated.rowcount:
                    claimed_row = connection.execute(
                        "SELECT * FROM email_outbox WHERE id = ?",
                        (row["id"],),
                    ).fetchone()
                    claimed.append(dict(claimed_row))
        return claimed

    def mark_sent(
        self,
        message_id: str,
        provider_message_id: str | None,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE email_outbox
                SET status = 'sent', provider_message_id = ?,
                    sent_at = ?, last_error = NULL
                WHERE id = ? AND status = 'sending'
                """,
                (
                    provider_message_id,
                    datetime.now(timezone.utc).isoformat(),
                    message_id,
                ),
            )

    def mark_delivery_failure(
        self,
        message_id: str,
        error: str,
        *,
        maximum_attempts: int = 5,
    ) -> None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT attempts FROM email_outbox WHERE id = ?",
                (message_id,),
            ).fetchone()
            if row is None:
                return
            attempts = int(row["attempts"])
            status = "failed" if attempts >= maximum_attempts else "queued"
            retry_at = datetime.now(timezone.utc) + timedelta(
                minutes=min(2 ** attempts, 60)
            )
            connection.execute(
                """
                UPDATE email_outbox
                SET status = ?, scheduled_for = ?, last_error = ?
                WHERE id = ? AND status = 'sending'
                """,
                (
                    status,
                    retry_at.isoformat(),
                    error[:1000],
                    message_id,
                ),
            )


email_outbox_store = EmailOutboxStore()
email_outbox_store.initialize()
