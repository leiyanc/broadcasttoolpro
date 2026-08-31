from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
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
        "BTP_STRIPE_PRICE_ADDITIONAL_CHANNEL_PROGRAMMING": "price_channel_programming",
        "BTP_STRIPE_PRICE_ADDITIONAL_CHANNEL_PROFESSIONAL": "price_channel_professional",
        "BTP_STRIPE_PRICE_ADDITIONAL_CHANNEL_ENTERPRISE": "price_channel_enterprise",
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
    assert captured["metadata"]["channel_quantity"] == "1"
    assert "price" not in captured["metadata"]


def test_checkout_separates_base_plan_from_additional_channels(monkeypatch):
    _configure(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        stripe_module.stripe.checkout.Session,
        "create",
        lambda **kwargs: captured.update(kwargs)
        or SimpleNamespace(url="https://checkout.stripe.test/channels"),
    )
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "stripe-channels.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Multi Channel Network", slug=None, plan="professional"
        )
        workspace = tenants.create_workspace(
            organization_id=organization["id"],
            name="Operations",
            slug=None,
            default_timezone="UTC",
        )
        for name in ("Channel One", "Channel Two", "Channel Three"):
            tenants.create_channel(
                workspace_id=workspace["id"],
                name=name,
                slug=None,
                channel_code=None,
                timezone="UTC",
                primary_language="en",
            )
        billing = BillingStore(database_path)
        billing.initialize()
        monkeypatch.setattr(stripe_module, "billing_store", billing)

        StripeBillingService().create_checkout_session(
            organization_id=organization["id"],
            email="owner@example.com",
            plan_code="professional",
            include_stream_monitoring=True,
        )

    assert captured["line_items"] == [
        {"price": "price_professional", "quantity": 1},
        {"price": "price_channel_professional", "quantity": 2},
        {"price": "price_monitoring", "quantity": 3},
    ]
    assert captured["metadata"]["channel_quantity"] == "3"
    assert captured["metadata"]["additional_channel_quantity"] == "2"


def test_additional_channel_preview_uses_discounted_plan_price(monkeypatch):
    _configure(monkeypatch)
    captured = {}
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "channel-preview.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Channel Preview Network", slug=None, plan="professional"
        )
        workspace = tenants.create_workspace(
            organization_id=organization["id"],
            name="Operations",
            slug=None,
            default_timezone="UTC",
        )
        included = tenants.create_channel(
            workspace_id=workspace["id"],
            name="Primary Channel",
            slug=None,
            channel_code="primary-channel",
            timezone="UTC",
            primary_language="en",
        )
        billing = BillingStore(database_path)
        billing.initialize()
        EntitlementStore(database_path).initialize()
        billing.apply_stripe_subscription(
            organization["id"],
            plan_code="professional",
            stream_monitoring=False,
            status="active",
            amount_cents=9900,
            currency="usd",
            customer_id="cus_channels",
            subscription_id="sub_channels",
            period_start="2026-08-01T00:00:00+00:00",
            period_end="2026-09-01T00:00:00+00:00",
            cancel_at_period_end=False,
        )
        monkeypatch.setattr(stripe_module, "billing_store", billing)
        subscription = {
            "id": "sub_channels",
            "items": {"data": [{
                "id": "si_plan",
                "price": {"id": "price_professional"},
                "quantity": 1,
            }]},
        }
        monkeypatch.setattr(
            stripe_module.stripe.Subscription,
            "retrieve",
            lambda _subscription_id: subscription,
        )
        monkeypatch.setattr(
            stripe_module.stripe.Invoice,
            "create_preview",
            lambda **kwargs: captured.update(kwargs)
            or {"amount_due": 2100, "currency": "usd"},
        )

        preview = StripeBillingService().preview_channel_purchase(
            organization_id=organization["id"],
            name="Second Channel",
            channel_code="second-channel",
            timezone="UTC",
            primary_language="en",
            stream_monitoring=True,
        )

    changes = captured["subscription_details"]["items"]
    assert {"price": "price_channel_professional", "quantity": 1} in changes
    assert {"price": "price_monitoring", "quantity": 1} in changes
    assert preview["additional_channel_monthly_cents"] == 4900
    assert preview["stream_monitoring_monthly_cents"] == 5900
    assert preview["monthly_increase_cents"] == 10800
    assert preview["amount_due_now_cents"] == 2100


