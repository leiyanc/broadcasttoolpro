from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import current_user, require_organization_role
from backend.services.billing_store import billing_store
from backend.services.entitlements import entitlement_store


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
        return {
            "subscription": billing_store.get_subscription(organization_id),
            "entitlements": entitlement_store.effective_entitlements(
                organization_id
            ),
            "invoices": billing_store.list_invoices(organization_id),
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc

