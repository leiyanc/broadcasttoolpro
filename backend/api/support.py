from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth import current_user
from backend.models.support import SupportMessageCreate, SupportRequestCreate
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


@router.get("/requests/{incident_id}")
def support_request_detail(
    incident_id: str,
    user: dict = Depends(current_user),
):
    _primary_organization(user)
    try:
        return admin_store.get_incident(
            incident_id,
            reporter_user_id=user["id"],
            customer_view=True,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc


@router.post("/requests/{incident_id}/messages")
def add_support_message(
    incident_id: str,
    request: SupportMessageCreate,
    user: dict = Depends(current_user),
):
    _primary_organization(user)
    try:
        admin_store.get_incident(
            incident_id,
            reporter_user_id=user["id"],
            customer_view=True,
        )
        return admin_store.add_incident_message(
            incident_id,
            author_user_id=user["id"],
            visibility="customer",
            message=request.message,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc


@router.post("/requests/{incident_id}/reopen")
def reopen_support_request(
    incident_id: str,
    user: dict = Depends(current_user),
):
    _primary_organization(user)
    try:
        detail = admin_store.get_incident(
            incident_id,
            reporter_user_id=user["id"],
            customer_view=True,
        )
        if detail["incident"]["status"] != "resolved":
            raise HTTPException(
                status_code=409,
                detail="Only resolved requests can be reopened.",
            )
        return admin_store.update_incident_status(
            incident_id,
            "open",
            actor_user_id=user["id"],
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
