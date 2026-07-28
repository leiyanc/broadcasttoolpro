from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth import current_user
from backend.models.admin import AddonAdminUpdate, OrganizationAdminUpdate
from backend.services.admin_store import admin_store
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
            }
            for organization in organizations
        ]
    }


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

