from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.main import app
from backend.services.billing_store import BillingStore
from backend.services.commercial_pricing import commercial_pricing
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


def test_commercial_pricing_uses_plan_and_addons():
    base_entitlements = {
        "addons": [
            {"code": "traffic_operations", "enabled": False},
            {"code": "stream_monitoring", "enabled": False},
        ]
    }
    programming = commercial_pricing(
        "professional",
        base_entitlements,
    )
    assert programming["display_name"] == "Programming Suite"
    assert programming["monthly_total_cents"] == 3900
    assert len(programming["available_plans"]) == 3
    assert programming["available_addons"][0]["monthly_cents"] == 5900

    professional = commercial_pricing(
        "professional",
        {
            "addons": [
                {"code": "traffic_operations", "enabled": True},
                {"code": "stream_monitoring", "enabled": False},
            ]
        },
    )
    assert professional["display_name"] == "Professional"
    assert professional["monthly_total_cents"] == 9900

    monitored = commercial_pricing(
        "professional",
        {
            "addons": [
                {"code": "traffic_operations", "enabled": True},
                {"code": "stream_monitoring", "enabled": True},
            ]
        },
    )
    assert monitored["monthly_total_cents"] == 15800

    enterprise = commercial_pricing(
        "enterprise",
        base_entitlements,
        "annual",
    )
    assert enterprise["monthly_total_cents"] == 24900
    assert enterprise["billing_total_cents"] == 298800
