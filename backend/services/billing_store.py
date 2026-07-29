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
                    provider TEXT NOT NULL DEFAULT 'manual',
                    provider_customer_id TEXT,
                    provider_subscription_id TEXT,
                    current_period_start TEXT NOT NULL,
                    current_period_end TEXT NOT NULL,
                    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
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
            """)

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

    def get_subscription(self, organization_id: str) -> dict:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT subscriptions.*, organizations.name AS organization_name,
                       organizations.plan
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
            values.append(current_period_end.astimezone(timezone.utc).isoformat())
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
        return self.get_subscription(organization_id)

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

    @staticmethod
    def _serialize(row: sqlite3.Row) -> dict:
        result = dict(row)
        result["cancel_at_period_end"] = bool(
            result["cancel_at_period_end"]
        )
        return result


billing_store = BillingStore()
billing_store.initialize()
