from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.services.email_outbox import EmailOutboxStore
from backend.services.email_suppression import EmailSuppressionStore
from backend.services.tenant_store import TenantStore


def _stores(directory: str):
    database_path = Path(directory) / "email-suppression.db"
    tenants = TenantStore(database_path)
    tenants.initialize()
    organization = tenants.create_organization(
        name="Suppression Test",
        slug=None,
        plan="professional",
    )
    outbox = EmailOutboxStore(database_path)
    outbox.initialize()
    suppressions = EmailSuppressionStore(database_path)
    suppressions.initialize()
    return outbox, suppressions, organization


def test_permanent_bounce_suppresses_recipient_and_cancels_queue():
    with TemporaryDirectory() as directory:
        outbox, suppressions, organization = _stores(directory)
        outbox.schedule_trial_lifecycle(
            organization_id=organization["id"],
            recipient_email="BOUNCED@example.com",
            trial_ends_at=datetime.now(timezone.utc).isoformat(),
        )

        event = suppressions.record_event(
            event_type="permanent_bounce",
            recipient_email="bounced@example.com",
            provider="amazon_ses",
            provider_message_id="ses-123",
            details={"bounce_type": "Permanent"},
        )

        assert event["event_type"] == "permanent_bounce"
        assert suppressions.is_suppressed("BOUNCED@example.com")
        assert outbox.pending() == []
        messages = outbox.list_for_organization(organization["id"])
        assert all(message["status"] == "canceled" for message in messages)


def test_complaint_suppression_can_be_removed_by_an_administrator():
    with TemporaryDirectory() as directory:
        _, suppressions, _ = _stores(directory)
        suppressions.record_event(
            event_type="complaint",
            recipient_email="complaint@example.com",
            provider="amazon_ses",
            details={"complaint_feedback_type": "abuse"},
        )

        assert suppressions.is_suppressed("complaint@example.com")
        assert suppressions.remove("complaint@example.com")
        assert not suppressions.is_suppressed("complaint@example.com")


def test_temporary_bounce_is_audited_without_suppression():
    with TemporaryDirectory() as directory:
        _, suppressions, _ = _stores(directory)
        suppressions.record_event(
            event_type="temporary_bounce",
            recipient_email="temporary@example.com",
            provider="amazon_ses",
            details={"bounce_type": "Transient"},
        )

        assert not suppressions.is_suppressed("temporary@example.com")
        events = suppressions.events()
        assert events[0]["details"]["bounce_type"] == "Transient"
