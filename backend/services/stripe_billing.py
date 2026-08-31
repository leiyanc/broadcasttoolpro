import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

import stripe

from backend.services.billing_store import billing_store
from backend.services.email_outbox import email_outbox_store
from backend.services.identity_store import identity_store
from backend.services.tenant_store import (
    TenantStore,
    _slugify,
    _validate_timezone,
)


PLAN_PRICE_ENV = {
    "programming_suite": "BTP_STRIPE_PRICE_PROGRAMMING",
    "professional": "BTP_STRIPE_PRICE_PROFESSIONAL",
    "enterprise": "BTP_STRIPE_PRICE_ENTERPRISE",
}
ADDITIONAL_CHANNEL_PRICE_ENV = {
    "programming_suite": "BTP_STRIPE_PRICE_ADDITIONAL_CHANNEL_PROGRAMMING",
    "professional": "BTP_STRIPE_PRICE_ADDITIONAL_CHANNEL_PROFESSIONAL",
    "enterprise": "BTP_STRIPE_PRICE_ADDITIONAL_CHANNEL_ENTERPRISE",
}
STREAM_PRICE_ENV = "BTP_STRIPE_PRICE_STREAM_MONITORING"
STRIPE_ACTIVE_STATUSES = {"active"}
PLAN_RANK = {
    "programming_suite": 1,
    "professional": 2,
    "enterprise": 3,
}
PLAN_MONTHLY_CENTS = {
    "programming_suite": 3900,
    "professional": 9900,
    "enterprise": 19900,
}
ADDITIONAL_CHANNEL_MONTHLY_CENTS = {
    "programming_suite": 2500,
    "professional": 4900,
    "enterprise": 7900,
}
STREAM_MONTHLY_CENTS = 5900


def _value(data: Any, key: str, default: Any = None) -> Any:
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


def _iso_timestamp(value: Any, fallback: datetime | None = None) -> str:
    if value:
        return datetime.fromtimestamp(
            int(value), timezone.utc
        ).isoformat()
    return (fallback or datetime.now(timezone.utc)).isoformat()


