from datetime import datetime, timedelta, timezone
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


def test_email_html_renders_billing_link_as_a_button(monkeypatch):
    monkeypatch.delenv("BTP_APPLICATION_URL", raising=False)

    content = AmazonSesProvider._html_body({
        "body_text": "Review the change.\nOpen Billing: https://example.test/app"
    })

    assert 'href="https://example.test/app"' in content
    assert ">Open Billing</a>" in content


def test_payment_failure_schedules_grace_notifications_and_recovery():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "email.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Grace Email Test", slug=None, plan="professional"
        )
        outbox = EmailOutboxStore(database_path)
        outbox.initialize()
        grace_end = (
            datetime.now(timezone.utc) + timedelta(hours=72)
        ).isoformat()

        created = outbox.schedule_payment_failure_lifecycle(
            organization_id=organization["id"],
            recipient_email="owner@example.com",
            grace_ends_at=grace_end,
            grace_hours=72,
            hosted_invoice_url="https://invoice.stripe.test/pay",
        )

        assert len(created) == 3
        assert "72-hour" in created[0]["subject"]
        assert "invoice.stripe.test" in created[0]["body_text"]

        outbox.cancel_payment_failure_lifecycle(
            organization_id=organization["id"]
        )
        outbox.schedule_payment_recovered(
            organization_id=organization["id"],
            recipient_email="owner@example.com",
        )
        messages = outbox.list_for_organization(organization["id"])
        statuses = {
            message["template_code"]: message["status"]
            for message in messages
        }
        assert any(code.startswith("payment_recovered_") for code in statuses)
        assert all(
            status == "canceled"
            for code, status in statuses.items()
            if code.startswith(("payment_grace_24h_", "payment_suspended_"))
        )


def test_subscription_change_queues_customer_and_admin_confirmations():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "email.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Plan Change Test", slug=None, plan="enterprise"
        )
        outbox = EmailOutboxStore(database_path)
        outbox.initialize()

        created = outbox.schedule_subscription_change_notifications(
            organization_id=organization["id"],
            recipient_email="owner@example.com",
            administrator_emails=["admin@example.com", "admin@example.com"],
            previous_plan="enterprise",
            new_plan="professional",
            include_stream_monitoring=True,
            effective="period_end",
            effective_at="2026-09-11T22:02:57+00:00",
            recurring_monthly_cents=15800,
            billing_url="https://example.test/app",
        )

        assert len(created) == 2
        customer = next(
            message for message in created
            if message["recipient_email"] == "owner@example.com"
        )
        assert "Previous plan: Enterprise" in customer["body_text"]
        assert "Organization: Plan Change Test" in customer["body_text"]
        assert "New plan: Professional" in customer["body_text"]
        assert "Stream Monitoring: Included" in customer["body_text"]
        assert "New monthly total: $158.00" in customer["body_text"]
        assert "Charged today: $0.00" in customer["body_text"]
        assert "September 11, 2026" in customer["body_text"]
        assert "Open Billing: https://example.test/app" in customer["body_text"]
        detail = outbox.subscription_message_detail(customer["id"])
        assert detail["body_text"] == customer["body_text"]


def test_cancellation_and_renewal_queue_transactional_notices():
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "email.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Renewal Notice Test", slug=None, plan="professional"
        )
        outbox = EmailOutboxStore(database_path)
        outbox.initialize()

        canceled = outbox.schedule_subscription_renewal_notice(
            organization_id=organization["id"],
            recipient_email="owner@example.com",
            administrator_emails=["admin@example.com"],
            cancel=True,
            effective_at="2026-09-11T22:02:57+00:00",
        )
        resumed = outbox.schedule_subscription_renewal_notice(
            organization_id=organization["id"],
            recipient_email="owner@example.com",
            administrator_emails=["admin@example.com"],
            cancel=False,
            effective_at=None,
        )

        assert len(canceled) == 2
        assert len(resumed) == 2
        assert "cancellation is scheduled" in canceled[0]["subject"]
        assert "2026-09-11" in canceled[0]["body_text"]
        assert "renewal was resumed" in resumed[0]["subject"]
        assert canceled[1]["recipient_email"] == "admin@example.com"
