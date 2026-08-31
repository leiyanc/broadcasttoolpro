from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta, timezone

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
            plan="professional",
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
            plan="professional",
        )
        second = store.create_organization(
            name="Second Network",
            slug=None,
            plan="professional",
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
    assert (
        "/api/billing/organizations/{organization_id}/channels/"
        "{channel_id}/removal/preview"
    ) in paths
    assert (
        "/api/billing/organizations/{organization_id}/channels/"
        "{channel_id}/removal"
    ) in paths
    assert (
        "/api/billing/organizations/{organization_id}/channels/"
        "{channel_id}/removal/cancel"
    ) in paths


def test_channel_deactivation_can_be_scheduled_canceled_and_applied():
    with TemporaryDirectory() as directory:
        store = TenantStore(Path(directory) / "channel-deactivation.db")
        store.initialize()
        organization = store.create_organization(
            name="Lifecycle Network", slug=None, plan="professional"
        )
        workspace = store.create_workspace(
            organization_id=organization["id"],
            name="Operations",
            slug=None,
            default_timezone="UTC",
        )
        channel = store.create_channel(
            workspace_id=workspace["id"],
            name="Lifecycle TV",
            slug=None,
            channel_code="lifecycle-tv",
            timezone="UTC",
            primary_language="en",
        )
        future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        scheduled = store.schedule_channel_deactivation(
            channel["id"], effective_at=future
        )
        assert scheduled["active"] is True
        assert scheduled["deactivation_scheduled_at"] == future

        canceled = store.cancel_channel_deactivation(channel["id"])
        assert canceled["active"] is True
        assert canceled["deactivation_scheduled_at"] is None

        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        store.schedule_channel_deactivation(channel["id"], effective_at=past)
        channels = store.list_organization_channels(organization["id"])
        assert channels[0]["active"] is False
        assert channels[0]["deactivation_scheduled_at"] is None
