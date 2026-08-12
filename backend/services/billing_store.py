import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from backend.services.tenant_store import DATABASE_PATH


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BillingStore:
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
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL CHECK (
                        status IN (
                            'trialing', 'active', 'past_due', 'canceled'
                        )
                    ),
                    billing_cycle TEXT NOT NULL CHECK (
                        billing_cycle IN ('monthly', 'annual')
                    ),
                    currency TEXT NOT NULL DEFAULT 'USD',
                    amount_cents INTEGER,
                    plan_code TEXT,
                    provider TEXT NOT NULL DEFAULT 'manual',
                    provider_customer_id TEXT,
                    provider_subscription_id TEXT,
                    current_period_start TEXT NOT NULL,
                    current_period_end TEXT NOT NULL,
                    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
                    payment_waived INTEGER NOT NULL DEFAULT 0,
                    waiver_reason TEXT,
                    waiver_expires_at TEXT,
                    waived_by_user_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (organization_id)
                        REFERENCES organizations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    subscription_id TEXT,
                    status TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    amount_due_cents INTEGER NOT NULL,
                    amount_paid_cents INTEGER NOT NULL DEFAULT 0,
                    invoice_date TEXT NOT NULL,
                    due_date TEXT,
                    paid_at TEXT,
                    provider_invoice_id TEXT,
                    hosted_invoice_url TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (organization_id)
                        REFERENCES organizations(id) ON DELETE CASCADE,
                    FOREIGN KEY (subscription_id)
                        REFERENCES subscriptions(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_invoices_organization
                    ON invoices(organization_id, invoice_date DESC);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_provider
                    ON invoices(provider_invoice_id)
                    WHERE provider_invoice_id IS NOT NULL;

                CREATE TABLE IF NOT EXISTS subscription_events (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    actor_user_id TEXT,
                    event_type TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (organization_id)
                        REFERENCES organizations(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_subscription_events_org
                    ON subscription_events(organization_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS billing_provider_events (
                    provider_event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    processed_at TEXT NOT NULL
                );
            """)
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(subscriptions)"
                ).fetchall()
            }
            migrations = {
                "payment_waived": (
                    "ALTER TABLE subscriptions ADD COLUMN "
                    "payment_waived INTEGER NOT NULL DEFAULT 0"
                ),
                "waiver_reason": (
                    "ALTER TABLE subscriptions ADD COLUMN waiver_reason TEXT"
                ),
                "waiver_expires_at": (
                    "ALTER TABLE subscriptions ADD COLUMN "
                    "waiver_expires_at TEXT"
                ),
                "waived_by_user_id": (
                    "ALTER TABLE subscriptions ADD COLUMN "
                    "waived_by_user_id TEXT"
                ),
                "plan_code": (
                    "ALTER TABLE subscriptions ADD COLUMN plan_code TEXT"
                ),
                "payment_failed_at": (
                    "ALTER TABLE subscriptions ADD COLUMN payment_failed_at TEXT"
                ),
                "grace_period_ends_at": (
                    "ALTER TABLE subscriptions ADD COLUMN "
                    "grace_period_ends_at TEXT"
                ),
                "pending_plan_code": (
                    "ALTER TABLE subscriptions ADD COLUMN pending_plan_code TEXT"
                ),
                "pending_stream_monitoring": (
                    "ALTER TABLE subscriptions ADD COLUMN "
                    "pending_stream_monitoring INTEGER"
                ),
                "pending_change_at": (
                    "ALTER TABLE subscriptions ADD COLUMN pending_change_at TEXT"
                ),
            }
            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)

    def mark_payment_failed(
        self,
        organization_id: str,
        *,
        grace_hours: int,
    ) -> dict:
        if grace_hours < 1:
            raise ValueError("Payment grace period must be positive.")
        now = datetime.now(timezone.utc)
        current = self.get_subscription(organization_id)
        existing_end = current.get("grace_period_ends_at")
        if existing_end:
            return current
        grace_end = now + timedelta(hours=grace_hours)
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE subscriptions
                SET status = 'past_due', payment_failed_at = ?,
                    grace_period_ends_at = ?, updated_at = ?
                WHERE organization_id = ? AND provider = 'stripe'
                """,
                (
                    now.isoformat(), grace_end.isoformat(),
                    now.isoformat(), organization_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError(
                    "Payment failure requires an active Stripe subscription."
                )
            connection.execute(
                """
                INSERT INTO subscription_events (
                    id, organization_id, event_type, details, created_at
                ) VALUES (?, ?, 'payment_failed', ?, ?)
                """,
                (
                    str(uuid4()), organization_id,
                    f"Payment failed. Access grace period ends in "
                    f"{grace_hours} hours.", now.isoformat(),
                ),
            )
        return self.get_subscription(organization_id)

    def clear_payment_failure(self, organization_id: str) -> tuple[dict, bool]:
        current = self.get_subscription(organization_id)
        recovered = bool(current.get("grace_period_ends_at"))
        now = _utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE subscriptions
                SET payment_failed_at = NULL, grace_period_ends_at = NULL,
                    updated_at = ?
                WHERE organization_id = ?
                """,
                (now, organization_id),
            )
            if recovered:
                connection.execute(
                    """
                    INSERT INTO subscription_events (
                        id, organization_id, event_type, details, created_at
                    ) VALUES (?, ?, 'payment_recovered', ?, ?)
                    """,
                    (
                        str(uuid4()), organization_id,
                        "Payment recovered and full access restored.", now,
                    ),
                )
        return self.get_subscription(organization_id), recovered

    def ensure_subscription(self, organization_id: str) -> dict:
        with self._connection() as connection:
            organization = connection.execute(
                "SELECT id FROM organizations WHERE id = ?",
                (organization_id,),
            ).fetchone()
            if organization is None:
                raise KeyError("Organization not found.")
            existing = connection.execute(
                "SELECT * FROM subscriptions WHERE organization_id = ?",
                (organization_id,),
            ).fetchone()
            if existing is not None:
                return self.get_subscription(organization_id)
            now = datetime.now(timezone.utc)
            subscription_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO subscriptions (
                    id, organization_id, status, billing_cycle, currency,
                    amount_cents, provider, current_period_start,
                    current_period_end, cancel_at_period_end,
                    created_at, updated_at
                ) VALUES (?, ?, 'active', 'monthly', 'USD', NULL, 'manual',
                          ?, ?, 0, ?, ?)
                """,
                (
                    subscription_id,
                    organization_id,
                    now.isoformat(),
                    (now + timedelta(days=30)).isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        return self.get_subscription(organization_id)

    def create_trial_subscription(
        self,
        organization_id: str,
        days: int = 7,
    ) -> dict:
        if days < 1 or days > 30:
            raise ValueError("Trial length must be between 1 and 30 days.")
        now = datetime.now(timezone.utc)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO subscriptions (
                    id, organization_id, status, billing_cycle, currency,
                    amount_cents, provider, current_period_start,
                    current_period_end, cancel_at_period_end,
                    created_at, updated_at
                ) VALUES (?, ?, 'trialing', 'monthly', 'USD', 0, 'trial',
                          ?, ?, 1, ?, ?)
                ON CONFLICT (organization_id)
                DO UPDATE SET
                    status = 'trialing',
                    amount_cents = 0,
                    provider = 'trial',
                    current_period_start = excluded.current_period_start,
                    current_period_end = excluded.current_period_end,
                    cancel_at_period_end = 1,
                    updated_at = excluded.updated_at
                """,
                (
                    str(uuid4()),
                    organization_id,
                    now.isoformat(),
                    (now + timedelta(days=days)).isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        return self.get_subscription(organization_id)

    def create_manual_paid_subscription(
        self,
        organization_id: str,
        *,
        amount_cents: int,
        billing_cycle: str = "monthly",
    ) -> dict:
        if amount_cents < 0:
            raise ValueError("Subscription amount cannot be negative.")
        if billing_cycle not in {"monthly", "annual"}:
            raise ValueError("A valid billing cycle is required.")
        now = datetime.now(timezone.utc)
        period_days = 365 if billing_cycle == "annual" else 30
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO subscriptions (
                    id, organization_id, status, billing_cycle, currency,
                    amount_cents, provider, current_period_start,
                    current_period_end, cancel_at_period_end,
                    created_at, updated_at
                ) VALUES (?, ?, 'active', ?, 'USD', ?, 'manual',
                          ?, ?, 0, ?, ?)
                ON CONFLICT (organization_id)
                DO UPDATE SET
                    status = 'active',
                    billing_cycle = excluded.billing_cycle,
                    amount_cents = excluded.amount_cents,
                    provider = 'manual',
                    payment_waived = 0,
                    waiver_reason = NULL,
                    waiver_expires_at = NULL,
                    waived_by_user_id = NULL,
                    current_period_start = excluded.current_period_start,
                    current_period_end = excluded.current_period_end,
                    cancel_at_period_end = 0,
                    updated_at = excluded.updated_at
                """,
                (
                    str(uuid4()),
                    organization_id,
                    billing_cycle,
                    amount_cents,
                    now.isoformat(),
                    (now + timedelta(days=period_days)).isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        return self.get_subscription(organization_id)

    def create_pending_stripe_subscription(
        self,
        organization_id: str,
        *,
        plan_code: str,
        amount_cents: int,
        billing_cycle: str = "monthly",
    ) -> dict:
        if plan_code not in {
            "programming_suite",
            "professional",
            "enterprise",
        }:
            raise ValueError("A valid subscription plan is required.")
        if amount_cents < 0:
            raise ValueError("Subscription amount cannot be negative.")
        if billing_cycle != "monthly":
            raise ValueError("Stripe subscriptions currently bill monthly.")
        now = datetime.now(timezone.utc)
        with self._connection() as connection:
            organization = connection.execute(
                "SELECT id FROM organizations WHERE id = ?",
                (organization_id,),
            ).fetchone()
            if organization is None:
                raise KeyError("Organization not found.")
            connection.execute(
                """
                INSERT INTO subscriptions (
                    id, organization_id, status, billing_cycle, currency,
                    amount_cents, plan_code, provider,
                    current_period_start, current_period_end,
                    cancel_at_period_end, payment_waived,
                    created_at, updated_at
                ) VALUES (?, ?, 'past_due', 'monthly', 'USD', ?, ?,
                          'stripe_pending', ?, ?, 0, 0, ?, ?)
                ON CONFLICT (organization_id)
                DO UPDATE SET
                    status = 'past_due',
                    billing_cycle = 'monthly',
                    currency = 'USD',
                    amount_cents = excluded.amount_cents,
                    plan_code = excluded.plan_code,
                    provider = 'stripe_pending',
                    provider_customer_id = NULL,
                    provider_subscription_id = NULL,
                    current_period_start = excluded.current_period_start,
                    current_period_end = excluded.current_period_end,
                    cancel_at_period_end = 0,
                    payment_waived = 0,
                    waiver_reason = NULL,
                    waiver_expires_at = NULL,
                    waived_by_user_id = NULL,
                    payment_failed_at = NULL,
                    grace_period_ends_at = NULL,
                    updated_at = excluded.updated_at
                """,
                (
                    str(uuid4()),
                    organization_id,
                    amount_cents,
                    plan_code,
                    now.isoformat(),
                    (now + timedelta(days=30)).isoformat(),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            connection.execute(
                """
                INSERT INTO subscription_events (
                    id, organization_id, event_type, details, created_at
                ) VALUES (?, ?, 'payment_requested', ?, ?)
                """,
                (
                    str(uuid4()),
                    organization_id,
                    f"Stripe payment requested for {plan_code}.",
                    now.isoformat(),
                ),
            )
        return self.get_subscription(organization_id)

    def revise_pending_stripe_subscription(
        self,
        organization_id: str,
        *,
        plan_code: str,
        amount_cents: int,
    ) -> dict:
        if plan_code not in {
            "programming_suite", "professional", "enterprise"
        }:
            raise ValueError("A valid subscription plan is required.")
        internal_plan = (
            "starter" if plan_code == "programming_suite" else plan_code
        )
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE subscriptions
                SET plan_code = ?, amount_cents = ?, updated_at = ?
                WHERE organization_id = ? AND provider = 'stripe_pending'
                """,
                (plan_code, amount_cents, _utc_now(), organization_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("No pending Stripe subscription was found.")
            connection.execute(
                "UPDATE organizations SET plan = ?, updated_at = ? WHERE id = ?",
                (internal_plan, _utc_now(), organization_id),
            )
        return self.get_subscription(organization_id)

    def create_complimentary_subscription(
        self,
        organization_id: str,
        *,
        expires_at: datetime,
        reason: str,
        waived_by_user_id: str,
        billing_cycle: str = "monthly",
    ) -> dict:
        if billing_cycle not in {"monthly", "annual"}:
            raise ValueError("A valid billing cycle is required.")
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        expires_at = expires_at.astimezone(timezone.utc)
        now = datetime.now(timezone.utc)
        if expires_at <= now:
            raise ValueError(
                "Complimentary access must expire in the future."
            )
        reason = reason.strip()
        if len(reason) < 3:
            raise ValueError(
                "A reason is required when payment is waived."
            )
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO subscriptions (
                    id, organization_id, status, billing_cycle, currency,
                    amount_cents, provider, current_period_start,
                    current_period_end, cancel_at_period_end,
                    payment_waived, waiver_reason, waiver_expires_at,
                    waived_by_user_id, created_at, updated_at
                ) VALUES (?, ?, 'active', ?, 'USD', 0, 'complimentary',
                          ?, ?, 1, 1, ?, ?, ?, ?, ?)
                ON CONFLICT (organization_id)
                DO UPDATE SET
                    status = 'active',
                    billing_cycle = excluded.billing_cycle,
                    amount_cents = 0,
                    provider = 'complimentary',
                    current_period_start = excluded.current_period_start,
                    current_period_end = excluded.current_period_end,
                    cancel_at_period_end = 1,
                    payment_waived = 1,
                    waiver_reason = excluded.waiver_reason,
                    waiver_expires_at = excluded.waiver_expires_at,
                    waived_by_user_id = excluded.waived_by_user_id,
                    updated_at = excluded.updated_at
                """,
                (
                    str(uuid4()),
                    organization_id,
                    billing_cycle,
                    now.isoformat(),
                    expires_at.isoformat(),
                    reason,
                    expires_at.isoformat(),
                    waived_by_user_id,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
        return self.get_subscription(organization_id)

    def get_subscription(self, organization_id: str) -> dict:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT subscriptions.*, organizations.name AS organization_name,
                       COALESCE(subscriptions.plan_code, organizations.plan)
                           AS plan
                FROM subscriptions
                JOIN organizations
                    ON organizations.id = subscriptions.organization_id
                WHERE subscriptions.organization_id = ?
                """,
                (organization_id,),
            ).fetchone()
        if row is None:
            return self.ensure_subscription(organization_id)
        return self._serialize(row)

    def update_subscription(
        self,
        organization_id: str,
        *,
        status: str | None,
        billing_cycle: str | None,
        current_period_end: datetime | None,
        cancel_at_period_end: bool | None,
        lifecycle_note: str | None = None,
        actor_user_id: str | None = None,
    ) -> dict:
        self.ensure_subscription(organization_id)
        assignments: list[str] = []
        values: list[object] = []
        for field, value in (
            ("status", status),
            ("billing_cycle", billing_cycle),
        ):
            if value is not None:
                assignments.append(f"{field} = ?")
                values.append(value)
        if current_period_end is not None:
            if current_period_end.tzinfo is None:
                current_period_end = current_period_end.replace(
                    tzinfo=timezone.utc
                )
            assignments.append("current_period_end = ?")
            normalized_end = current_period_end.astimezone(
                timezone.utc
            ).isoformat()
            values.append(normalized_end)
            current = self.get_subscription(organization_id)
            if current["payment_waived"]:
                assignments.append("waiver_expires_at = ?")
                values.append(normalized_end)
        if cancel_at_period_end is not None:
            assignments.append("cancel_at_period_end = ?")
            values.append(int(cancel_at_period_end))
        if not assignments:
            raise ValueError("At least one subscription field is required.")
        assignments.append("updated_at = ?")
        values.append(_utc_now())
        values.append(organization_id)
        with self._connection() as connection:
            connection.execute(
                f"""
                UPDATE subscriptions
                SET {", ".join(assignments)}
                WHERE organization_id = ?
                """,
                values,
            )
            details = (lifecycle_note or "").strip() or (
                "Subscription lifecycle settings updated."
            )
            connection.execute(
                """
                INSERT INTO subscription_events (
                    id, organization_id, actor_user_id, event_type,
                    details, created_at
                ) VALUES (?, ?, ?, 'subscription_updated', ?, ?)
                """,
                (
                    str(uuid4()),
                    organization_id,
                    actor_user_id,
                    details,
                    _utc_now(),
                ),
            )
        return self.get_subscription(organization_id)

    def schedule_subscription_change(
        self,
        organization_id: str,
        *,
        plan_code: str,
        stream_monitoring: bool,
        change_at: str,
    ) -> dict:
        self.get_subscription(organization_id)
        with self._connection() as connection:
            now = _utc_now()
            connection.execute(
                """
                UPDATE subscriptions
                SET pending_plan_code = ?, pending_stream_monitoring = ?,
                    pending_change_at = ?, updated_at = ?
                WHERE organization_id = ?
                """,
                (
                    plan_code, int(stream_monitoring), change_at,
                    now, organization_id,
                ),
            )
            plan_name = {
                "programming_suite": "Programming Suite",
                "professional": "Professional",
                "enterprise": "Enterprise",
            }.get(plan_code, plan_code)
            monitoring = " with Stream Monitoring" if stream_monitoring else ""
            connection.execute(
                """
                INSERT INTO subscription_events (
                    id, organization_id, event_type, details, created_at
                ) VALUES (?, ?, 'subscription_change_scheduled', ?, ?)
                """,
                (
                    str(uuid4()), organization_id,
                    f"Subscription change to {plan_name}{monitoring} "
                    f"scheduled for {change_at}.",
                    now,
                ),
            )
        return self.get_subscription(organization_id)

    def record_subscription_change(
        self,
        organization_id: str,
        *,
        plan_code: str,
        stream_monitoring: bool,
        effective: str,
    ) -> None:
        plan_name = {
            "programming_suite": "Programming Suite",
            "professional": "Professional",
            "enterprise": "Enterprise",
        }.get(plan_code, plan_code)
        monitoring = " with Stream Monitoring" if stream_monitoring else ""
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO subscription_events (
                    id, organization_id, event_type, details, created_at
                ) VALUES (?, ?, 'subscription_change_applied', ?, ?)
                """,
                (
                    str(uuid4()), organization_id,
                    f"Subscription changed to {plan_name}{monitoring} "
                    f"{effective}.",
                    _utc_now(),
                ),
            )

    def clear_scheduled_change(self, organization_id: str) -> dict:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE subscriptions
                SET pending_plan_code = NULL,
                    pending_stream_monitoring = NULL,
                    pending_change_at = NULL, updated_at = ?
                WHERE organization_id = ?
                """,
                (_utc_now(), organization_id),
            )
        return self.get_subscription(organization_id)

    def subscription_events(
        self,
        organization_id: str,
        limit: int = 20,
    ) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT subscription_events.*
                FROM subscription_events
                WHERE subscription_events.organization_id = ?
                ORDER BY subscription_events.created_at DESC
                LIMIT ?
                """,
                (organization_id, min(max(limit, 1), 100)),
            ).fetchall()
        events = [dict(row) for row in rows]
        for event in events:
            event["actor_name"] = (
                "Administrator" if event["actor_user_id"] else "System"
            )
        return events

    def list_invoices(self, organization_id: str) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM invoices
                WHERE organization_id = ?
                ORDER BY invoice_date DESC
                """,
                (organization_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def provider_event_processed(self, provider_event_id: str) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM billing_provider_events
                WHERE provider_event_id = ?
                """,
                (provider_event_id,),
            ).fetchone()
        return row is not None

    def record_provider_event(
        self,
        provider_event_id: str,
        event_type: str,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO billing_provider_events (
                    provider_event_id, event_type, processed_at
                ) VALUES (?, ?, ?)
                """,
                (provider_event_id, event_type, _utc_now()),
            )

    def apply_stripe_subscription(
        self,
        organization_id: str,
        *,
        plan_code: str,
        stream_monitoring: bool,
        status: str,
        amount_cents: int,
        currency: str,
        customer_id: str,
        subscription_id: str,
        period_start: str,
        period_end: str,
        cancel_at_period_end: bool,
    ) -> dict:
        if plan_code not in {
            "programming_suite",
            "professional",
            "enterprise",
        }:
            raise ValueError("Stripe subscription contains an unknown plan.")
        internal_plan = (
            "starter" if plan_code == "programming_suite" else plan_code
        )
        traffic_enabled = plan_code == "professional"
        if plan_code == "enterprise":
            stream_monitoring = True
        now = _utc_now()
        with self._connection() as connection:
            organization = connection.execute(
                "SELECT id FROM organizations WHERE id = ?",
                (organization_id,),
            ).fetchone()
            if organization is None:
                raise KeyError("Organization not found.")
            connection.execute(
                """
                UPDATE organizations
                SET plan = ?, updated_at = ?
                WHERE id = ?
                """,
                (internal_plan, now, organization_id),
            )
            for addon_code, enabled in (
                ("traffic_operations", traffic_enabled),
                ("stream_monitoring", stream_monitoring),
            ):
                connection.execute(
                    """
                    INSERT INTO organization_addons (
                        organization_id, addon_code, enabled
                    ) VALUES (?, ?, ?)
                    ON CONFLICT (organization_id, addon_code)
                    DO UPDATE SET enabled = excluded.enabled
                    """,
                    (organization_id, addon_code, int(enabled)),
                )
            connection.execute(
                """
                INSERT INTO subscriptions (
                    id, organization_id, status, billing_cycle, currency,
                    amount_cents, plan_code, provider, provider_customer_id,
                    provider_subscription_id, current_period_start,
                    current_period_end, cancel_at_period_end,
                    payment_waived, waiver_reason, waiver_expires_at,
                    waived_by_user_id, created_at, updated_at
                ) VALUES (?, ?, ?, 'monthly', ?, ?, ?, 'stripe', ?, ?, ?, ?, ?,
                          0, NULL, NULL, NULL, ?, ?)
                ON CONFLICT (organization_id)
                DO UPDATE SET
                    status = excluded.status,
                    billing_cycle = 'monthly',
                    currency = excluded.currency,
                    amount_cents = excluded.amount_cents,
                    plan_code = excluded.plan_code,
                    provider = 'stripe',
                    provider_customer_id = excluded.provider_customer_id,
                    provider_subscription_id =
                        excluded.provider_subscription_id,
                    current_period_start = excluded.current_period_start,
                    current_period_end = excluded.current_period_end,
                    cancel_at_period_end = excluded.cancel_at_period_end,
                    payment_waived = 0,
                    waiver_reason = NULL,
                    waiver_expires_at = NULL,
                    waived_by_user_id = NULL,
                    payment_failed_at = CASE
                        WHEN excluded.status = 'active' THEN NULL
                        ELSE subscriptions.payment_failed_at
                    END,
                    grace_period_ends_at = CASE
                        WHEN excluded.status = 'active' THEN NULL
                        ELSE subscriptions.grace_period_ends_at
                    END,
                    updated_at = excluded.updated_at
                """,
                (
                    str(uuid4()),
                    organization_id,
                    status,
                    currency.upper(),
                    amount_cents,
                    plan_code,
                    customer_id,
                    subscription_id,
                    period_start,
                    period_end,
                    int(cancel_at_period_end),
                    now,
                    now,
                ),
            )
        return self.get_subscription(organization_id)

    def organization_for_provider_subscription(
        self,
        provider_subscription_id: str,
    ) -> str | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT organization_id FROM subscriptions
                WHERE provider_subscription_id = ?
                """,
                (provider_subscription_id,),
            ).fetchone()
        return row["organization_id"] if row else None

    def upsert_stripe_invoice(
        self,
        organization_id: str,
        *,
        provider_invoice_id: str,
        status: str,
        currency: str,
        amount_due_cents: int,
        amount_paid_cents: int,
        invoice_date: str,
        due_date: str | None,
        paid_at: str | None,
        hosted_invoice_url: str | None,
    ) -> None:
        subscription = self.get_subscription(organization_id)
        with self._connection() as connection:
            existing = connection.execute(
                "SELECT id FROM invoices WHERE provider_invoice_id = ?",
                (provider_invoice_id,),
            ).fetchone()
            if existing is not None:
                connection.execute(
                    """
                    UPDATE invoices
                    SET status = ?, currency = ?, amount_due_cents = ?,
                        amount_paid_cents = ?, invoice_date = ?, due_date = ?,
                        paid_at = ?, hosted_invoice_url = ?
                    WHERE provider_invoice_id = ?
                    """,
                    (
                        status, currency.upper(), amount_due_cents,
                        amount_paid_cents, invoice_date, due_date, paid_at,
                        hosted_invoice_url, provider_invoice_id,
                    ),
                )
                return
            connection.execute(
                """
                INSERT INTO invoices (
                    id, organization_id, subscription_id, status, currency,
                    amount_due_cents, amount_paid_cents, invoice_date,
                    due_date, paid_at, provider_invoice_id,
                    hosted_invoice_url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()), organization_id, subscription["id"],
                    status, currency.upper(), amount_due_cents,
                    amount_paid_cents, invoice_date, due_date, paid_at,
                    provider_invoice_id, hosted_invoice_url, _utc_now(),
                ),
            )

    @staticmethod
    def _serialize(row: sqlite3.Row) -> dict:
        result = dict(row)
        result["cancel_at_period_end"] = bool(
            result["cancel_at_period_end"]
        )
        result["payment_waived"] = bool(result["payment_waived"])
        if result.get("pending_stream_monitoring") is not None:
            result["pending_stream_monitoring"] = bool(
                result["pending_stream_monitoring"]
            )
        grace_end = result.get("grace_period_ends_at")
        grace_end_value = None
        if grace_end:
            grace_end_value = datetime.fromisoformat(grace_end)
            if grace_end_value.tzinfo is None:
                grace_end_value = grace_end_value.replace(tzinfo=timezone.utc)
        result["in_payment_grace"] = bool(
            result.get("provider") == "stripe"
            and result.get("status") == "past_due"
            and grace_end_value
            and grace_end_value > datetime.now(timezone.utc)
        )
        failed_at = result.get("payment_failed_at")
        result["payment_grace_hours"] = None
        if failed_at and grace_end_value:
            failed_at_value = datetime.fromisoformat(failed_at)
            if failed_at_value.tzinfo is None:
                failed_at_value = failed_at_value.replace(tzinfo=timezone.utc)
            result["payment_grace_hours"] = round(
                (grace_end_value - failed_at_value).total_seconds() / 3600
            )
        result["access_state"] = (
            "awaiting_payment"
            if result.get("provider") == "stripe_pending"
            else "payment_grace"
            if result["in_payment_grace"]
            else "payment_suspended"
            if result.get("provider") == "stripe"
            and result.get("status") == "past_due"
            else "active"
            if result.get("status") in {"active", "trialing"}
            else "canceled"
        )
        return result


billing_store = BillingStore()
billing_store.initialize()
