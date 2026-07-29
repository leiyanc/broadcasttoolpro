from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import current_user
from backend.models.admin import (
    AddonAdminUpdate,
    IncidentMessageCreate,
    IncidentStatusUpdate,
    OrganizationAdminUpdate,
)
from backend.models.billing import SubscriptionAdminUpdate
from backend.services.admin_store import admin_store
from backend.services.billing_store import billing_store
from backend.services.backup_manager import backup_manager
from backend.services.google_drive_backup import google_drive_backup
from backend.services.identity_store import identity_store
from backend.services.entitlements import entitlement_store


router = APIRouter(
    prefix="/api/admin",
    tags=["Super Admin"],
)


def superuser(user: dict = Depends(current_user)) -> dict:
    if not user.get("is_superuser"):
        raise HTTPException(
            status_code=403,
            detail="Super Admin access is required.",
        )
    return user


@router.get("/overview")
def admin_overview(_: dict = Depends(superuser)):
    return admin_store.overview()


@router.get("/security-events")
def security_events(
    limit: int = 100,
    _: dict = Depends(superuser),
):
    return {
        "events": identity_store.security_events(
            min(max(limit, 1), 500)
        ),
    }


@router.get("/backups")
def backup_status(_: dict = Depends(superuser)):
    return {
        **backup_manager.status(),
        "google_drive": google_drive_backup.status(),
    }


@router.post("/backups")
def create_backup(_: dict = Depends(superuser)):
    try:
        backup = backup_manager.create_backup()
        if backup is None:
            raise HTTPException(
                status_code=409,
                detail="A backup is already running or unavailable.",
            )
        drive_result = None
        if google_drive_backup.is_authorized():
            drive_result = google_drive_backup.upload_safely(
                backup_directory=backup_manager.backup_directory,
                manifest=backup,
            )
        return {
            "backup": backup,
            "verification": backup_manager.verify_latest(),
            "google_drive_upload": drive_result,
            "status": {
                **backup_manager.status(),
                "google_drive": google_drive_backup.status(),
            },
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/organizations")
def admin_organizations(_: dict = Depends(superuser)):
    organizations = admin_store.organizations()
    return {
        "organizations": [
            {
                **organization,
                "entitlements": entitlement_store.effective_entitlements(
                    organization["id"]
                ),
                "subscription": billing_store.get_subscription(
                    organization["id"]
                ),
            }
            for organization in organizations
        ]
    }


@router.patch("/organizations/{organization_id}/subscription")
def update_subscription(
    organization_id: str,
    request: SubscriptionAdminUpdate,
    _: dict = Depends(superuser),
):
    try:
        return billing_store.update_subscription(
            organization_id,
            **request.model_dump(),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/organizations/{organization_id}")
def update_organization(
    organization_id: str,
    request: OrganizationAdminUpdate,
    _: dict = Depends(superuser),
):
    try:
        return admin_store.update_organization(
            organization_id,
            **request.model_dump(),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/organizations/{organization_id}/addons/{addon_code}")
def update_addon(
    organization_id: str,
    addon_code: str,
    request: AddonAdminUpdate,
    _: dict = Depends(superuser),
):
    try:
        entitlement_store.set_addon(
            organization_id,
            addon_code,
            request.enabled,
        )
        return entitlement_store.effective_entitlements(organization_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/incidents")
def admin_incidents(
    limit: int = 100,
    _: dict = Depends(superuser),
):
    return {
        "incidents": admin_store.list_incidents(limit),
    }


@router.patch("/incidents/{incident_id}")
def update_incident_status(
    incident_id: str,
    request: IncidentStatusUpdate,
    user: dict = Depends(superuser),
):
    try:
        return admin_store.update_incident_status(
            incident_id,
            request.status,
            actor_user_id=user["id"],
            resolution=request.resolution,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/incidents/{incident_id}")
def incident_detail(
    incident_id: str,
    _: dict = Depends(superuser),
):
    try:
        return admin_store.get_incident(incident_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc


@router.post("/incidents/{incident_id}/messages")
def add_incident_message(
    incident_id: str,
    request: IncidentMessageCreate,
    user: dict = Depends(superuser),
):
    try:
        return admin_store.add_incident_message(
            incident_id,
            author_user_id=user["id"],
            visibility=request.visibility,
            message=request.message,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