class StripeBillingService:
    def _channel_store(self) -> TenantStore:
        return TenantStore(billing_store.database_path)

    def _validate_new_channel(
        self,
        organization_id: str,
        *,
        name: str,
        channel_code: str,
    ) -> list[dict]:
        channels = self._channel_store().list_organization_channels(
            organization_id
        )
        normalized_name = name.strip().casefold()
        normalized_code = channel_code.strip().casefold()
        normalized_slug = _slugify(name)
        if any(channel["name"].strip().casefold() == normalized_name
               for channel in channels):
            raise ValueError("A channel with this name already exists.")
        if any((channel.get("channel_code") or "").strip().casefold()
               == normalized_code for channel in channels):
            raise ValueError("This Channel ID is already registered.")
        if any(channel["slug"] == normalized_slug for channel in channels):
            raise ValueError("A channel with this name already exists.")
        return channels

    def _local_plan_code(self, organization_id: str) -> tuple[dict, str]:
        local = billing_store.get_subscription(organization_id)
        plan_code = local.get("plan") or "programming_suite"
        if plan_code == "starter":
            plan_code = "programming_suite"
        if plan_code not in PLAN_RANK:
            raise ValueError("The organization has an unknown subscription plan.")
        return local, plan_code

    def _create_channel_record(
        self,
        *,
        organization_id: str,
        name: str,
        channel_code: str,
        timezone: str,
        primary_language: str,
        stream_monitoring: bool = False,
    ) -> dict:
        store = self._channel_store()
        workspaces = store.list_workspaces(organization_id)
        if not workspaces:
            workspace = store.create_workspace(
                organization_id=organization_id,
                name="Channel Operations",
                slug=None,
                default_timezone=timezone,
            )
        else:
            workspace = workspaces[0]
        return store.create_channel(
            workspace_id=workspace["id"],
            name=name,
            slug=None,
            channel_code=channel_code,
            timezone=timezone,
            primary_language=primary_language,
            stream_monitoring=stream_monitoring,
        )

    def _subscription_recipient(self, organization_id: str) -> str:
        members = identity_store.list_members(organization_id)
        preferred = next((
            member for member in members
            if member["status"] == "active"
            and member["role"] in {"owner", "admin"}
        ), None)
        return preferred["email"] if preferred else ""

    def _queue_change_notifications(
        self,
        *,
        organization_id: str,
        previous_plan: str,
        new_plan: str,
        include_stream_monitoring: bool,
        effective: str,
        effective_at: str | None = None,
    ) -> None:
        recipient = self._subscription_recipient(organization_id)
        if not recipient:
            return
        administrators = identity_store.superuser_notification_targets()
        try:
            email_outbox_store.schedule_subscription_change_notifications(
                organization_id=organization_id,
                recipient_email=recipient,
                administrator_emails=[item["email"] for item in administrators],
                previous_plan=previous_plan,
                new_plan=new_plan,
                include_stream_monitoring=include_stream_monitoring,
                effective=effective,
                effective_at=effective_at,
                recurring_monthly_cents=(
                    PLAN_MONTHLY_CENTS[new_plan]
                    + (STREAM_MONTHLY_CENTS if (
                        include_stream_monitoring and new_plan != "enterprise"
                    ) else 0)
                ),
                billing_url=os.getenv(
                    "BTP_APPLICATION_URL", "http://127.0.0.1:8000/app"
                ).strip(),
            )
        except (OSError, RuntimeError, sqlite3.Error):
            pass

    def payment_grace_hours(self) -> int:
        try:
            value = int(os.getenv("BTP_PAYMENT_GRACE_HOURS", "72"))
        except ValueError:
            value = 72
        return min(max(value, 1), 168)

    def _secret_key(self) -> str:
        return os.getenv("BTP_STRIPE_SECRET_KEY", "").strip()

    def webhook_secret(self) -> str:
        return os.getenv("BTP_STRIPE_WEBHOOK_SECRET", "").strip()

    def price_id(self, plan_code: str) -> str:
        variable = PLAN_PRICE_ENV.get(plan_code)
        if variable is None:
            raise ValueError("Unknown subscription plan.")
        price_id = os.getenv(variable, "").strip()
        if not price_id:
            raise RuntimeError("Stripe pricing is not configured.")
        return price_id

    def stream_price_id(self) -> str:
        price_id = os.getenv(STREAM_PRICE_ENV, "").strip()
        if not price_id:
            raise RuntimeError("Stripe add-on pricing is not configured.")
        return price_id

    def additional_channel_price_id(self, plan_code: str) -> str:
        variable = ADDITIONAL_CHANNEL_PRICE_ENV.get(plan_code)
        if variable is None:
            raise ValueError("Unknown subscription plan.")
        price_id = os.getenv(variable, "").strip()
        if not price_id:
            raise RuntimeError(
                "Stripe additional-channel pricing is not configured."
            )
        return price_id

    def is_configured(self) -> bool:
        return bool(
            self._secret_key()
            and all(os.getenv(name, "").strip() for name in PLAN_PRICE_ENV.values())
            and os.getenv(STREAM_PRICE_ENV, "").strip()
        )

    def create_checkout_session(
        self,
        *,
        organization_id: str,
        email: str,
        plan_code: str,
        include_stream_monitoring: bool,
    ) -> str:
        secret_key = self._secret_key()
        if not secret_key or not self.is_configured():
            raise RuntimeError("Stripe Checkout is not available.")
        if include_stream_monitoring and plan_code not in {
            "programming_suite", "professional"
        }:
            raise ValueError(
                "Stream Monitoring can be added to Programming Suite or "
                "Professional. "
                "It is already included with Enterprise."
            )
        current = billing_store.get_subscription(organization_id)
        if (
            current["provider"] == "stripe"
            and current["status"] in STRIPE_ACTIVE_STATUSES
        ):
            raise ValueError(
                "This organization already has an active Stripe subscription."
            )
        channel_quantity = max(
            1,
            len(
                TenantStore(
                    billing_store.database_path
                ).list_organization_channels(organization_id)
            ),
        )
        additional_channel_quantity = max(0, channel_quantity - 1)
        line_items = [{"price": self.price_id(plan_code), "quantity": 1}]
        if additional_channel_quantity:
            line_items.append({
                "price": self.additional_channel_price_id(plan_code),
                "quantity": additional_channel_quantity,
            })
        if include_stream_monitoring:
            line_items.append({
                "price": self.stream_price_id(),
                "quantity": channel_quantity,
            })
        application_url = os.getenv(
            "BTP_APPLICATION_URL",
            "http://127.0.0.1:8000/app",
        ).rstrip("/")
        metadata = {
            "organization_id": organization_id,
            "plan_code": plan_code,
            "stream_monitoring": str(include_stream_monitoring).lower(),
            "channel_quantity": str(channel_quantity),
            "additional_channel_quantity": str(
                additional_channel_quantity
            ),
        }
        stripe.api_key = secret_key
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=email,
            line_items=line_items,
            allow_promotion_codes=True,
            success_url=f"{application_url}?billing=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{application_url}?billing=cancelled",
            metadata=metadata,
            subscription_data={"metadata": metadata},
        )
        return session.url

    def _channel_purchase_changes(
        self,
        *,
        subscription: Any,
        plan_code: str,
        additional_quantity: int,
        monitoring_quantity: int,
    ) -> list[dict]:
        items = _value(_value(subscription, "items", {}), "data", []) or []
        additional_price_ids = {
            os.getenv(variable, "").strip()
            for variable in ADDITIONAL_CHANNEL_PRICE_ENV.values()
            if os.getenv(variable, "").strip()
        }
        additional_item = next((
            item for item in items
            if _value(_value(item, "price", {}), "id")
            in additional_price_ids
        ), None)
        changes: list[dict] = []
        additional_price = self.additional_channel_price_id(plan_code)
        if additional_item:
            changes.append({
                "id": _value(additional_item, "id"),
                "price": additional_price,
                "quantity": additional_quantity,
            })
        else:
            changes.append({
                "price": additional_price,
                "quantity": additional_quantity,
            })

        monitoring_item = next((
            item for item in items
            if _value(_value(item, "price", {}), "id")
            == self.stream_price_id()
        ), None)
        if plan_code == "professional" and monitoring_quantity > 0:
            if monitoring_item:
                changes.append({
                    "id": _value(monitoring_item, "id"),
                    "quantity": monitoring_quantity,
                })
            else:
                changes.append({
                    "price": self.stream_price_id(),
                    "quantity": monitoring_quantity,
                })
        return changes

    def _channel_purchase_context(
        self,
        organization_id: str,
        *,
        name: str,
        channel_code: str,
        stream_monitoring: bool = False,
    ) -> tuple[dict, Any, str, list[dict], int, int]:
        channels = self._validate_new_channel(
            organization_id,
            name=name,
            channel_code=channel_code,
        )
        local = billing_store.get_subscription(organization_id)
        if local["provider"] != "stripe" or local["status"] not in {
            "active"
        }:
            raise ValueError(
                "An active Stripe subscription is required to add a channel."
            )
        stripe.api_key = self._secret_key()
        subscription = stripe.Subscription.retrieve(
            local["provider_subscription_id"]
        )
        plan_code, _monitoring = self._price_codes(subscription)
        if stream_monitoring and plan_code == "programming_suite":
            raise ValueError(
                "Stream Monitoring for an added channel requires Professional "
                "or Enterprise."
            )
        additional_quantity = len(channels)
        monitoring_quantity = sum(
            1 for channel in channels
            if channel.get("active") and channel.get("stream_monitoring")
        ) + int(stream_monitoring or plan_code == "enterprise")
        changes = self._channel_purchase_changes(
            subscription=subscription,
            plan_code=plan_code,
            additional_quantity=additional_quantity,
            monitoring_quantity=monitoring_quantity,
        )
        return (
            local, subscription, plan_code, changes,
            additional_quantity, monitoring_quantity,
        )

    def preview_channel_purchase(
        self,
        *,
        organization_id: str,
        name: str,
        channel_code: str | None = None,
        timezone: str = "UTC",
        primary_language: str = "und",
        stream_monitoring: bool,
    ) -> dict:
        channel_code = channel_code or _slugify(name)
        _validate_timezone(timezone)
        channels = self._validate_new_channel(
            organization_id,
            name=name,
            channel_code=channel_code,
        )
        if not channels:
            local, plan_code = self._local_plan_code(organization_id)
            if local["status"] != "active":
                raise ValueError("An active subscription is required.")
            return {
                "plan_code": plan_code,
                "new_channel_count": 1,
                "first_channel_included": True,
                "additional_channel_monthly_cents": 0,
                "stream_monitoring_monthly_cents": 0,
                "monthly_increase_cents": 0,
                "amount_due_now_cents": 0,
                "currency": "usd",
                "monitoring_channel_count": int(plan_code == "enterprise"),
            }
        (
            _local, subscription, plan_code, changes,
            additional_quantity, monitoring_quantity,
        ) = self._channel_purchase_context(
            organization_id,
            name=name,
            channel_code=channel_code,
            stream_monitoring=stream_monitoring,
        )
        invoice = stripe.Invoice.create_preview(
            subscription=_value(subscription, "id"),
            subscription_details={
                "items": changes,
                "proration_behavior": "always_invoice",
            },
        )
        additional_cents = ADDITIONAL_CHANNEL_MONTHLY_CENTS[plan_code]
        monitoring_cents = (
            STREAM_MONTHLY_CENTS
            if stream_monitoring and plan_code == "professional"
            else 0
        )
        return {
            "plan_code": plan_code,
            "new_channel_count": additional_quantity + 1,
            "additional_channel_monthly_cents": additional_cents,
            "stream_monitoring_monthly_cents": monitoring_cents,
            "monthly_increase_cents": additional_cents + monitoring_cents,
            "amount_due_now_cents": int(
                _value(invoice, "amount_due", _value(invoice, "total", 0)) or 0
            ),
            "currency": _value(invoice, "currency", "usd") or "usd",
            "monitoring_channel_count": monitoring_quantity,
        }

    def purchase_channel(
        self,
        *,
        organization_id: str,
        name: str,
        channel_code: str | None = None,
        timezone: str = "UTC",
        primary_language: str = "und",
        stream_monitoring: bool,
    ) -> dict:
        channel_code = channel_code or _slugify(name)
        _validate_timezone(timezone)
        channels = self._validate_new_channel(
            organization_id,
            name=name,
            channel_code=channel_code,
        )
        if not channels:
            local, plan_code = self._local_plan_code(organization_id)
            if local["status"] != "active":
                raise ValueError("An active subscription is required.")
            return self._create_channel_record(
                organization_id=organization_id,
                name=name,
                channel_code=channel_code,
                timezone=timezone,
                primary_language=primary_language,
                stream_monitoring=(
                    stream_monitoring or plan_code == "enterprise"
                ),
            )
        (
            _local, subscription, plan_code, changes,
            additional_quantity, monitoring_quantity,
        ) = self._channel_purchase_context(
            organization_id,
            name=name,
            channel_code=channel_code,
            stream_monitoring=stream_monitoring,
        )
        updated = stripe.Subscription.modify(
            _value(subscription, "id"),
            items=changes,
            proration_behavior="always_invoice",
            payment_behavior="error_if_incomplete",
            metadata={
                "organization_id": organization_id,
                "plan_code": plan_code,
                "channel_quantity": str(additional_quantity + 1),
                "additional_channel_quantity": str(additional_quantity),
                "monitoring_channel_quantity": str(monitoring_quantity),
            },
        )
        channel = self._create_channel_record(
            organization_id=organization_id,
            name=name,
            channel_code=channel_code,
            timezone=timezone,
            primary_language=primary_language,
            stream_monitoring=(
                stream_monitoring or plan_code == "enterprise"
            ),
        )
        self._apply_subscription(updated)
        return channel

    def _channel_removal_context(
        self,
        organization_id: str,
        channel_id: str,
    ) -> tuple[dict, dict, Any, str, list[dict], int, int, int]:
        store = self._channel_store()
        channels = [
            channel for channel in store.list_organization_channels(
                organization_id
            )
            if channel["active"]
        ]
        channel = next(
            (item for item in channels if item["id"] == channel_id),
            None,
        )
        if channel is None:
            raise ValueError("The selected active channel was not found.")
        if channel.get("deactivation_scheduled_at"):
            raise ValueError("This channel is already scheduled for removal.")
        if len(channels) <= 1:
            raise ValueError(
                "The organization's only active channel cannot be removed."
            )
        if channel_id == store.included_channel_id(organization_id):
            raise ValueError(
                "The included channel is required and cannot be removed."
            )
        local = billing_store.get_subscription(organization_id)
        if local["provider"] != "stripe" or local["status"] not in {
            "active"
        }:
            raise ValueError(
                "An active Stripe subscription is required to remove a channel."
            )
        stripe.api_key = self._secret_key()
        subscription = stripe.Subscription.retrieve(
            local["provider_subscription_id"]
        )
        if _value(subscription, "schedule"):
            raise ValueError(
                "Complete or cancel the existing scheduled subscription "
                "change before removing a channel."
            )
        plan_code, _monitoring = self._price_codes(subscription)
        new_channel_count = len(channels) - 1
        additional_quantity = max(0, new_channel_count - 1)
        monitoring_quantity = sum(
            1 for item in channels
            if item.get("stream_monitoring") and item["id"] != channel_id
        )
        items = _value(_value(subscription, "items", {}), "data", []) or []
        return (
            local, channel, subscription, plan_code, items,
            new_channel_count, additional_quantity, monitoring_quantity,
        )

    def _channel_removal_target_items(
        self,
        *,
        items: list[Any],
        plan_code: str,
        additional_quantity: int,
        monitoring_quantity: int,
    ) -> list[dict]:
        plan_prices = {self.price_id(code) for code in PLAN_RANK}
        additional_prices = {
            os.getenv(variable, "").strip()
            for variable in ADDITIONAL_CHANNEL_PRICE_ENV.values()
            if os.getenv(variable, "").strip()
        }
        stream_price = self.stream_price_id()
        target: list[dict] = []
        for item in items:
            price_id = _value(_value(item, "price", {}), "id")
            quantity = int(_value(item, "quantity", 1) or 1)
            if price_id in plan_prices:
                target.append({"price": price_id, "quantity": 1})
            elif price_id in additional_prices:
                if additional_quantity:
                    target.append({
                        "price": self.additional_channel_price_id(plan_code),
                        "quantity": additional_quantity,
                    })
            elif price_id == stream_price:
                if plan_code == "professional" and monitoring_quantity:
                    target.append({
                        "price": price_id,
                        "quantity": monitoring_quantity,
                    })
            else:
                target.append({"price": price_id, "quantity": quantity})
        return target

    def preview_channel_removal(
        self,
        *,
        organization_id: str,
        channel_id: str,
    ) -> dict:
        (
            _local, channel, subscription, plan_code, _items,
            new_channel_count, _additional_quantity, _monitoring_quantity,
        ) = self._channel_removal_context(organization_id, channel_id)
        period_end = _value(subscription, "current_period_end")
        if not period_end:
            items = _value(_value(subscription, "items", {}), "data", []) or []
            period_end = _value(items[0] if items else {}, "current_period_end")
        if not period_end:
            raise ValueError("Stripe did not return the current renewal date.")
        monthly_decrease = ADDITIONAL_CHANNEL_MONTHLY_CENTS[plan_code]
        if channel.get("stream_monitoring") and plan_code == "professional":
            monthly_decrease += STREAM_MONTHLY_CENTS
        return {
            "channel_id": channel_id,
            "channel_name": channel["name"],
            "effective": "period_end",
            "effective_at": _iso_timestamp(period_end),
            "new_channel_count": new_channel_count,
            "monthly_decrease_cents": monthly_decrease,
            "amount_due_now_cents": 0,
            "currency": "usd",
        }

    def schedule_channel_removal(
        self,
        *,
        organization_id: str,
        channel_id: str,
    ) -> dict:
        (
            _local, channel, subscription, plan_code, items,
            new_channel_count, additional_quantity, monitoring_quantity,
        ) = self._channel_removal_context(organization_id, channel_id)
        period_start = _value(subscription, "current_period_start") or _value(
            items[0] if items else {}, "current_period_start"
        )
        period_end = _value(subscription, "current_period_end") or _value(
            items[0] if items else {}, "current_period_end"
        )
        if not period_start or not period_end:
            raise ValueError("Stripe did not return the current billing period.")
        current_items = [
            {
                "price": _value(_value(item, "price", {}), "id"),
                "quantity": int(_value(item, "quantity", 1) or 1),
            }
            for item in items
        ]
        target_items = self._channel_removal_target_items(
            items=items,
            plan_code=plan_code,
            additional_quantity=additional_quantity,
            monitoring_quantity=monitoring_quantity,
        )
        schedule = stripe.SubscriptionSchedule.create(
            from_subscription=_value(subscription, "id")
        )
        schedule_id = _value(schedule, "id")
        try:
            stripe.SubscriptionSchedule.modify(
                schedule_id,
                end_behavior="release",
                phases=[
                    {
                        "start_date": period_start,
                        "end_date": period_end,
                        "items": current_items,
                        "proration_behavior": "none",
                    },
                    {
                        "start_date": period_end,
                        "items": target_items,
                        "proration_behavior": "none",
                        "metadata": {
                            "organization_id": organization_id,
                            "plan_code": plan_code,
                            "channel_quantity": str(new_channel_count),
                            "additional_channel_quantity": str(
                                additional_quantity
                            ),
                            "monitoring_channel_quantity": str(
                                monitoring_quantity
                            ),
                        },
                    },
                ],
            )
        except Exception:
            try:
                stripe.SubscriptionSchedule.release(schedule_id)
            except Exception:
                pass
            raise
        effective_at = _iso_timestamp(period_end)
        scheduled = self._channel_store().schedule_channel_deactivation(
            channel_id,
            effective_at=effective_at,
        )
        return {
            "channel": scheduled,
            "effective": "period_end",
            "effective_at": effective_at,
        }

    def cancel_channel_removal(
        self,
        *,
        organization_id: str,
        channel_id: str,
    ) -> dict:
        store = self._channel_store()
        channels = store.list_organization_channels(organization_id)
        channel = next(
            (item for item in channels if item["id"] == channel_id),
            None,
        )
        if channel is None or not channel.get("deactivation_scheduled_at"):
            raise ValueError("This channel has no scheduled removal.")
        local = billing_store.get_subscription(organization_id)
        if local["provider"] != "stripe":
            raise ValueError("An active Stripe subscription is required.")
        stripe.api_key = self._secret_key()
        subscription = stripe.Subscription.retrieve(
            local["provider_subscription_id"]
        )
        schedule = _value(subscription, "schedule")
        schedule_id = _value(schedule, "id") or schedule
        if not schedule_id:
            raise ValueError("Stripe has no scheduled channel change.")
        stripe.SubscriptionSchedule.release(schedule_id)
        return store.cancel_channel_deactivation(channel_id)

    def _target_prices(
        self,
        plan_code: str,
        include_stream_monitoring: bool,
    ) -> list[str]:
        if plan_code not in PLAN_RANK:
            raise ValueError("Unknown subscription plan.")
        if plan_code == "enterprise":
            include_stream_monitoring = False
        elif include_stream_monitoring and plan_code not in {
            "programming_suite", "professional"
        }:
            raise ValueError("Stream Monitoring is not available for this plan.")
        prices = [self.price_id(plan_code)]
        if include_stream_monitoring:
            prices.append(self.stream_price_id())
        return prices

    def _change_context(
        self,
        organization_id: str,
        plan_code: str,
        include_stream_monitoring: bool,
    ) -> tuple[dict, Any, str, bool, bool, list[Any], list[str]]:
        local = billing_store.get_subscription(organization_id)
        if local["provider"] != "stripe" or local["status"] not in {
            "active", "past_due"
        }:
            raise ValueError("An active Stripe subscription is required.")
        stripe.api_key = self._secret_key()
        subscription = stripe.Subscription.retrieve(
            local["provider_subscription_id"]
        )
        current_plan, current_monitoring = self._price_codes(subscription)
        if plan_code == "enterprise":
            include_stream_monitoring = False
        if current_plan == plan_code and current_monitoring == include_stream_monitoring:
            raise ValueError("The requested subscription is already active.")
        target_prices = self._target_prices(plan_code, include_stream_monitoring)
        is_upgrade = PLAN_RANK[plan_code] > PLAN_RANK[current_plan] or (
            PLAN_RANK[plan_code] == PLAN_RANK[current_plan]
            and include_stream_monitoring
            and not current_monitoring
        )
        items = _value(_value(subscription, "items", {}), "data", []) or []
        return (
            local, subscription, current_plan, current_monitoring,
            is_upgrade, items, target_prices,
        )

    def _change_items(
        self,
        items: list[Any],
        target_prices: list[str],
        plan_code: str,
    ) -> list[dict]:
        plan_prices = {self.price_id(code) for code in PLAN_RANK}
        plan_item = next(
            item for item in items
            if _value(_value(item, "price", {}), "id") in plan_prices
        )
        changes = [{
            "id": _value(plan_item, "id"),
            "price": target_prices[0],
            "quantity": 1,
        }]
        additional_price_ids = {
            os.getenv(variable, "").strip()
            for variable in ADDITIONAL_CHANNEL_PRICE_ENV.values()
            if os.getenv(variable, "").strip()
        }
        additional_item = next((
            item for item in items
            if _value(_value(item, "price", {}), "id")
            in additional_price_ids
        ), None)
        if additional_item:
            changes.append({
                "id": _value(additional_item, "id"),
                "price": self.additional_channel_price_id(plan_code),
                "quantity": int(_value(additional_item, "quantity", 1) or 1),
            })
        addon_item = next(
            (
                item for item in items
                if _value(_value(item, "price", {}), "id")
                == self.stream_price_id()
            ),
            None,
        )
        target_has_addon = len(target_prices) == 2
        if target_has_addon and not addon_item:
            changes.append({"price": target_prices[1], "quantity": 1})
        elif addon_item and not target_has_addon:
            changes.append({"id": _value(addon_item, "id"), "deleted": True})
        return changes

    def preview_subscription_change(
        self,
        *,
        organization_id: str,
        plan_code: str,
        include_stream_monitoring: bool,
    ) -> dict:
        (
            _local, subscription, _current_plan, _current_monitoring,
            is_upgrade, items, target_prices,
        ) = self._change_context(
            organization_id, plan_code, include_stream_monitoring
        )
        normalized_monitoring = plan_code != "enterprise" and include_stream_monitoring
        recurring_cents = PLAN_MONTHLY_CENTS[plan_code] + (
            STREAM_MONTHLY_CENTS if normalized_monitoring else 0
        )
        period_end = _value(subscription, "current_period_end") or _value(
            items[0] if items else {}, "current_period_end"
        )
        preview = {
            "effective": "immediately" if is_upgrade else "period_end",
            "effective_at": (
                datetime.now(timezone.utc).isoformat()
                if is_upgrade else _iso_timestamp(period_end)
            ),
            "currency": "usd",
            "amount_due_now_cents": 0,
            "recurring_monthly_cents": recurring_cents,
            "plan_code": plan_code,
            "include_stream_monitoring": normalized_monitoring,
        }
        if not is_upgrade:
            return preview
        invoice = stripe.Invoice.create_preview(
            subscription=_value(subscription, "id"),
            subscription_details={
                "items": self._change_items(items, target_prices, plan_code),
                "proration_behavior": "always_invoice",
            },
        )
        preview["amount_due_now_cents"] = int(
            _value(invoice, "amount_due", _value(invoice, "total", 0)) or 0
        )
        preview["currency"] = _value(invoice, "currency", "usd") or "usd"
        return preview

    def change_subscription(
        self,
        *,
        organization_id: str,
        plan_code: str,
        include_stream_monitoring: bool,
    ) -> dict:
        (
            local, subscription, current_plan, current_monitoring,
            is_upgrade, items, target_prices,
        ) = self._change_context(
            organization_id, plan_code, include_stream_monitoring
        )
        if plan_code == "enterprise":
            include_stream_monitoring = False
        current_items = [
            {
                "price": _value(_value(item, "price", {}), "id"),
                "quantity": int(_value(item, "quantity", 1) or 1),
            }
            for item in items
        ]
        if is_upgrade:
            changes = self._change_items(items, target_prices, plan_code)
            schedule_id = _value(subscription, "schedule")
            if schedule_id:
                stripe.SubscriptionSchedule.release(schedule_id)
            updated = stripe.Subscription.modify(
                _value(subscription, "id"),
                items=changes,
                proration_behavior="always_invoice",
                payment_behavior="pending_if_incomplete",
                metadata={
                    "organization_id": organization_id,
                    "plan_code": plan_code,
                    "stream_monitoring": str(include_stream_monitoring).lower(),
                },
            )
            if _value(updated, "pending_update"):
                self._queue_change_notifications(
                    organization_id=organization_id,
                    previous_plan=current_plan,
                    new_plan=plan_code,
                    include_stream_monitoring=include_stream_monitoring,
                    effective="pending_payment",
                )
                return {
                    "effective": "pending_payment",
                    "message": "Payment must complete before the plan changes.",
                }
            self._apply_subscription(updated)
            billing_store.clear_scheduled_change(organization_id)
            billing_store.record_subscription_change(
                organization_id,
                plan_code=plan_code,
                stream_monitoring=include_stream_monitoring,
                effective="immediately",
            )
            self._queue_change_notifications(
                organization_id=organization_id,
                previous_plan=current_plan,
                new_plan=plan_code,
                include_stream_monitoring=include_stream_monitoring,
                effective="immediately",
            )
            return {"effective": "immediately"}

        schedule_id = _value(subscription, "schedule")
        if schedule_id:
            stripe.SubscriptionSchedule.release(schedule_id)
            subscription = stripe.Subscription.retrieve(
                local["provider_subscription_id"]
            )
        schedule = stripe.SubscriptionSchedule.create(
            from_subscription=_value(subscription, "id")
        )
        period_start = _value(subscription, "current_period_start") or _value(
            items[0] if items else {}, "current_period_start"
        )
        period_end = _value(subscription, "current_period_end") or _value(
            items[0] if items else {}, "current_period_end"
        )
        additional_price_ids = {
            os.getenv(variable, "").strip()
            for variable in ADDITIONAL_CHANNEL_PRICE_ENV.values()
            if os.getenv(variable, "").strip()
        }
        additional_item = next((
            item for item in items
            if _value(_value(item, "price", {}), "id")
            in additional_price_ids
        ), None)
        monitoring_item = next((
            item for item in items
            if _value(_value(item, "price", {}), "id")
            == self.stream_price_id()
        ), None)
        target_items = [{"price": target_prices[0], "quantity": 1}]
        if additional_item:
            target_items.append({
                "price": self.additional_channel_price_id(plan_code),
                "quantity": int(_value(additional_item, "quantity", 1) or 1),
            })
        if len(target_prices) == 2:
            target_items.append({
                "price": target_prices[1],
                "quantity": int(_value(monitoring_item, "quantity", 1) or 1),
            })
        stripe.SubscriptionSchedule.modify(
            _value(schedule, "id"),
            end_behavior="release",
            phases=[
                {
                    "start_date": period_start,
                    "end_date": period_end,
                    "items": current_items,
                    "proration_behavior": "none",
                },
                {
                    "start_date": period_end,
                    "items": target_items,
                    "proration_behavior": "none",
                    "metadata": {
                        "organization_id": organization_id,
                        "plan_code": plan_code,
                        "stream_monitoring": str(
                            include_stream_monitoring
                        ).lower(),
                    },
                },
            ],
        )
        change_at = _iso_timestamp(period_end)
        billing_store.schedule_subscription_change(
            organization_id,
            plan_code=plan_code,
            stream_monitoring=include_stream_monitoring,
            change_at=change_at,
        )
        self._queue_change_notifications(
            organization_id=organization_id,
            previous_plan=current_plan,
            new_plan=plan_code,
            include_stream_monitoring=include_stream_monitoring,
            effective="period_end",
            effective_at=change_at,
        )
        return {"effective": "period_end", "change_at": change_at}

    def set_cancel_at_period_end(
        self,
        *,
        organization_id: str,
        cancel: bool,
    ) -> dict:
        local = billing_store.get_subscription(organization_id)
        if local["provider"] != "stripe" or not local.get(
            "provider_subscription_id"
        ):
            raise ValueError("An active Stripe subscription is required.")
        stripe.api_key = self._secret_key()
        subscription = stripe.Subscription.retrieve(
            local["provider_subscription_id"]
        )
        schedule_id = _value(subscription, "schedule")
        if cancel and schedule_id:
            stripe.SubscriptionSchedule.release(schedule_id)
            subscription = stripe.Subscription.retrieve(
                local["provider_subscription_id"]
            )
        updated = stripe.Subscription.modify(
            _value(subscription, "id", local["provider_subscription_id"]),
            cancel_at_period_end=cancel,
            proration_behavior="none",
        )
        if cancel and local.get("pending_plan_code"):
            billing_store.clear_scheduled_change(organization_id)
        billing_store.update_subscription(
            organization_id,
            status=None,
            billing_cycle=None,
            current_period_end=None,
            cancel_at_period_end=cancel,
            lifecycle_note=(
                "Customer scheduled subscription cancellation."
                if cancel else "Customer resumed subscription renewal."
            ),
        )
        recipient = self._subscription_recipient(organization_id)
        if recipient:
            try:
                email_outbox_store.schedule_subscription_renewal_notice(
                    organization_id=organization_id,
                    recipient_email=recipient,
                    administrator_emails=[
                        item["email"] for item
                        in identity_store.superuser_notification_targets()
                    ],
                    cancel=cancel,
                    effective_at=local.get("current_period_end"),
                )
            except (OSError, RuntimeError, sqlite3.Error):
                pass
        return updated

    def cancel_scheduled_change(self, *, organization_id: str) -> dict:
        local = billing_store.get_subscription(organization_id)
        if local["provider"] != "stripe" or not local.get(
            "provider_subscription_id"
        ):
            raise ValueError("An active Stripe subscription is required.")
        if not local.get("pending_plan_code"):
            raise ValueError("There is no scheduled subscription change.")
        stripe.api_key = self._secret_key()
        subscription = stripe.Subscription.retrieve(
            local["provider_subscription_id"]
        )
        schedule_id = _value(subscription, "schedule")
        if not schedule_id:
            raise ValueError("Stripe has no scheduled subscription change.")
        stripe.SubscriptionSchedule.release(schedule_id)
        return billing_store.cancel_scheduled_change(organization_id)

    def construct_event(self, payload: bytes, signature: str) -> Any:
        secret = self.webhook_secret()
        if not secret:
            raise RuntimeError("Stripe webhook verification is not configured.")
        return stripe.Webhook.construct_event(payload, signature, secret)

    def process_event(self, event: Any) -> None:
        event_id = _value(event, "id")
        event_type = _value(event, "type")
        if not event_id or not event_type:
            raise ValueError("Invalid Stripe event.")
        if billing_store.provider_event_processed(event_id):
            return
        data = _value(_value(event, "data", {}), "object", {})
        if event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            self._apply_subscription(data)
        elif event_type in {
            "invoice.paid",
            "invoice.payment_failed",
            "invoice.payment_action_required",
        }:
            self._apply_invoice(data, event_type=event_type)
        billing_store.record_provider_event(event_id, event_type)

    def _price_codes(self, subscription: Any) -> tuple[str, bool]:
        items = _value(_value(subscription, "items", {}), "data", []) or []
        price_ids = {
            _value(_value(item, "price", {}), "id")
            for item in items
        }
        plan_code = next(
            (
                code for code, variable in PLAN_PRICE_ENV.items()
                if os.getenv(variable, "").strip() in price_ids
            ),
            None,
        )
        if plan_code is None:
            raise ValueError("Stripe subscription does not match a configured plan.")
        return plan_code, self.stream_price_id() in price_ids

    def _apply_subscription(self, subscription: Any) -> None:
        metadata = _value(subscription, "metadata", {}) or {}
        organization_id = _value(metadata, "organization_id")
        if not organization_id:
            organization_id = billing_store.organization_for_provider_subscription(
                _value(subscription, "id", "")
            )
        if not organization_id:
            raise ValueError("Stripe subscription is missing organization metadata.")
        plan_code, stream_monitoring = self._price_codes(subscription)
        stripe_status = _value(subscription, "status", "past_due")
        cancellation_details = (
            _value(subscription, "cancellation_details", {}) or {}
        )
        cancellation_reason = _value(cancellation_details, "reason", "")
        payment_failure_cancellation = (
            stripe_status == "canceled"
            and cancellation_reason == "payment_failed"
        )
        status = (
            "active" if stripe_status == "active"
            else "canceled" if stripe_status == "trialing"
            else "past_due" if payment_failure_cancellation
            else "canceled" if stripe_status == "canceled"
            else "past_due"
        )
        items = _value(_value(subscription, "items", {}), "data", []) or []
        period_source = items[0] if items else subscription
        period_start = _value(subscription, "current_period_start") or _value(
            period_source, "current_period_start"
        )
        period_end = _value(subscription, "current_period_end") or _value(
            period_source, "current_period_end"
        )
        amount_cents = sum(
            int(_value(_value(item, "price", {}), "unit_amount", 0) or 0)
            * int(_value(item, "quantity", 1) or 1)
            for item in items
        )
        currency = next(
            (
                _value(_value(item, "price", {}), "currency")
                for item in items
                if _value(_value(item, "price", {}), "currency")
            ),
            "usd",
        )
        previous = billing_store.get_subscription(organization_id)
        billing_store.apply_stripe_subscription(
            organization_id,
            plan_code=plan_code,
            stream_monitoring=stream_monitoring,
            status=status,
            amount_cents=amount_cents,
            currency=currency,
            customer_id=_value(subscription, "customer", ""),
            subscription_id=_value(subscription, "id", ""),
            period_start=_iso_timestamp(period_start),
            period_end=_iso_timestamp(period_end),
            cancel_at_period_end=bool(
                _value(subscription, "cancel_at_period_end", False)
            ),
        )
        pending = previous.get("pending_plan_code")
        pending_monitoring = previous.get("pending_stream_monitoring")
        if pending == plan_code and bool(pending_monitoring) == stream_monitoring:
            billing_store.clear_scheduled_change(organization_id)
        if payment_failure_cancellation:
            already_in_grace = bool(previous.get("grace_period_ends_at"))
            failed = billing_store.mark_payment_failed(
                organization_id,
                grace_hours=self.payment_grace_hours(),
            )
            if not already_in_grace:
                members = identity_store.list_members(organization_id)
                recipient = next(
                    (
                        member["email"] for member in members
                        if member["status"] == "active"
                        and member["role"] in {"owner", "admin"}
                    ),
                    "",
                )
                if recipient:
                    email_outbox_store.schedule_payment_failure_lifecycle(
                        organization_id=organization_id,
                        recipient_email=recipient,
                        grace_ends_at=failed["grace_period_ends_at"],
                        grace_hours=self.payment_grace_hours(),
                        hosted_invoice_url=None,
                    )

    def _invoice_subscription_id(self, invoice: Any) -> str | None:
        subscription_id = _value(invoice, "subscription")
        if subscription_id:
            return subscription_id
        parent = _value(invoice, "parent", {}) or {}
        details = _value(parent, "subscription_details", {}) or {}
        return _value(details, "subscription")

    def _billing_recipient(self, organization_id: str, invoice: Any) -> str:
        invoice_email = _value(invoice, "customer_email", "") or ""
        if invoice_email.strip():
            return invoice_email.strip().lower()
        members = identity_store.list_members(organization_id)
        preferred = next(
            (
                member for member in members
                if member["status"] == "active"
                and member["role"] in {"owner", "admin"}
            ),
            None,
        )
        return preferred["email"] if preferred else ""

    def _apply_invoice(self, invoice: Any, *, event_type: str) -> None:
        subscription_id = self._invoice_subscription_id(invoice)
        if not subscription_id:
            return
        stripe.api_key = self._secret_key()
        subscription = stripe.Subscription.retrieve(subscription_id)
        organization_id = billing_store.organization_for_provider_subscription(
            subscription_id
        )
        previous = (
            billing_store.get_subscription(organization_id)
            if organization_id else None
        )
        self._apply_subscription(subscription)
        organization_id = organization_id or (
            billing_store.organization_for_provider_subscription(
                subscription_id
            )
        )
        if not organization_id:
            raise ValueError(
                "Stripe invoice could not be matched to an organization."
            )
        is_initial_invoice = not billing_store.list_invoices(organization_id)
        transitions = _value(invoice, "status_transitions", {}) or {}
        billing_store.upsert_stripe_invoice(
            organization_id,
            provider_invoice_id=_value(invoice, "id", ""),
            status=_value(invoice, "status", "open") or "open",
            currency=_value(invoice, "currency", "usd"),
            amount_due_cents=int(_value(invoice, "amount_due", 0) or 0),
            amount_paid_cents=int(_value(invoice, "amount_paid", 0) or 0),
            invoice_date=_iso_timestamp(_value(invoice, "created")),
            due_date=(
                _iso_timestamp(_value(invoice, "due_date"))
                if _value(invoice, "due_date") else None
            ),
            paid_at=(
                _iso_timestamp(_value(transitions, "paid_at"))
                if _value(transitions, "paid_at") else None
            ),
            hosted_invoice_url=_value(invoice, "hosted_invoice_url"),
        )
        recipient = self._billing_recipient(organization_id, invoice)
        if event_type in {
            "invoice.payment_failed",
            "invoice.payment_action_required",
        }:
            already_in_grace = bool(
                previous and previous.get("grace_period_ends_at")
            )
            failed = billing_store.mark_payment_failed(
                organization_id,
                grace_hours=self.payment_grace_hours(),
            )
            if recipient and not already_in_grace:
                email_outbox_store.schedule_payment_failure_lifecycle(
                    organization_id=organization_id,
                    recipient_email=recipient,
                    grace_ends_at=failed["grace_period_ends_at"],
                    grace_hours=self.payment_grace_hours(),
                    hosted_invoice_url=_value(
                        invoice, "hosted_invoice_url"
                    ),
                )
        elif event_type == "invoice.paid":
            recovered = bool(
                previous and previous.get("grace_period_ends_at")
            )
            billing_store.clear_payment_failure(organization_id)
            email_outbox_store.cancel_payment_failure_lifecycle(
                organization_id=organization_id,
            )
            if recipient and recovered:
                email_outbox_store.schedule_payment_recovered(
                    organization_id=organization_id,
                    recipient_email=recipient,
                )
            if recipient and is_initial_invoice:
                current = billing_store.get_subscription(organization_id)
                administrators = identity_store.superuser_notification_targets()
                try:
                    email_outbox_store.schedule_subscription_activation_notifications(
                        organization_id=organization_id,
                        recipient_email=recipient,
                        administrator_emails=[
                            item["email"] for item in administrators
                        ],
                        provider_invoice_id=_value(invoice, "id", ""),
                        plan_code=current["plan"],
                        include_stream_monitoring=bool(
                            current.get("stream_monitoring")
                        ),
                        amount_paid_cents=int(
                            _value(invoice, "amount_paid", 0) or 0
                        ),
                        recurring_monthly_cents=int(
                            current.get("amount_cents", 0) or 0
                        ),
                        renews_at=current.get("current_period_end"),
                        billing_url=os.getenv(
                            "BTP_APPLICATION_URL",
                            "http://127.0.0.1:8000/app",
                        ).strip(),
                        hosted_invoice_url=_value(
                            invoice, "hosted_invoice_url"
                        ),
                    )
                except (OSError, RuntimeError, sqlite3.Error):
                    pass


stripe_billing = StripeBillingService()
