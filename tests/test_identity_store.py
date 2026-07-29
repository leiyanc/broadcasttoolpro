from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta, timezone

from backend.main import app
from backend.services.billing_store import BillingStore
from backend.services.entitlements import EntitlementStore
from backend.services.email_outbox import EmailOutboxStore
from backend.services.identity_store import (
    AuthenticationLockedError,
    IdentityStore,
)
from backend.services.tenant_store import TenantStore


def _stores(directory: str) -> tuple[TenantStore, IdentityStore]:
    database_path = Path(directory) / "identity.db"
    tenants = TenantStore(database_path)
    tenants.initialize()
    identities = IdentityStore(database_path)
    identities.initialize()
    return tenants, identities


def test_bootstrap_creates_owner_and_secure_session():
    with TemporaryDirectory() as directory:
        _, identities = _stores(directory)

        user, organization, token = identities.bootstrap(
            organization_name="Tarima Media",
            display_name="Platform Owner",
            email="owner@example.com",
            password="a-secure-password",
        )

        assert organization["role"] == "owner"
        assert identities.user_from_session(token) == user
        assert "password" not in user

        authenticated, second_token = identities.authenticate(
            "owner@example.com",
            "a-secure-password",
        )
        assert authenticated == user
        assert identities.user_from_session(second_token) == user

        identities.revoke_session(second_token)
        assert identities.user_from_session(second_token) is None

        remembered_user, remembered_token = identities.authenticate(
            "owner@example.com",
            "a-secure-password",
            session_hours=30 * 24,
        )
        assert remembered_user == user
        assert identities.user_from_session(remembered_token) == user


def test_roles_are_scoped_to_each_organization():
    with TemporaryDirectory() as directory:
        tenants, identities = _stores(directory)
        owner, first_organization, _ = identities.bootstrap(
            organization_name="First Network",
            display_name="Owner",
            email="owner@example.com",
            password="a-secure-password",
        )
        second_organization = tenants.create_organization(
            name="Second Network",
            slug=None,
            plan="professional",
        )
        identities.add_membership(
            organization_id=second_organization["id"],
            user_id=owner["id"],
            role="viewer",
        )

        member = identities.create_member(
            organization_id=first_organization["id"],
            display_name="Operator",
            email="operator@example.com",
            password="another-secure-password",
            role="operator",
        )

        assert identities.require_role(
            member["id"],
            first_organization["id"],
            "operator",
        )["role"] == "operator"
        try:
            identities.require_role(
                member["id"],
                first_organization["id"],
                "admin",
            )
        except PermissionError as exc:
            assert "admin" in str(exc)
        else:
            raise AssertionError("Expected the admin role check to fail.")

        assert identities.require_role(
            owner["id"],
            second_organization["id"],
            "viewer",
        )["role"] == "viewer"


def test_authentication_routes_are_registered():
    paths = set(app.openapi()["paths"])

    assert "/api/auth/bootstrap" in paths
    assert "/api/auth/status" in paths
    assert "/api/auth/login" in paths
    assert "/api/auth/trial" in paths
    assert "/api/auth/me" in paths
    assert "/api/auth/logout" in paths
    assert "/api/auth/password-reset/request" in paths
    assert "/api/auth/password-reset/confirm" in paths
    assert "/api/admin/security-events" in paths
    assert (
        "/api/auth/organizations/{organization_id}/members"
        in paths
    )


def test_trial_registration_is_limited_to_three_modules():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "trial.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        identities = IdentityStore(database_path)
        identities.initialize()
        billing = BillingStore(database_path)
        billing.initialize()
        entitlements = EntitlementStore(database_path)
        entitlements.initialize()

        user, organization, token = identities.register_trial(
            organization_name="Trial Network",
            display_name="Trial Owner",
            email="trial@example.com",
            password="a-secure-password",
        )
        subscription = billing.create_trial_subscription(
            organization["id"],
            days=7,
        )
        access = entitlements.effective_entitlements(organization["id"])

        assert identities.user_from_session(token) == user
        assert user["is_superuser"] is False
        assert subscription["status"] == "trialing"
        assert access["access"]["type"] == "trial"
        assert access["access"]["download_formats"] == ["pdf"]
        assert access["access"]["watermark"] is True
        assert access["modules"]["xmltv_validator"]["enabled"] is True
        assert access["modules"]["prelogs"]["enabled"] is True
        assert access["modules"]["hls_validator"]["enabled"] is True
        assert access["modules"]["xmltv_generator"]["enabled"] is False
        assert access["modules"]["xmltv_repair"]["enabled"] is False
        assert access["modules"]["postlogs"]["enabled"] is False
        assert access["modules"]["hls_monitor"]["enabled"] is False

        outbox = EmailOutboxStore(database_path)
        outbox.initialize()
        communications = outbox.schedule_trial_lifecycle(
            organization_id=organization["id"],
            recipient_email=user["email"],
            trial_ends_at=subscription["current_period_end"],
        )
        assert len(communications) == 4
        assert communications[0]["template_code"] == "trial_welcome"
        assert communications[-1]["template_code"] == "trial_expired"
        assert len(outbox.pending()) == 1

        billing.update_subscription(
            organization["id"],
            status="trialing",
            billing_cycle=None,
            current_period_end=(
                datetime.now(timezone.utc) - timedelta(minutes=1)
            ),
            cancel_at_period_end=True,
        )
        expired = entitlements.effective_entitlements(organization["id"])
        assert expired["access"]["active"] is False
        assert not any(
            module["enabled"]
            for module in expired["modules"].values()
        )


def test_failed_logins_are_temporarily_locked_and_audited():
    with TemporaryDirectory() as directory:
        _, identities = _stores(directory)
        identities.bootstrap(
            organization_name="Secure Network",
            display_name="Owner",
            email="owner@example.com",
            password="a-secure-password",
        )

        for _ in range(5):
            try:
                identities.authenticate(
                    "owner@example.com",
                    "incorrect-password",
                )
            except ValueError:
                pass

        try:
            identities.authenticate(
                "owner@example.com",
                "a-secure-password",
            )
        except AuthenticationLockedError:
            pass
        else:
            raise AssertionError("The temporary login lock was not enforced.")

        event_types = {
            event["event_type"]
            for event in identities.security_events()
        }
        assert "login_failed" in event_types
        assert "login_blocked" in event_types


def test_password_reset_is_single_use_and_revokes_existing_sessions():
    with TemporaryDirectory() as directory:
        _, identities = _stores(directory)
        user, _, original_session = identities.bootstrap(
            organization_name="Recovery Network",
            display_name="Owner",
            email="owner@example.com",
            password="a-secure-password",
        )
        reset = identities.create_password_reset("owner@example.com")
        assert reset is not None
        _, token = reset

        identities.reset_password(token, "a-new-secure-password")

        assert identities.user_from_session(original_session) is None
        authenticated, _ = identities.authenticate(
            "owner@example.com",
            "a-new-secure-password",
        )
        assert authenticated["id"] == user["id"]
        try:
            identities.reset_password(token, "another-secure-password")
        except ValueError:
            pass
        else:
            raise AssertionError("A reset token must be single use.")
