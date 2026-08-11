from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from backend.services.billing_store import BillingStore
from backend.services.entitlements import EntitlementStore
from backend.services.stripe_billing import StripeBillingService
from backend.services.tenant_store import TenantStore
import backend.services.stripe_billing as stripe_module


def _configure(monkeypatch):
    values = {
        "BTP_STRIPE_SECRET_KEY": "sk_test_example",
        "BTP_STRIPE_WEBHOOK_SECRET": "whsec_example",
        "BTP_STRIPE_PRICE_PROGRAMMING": "price_programming",
        "BTP_STRIPE_PRICE_PROFESSIONAL": "price_professional",
        "BTP_STRIPE_PRICE_ENTERPRISE": "price_enterprise",
        "BTP_STRIPE_PRICE_STREAM_MONITORING": "price_monitoring",
        "BTP_APPLICATION_URL": "https://example.test/app",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_checkout_uses_server_side_prices_and_metadata(monkeypatch):
    _configure(monkeypatch)
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(url="https://checkout.stripe.test/session")

    monkeypatch.setattr(stripe_module.stripe.checkout.Session, "create", fake_create)
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "stripe.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Checkout Network", slug=None, plan="professional"
        )
        billing = BillingStore(database_path)
        billing.initialize()
        monkeypatch.setattr(stripe_module, "billing_store", billing)

        url = StripeBillingService().create_checkout_session(
            organization_id=organization["id"],
            email="owner@example.com",
            plan_code="professional",
            include_stream_monitoring=True,
        )

    assert url == "https://checkout.stripe.test/session"
    assert captured["mode"] == "subscription"
    assert captured["line_items"] == [
        {"price": "price_professional", "quantity": 1},
        {"price": "price_monitoring", "quantity": 1},
    ]
    assert captured["subscription_data"]["metadata"]["organization_id"]
    assert "price" not in captured["metadata"]


def test_upgrade_preview_uses_stripe_proration_and_enterprise_includes_monitoring(
    monkeypatch,
):
    _configure(monkeypatch)
    subscription = {
        "id": "sub_change",
        "status": "active",
        "current_period_end": 1_788_592_000,
        "items": {"data": [
            {
                "id": "si_plan",
                "price": {"id": "price_professional"},
                "quantity": 1,
            },
            {
                "id": "si_monitoring",
                "price": {"id": "price_monitoring"},
                "quantity": 1,
            },
        ]},
    }
    monkeypatch.setattr(
        stripe_module,
        "billing_store",
        SimpleNamespace(get_subscription=lambda _organization_id: {
            "provider": "stripe",
            "status": "active",
            "provider_subscription_id": "sub_change",
        }),
    )
    monkeypatch.setattr(
        stripe_module.stripe.Subscription,
        "retrieve",
        lambda _subscription_id: subscription,
    )
    captured = {}

    def preview(**kwargs):
        captured.update(kwargs)
        return {"amount_due": 4125, "currency": "usd"}

    monkeypatch.setattr(stripe_module.stripe.Invoice, "create_preview", preview)
    result = StripeBillingService().preview_subscription_change(
        organization_id="org_1",
        plan_code="enterprise",
        include_stream_monitoring=True,
    )

    assert result["effective"] == "immediately"
    assert result["amount_due_now_cents"] == 4125
    assert result["recurring_monthly_cents"] == 19900
    assert result["include_stream_monitoring"] is False
    assert captured["subscription_details"]["items"] == [
        {"id": "si_plan", "price": "price_enterprise", "quantity": 1},
        {"id": "si_monitoring", "deleted": True},
    ]


