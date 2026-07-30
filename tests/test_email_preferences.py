from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.main import app
from backend.services.email_outbox import EmailOutboxStore
from backend.services.tenant_store import TenantStore


def _outbox(directory: str) -> tuple[EmailOutboxStore, str]:
    database_path = Path(directory) / "email-preferences.db"
    tenants = TenantStore(database_path)
    tenants.initialize()
    organization = tenants.create_organization(
        name="Preference Test",
        slug=None,
        plan="professional",
    )
    outbox = EmailOutboxStore(database_path)
    outbox.initialize()
    return outbox, organization["id"]


def test_trial_reminders_are_enabled_by_default():
    with TemporaryDirectory() as directory:
        outbox, _ = _outbox(directory)

        preferences = outbox.preferences_for("OWNER@EXAMPLE.COM")

        assert preferences["recipient_email"] == "owner@example.com"
        assert preferences["trial_reminders"] is True
        assert preferences["updated_at"] is None


def test_disabling_trial_reminders_cancels_only_optional_messages():
    with TemporaryDirectory() as directory:
        outbox, organization_id = _outbox(directory)
        outbox.schedule_trial_lifecycle(
            organization_id=organization_id,
            recipient_email="owner@example.com",
            trial_ends_at=datetime.now(timezone.utc).isoformat(),
        )

        preferences = outbox.update_preferences(
            "owner@example.com",
            trial_reminders=False,
        )

        assert preferences["trial_reminders"] is False
        messages = {
            message["template_code"]: message
            for message in outbox.list_for_organization(organization_id)
        }
        assert messages["trial_three_days_remaining"]["status"] == "canceled"
        assert messages["trial_one_day_remaining"]["status"] == "canceled"
        assert messages["trial_welcome"]["status"] == "queued"
        assert messages["trial_expired"]["status"] == "queued"
        assert {
            message["template_code"]
            for message in outbox.pending()
        } == {"trial_welcome", "trial_expired"}


def test_email_preference_routes_are_registered():
    paths = app.openapi()["paths"]

    assert "/api/auth/email-preferences" in paths
    assert "get" in paths["/api/auth/email-preferences"]
    assert "put" in paths["/api/auth/email-preferences"]
