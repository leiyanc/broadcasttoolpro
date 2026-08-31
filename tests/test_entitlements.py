from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.main import app
from backend.services.billing_store import BillingStore
from backend.services.entitlements import EntitlementStore
from backend.services.tenant_store import TenantStore


def test_professional_plan_and_addons_are_separated():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "entitlements.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Tarima Media",
            slug=None,
            plan="professional",
        )
        billing = BillingStore(database_path)
        billing.initialize()
        billing.get_subscription(organization["id"])
        entitlements = EntitlementStore(database_path)
        entitlements.initialize()

        result = entitlements.effective_entitlements(organization["id"])

        assert result["modules"]["xmltv_generator"]["enabled"] is True
        assert result["modules"]["hls_validator"]["enabled"] is True
        assert result["modules"]["prelogs"]["enabled"] is False
        assert result["modules"]["hls_monitor"]["enabled"] is False
        assert result["modules"]["media_qc"]["available"] is True
        assert result["modules"]["media_qc"]["enabled"] is False

        entitlements.set_addon(
            organization["id"],
            "traffic_operations",
            True,
        )
        result = entitlements.effective_entitlements(organization["id"])
        assert result["modules"]["prelogs"]["enabled"] is True
        assert result["modules"]["postlogs"]["enabled"] is True
        assert result["modules"]["hls_monitor"]["enabled"] is False


def test_enterprise_plan_enables_media_loudness_compliance():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "entitlements.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Enterprise Network",
            slug=None,
            plan="enterprise",
        )
        billing = BillingStore(database_path)
        billing.initialize()
        billing.get_subscription(organization["id"])
        entitlements = EntitlementStore(database_path)
        entitlements.initialize()

        result = entitlements.effective_entitlements(organization["id"])

        assert result["modules"]["media_qc"]["available"] is True
        assert result["modules"]["media_qc"]["enabled"] is True


def test_stream_monitoring_addon_enables_media_loudness_compliance():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "entitlements.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Professional Network",
            slug=None,
            plan="professional",
        )
        billing = BillingStore(database_path)
        billing.initialize()
        billing.get_subscription(organization["id"])
        entitlements = EntitlementStore(database_path)
        entitlements.initialize()
        entitlements.set_addon(
            organization["id"],
            "stream_monitoring",
            True,
        )

        result = entitlements.effective_entitlements(organization["id"])

        assert result["modules"]["hls_monitor"]["enabled"] is True
        assert result["modules"]["media_qc"]["enabled"] is True


def test_entitlement_route_is_registered():
    paths = set(app.openapi()["paths"])

    assert (
        "/api/platform/organizations/{organization_id}/entitlements"
        in paths
    )


def test_canceled_subscription_blocks_product_access():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "entitlements.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Canceled Network",
            slug=None,
            plan="professional",
        )
        billing = BillingStore(database_path)
        billing.initialize()
        billing.create_manual_paid_subscription(
            organization["id"],
            amount_cents=9900,
        )
        billing.update_subscription(
            organization["id"],
            status="canceled",
            billing_cycle=None,
            current_period_end=None,
            cancel_at_period_end=None,
        )
        entitlements = EntitlementStore(database_path)
        entitlements.initialize()

        result = entitlements.effective_entitlements(organization["id"])

        assert result["access"]["active"] is False
        assert not any(
            module["enabled"] for module in result["modules"].values()
        )


def test_cancel_at_period_end_expires_automatically():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "entitlements.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Ending Network",
            slug=None,
            plan="professional",
        )
        billing = BillingStore(database_path)
        billing.initialize()
        billing.create_manual_paid_subscription(
            organization["id"],
            amount_cents=9900,
        )
        future_end = datetime.now(timezone.utc) + timedelta(days=7)
        billing.update_subscription(
            organization["id"],
            status=None,
            billing_cycle=None,
            current_period_end=future_end,
            cancel_at_period_end=True,
        )
        entitlements = EntitlementStore(database_path)
        entitlements.initialize()

        current = entitlements.effective_entitlements(organization["id"])
        assert current["access"]["active"] is True
        assert current["access"]["ends_at"] == future_end.isoformat()

        billing.update_subscription(
            organization["id"],
            status=None,
            billing_cycle=None,
            current_period_end=(
                datetime.now(timezone.utc) - timedelta(minutes=1)
            ),
            cancel_at_period_end=True,
        )
        expired = entitlements.effective_entitlements(organization["id"])
        assert expired["access"]["active"] is False