def test_channel_activates_only_after_stripe_accepts_update(monkeypatch):
    _configure(monkeypatch)
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "channel-purchase.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Purchased Channel Network", slug=None, plan="professional"
        )
        workspace = tenants.create_workspace(
            organization_id=organization["id"],
            name="Operations",
            slug=None,
            default_timezone="UTC",
        )
        tenants.create_channel(
            workspace_id=workspace["id"],
            name="Primary Channel",
            slug=None,
            channel_code="primary-channel",
            timezone="UTC",
            primary_language="en",
        )
        billing = BillingStore(database_path)
        billing.initialize()
        EntitlementStore(database_path).initialize()
        billing.apply_stripe_subscription(
            organization["id"],
            plan_code="professional",
            stream_monitoring=False,
            status="active",
            amount_cents=9900,
            currency="usd",
            customer_id="cus_purchase",
            subscription_id="sub_purchase",
            period_start="2026-08-01T00:00:00+00:00",
            period_end="2026-09-01T00:00:00+00:00",
            cancel_at_period_end=False,
        )
        monkeypatch.setattr(stripe_module, "billing_store", billing)
        current = {
            "id": "sub_purchase",
            "items": {"data": [{
                "id": "si_plan",
                "price": {"id": "price_professional"},
                "quantity": 1,
            }]},
        }
        updated = {
            "id": "sub_purchase",
            "customer": "cus_purchase",
            "status": "active",
            "metadata": {"organization_id": organization["id"]},
            "current_period_start": 1_785_542_400,
            "current_period_end": 1_788_220_800,
            "cancel_at_period_end": False,
            "items": {"data": [
                {
                    "id": "si_plan",
                    "price": {
                        "id": "price_professional",
                        "unit_amount": 9900,
                        "currency": "usd",
                    },
                    "quantity": 1,
                },
                {
                    "id": "si_channel",
                    "price": {
                        "id": "price_channel_professional",
                        "unit_amount": 4900,
                        "currency": "usd",
                    },
                    "quantity": 1,
                },
            ]},
        }
        monkeypatch.setattr(
            stripe_module.stripe.Subscription,
            "retrieve",
            lambda _subscription_id: current,
        )
        monkeypatch.setattr(
            stripe_module.stripe.Subscription,
            "modify",
            lambda _subscription_id, **_kwargs: updated,
        )

        channel = StripeBillingService().purchase_channel(
            organization_id=organization["id"],
            name="Second Channel",
            channel_code="second-channel",
            timezone="America/New_York",
            primary_language="es",
            stream_monitoring=False,
        )

        channels = tenants.list_organization_channels(organization["id"])
    assert channel["name"] == "Second Channel"
    assert channel["channel_code"] == "second-channel"
    assert channel["stream_monitoring"] is False
    assert len(channels) == 2


def test_failed_stripe_channel_update_does_not_create_channel(monkeypatch):
    _configure(monkeypatch)
    service = StripeBillingService()
    monkeypatch.setattr(
        service,
        "_channel_purchase_context",
        lambda *_args, **_kwargs: (
            {}, {"id": "sub_failed_channel"}, "professional",
            [{"price": "price_channel_professional", "quantity": 1}],
            1, 0,
        ),
    )
    monkeypatch.setattr(
        service,
        "_validate_new_channel",
        lambda *_args, **_kwargs: [{"id": "existing-channel"}],
    )
    monkeypatch.setattr(
        stripe_module.stripe.Subscription,
        "modify",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("payment rejected")
        ),
    )
    store_requested = {"value": False}
    monkeypatch.setattr(
        service,
        "_channel_store",
        lambda: store_requested.update(value=True),
    )

    try:
        service.purchase_channel(
            organization_id="org_failed",
            name="Unpaid Channel",
            channel_code="unpaid-channel",
            timezone="UTC",
            primary_language="en",
            stream_monitoring=False,
        )
    except RuntimeError as exc:
        assert str(exc) == "payment rejected"
    else:
        raise AssertionError("Expected the Stripe update to fail.")

    assert store_requested["value"] is False