def test_downgrade_preview_is_scheduled_without_proration(monkeypatch):
    _configure(monkeypatch)
    subscription = {
        "id": "sub_change",
        "current_period_end": 1_788_592_000,
        "items": {"data": [{
            "id": "si_plan",
            "price": {"id": "price_enterprise"},
            "quantity": 1,
        }]},
    }
    monkeypatch.setattr(
        stripe_module,
        "billing_store",
        SimpleNamespace(get_subscription=lambda _organization_id: {
            "provider": "stripe",
            "status": "active",
            "provider_subscription_id": "sub_change",
        }),
    )
    monkeypatch.setattr(
        stripe_module.stripe.Subscription,
        "retrieve",
        lambda _subscription_id: subscription,
    )
    monkeypatch.setattr(
        stripe_module.stripe.Invoice,
        "create_preview",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("Downgrades must not create a prorated invoice")
        ),
    )

    result = StripeBillingService().preview_subscription_change(
        organization_id="org_1",
        plan_code="professional",
        include_stream_monitoring=True,
    )

    assert result["effective"] == "period_end"
    assert result["amount_due_now_cents"] == 0
    assert result["recurring_monthly_cents"] == 15800
    assert result["effective_at"].startswith("2026-")


def test_subscription_webhook_provisions_entitlements_once(monkeypatch):
    _configure(monkeypatch)
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "stripe.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Webhook Network", slug=None, plan="professional"
        )
        entitlements = EntitlementStore(database_path)
        entitlements.initialize()
        billing = BillingStore(database_path)
        billing.initialize()
        monkeypatch.setattr(stripe_module, "billing_store", billing)
        service = StripeBillingService()
        event = {
            "id": "evt_subscription_1",
            "type": "customer.subscription.updated",
            "data": {"object": {
                "id": "sub_1",
                "customer": "cus_1",
                "status": "active",
                "metadata": {"organization_id": organization["id"]},
                "cancel_at_period_end": False,
                "current_period_start": 1_786_000_000,
                "current_period_end": 1_788_592_000,
                "items": {"data": [
                    {
                        "price": {
                            "id": "price_professional",
                            "unit_amount": 9900,
                            "currency": "usd",
                        },
                        "quantity": 1,
                    },
                    {
                        "price": {
                            "id": "price_monitoring",
                            "unit_amount": 5900,
                            "currency": "usd",
                        },
                        "quantity": 1,
                    },
                ]},
            }},
        }

        service.process_event(event)
        service.process_event(event)
        subscription = billing.get_subscription(organization["id"])
        access = entitlements.effective_entitlements(organization["id"])

        assert subscription["provider"] == "stripe"
        assert subscription["amount_cents"] == 15800
        assert access["modules"]["prelogs"]["enabled"] is True
        assert access["modules"]["hls_monitor"]["enabled"] is True
        assert billing.provider_event_processed("evt_subscription_1") is True


def test_invoice_failure_starts_grace_and_payment_restores_access(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setenv("BTP_PAYMENT_GRACE_HOURS", "72")

    class RecordingOutbox:
        def __init__(self):
            self.failed = []
            self.recovered = []
            self.canceled = []

        def schedule_payment_failure_lifecycle(self, **kwargs):
            self.failed.append(kwargs)

        def cancel_payment_failure_lifecycle(self, **kwargs):
            self.canceled.append(kwargs)

        def schedule_payment_recovered(self, **kwargs):
            self.recovered.append(kwargs)

    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "stripe.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Renewal Network", slug=None, plan="professional"
        )
        EntitlementStore(database_path).initialize()
        billing = BillingStore(database_path)
        billing.initialize()
        monkeypatch.setattr(stripe_module, "billing_store", billing)
        outbox = RecordingOutbox()
        monkeypatch.setattr(stripe_module, "email_outbox_store", outbox)
        monkeypatch.setattr(
            stripe_module.identity_store,
            "list_members",
            lambda _organization_id: [],
        )
        status = {"value": "past_due"}

        def subscription():
            return {
                "id": "sub_renewal",
                "customer": "cus_renewal",
                "status": status["value"],
                "metadata": {"organization_id": organization["id"]},
                "cancel_at_period_end": False,
                "current_period_start": 1_786_000_000,
                "current_period_end": 1_788_592_000,
                "items": {"data": [{
                    "price": {
                        "id": "price_professional",
                        "unit_amount": 9900,
                        "currency": "usd",
                    },
                    "quantity": 1,
                }]},
            }

        monkeypatch.setattr(
            stripe_module.stripe.Subscription,
            "retrieve",
            lambda _subscription_id: subscription(),
        )
        invoice = {
            "id": "in_renewal",
            "subscription": "sub_renewal",
            "customer_email": "owner@example.com",
            "status": "open",
            "currency": "usd",
            "amount_due": 9900,
            "amount_paid": 0,
            "created": 1_786_000_000,
            "hosted_invoice_url": "https://invoice.stripe.test/renewal",
        }
        service = StripeBillingService()

        service._apply_invoice(
            invoice, event_type="invoice.payment_failed"
        )
        failed = billing.get_subscription(organization["id"])
        assert failed["access_state"] == "payment_grace"
        assert outbox.failed[0]["grace_hours"] == 72

        status["value"] = "active"
        invoice["status"] = "paid"
        invoice["amount_paid"] = 9900
        service._apply_invoice(invoice, event_type="invoice.paid")
        recovered = billing.get_subscription(organization["id"])
        assert recovered["access_state"] == "active"
        assert len(outbox.canceled) == 1
        assert len(outbox.recovered) == 1


