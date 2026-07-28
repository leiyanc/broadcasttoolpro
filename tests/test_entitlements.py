from pathlib import Path
from tempfile import TemporaryDirectory

from backend.main import app
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
        entitlements = EntitlementStore(database_path)
        entitlements.initialize()

        result = entitlements.effective_entitlements(organization["id"])

        assert result["modules"]["xmltv_generator"]["enabled"] is True
        assert result["modules"]["hls_validator"]["enabled"] is True
        assert result["modules"]["prelogs"]["enabled"] is False
        assert result["modules"]["hls_monitor"]["enabled"] is False
        assert result["modules"]["media_qc"]["available"] is False
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


def test_entitlement_route_is_registered():
    paths = set(app.openapi()["paths"])

    assert (
        "/api/platform/organizations/{organization_id}/entitlements"
        in paths
    )
