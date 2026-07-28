from pathlib import Path
from tempfile import TemporaryDirectory

from backend.main import app
from backend.services.admin_store import AdminStore
from backend.services.identity_store import IdentityStore
from backend.services.tenant_store import TenantStore


def test_user_support_requests_can_be_created_and_tracked():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "support.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        identities = IdentityStore(database_path)
        identities.initialize()
        user, organization, _ = identities.bootstrap(
            organization_name="Orion Media",
            display_name="Platform Owner",
            email="owner@example.com",
            password="a-secure-password",
        )
        support = AdminStore(database_path)
        support.initialize()

        incident_id = support.record_incident(
            organization_id=organization["id"],
            reporter_user_id=user["id"],
            module="XMLTV Validator",
            category="validation",
            severity="warning",
            priority="high",
            summary="Validation result needs review",
            details="The same timestamp warning appears on every programme.",
            error_message="VAL-010: Timestamp could not be normalized.",
        )

        requests = support.list_user_incidents(user["id"])
        assert requests[0]["id"] == incident_id
        assert requests[0]["status"] == "open"
        assert requests[0]["category"] == "validation"
        updated = support.update_incident_status(
            incident_id,
            "investigating",
        )
        assert updated["status"] == "investigating"
        customer_message = support.add_incident_message(
            incident_id,
            author_user_id=user["id"],
            visibility="customer",
            message="I can reproduce this with the latest file.",
        )
        support.add_incident_message(
            incident_id,
            author_user_id=user["id"],
            visibility="internal",
            message="Internal diagnostic note.",
        )
        customer_detail = support.get_incident(
            incident_id,
            reporter_user_id=user["id"],
            customer_view=True,
        )
        assert customer_detail["messages"] == [
            {
                **customer_message,
                "author_name": "Platform Owner",
            }
        ]
        resolved = support.update_incident_status(
            incident_id,
            "resolved",
            actor_user_id=user["id"],
            resolution="The timestamp mapping was corrected.",
        )
        assert resolved["resolution"] == (
            "The timestamp mapping was corrected."
        )
        admin_requests = support.list_incidents()
        assert admin_requests[0]["reporter_name"] == "Platform Owner"
        assert admin_requests[0]["reporter_email"] == "owner@example.com"


def test_support_routes_are_registered():
    paths = set(app.openapi()["paths"])

    assert "/api/support/requests" in paths
    assert "/api/support/requests/{incident_id}" in paths
    assert "/api/support/requests/{incident_id}/messages" in paths
    assert "/api/support/requests/{incident_id}/reopen" in paths
    assert "/api/admin/incidents/{incident_id}" in paths
    assert "/api/admin/incidents/{incident_id}/messages" in paths
