from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.main import app
from backend.services.billing_store import BillingStore
from backend.services.tenant_store import TenantStore


def test_subscription_is_created_once_for_an_organization():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "billing.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Orion Media",
            slug=None,
            plan="professional",
        )
        billing = BillingStore(database_path)
        billing.initialize()

        first = billing.get_subscription(organization["id"])
        second = billing.get_subscription(organization["id"])

        assert first["id"] == second["id"]
        assert first["plan"] == "professional"
        assert first["status"] == "active"
        assert first["provider"] == "manual"
        assert first["amount_cents"] is None
        assert billing.list_invoices(organization["id"]) == []


def test_subscription_status_and_cycle_can_be_updated():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "billing.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Customer Network",
            slug=None,
            plan="professional",
        )
        billing = BillingStore(database_path)
        billing.initialize()
        period_end = datetime.now(timezone.utc) + timedelta(days=365)

        result = billing.update_subscription(
            organization["id"],
            status="trialing",
            billing_cycle="annual",
            current_period_end=period_end,
            cancel_at_period_end=True,
        )

        assert result["status"] == "trialing"
        assert result["billing_cycle"] == "annual"
        assert result["cancel_at_period_end"] is True


def test_billing_routes_are_registered():
    paths = set(app.openapi()["paths"])

    assert "/api/billing/organizations/{organization_id}" in paths
    assert (
        "/api/admin/organizations/{organization_id}/subscription"
        in paths
    )