def test_payment_failure_cancellation_preserves_72_hour_grace(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setenv("BTP_PAYMENT_GRACE_HOURS", "72")

    class RecordingOutbox:
        def __init__(self):
            self.failed = []

        def schedule_payment_failure_lifecycle(self, **kwargs):
            self.failed.append(kwargs)

    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "stripe.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Grace Network", slug=None, plan="professional"
        )
        EntitlementStore(database_path).initialize()
        billing = BillingStore(database_path)
        billing.initialize()
        monkeypatch.setattr(stripe_module, "billing_store", billing)
        outbox = RecordingOutbox()
        monkeypatch.setattr(stripe_module, "email_outbox_store", outbox)
        monkeypatch.setattr(
            stripe_module.identity_store,
            "list_members",
            lambda _organization_id: [{
                "email": "owner@example.com",
                "status": "active",
                "role": "owner",
            }],
        )
        subscription = {
            "id": "sub_failed",
            "customer": "cus_failed",
            "status": "canceled",
            "metadata": {"organization_id": organization["id"]},
            "cancellation_details": {"reason": "payment_failed"},
            "cancel_at_period_end": False,
            "current_period_start": 1_786_000_000,
            "current_period_end": 1_788_592_000,
            "items": {"data": [{
                "price": {
                    "id": "price_professional",
                    "unit_amount": 9900,
                    "currency": "usd",
                },
                "quantity": 1,
            }]},
        }

        StripeBillingService()._apply_subscription(subscription)

        result = billing.get_subscription(organization["id"])
        assert result["status"] == "past_due"
        assert result["access_state"] == "payment_grace"
        assert result["grace_period_ends_at"] is not None
        assert len(outbox.failed) == 1
        assert outbox.failed[0]["grace_hours"] == 72


def test_voluntary_stripe_cancellation_remains_canceled(monkeypatch):
    _configure(monkeypatch)
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "stripe.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Canceled Network", slug=None, plan="professional"
        )
        EntitlementStore(database_path).initialize()
        billing = BillingStore(database_path)
        billing.initialize()
        monkeypatch.setattr(stripe_module, "billing_store", billing)
        subscription = {
            "id": "sub_canceled",
            "customer": "cus_canceled",
            "status": "canceled",
            "metadata": {"organization_id": organization["id"]},
            "cancellation_details": {"reason": "cancellation_requested"},
            "cancel_at_period_end": False,
            "current_period_start": 1_786_000_000,
            "current_period_end": 1_788_592_000,
            "items": {"data": [{
                "price": {
                    "id": "price_professional",
                    "unit_amount": 9900,
                    "currency": "usd",
                },
                "quantity": 1,
            }]},
        }

        StripeBillingService()._apply_subscription(subscription)

        result = billing.get_subscription(organization["id"])
        assert result["status"] == "canceled"
