from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.main import app
from backend.services.access_request_store import AccessRequestStore
from backend.services.billing_store import BillingStore
from backend.services.entitlements import EntitlementStore
from backend.services.identity_store import IdentityStore
from backend.services.tenant_store import TenantStore


def _stores(directory: str):
    database_path = Path(directory) / "access.db"
    tenants = TenantStore(database_path)
    tenants.initialize()
    identities = IdentityStore(database_path)
    identities.initialize()
    billing = BillingStore(database_path)
    billing.initialize()
    entitlements = EntitlementStore(database_path)
    entitlements.initialize()
    requests = AccessRequestStore(database_path)
    requests.initialize()
    return identities, billing, entitlements, requests


def test_paid_access_request_is_separate_from_trial():
    with TemporaryDirectory() as directory:
        identities, billing, entitlements, requests = _stores(directory)
        access_request = requests.create(
            organization_name="Paid Network",
            contact_name="Account Owner",
            email="owner@paid.example",
            message="We need programming and traffic workflows.",
        )
        user, organization, token = identities.provision_customer(
            organization_name=access_request["organization_name"],
            display_name=access_request["contact_name"],
            email=access_request["email"],
            plan="professional",
        )
        billing.create_manual_paid_subscription(
            organization["id"],
            amount_cents=9900,
        )
        entitlements.set_addon(
            organization["id"],
            "traffic_operations",
            True,
        )
        approved = requests.approve(
            access_request["id"],
            plan="professional",
            organization_id=organization["id"],
            user_id=user["id"],
        )

        assert approved["status"] == "approved"
        assert approved["assigned_plan"] == "professional"
        assert billing.get_subscription(organization["id"])["status"] == "active"
        access = entitlements.effective_entitlements(organization["id"])
        assert access["access"]["type"] == "paid"
        assert access["modules"]["prelogs"]["enabled"] is True

        activated, session = identities.activate_account(
            token,
            "customer-secure-password",
        )
        assert activated["status"] == "active"
        assert identities.user_from_session(session)["id"] == user["id"]


def test_access_request_and_activation_routes_are_registered():
    paths = set(app.openapi()["paths"])

    assert "/api/auth/access-requests" in paths
    assert "/api/auth/activate-account" in paths
    assert "/api/admin/access-requests" in paths
    assert "/api/admin/access-requests/{request_id}/approve" in paths
    assert "/api/admin/access-requests/{request_id}/reject" in paths


def test_complimentary_enterprise_access_expires_automatically():
    with TemporaryDirectory() as directory:
        identities, billing, entitlements, _ = _stores(directory)
        user, organization, _ = identities.provision_customer(
            organization_name="Industry Evaluator",
            display_name="Broadcast Expert",
            email="expert@example.com",
            plan="enterprise",
        )
        subscription = billing.create_complimentary_subscription(
            organization["id"],
            expires_at=(
                datetime.now(timezone.utc) + timedelta(days=30)
            ),
            reason="Industry evaluator",
            waived_by_user_id=user["id"],
        )

        access = entitlements.effective_entitlements(organization["id"])

        assert subscription["payment_waived"] is True
        assert subscription["provider"] == "complimentary"
        assert subscription["amount_cents"] == 0
        assert access["access"]["type"] == "complimentary"
        assert access["access"]["active"] is True
        assert access["modules"]["hls_monitor"]["enabled"] is True

        expired_at = (
            datetime.now(timezone.utc) - timedelta(minutes=1)
        ).isoformat()
        with billing._connection() as connection:
            connection.execute(
                """
                UPDATE subscriptions
                SET waiver_expires_at = ?, current_period_end = ?
                WHERE organization_id = ?
                """,
                (expired_at, expired_at, organization["id"]),
            )

        expired = entitlements.effective_entitlements(organization["id"])
        assert expired["access"]["active"] is False
        assert not any(
            module["enabled"]
            for module in expired["modules"].values()
        )
