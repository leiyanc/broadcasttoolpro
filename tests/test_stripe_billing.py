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
