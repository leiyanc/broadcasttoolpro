from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.services.email_delivery import (
    AmazonSesProvider,
    EmailDeliveryService,
)
from backend.services.email_outbox import EmailOutboxStore
from backend.services.tenant_store import TenantStore


class RecordingProvider:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.messages: list[dict] = []

    def send(self, message: dict) -> str:
        self.messages.append(message)
        if self.error:
            raise self.error
        return "ses-message-123"


def _outbox(directory: str) -> tuple[EmailOutboxStore, str]:
    database_path = Path(directory) / "email.db"
    tenants = TenantStore(database_path)
    tenants.initialize()
    organization = tenants.create_organization(
        name="Delivery Test",
        slug=None,
        plan="professional",
    )
    outbox = EmailOutboxStore(database_path)
    outbox.initialize()
    outbox.schedule_trial_lifecycle(
        organization_id=organization["id"],
        recipient_email="owner@example.com",
        trial_ends_at=datetime.now(timezone.utc).isoformat(),
    )
    return outbox, organization["id"]


def test_due_email_is_delivered_and_audited():
    with TemporaryDirectory() as directory:
        outbox, organization_id = _outbox(directory)
        provider = RecordingProvider()

        result = EmailDeliveryService(outbox, provider).deliver_due()

        assert result["sent"] == 4
        assert result["failed"] == 0
        messages = outbox.list_for_organization(organization_id)
        assert all(message["status"] == "sent" for message in messages)
        assert all(
            message["provider_message_id"] == "ses-message-123"
            for message in messages
        )


def test_failed_email_is_requeued_without_losing_the_error():
    with TemporaryDirectory() as directory:
        outbox, organization_id = _outbox(directory)
        provider = RecordingProvider(RuntimeError("SES unavailable"))

        result = EmailDeliveryService(outbox, provider).deliver_due()

        assert result["failed"] == 4
        messages = outbox.list_for_organization(organization_id)
        assert all(message["status"] == "queued" for message in messages)
        assert all(
            message["last_error"] == "SES unavailable"
            for message in messages
        )


def test_super_admin_can_inspect_and_retry_failed_delivery():
    with TemporaryDirectory() as directory:
        outbox, _ = _outbox(directory)
        messages = outbox.claim_pending()
        for message in messages:
            outbox.mark_delivery_failure(
                message["id"],
                "Address not verified",
                maximum_attempts=1,
            )

        attempt = outbox.recent_delivery_attempts()[0]
        assert attempt["status"] == "failed"
        assert attempt["last_error"] == "Address not verified"

        retried = outbox.retry_delivery(attempt["id"])

        assert retried["status"] == "queued"
        assert retried["attempts"] == 0
        assert retried["last_error"] is None


def test_email_html_uses_the_branded_logo(monkeypatch):
    monkeypatch.setenv(
        "BTP_APPLICATION_URL",
        "https://broadcast-tool-pro-staging.onrender.com/app",
    )

    content = AmazonSesProvider._html_body({"body_text": "Hello\nWorld"})

    assert (
        "https://broadcast-tool-pro-staging.onrender.com/"
        "static/assets/broadcast-tool-pro-logo.png"
    ) in content
    assert 'alt="Broadcast Tool Pro"' in content
    assert "Hello<br>World" in content


def test_email_html_keeps_a_text_brand_fallback(monkeypatch):
    monkeypatch.delenv("BTP_APPLICATION_URL", raising=False)

    content = AmazonSesProvider._html_body({"body_text": "Hello"})

    assert "Broadcast Tool Pro</div>" in content
    assert "<img" not in content
