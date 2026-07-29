from pathlib import Path
from tempfile import TemporaryDirectory

from backend.main import app
from backend.services.admin_store import AdminStore
from backend.services.entitlements import EntitlementStore
from backend.services.identity_store import IdentityStore
from backend.services.tenant_store import TenantStore


def test_control_plane_reports_platform_state():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "admin.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        identities = IdentityStore(database_path)
        identities.initialize()
        user, organization, _ = identities.bootstrap(
            organization_name="Tarima Media",
            display_name="Platform Owner",
            email="owner@example.com",
            password="a-secure-password",
        )
        workspace = tenants.create_workspace(
            organization_id=organization["id"],
            name="Operations",
            slug=None,
            default_timezone="America/New_York",
        )
        tenants.create_channel(
            workspace_id=workspace["id"],
            name="Tarima TV",
            slug=None,
            channel_code="TRMATV",
            timezone="America/New_York",
            primary_language="es",
        )
        admin = AdminStore(database_path)
        admin.initialize()

        overview = admin.overview()
        organizations = admin.organizations()

        assert user["is_superuser"] is True
        assert overview["organizations"] == 1
        assert overview["users"] == 1
        assert overview["channels"] == 1
        assert organizations[0]["member_count"] == 1
        assert organizations[0]["channel_count"] == 1


def test_control_plane_manages_addons_and_incidents():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "admin.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        identities = IdentityStore(database_path)
        identities.initialize()
        organization = tenants.create_organization(
            name="Customer Network",
            slug=None,
            plan="professional",
        )
        entitlements = EntitlementStore(database_path)
        entitlements.initialize()
        admin = AdminStore(database_path)
        admin.initialize()

        entitlements.set_addon(
            organization["id"],
            "stream_monitoring",
            True,
        )
        incident_id = admin.record_incident(
            organization_id=organization["id"],
            module="hls_monitor",
            severity="critical",
            summary="Stream inspection failed.",
        )

        assert entitlements.effective_entitlements(
            organization["id"]
        )["modules"]["hls_monitor"]["enabled"] is True
        assert admin.overview()["open_incidents"] == 1
        assert admin.list_incidents()[0]["id"] == incident_id


def test_super_admin_routes_are_registered():
    paths = set(app.openapi()["paths"])

    assert "/api/admin/overview" in paths
    assert "/api/admin/organizations" in paths
    assert "/api/admin/incidents" in paths
    assert "/api/admin/incidents/{incident_id}" in paths
    assert "/api/admin/backups" in paths
