from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.main import app
from backend.services.billing_store import BillingStore
from backend.services.commercial_pricing import commercial_pricing
from backend.services.tenant_store import TenantStore
from backend.services.entitlements import EntitlementStore


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
            lifecycle_note="Annual access scheduled to end.",
        )

        assert result["status"] == "trialing"
        assert result["billing_cycle"] == "annual"
        assert result["cancel_at_period_end"] is True
        events = billing.subscription_events(organization["id"])
        assert len(events) == 1
        assert events[0]["details"] == "Annual access scheduled to end."


def test_pending_stripe_subscription_preserves_commercial_plan():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "billing.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Pending Customer",
            slug=None,
            plan="professional",
        )
        billing = BillingStore(database_path)
        billing.initialize()

        result = billing.create_pending_stripe_subscription(
            organization["id"],
            plan_code="programming_suite",
            amount_cents=3900,
        )

        assert result["status"] == "past_due"
        assert result["provider"] == "stripe_pending"
        assert result["plan"] == "programming_suite"
        assert result["amount_cents"] == 3900
        events = billing.subscription_events(organization["id"])
        assert events[0]["event_type"] == "payment_requested"


def test_complimentary_extension_updates_the_enforced_expiration():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "billing.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Pilot Network",
            slug=None,
            plan="enterprise",
        )
        billing = BillingStore(database_path)
        billing.initialize()
        original_end = datetime.now(timezone.utc) + timedelta(days=30)
        extended_end = datetime.now(timezone.utc) + timedelta(days=60)
        billing.create_complimentary_subscription(
            organization["id"],
            expires_at=original_end,
            reason="Initial pilot",
            waived_by_user_id="admin-user",
        )

        result = billing.update_subscription(
            organization["id"],
            status="active",
            billing_cycle=None,
            current_period_end=extended_end,
            cancel_at_period_end=True,
            lifecycle_note="Pilot extended after review.",
        )

        assert result["waiver_expires_at"] == extended_end.isoformat()
        assert result["current_period_end"] == extended_end.isoformat()


def test_failed_stripe_payment_has_grace_then_suspends_access():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "billing.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Grace Network", slug=None, plan="professional"
        )
        entitlements = EntitlementStore(database_path)
        entitlements.initialize()
        billing = BillingStore(database_path)
        billing.initialize()
        now = datetime.now(timezone.utc)
        billing.apply_stripe_subscription(
            organization["id"],
            plan_code="professional",
            stream_monitoring=False,
            status="active",
            amount_cents=9900,
            currency="usd",
            customer_id="cus_grace",
            subscription_id="sub_grace",
            period_start=now.isoformat(),
            period_end=(now + timedelta(days=30)).isoformat(),
            cancel_at_period_end=False,
        )

        failed = billing.mark_payment_failed(
            organization["id"], grace_hours=72
        )
        during_grace = entitlements.effective_entitlements(
            organization["id"]
        )

        assert failed["status"] == "past_due"
        assert failed["access_state"] == "payment_grace"
        assert during_grace["access"]["active"] is True
        assert during_grace["access"]["type"] == "payment_grace"

        with billing._connection() as connection:
            connection.execute(
                "UPDATE subscriptions SET grace_period_ends_at = ? "
                "WHERE organization_id = ?",
                (
                    (now - timedelta(minutes=1)).isoformat(),
                    organization["id"],
                ),
            )

        suspended = billing.get_subscription(organization["id"])
        blocked = entitlements.effective_entitlements(organization["id"])
        assert suspended["access_state"] == "payment_suspended"
        assert blocked["access"]["active"] is False


def test_successful_stripe_renewal_clears_payment_grace():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "billing.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Recovered Network", slug=None, plan="professional"
        )
        EntitlementStore(database_path).initialize()
        billing = BillingStore(database_path)
        billing.initialize()
        now = datetime.now(timezone.utc)
        common = {
            "organization_id": organization["id"],
            "plan_code": "professional",
            "stream_monitoring": False,
            "amount_cents": 9900,
            "currency": "usd",
            "customer_id": "cus_recovered",
            "subscription_id": "sub_recovered",
            "period_start": now.isoformat(),
            "period_end": (now + timedelta(days=30)).isoformat(),
            "cancel_at_period_end": False,
        }
        billing.apply_stripe_subscription(status="active", **common)
        billing.mark_payment_failed(organization["id"], grace_hours=72)

        recovered = billing.apply_stripe_subscription(
            status="active", **common
        )

        assert recovered["access_state"] == "active"
        assert recovered["payment_failed_at"] is None
        assert recovered["grace_period_ends_at"] is None


def test_billing_routes_are_registered():
    paths = set(app.openapi()["paths"])

    assert "/api/billing/organizations/{organization_id}" in paths
    assert (
        "/api/admin/organizations/{organization_id}/subscription"
        in paths
    )
    assert (
        "/api/billing/organizations/{organization_id}/checkout"
        in paths
    )
    assert "/api/billing/stripe/webhook" in paths


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
    assert enterprise["monthly_total_cents"] == 19900
    assert enterprise["billing_total_cents"] == 238800
