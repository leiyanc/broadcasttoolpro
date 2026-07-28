from pathlib import Path
from tempfile import TemporaryDirectory

from backend.main import app
from backend.services.identity_store import IdentityStore
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
            plan="starter",
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
    assert "/api/auth/login" in paths
    assert "/api/auth/me" in paths
    assert "/api/auth/logout" in paths
    assert (
        "/api/auth/organizations/{organization_id}/members"
        in paths
    )