def test_legacy_organization_receives_first_channel_without_stripe_charge(
    monkeypatch,
):
    _configure(monkeypatch)
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "legacy-first-channel.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Legacy Network", slug=None, plan="professional"
        )
        billing = BillingStore(database_path)
        billing.initialize()
        billing.create_manual_paid_subscription(
            organization["id"], amount_cents=9900
        )
        monkeypatch.setattr(stripe_module, "billing_store", billing)
        monkeypatch.setattr(
            stripe_module.stripe.Subscription,
            "retrieve",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("The included first channel must not call Stripe")
            ),
        )
        service = StripeBillingService()

        preview = service.preview_channel_purchase(
            organization_id=organization["id"],
            name="Legacy Primary",
            stream_monitoring=False,
        )
        channel = service.purchase_channel(
            organization_id=organization["id"],
            name="Legacy Primary",
            stream_monitoring=False,
        )

    assert preview["first_channel_included"] is True
    assert preview["amount_due_now_cents"] == 0
    assert preview["monthly_increase_cents"] == 0
    assert channel["name"] == "Legacy Primary"
    assert channel["channel_code"] == "legacy-primary"
    assert channel["timezone"] == "UTC"
    assert channel["primary_language"] == "und"


def test_channel_removal_is_scheduled_for_renewal_and_can_be_canceled(
    monkeypatch,
):
    _configure(monkeypatch)
    captured = {}
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "channel-removal.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Removal Network", slug=None, plan="professional"
        )
        workspace = tenants.create_workspace(
            organization_id=organization["id"],
            name="Operations",
            slug=None,
            default_timezone="UTC",
        )
        included = tenants.create_channel(
            workspace_id=workspace["id"],
            name="Primary Channel",
            slug=None,
            channel_code="primary-channel",
            timezone="UTC",
            primary_language="en",
        )
        removable = tenants.create_channel(
            workspace_id=workspace["id"],
            name="Second Channel",
            slug=None,
            channel_code="second-channel",
            timezone="UTC",
            primary_language="en",
            stream_monitoring=True,
        )
        billing = BillingStore(database_path)
        billing.initialize()
        EntitlementStore(database_path).initialize()
        billing.apply_stripe_subscription(
            organization["id"],
            plan_code="professional",
            stream_monitoring=True,
            status="active",
            amount_cents=20700,
            currency="usd",
            customer_id="cus_removal",
            subscription_id="sub_removal",
            period_start="2026-08-01T00:00:00+00:00",
            period_end="2026-09-01T00:00:00+00:00",
            cancel_at_period_end=False,
        )
        monkeypatch.setattr(stripe_module, "billing_store", billing)
        subscription = {
            "id": "sub_removal",
            "schedule": None,
            "current_period_start": 1_785_542_400,
            "current_period_end": 1_788_220_800,
            "items": {"data": [
                {
                    "id": "si_plan",
                    "price": {"id": "price_professional"},
                    "quantity": 1,
                },
                {
                    "id": "si_channel",
                    "price": {"id": "price_channel_professional"},
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
            stripe_module.stripe.Subscription,
            "retrieve",
            lambda _subscription_id: subscription,
        )
        monkeypatch.setattr(
            stripe_module.stripe.SubscriptionSchedule,
            "create",
            lambda **kwargs: captured.update(create=kwargs)
            or {"id": "sub_sched_removal"},
        )
        monkeypatch.setattr(
            stripe_module.stripe.SubscriptionSchedule,
            "modify",
            lambda schedule_id, **kwargs: captured.update(
                schedule_id=schedule_id, modify=kwargs
            ) or {"id": schedule_id},
        )
        released = []
        monkeypatch.setattr(
            stripe_module.stripe.SubscriptionSchedule,
            "release",
            lambda schedule_id: released.append(schedule_id),
        )
        service = StripeBillingService()

        with pytest.raises(ValueError, match="included channel"):
            service.preview_channel_removal(
                organization_id=organization["id"],
                channel_id=included["id"],
            )

        preview = service.preview_channel_removal(
            organization_id=organization["id"],
            channel_id=removable["id"],
        )
        result = service.schedule_channel_removal(
            organization_id=organization["id"],
            channel_id=removable["id"],
        )

        assert preview["amount_due_now_cents"] == 0
        assert preview["monthly_decrease_cents"] == 10800
        assert preview["new_channel_count"] == 1
        assert captured["create"] == {"from_subscription": "sub_removal"}
        target_items = captured["modify"]["phases"][1]["items"]
        assert target_items == [
            {"price": "price_professional", "quantity": 1}
        ]
        assert captured["modify"]["phases"][1]["proration_behavior"] == "none"
        scheduled = tenants.get_channel(removable["id"])
        assert scheduled["active"] is True
        assert scheduled["deactivation_scheduled_at"] == result["effective_at"]

        subscription["schedule"] = {"id": "sub_sched_removal"}
        kept = service.cancel_channel_removal(
            organization_id=organization["id"],
            channel_id=removable["id"],
        )
        assert released == ["sub_sched_removal"]
        assert kept["active"] is True
        assert kept["deactivation_scheduled_at"] is None


def test_only_active_channel_cannot_be_removed(monkeypatch):
    _configure(monkeypatch)
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "last-channel.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Single Channel Network", slug=None, plan="professional"
        )
        workspace = tenants.create_workspace(
            organization_id=organization["id"],
            name="Operations",
            slug=None,
            default_timezone="UTC",
        )
        channel = tenants.create_channel(
            workspace_id=workspace["id"],
            name="Only Channel",
            slug=None,
            channel_code="only-channel",
            timezone="UTC",
            primary_language="en",
        )
        billing = BillingStore(database_path)
        billing.initialize()
        monkeypatch.setattr(stripe_module, "billing_store", billing)
        monkeypatch.setattr(
            stripe_module.stripe.Subscription,
            "retrieve",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("The last-channel guard must run before Stripe")
            ),
        )

        try:
            StripeBillingService().preview_channel_removal(
                organization_id=organization["id"],
                channel_id=channel["id"],
            )
        except ValueError as exc:
            assert "only active channel" in str(exc)
        else:
            raise AssertionError("Expected removal of the last channel to fail.")


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


def test_successful_upgrade_updates_current_plan_immediately(monkeypatch):
    _configure(monkeypatch)
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "stripe.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Upgrade Network", slug=None, plan="professional"
        )
        EntitlementStore(database_path).initialize()
        billing = BillingStore(database_path)
        billing.initialize()
        billing.apply_stripe_subscription(
            organization["id"],
            plan_code="professional",
            stream_monitoring=False,
            status="active",
            amount_cents=9900,
            currency="usd",
            customer_id="cus_upgrade",
            subscription_id="sub_upgrade",
            period_start="2026-08-11T00:00:00+00:00",
            period_end="2026-09-11T00:00:00+00:00",
            cancel_at_period_end=False,
        )
        monkeypatch.setattr(stripe_module, "billing_store", billing)
        current = {
            "id": "sub_upgrade",
            "customer": "cus_upgrade",
            "status": "active",
            "metadata": {"organization_id": organization["id"]},
            "current_period_start": 1_786_406_400,
            "current_period_end": 1_789_084_800,
            "items": {"data": [{
                "id": "si_plan",
                "price": {"id": "price_professional", "unit_amount": 9900,
                          "currency": "usd"},
                "quantity": 1,
            }]},
        }
        upgraded = {
            **current,
            "items": {"data": [{
                "id": "si_plan",
                "price": {"id": "price_enterprise", "unit_amount": 19900,
                          "currency": "usd"},
                "quantity": 1,
            }]},
        }
        monkeypatch.setattr(
            stripe_module.stripe.Subscription, "retrieve", lambda _id: current
        )
        monkeypatch.setattr(
            stripe_module.stripe.Subscription, "modify", lambda _id, **_kw: upgraded
        )

        result = StripeBillingService().change_subscription(
            organization_id=organization["id"],
            plan_code="enterprise",
            include_stream_monitoring=False,
        )

        assert result["effective"] == "immediately"
        assert billing.get_subscription(organization["id"])["plan"] == "enterprise"
        events = billing.subscription_events(organization["id"])
        assert events[0]["event_type"] == "subscription_change_applied"


