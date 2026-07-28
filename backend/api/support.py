from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth import current_user
from backend.models.support import SupportRequestCreate
from backend.services.admin_store import admin_store
from backend.services.identity_store import identity_store


router = APIRouter(
    prefix="/api/support",
    tags=["Support"],
)


def _primary_organization(user: dict) -> dict:
    organizations = identity_store.organizations_for_user(user["id"])
    if not organizations:
        raise HTTPException(
            status_code=403,
            detail="The user is not assigned to an organization.",
        )
    return organizations[0]


@router.post("/requests", status_code=status.HTTP_201_CREATED)
def create_support_request(
    request: SupportRequestCreate,
    user: dict = Depends(current_user),
):
    organization = _primary_organization(user)
    incident_id = admin_store.record_incident(
        organization_id=organization["id"],
        reporter_user_id=user["id"],
        module=request.module,
        category=request.category,
        severity={
            "low": "info",
            "normal": "info",
            "high": "warning",
            "urgent": "critical",
        }[request.priority],
        priority=request.priority,
        summary=request.summary,
        details=request.details,
        error_message=request.error_message,
    )
    return {
        "id": incident_id,
        "status": "open",
        "message": "Your support request was submitted.",
    }


@router.get("/requests")
def my_support_requests(user: dict = Depends(current_user)):
    _primary_organization(user)
    return {
        "requests": admin_store.list_user_incidents(user["id"]),
    }

