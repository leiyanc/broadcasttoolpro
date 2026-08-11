from fastapi import APIRouter, Depends, HTTPException, Request
from stripe import SignatureVerificationError, StripeError

from backend.api.auth import current_user, require_organization_role
from backend.models.billing import CheckoutSessionCreate
from backend.services.billing_store import billing_store
from backend.services.access_request_store import access_request_store
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
        approved_request = (
            access_request_store.approved_for_organization(organization_id)
        )
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
            "approved_checkout": (
                {
                    "plan_code": approved_request["requested_plan"],
                    "include_stream_monitoring": approved_request[
                        "include_stream_monitoring"
                    ],
                }
                if subscription["provider"] == "stripe_pending"
                and approved_request
                else None
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
            approved_request = (
                access_request_store.approved_for_organization(
                    organization_id
                )
            )
            approved_plan = (
                approved_request["requested_plan"]
                if approved_request else subscription["plan"]
            )
            if request.plan_code != approved_plan:
                raise ValueError(
                    "Complete Checkout for the plan approved by Broadcast "
                    "Tool Pro. Contact support to change the approved plan."
                )
            approved_monitoring = bool(
                approved_request
                and approved_request["include_stream_monitoring"]
            )
            amount_cents = {
                "programming_suite": 3900,
                "professional": 9900,
                "enterprise": 19900,
            }[approved_plan] + (5900 if approved_monitoring else 0)
            if subscription["plan"] != approved_plan:
                subscription = billing_store.revise_pending_stripe_subscription(
                    organization_id,
                    plan_code=approved_plan,
                    amount_cents=amount_cents,
                )
            entitlements = entitlement_store.effective_entitlements(
                organization_id
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