def test_incomplete_upgrade_keeps_current_plan(monkeypatch):
    _configure(monkeypatch)
    current = {
        "id": "sub_pending_upgrade",
        "status": "active",
        "items": {"data": [{
            "id": "si_plan",
            "price": {"id": "price_professional"},
            "quantity": 1,
        }]},
    }
    store = SimpleNamespace(
        get_subscription=lambda _id: {
            "provider": "stripe", "status": "active",
            "provider_subscription_id": "sub_pending_upgrade",
        }
    )
    monkeypatch.setattr(stripe_module, "billing_store", store)
    monkeypatch.setattr(
        stripe_module.stripe.Subscription, "retrieve", lambda _id: current
    )
    monkeypatch.setattr(
        stripe_module.stripe.Subscription,
        "modify",
        lambda _id, **_kw: {**current, "pending_update": {"expires_at": 1}},
    )

    result = StripeBillingService().change_subscription(
        organization_id="org_1",
        plan_code="enterprise",
        include_stream_monitoring=False,
    )

    assert result["effective"] == "pending_payment"


def test_cancellation_releases_pending_plan_schedule(monkeypatch):
    _configure(monkeypatch)
    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "stripe.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Cancellation Network", slug=None, plan="enterprise"
        )
        EntitlementStore(database_path).initialize()
        billing = BillingStore(database_path)
        billing.initialize()
        billing.apply_stripe_subscription(
            organization["id"],
            plan_code="enterprise",
            stream_monitoring=True,
            status="active",
            amount_cents=19900,
            currency="usd",
            customer_id="cus_cancel",
            subscription_id="sub_cancel",
            period_start="2026-08-11T00:00:00+00:00",
            period_end="2026-09-11T00:00:00+00:00",
            cancel_at_period_end=False,
        )
        billing.schedule_subscription_change(
            organization["id"],
            plan_code="professional",
            stream_monitoring=False,
            change_at="2026-09-11T00:00:00+00:00",
        )
        monkeypatch.setattr(stripe_module, "billing_store", billing)
        subscriptions = [
            {"id": "sub_cancel", "schedule": "sub_sched_cancel"},
            {"id": "sub_cancel", "schedule": None},
        ]
        released = []
        modified = []
        monkeypatch.setattr(
            stripe_module.stripe.Subscription,
            "retrieve",
            lambda _id: subscriptions.pop(0),
        )
        monkeypatch.setattr(
            stripe_module.stripe.SubscriptionSchedule,
            "release",
            lambda schedule_id: released.append(schedule_id),
        )

        def modify(subscription_id, **kwargs):
            modified.append((subscription_id, kwargs))
            return {"id": subscription_id, **kwargs}

        monkeypatch.setattr(
            stripe_module.stripe.Subscription, "modify", modify
        )
        monkeypatch.setattr(
            stripe_module.identity_store, "list_members", lambda _id: []
        )

        result = StripeBillingService().set_cancel_at_period_end(
            organization_id=organization["id"], cancel=True
        )

        assert result["cancel_at_period_end"] is True
        assert released == ["sub_sched_cancel"]
        assert modified[0][0] == "sub_cancel"
        current = billing.get_subscription(organization["id"])
        assert current["cancel_at_period_end"] is True
        assert current["pending_plan_code"] is None


