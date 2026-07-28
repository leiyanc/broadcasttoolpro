from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.auth import current_user, require_organization_role
from backend.models.tenancy import (
    ChannelCreate,
    OrganizationCreate,
    WorkspaceCreate,
)
from backend.services.identity_store import identity_store
from backend.services.entitlements import entitlement_store
from backend.services.tenant_store import tenant_store


router = APIRouter(
    prefix="/api/platform",
    tags=["SaaS Foundation"],
)


def _not_found(exc: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc.args[0]))


def _invalid(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.post("/organizations", status_code=status.HTTP_201_CREATED)
def create_organization(
    request: OrganizationCreate,
    user: dict = Depends(current_user),
):
    try:
        organization = tenant_store.create_organization(
            **request.model_dump()
        )
        identity_store.add_membership(
            organization_id=organization["id"],
            user_id=user["id"],
            role="owner",
        )
        return organization
    except ValueError as exc:
        raise _invalid(exc) from exc


@router.get("/organizations")
def list_organizations(user: dict = Depends(current_user)):
    return {
        "organizations": identity_store.organizations_for_user(user["id"])
    }


@router.get("/organizations/{organization_id}")
def get_organization(
    organization_id: str,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id)
    try:
        return tenant_store.get_organization(organization_id)
    except KeyError as exc:
        raise _not_found(exc) from exc


@router.get("/organizations/{organization_id}/entitlements")
def organization_entitlements(
    organization_id: str,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id)
    try:
        return entitlement_store.effective_entitlements(organization_id)
    except KeyError as exc:
        raise _not_found(exc) from exc


@router.post(
    "/organizations/{organization_id}/workspaces",
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(
    organization_id: str,
    request: WorkspaceCreate,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    try:
        return tenant_store.create_workspace(
            organization_id=organization_id,
            **request.model_dump(),
        )
    except KeyError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise _invalid(exc) from exc


@router.get("/organizations/{organization_id}/workspaces")
def list_workspaces(
    organization_id: str,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id)
    try:
        workspaces = tenant_store.list_workspaces(organization_id)
    except KeyError as exc:
        raise _not_found(exc) from exc
    return {"workspaces": workspaces}


@router.get("/workspaces/{workspace_id}")
def get_workspace(
    workspace_id: str,
    user: dict = Depends(current_user),
):
    try:
        workspace = tenant_store.get_workspace(workspace_id)
    except KeyError as exc:
        raise _not_found(exc) from exc
    require_organization_role(
        user["id"],
        workspace["organization_id"],
    )
    return workspace


@router.post(
    "/workspaces/{workspace_id}/channels",
    status_code=status.HTTP_201_CREATED,
)
def create_channel(
    workspace_id: str,
    request: ChannelCreate,
    user: dict = Depends(current_user),
):
    try:
        workspace = tenant_store.get_workspace(workspace_id)
        require_organization_role(
            user["id"],
            workspace["organization_id"],
            "admin",
        )
        return tenant_store.create_channel(
            workspace_id=workspace_id,
            **request.model_dump(),
        )
    except KeyError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise _invalid(exc) from exc


@router.get("/workspaces/{workspace_id}/channels")
def list_channels(
    workspace_id: str,
    user: dict = Depends(current_user),
):
    try:
        workspace = tenant_store.get_workspace(workspace_id)
        require_organization_role(
            user["id"],
            workspace["organization_id"],
        )
        channels = tenant_store.list_channels(workspace_id)
    except KeyError as exc:
        raise _not_found(exc) from exc
    return {"channels": channels}


@router.get("/channels/{channel_id}")
def get_channel(
    channel_id: str,
    user: dict = Depends(current_user),
):
    try:
        channel = tenant_store.get_channel(channel_id)
        workspace = tenant_store.get_workspace(channel["workspace_id"])
    except KeyError as exc:
        raise _not_found(exc) from exc
    require_organization_role(
        user["id"],
        workspace["organization_id"],
    )
    return channel
