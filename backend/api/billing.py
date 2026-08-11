from fastapi import APIRouter, Depends, HTTPException, Request
from stripe import SignatureVerificationError, StripeError

from backend.api.auth import current_user, require_organization_role
from backend.models.billing import CheckoutSessionCreate
from backend.services.billing_store import billing_store
from backend.services.commercial_pricing import commercial_pricing
from backend.services.entitlements import entitlement_store
from backend.services.stripe_billing import stripe_billing


router = APIRouter(
    prefix="/api/billing",
    tags=["Billing"],
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
        return {
            "subscription": subscription,
            "entitlements": entitlements,
            "pricing": commercial_pricing(
                subscription["plan"],
                entitlements,
                subscription["billing_cycle"],
            ),
            "invoices": billing_store.list_invoices(organization_id),
            "payments_available": bool(
                stripe_billing.is_configured()
                and stripe_billing.webhook_secret()
            ),
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
        if subscription["provider"] == "stripe_pending":
            if request.plan_code != subscription["plan"]:
                raise ValueError(
                    "Complete Checkout for the plan approved by Broadcast "
                    "Tool Pro. Contact support to change the approved plan."
                )
            entitlements = entitlement_store.effective_entitlements(
                organization_id
            )
            approved_monitoring = (
                request.plan_code == "professional"
                and any(
                    addon["code"] == "stream_monitoring"
                    and addon["enabled"]
                    for addon in entitlements.get("addons", [])
                )
            )
            if request.include_stream_monitoring != approved_monitoring:
                raise ValueError(
                    "The Stream Monitoring selection must match the "
                    "approved access request."
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
