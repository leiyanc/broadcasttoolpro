from fastapi import APIRouter, Depends, HTTPException, Request
from stripe import SignatureVerificationError, StripeError

from backend.api.auth import current_user, require_organization_role
from backend.models.billing import (
    ChannelPurchaseCreate,
    CheckoutSessionCreate,
    SubscriptionChangeCreate,
)
from backend.services.billing_store import billing_store
from backend.services.commercial_pricing import commercial_pricing
from backend.services.entitlements import entitlement_store
from backend.services.stripe_billing import stripe_billing
from backend.services.tenant_store import tenant_store


router = APIRouter(
    prefix="/api/billing",
    tags=["Billing"],
)


def _requires_checkout_selection_sync(subscription: dict) -> bool:
    """Keep the local pending selection aligned with Stripe Checkout."""
    return subscription["provider"] == "stripe_pending" or (
        subscription["provider"] == "stripe"
        and subscription["status"] == "canceled"
    )


@router.get("/organizations/{organization_id}")
def organization_billing(
    organization_id: str,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    try:
        subscription = billing_store.get_subscription(organization_id)
        entitlements = entitlement_store.effective_entitlements(
            organization_id
        )
        channels = tenant_store.list_organization_channels(organization_id)
        channel_count = len([
            channel for channel in channels if channel["active"]
        ])
        return {
            "subscription": subscription,
            "entitlements": entitlements,
            "pricing": commercial_pricing(
                subscription["plan"],
                entitlements,
                subscription["billing_cycle"],
                channel_count,
            ),
            "invoices": billing_store.list_invoices(organization_id),
            "channels": channels,
            "payments_available": bool(
                stripe_billing.is_configured()
                and stripe_billing.webhook_secret()
            ),
            "approved_checkout": None,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc


@router.post("/organizations/{organization_id}/checkout")
def create_checkout(
    organization_id: str,
    request: CheckoutSessionCreate,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    if not stripe_billing.webhook_secret():
        raise HTTPException(
            status_code=503,
            detail="Online payment confirmation is not configured.",
        )
    try:
        subscription = billing_store.get_subscription(organization_id)
        if _requires_checkout_selection_sync(subscription):
            amount_cents = {
                "programming_suite": 3900,
                "professional": 9900,
                "enterprise": 19900,
            }[request.plan_code] + (
                5900 if request.include_stream_monitoring else 0
            )
            subscription = billing_store.revise_pending_stripe_subscription(
                organization_id,
                plan_code=request.plan_code,
                amount_cents=amount_cents,
            )
        checkout_url = stripe_billing.create_checkout_session(
            organization_id=organization_id,
            email=user["email"],
            plan_code=request.plan_code,
            include_stream_monitoring=request.include_stream_monitoring,
        )
        return {"checkout_url": checkout_url}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, StripeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe Checkout is temporarily unavailable.",
        ) from exc


@router.post("/organizations/{organization_id}/change")
def change_subscription(
    organization_id: str,
    request: SubscriptionChangeCreate,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    try:
        return stripe_billing.change_subscription(
            organization_id=organization_id,
            plan_code=request.plan_code,
            include_stream_monitoring=request.include_stream_monitoring,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, StripeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe could not update the subscription.",
        ) from exc


@router.post("/organizations/{organization_id}/channels/preview")
def preview_channel_purchase(
    organization_id: str,
    request: ChannelPurchaseCreate,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    try:
        return stripe_billing.preview_channel_purchase(
            organization_id=organization_id,
            name=request.name,
            channel_code=request.channel_code,
            timezone=request.timezone,
            primary_language=request.primary_language,
            stream_monitoring=request.stream_monitoring,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, StripeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe could not calculate the channel cost.",
        ) from exc


@router.post("/organizations/{organization_id}/channels")
def purchase_channel(
    organization_id: str,
    request: ChannelPurchaseCreate,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    try:
        return stripe_billing.purchase_channel(
            organization_id=organization_id,
            **request.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, StripeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe could not add the channel to the subscription.",
        ) from exc


@router.post(
    "/organizations/{organization_id}/channels/{channel_id}/removal/preview"
)
def preview_channel_removal(
    organization_id: str,
    channel_id: str,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    try:
        return stripe_billing.preview_channel_removal(
            organization_id=organization_id,
            channel_id=channel_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, StripeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe could not calculate the channel removal.",
        ) from exc


@router.post(
    "/organizations/{organization_id}/channels/{channel_id}/removal"
)
def schedule_channel_removal(
    organization_id: str,
    channel_id: str,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    try:
        return stripe_billing.schedule_channel_removal(
            organization_id=organization_id,
            channel_id=channel_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, StripeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe could not schedule the channel removal.",
        ) from exc


@router.post(
    "/organizations/{organization_id}/channels/{channel_id}/removal/cancel"
)
def cancel_channel_removal(
    organization_id: str,
    channel_id: str,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    try:
        return stripe_billing.cancel_channel_removal(
            organization_id=organization_id,
            channel_id=channel_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, StripeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe could not cancel the channel removal.",
        ) from exc


@router.post("/organizations/{organization_id}/change/preview")
def preview_subscription_change(
    organization_id: str,
    request: SubscriptionChangeCreate,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    try:
        return stripe_billing.preview_subscription_change(
            organization_id=organization_id,
            plan_code=request.plan_code,
            include_stream_monitoring=request.include_stream_monitoring,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, StripeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe could not calculate the subscription change.",
        ) from exc


@router.post("/organizations/{organization_id}/change/cancel")
def cancel_scheduled_subscription_change(
    organization_id: str,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    try:
        stripe_billing.cancel_scheduled_change(
            organization_id=organization_id,
        )
        return {"canceled": True}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, StripeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe could not cancel the scheduled change.",
        ) from exc


@router.post("/organizations/{organization_id}/cancellation")
def change_cancellation(
    organization_id: str,
    cancel: bool,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    try:
        stripe_billing.set_cancel_at_period_end(
            organization_id=organization_id,
            cancel=cancel,
        )
        return {"cancel_at_period_end": cancel}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RuntimeError, StripeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe could not update the cancellation.",
        ) from exc


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = stripe_billing.construct_event(payload, signature)
        stripe_billing.process_event(event)
    except (ValueError, SignatureVerificationError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid Stripe webhook.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Stripe webhook verification is unavailable.",
        ) from exc
    return {"received": True}