def test_customer_can_cancel_a_scheduled_plan_change(monkeypatch):
    _configure(monkeypatch)
    store = SimpleNamespace(
        get_subscription=lambda _id: {
            "provider": "stripe",
            "provider_subscription_id": "sub_keep_enterprise",
            "pending_plan_code": "professional",
        },
        cancel_scheduled_change=lambda _id: {"pending_plan_code": None},
    )
    released = []
    monkeypatch.setattr(stripe_module, "billing_store", store)
    monkeypatch.setattr(
        stripe_module.stripe.Subscription,
        "retrieve",
        lambda _id: {"id": "sub_keep_enterprise", "schedule": "sched_change"},
    )
    monkeypatch.setattr(
        stripe_module.stripe.SubscriptionSchedule,
        "release",
        lambda schedule_id: released.append(schedule_id),
    )

    result = StripeBillingService().cancel_scheduled_change(
        organization_id="org_1"
    )

    assert result["pending_plan_code"] is None
    assert released == ["sched_change"]


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


def test_first_paid_invoice_queues_activation_confirmation_once(monkeypatch):
    _configure(monkeypatch)

    class RecordingOutbox:
        def __init__(self):
            self.activations = []
            self.canceled = []

        def schedule_subscription_activation_notifications(self, **kwargs):
            self.activations.append(kwargs)

        def cancel_payment_failure_lifecycle(self, **kwargs):
            self.canceled.append(kwargs)

    with TemporaryDirectory() as directory:
        database_path = Path(directory) / "stripe.db"
        tenants = TenantStore(database_path)
        tenants.initialize()
        organization = tenants.create_organization(
            name="Activation Network", slug=None, plan="starter"
        )
        EntitlementStore(database_path).initialize()
        billing = BillingStore(database_path)
        billing.initialize()
        monkeypatch.setattr(stripe_module, "billing_store", billing)
        outbox = RecordingOutbox()
        monkeypatch.setattr(stripe_module, "email_outbox_store", outbox)
        monkeypatch.setattr(
            stripe_module.identity_store,
            "superuser_notification_targets",
            lambda: [{"email": "admin@example.com"}],
        )
        subscription = {
            "id": "sub_activation",
            "customer": "cus_activation",
            "status": "active",
            "metadata": {"organization_id": organization["id"]},
            "cancel_at_period_end": False,
            "current_period_start": 1_786_000_000,
            "current_period_end": 1_788_592_000,
            "items": {"data": [{
                "price": {
                    "id": "price_programming",
                    "unit_amount": 3900,
                    "currency": "usd",
                },
                "quantity": 1,
            }]},
        }
        monkeypatch.setattr(
            stripe_module.stripe.Subscription,
            "retrieve",
            lambda _subscription_id: subscription,
        )
        service = StripeBillingService()
        first_invoice = {
            "id": "in_activation",
            "subscription": "sub_activation",
            "customer_email": "owner@example.com",
            "status": "paid",
            "currency": "usd",
            "amount_due": 0,
            "amount_paid": 0,
            "created": 1_786_000_000,
            "hosted_invoice_url": "https://invoice.stripe.test/activation",
        }

        service._apply_invoice(first_invoice, event_type="invoice.paid")
        service._apply_invoice(
            {**first_invoice, "id": "in_renewal", "created": 1_788_592_000},
            event_type="invoice.paid",
        )

        assert len(outbox.activations) == 1
        activation = outbox.activations[0]
        assert activation["provider_invoice_id"] == "in_activation"
        assert activation["recipient_email"] == "owner@example.com"
        assert activation["administrator_emails"] == ["admin@example.com"]
        assert activation["plan_code"] == "programming_suite"
        assert activation["amount_paid_cents"] == 0
        assert activation["recurring_monthly_cents"] == 3900


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
