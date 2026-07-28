from pathlib import Path
from tempfile import TemporaryDirectory

from backend.main import app
from backend.services.tenant_store import TenantStore


def test_tenant_hierarchy_is_persisted_and_isolated():
    with TemporaryDirectory() as directory:
        store = TenantStore(Path(directory) / "tenants.db")
        store.initialize()

        organization = store.create_organization(
            name="Tarima Media",
            slug=None,
            plan="professional",
        )
        other_organization = store.create_organization(
            name="Other Network",
            slug=None,
            plan="starter",
        )
        workspace = store.create_workspace(
            organization_id=organization["id"],
            name="FAST Operations",
            slug=None,
            default_timezone="America/New_York",
        )
        other_workspace = store.create_workspace(
            organization_id=other_organization["id"],
            name="FAST Operations",
            slug=None,
            default_timezone="UTC",
        )
        channel = store.create_channel(
            workspace_id=workspace["id"],
            name="Tarima TV",
            slug=None,
            channel_code="TRMATV",
            timezone="America/New_York",
            primary_language="es",
        )

        assert store.list_workspaces(organization["id"]) == [workspace]
        assert store.list_workspaces(other_organization["id"]) == [
            other_workspace
        ]
        assert store.list_channels(workspace["id"]) == [channel]
        assert store.list_channels(other_workspace["id"]) == []
        assert channel["active"] is True


def test_duplicate_slugs_are_scoped_to_the_parent():
    with TemporaryDirectory() as directory:
        store = TenantStore(Path(directory) / "tenants.db")
        store.initialize()
        first = store.create_organization(
            name="First Network",
            slug=None,
            plan="starter",
        )
        second = store.create_organization(
            name="Second Network",
            slug=None,
            plan="starter",
        )

        store.create_workspace(
            organization_id=first["id"],
            name="Operations",
            slug=None,
            default_timezone="UTC",
        )
        store.create_workspace(
            organization_id=second["id"],
            name="Operations",
            slug=None,
            default_timezone="UTC",
        )

        try:
            store.create_workspace(
                organization_id=first["id"],
                name="Operations",
                slug=None,
                default_timezone="UTC",
            )
        except ValueError as exc:
            assert "already in use" in str(exc)
        else:
            raise AssertionError("Expected a duplicate workspace slug error.")


def test_platform_routes_are_registered():
    paths = set(app.openapi()["paths"])

    assert "/api/platform/organizations" in paths
    assert (
        "/api/platform/organizations/{organization_id}/workspaces"
        in paths
    )
    assert "/api/platform/workspaces/{workspace_id}/channels" in paths

