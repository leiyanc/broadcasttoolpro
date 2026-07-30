import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import current_user
from backend.models.admin import (
    AddonAdminUpdate,
    AccessRequestApproval,
    IncidentMessageCreate,
    IncidentStatusUpdate,
    OrganizationAdminUpdate,
)
from backend.models.billing import SubscriptionAdminUpdate
from backend.services.admin_store import admin_store
from backend.services.access_request_store import access_request_store
from backend.services.billing_store import billing_store
from backend.services.backup_manager import backup_manager
from backend.services.google_drive_backup import google_drive_backup
from backend.services.identity_store import identity_store
from backend.services.entitlements import entitlement_store
from backend.services.email_outbox import email_outbox_store


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


@router.get("/access-requests")
def access_requests(
    limit: int = 100,
    _: dict = Depends(superuser),
):
    return {
        "requests": access_request_store.list(limit),
    }


@router.post("/access-requests/{request_id}/approve")
def approve_access_request(
    request_id: str,
    request: AccessRequestApproval,
    administrator: dict = Depends(superuser),
):
    try:
        access_request = access_request_store.get(request_id)
        if access_request["status"] != "pending":
            raise ValueError("Only a pending request can be approved.")
        if request.waive_payment:
            if request.access_expires_at is None:
                raise ValueError(
                    "An expiration date is required when payment is waived."
                )
            expiration = request.access_expires_at
            if expiration.tzinfo is None:
                expiration = expiration.replace(tzinfo=timezone.utc)
            if expiration.astimezone(timezone.utc) <= datetime.now(
                timezone.utc
            ):
                raise ValueError(
                    "Complimentary access must expire in the future."
                )
            if len((request.waiver_reason or "").strip()) < 3:
                raise ValueError(
                    "A reason is required when payment is waived."
                )
        user, organization, activation_token = (
            identity_store.provision_customer(
                organization_name=access_request["organization_name"],
                display_name=access_request["contact_name"],
                email=access_request["email"],
                plan=request.plan,
            )
        )
        if request.waive_payment:
            subscription = billing_store.create_complimentary_subscription(
                organization["id"],
                expires_at=request.access_expires_at,
                reason=request.waiver_reason or "",
                waived_by_user_id=administrator["id"],
            )
        else:
            amount_cents = (
                9900 if request.plan == "professional" else 19900
            )
            subscription = billing_store.create_manual_paid_subscription(
                organization["id"],
                amount_cents=amount_cents,
            )
        if request.plan == "professional":
            entitlement_store.set_addon(
                organization["id"],
                "traffic_operations",
                True,
            )
        approved = access_request_store.approve(
            request_id,
            plan=request.plan,
            organization_id=organization["id"],
            user_id=user["id"],
        )
        application_url = os.getenv(
            "BTP_APPLICATION_URL",
            "http://127.0.0.1:8000/app",
        ).rstrip("/")
        activation_url = (
            f"{application_url}?mode=activate&token={activation_token}"
        )
        email_outbox_store.schedule_account_activation(
            organization_id=organization["id"],
            recipient_email=user["email"],
            organization_name=organization["name"],
            plan=request.plan,
            activation_url=activation_url,
        )
        return {
            "request": approved,
            "organization": organization,
            "subscription": subscription,
            "activation_url": activation_url,
            "message": (
                f"{request.plan.title()} account created"
                f"{' with waived payment' if request.waive_payment else ''}. "
                "The activation message is queued."
            ),
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/access-requests/{request_id}/reject")
def reject_access_request(
    request_id: str,
    _: dict = Depends(superuser),
):
    try:
        return access_request_store.reject(request_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
