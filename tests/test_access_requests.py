from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

import pytest
from pydantic import ValidationError

from backend.main import app
from backend.models.admin import AccessRequestApproval
from backend.services.access_request_store import AccessRequestStore
from backend.services.billing_store import BillingStore
from backend.services.email_outbox import EmailOutboxStore
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


def test_access_request_preserves_requested_package_and_approved_override():
    with TemporaryDirectory() as directory:
        identities, _, _, requests = _stores(directory)
        access_request = requests.create(
            organization_name="Plan Network",
            contact_name="Plan Owner",
            email="plans@example.com",
            requested_plan="professional",
            include_stream_monitoring=True,
            billing_cycle="monthly",
        )
        user, organization, _ = identities.provision_customer(
            organization_name="Plan Network",
            display_name="Plan Owner",
            email="plans@example.com",
            plan="enterprise",
        )
        approved = requests.approve(
            access_request["id"],
            plan="enterprise",
            include_stream_monitoring=False,
            organization_id=organization["id"],
            user_id=user["id"],
        )

        assert approved["requested_plan"] == "professional"
        assert approved["include_stream_monitoring"] is True
        assert approved["assigned_plan"] == "enterprise"
        assert approved["assigned_stream_monitoring"] is False


def test_access_request_schema_migrates_existing_plan_constraint():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "access.db"
        with sqlite3.connect(database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript("""
                CREATE TABLE organizations (id TEXT PRIMARY KEY);
                CREATE TABLE users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE
                );
                CREATE TABLE access_requests (
                    id TEXT PRIMARY KEY,
                    organization_name TEXT NOT NULL,
                    contact_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    message TEXT,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (
                        status IN ('pending', 'approved', 'rejected')
                    ),
                    assigned_plan TEXT CHECK (
                        assigned_plan IN ('professional', 'enterprise')
                    ),
                    organization_id TEXT,
                    user_id TEXT,
                    existing_account INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
        requests = AccessRequestStore(database_path)
        requests.initialize()
        created = requests.create(
            organization_name="Programming Network",
            contact_name="Programming Owner",
            email="programming@example.com",
            requested_plan="programming_suite",
        )

        assert created["requested_plan"] == "programming_suite"


def test_access_request_and_activation_routes_are_registered():
    paths = set(app.openapi()["paths"])

    assert "/api/auth/access-requests" not in paths
    assert "/api/auth/signup" in paths
    assert "/api/auth/sales-inquiries" in paths
    assert "/api/auth/activate-account" in paths
    assert "/api/admin/access-requests" in paths
    assert "/api/admin/access-requests/{request_id}/approve" in paths
    assert "/api/admin/access-requests/{request_id}/reject" in paths


def test_sales_inquiry_contains_no_plan_or_billing_language():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "sales.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Broadcast Tool Pro",
            slug=None,
            plan="enterprise",
        )
        outbox = EmailOutboxStore(database_path)
        outbox.initialize()

        messages = outbox.schedule_sales_inquiry(
            notification_organization_id=organization["id"],
            reference="SALES-TEST123",
            organization_name="Sample TV",
            contact_name="Operator 2",
            requester_email="operator@example.com",
            request_message="Necesito un demo de la solución",
            sales_email="hello@broadcasttoolpro.com",
        )

        assert len(messages) == 2
        internal = next(
            message for message in messages
            if message["recipient_email"] == "hello@broadcasttoolpro.com"
        )
        assert internal["subject"] == "New sales inquiry: Sample TV"
        assert "Necesito un demo" in internal["body_text"]
        assert "Requested plan" not in internal["body_text"]
        assert "Billing cycle" not in internal["body_text"]
        assert "Stream Monitoring add-on" not in internal["body_text"]


def test_self_service_signup_queues_customer_and_admin_messages():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "signup-email.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="New Customer",
            slug=None,
            plan="professional",
        )
        outbox = EmailOutboxStore(database_path)
        outbox.initialize()

        messages = outbox.schedule_self_service_signup(
            organization_id=organization["id"],
            recipient_email="owner@example.com",
            administrator_emails=["hello@broadcasttoolpro.com"],
            organization_name="New Customer",
            plan_code="professional",
            include_stream_monitoring=True,
        )

        assert len(messages) == 2
        customer = next(
            message for message in messages
            if message["recipient_email"] == "owner@example.com"
        )
        administrator = next(
            message for message in messages
            if message["recipient_email"] == "hello@broadcasttoolpro.com"
        )
        assert customer["subject"] == (
            "Complete your Broadcast Tool Pro subscription"
        )
        assert "Stripe Checkout" in customer["body_text"]
        assert "awaiting Stripe payment" in administrator["body_text"]


def test_access_approval_represents_paid_and_complimentary_decisions():
    paid = AccessRequestApproval(plan="professional")
    complimentary = AccessRequestApproval(
        plan="enterprise",
        payment_method="complimentary",
        access_expires_at=(
            datetime.now(timezone.utc) + timedelta(days=30)
        ),
        waiver_reason="Controlled industry pilot",
    )

    assert paid.payment_method == "stripe"
    assert complimentary.payment_method == "complimentary"

    with pytest.raises(ValidationError):
        AccessRequestApproval(
            plan="enterprise",
            payment_method="complimentary",
        )

    with pytest.raises(ValidationError):
        AccessRequestApproval(
            plan="programming_suite",
            include_stream_monitoring=True,
        )


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


def test_access_request_schedules_requester_and_admin_notifications():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "access.db"
        identities, _, _, requests = _stores(directory)
        admin, organization, _ = identities.bootstrap(
            organization_name="Broadcast Tool Pro",
            display_name="Platform Admin",
            email="admin@example.com",
            password="secure-admin-password",
        )
        access_request = requests.create(
            organization_name="Pilot Network",
            contact_name="Operations Manager",
            email="operator@example.com",
            message="We want to evaluate traffic workflows.",
        )
        targets = identities.superuser_notification_targets()
        outbox = EmailOutboxStore(database_path)
        outbox.initialize()

        messages = outbox.schedule_access_request_received(
            notification_organization_id=organization["id"],
            request_id=access_request["id"],
            organization_name=access_request["organization_name"],
            contact_name=access_request["contact_name"],
            requester_email=access_request["email"],
            request_message=access_request["message"],
            administrator_emails=[target["email"] for target in targets],
        )

        assert admin["is_superuser"] is True
        assert len(messages) == 2
        assert {
            message["recipient_email"] for message in messages
        } == {"operator@example.com", "admin@example.com"}
        assert all(message["status"] == "queued" for message in messages)


def test_rejected_email_can_submit_a_future_access_request():
    with TemporaryDirectory() as directory:
        _, _, _, requests = _stores(directory)
        first = requests.create(
            organization_name="Returning Network",
            contact_name="Operations Manager",
            email="returning@example.com",
            message=None,
        )
        requests.reject(first["id"])

        second = requests.create(
            organization_name="Returning Network",
            contact_name="Operations Manager",
            email="returning@example.com",
            message="We are ready to reconsider the platform.",
        )

        assert second["id"] != first["id"]
        assert second["status"] == "pending"


def test_existing_suspended_account_can_request_and_regain_access():
    with TemporaryDirectory() as directory:
        identities, billing, _, requests = _stores(directory)
        user, organization, _ = identities.register_trial(
            organization_name="Returning Network",
            display_name="Operations Manager",
            email="existing@example.com",
            password="secure-trial-password",
        )
        billing.create_trial_subscription(organization["id"])
        with identities._connection() as connection:
            connection.execute(
                """
                UPDATE organizations SET status = 'suspended'
                WHERE id = ?
                """,
                (organization["id"],),
            )

        access_request = requests.create(
            organization_name="Returning Network",
            contact_name="Operations Manager",
            email="existing@example.com",
            message="We are ready for a paid plan.",
        )
        reactivated_user, reactivated_organization = (
            identities.reactivate_customer_account(
                "existing@example.com",
                "professional",
            )
        )

        assert access_request["existing_account"] is True
        assert reactivated_user["id"] == user["id"]
        assert reactivated_organization["id"] == organization["id"]
        assert reactivated_organization["status"] == "active"
        assert reactivated_organization["plan"] == "professional"
