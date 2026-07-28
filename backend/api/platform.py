from fastapi import APIRouter, HTTPException, status

from backend.models.tenancy import (
    ChannelCreate,
    OrganizationCreate,
    WorkspaceCreate,
)
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
def create_organization(request: OrganizationCreate):
    try:
        return tenant_store.create_organization(**request.model_dump())
    except ValueError as exc:
        raise _invalid(exc) from exc


@router.get("/organizations")
def list_organizations():
    return {"organizations": tenant_store.list_organizations()}


@router.get("/organizations/{organization_id}")
def get_organization(organization_id: str):
    try:
        return tenant_store.get_organization(organization_id)
    except KeyError as exc:
        raise _not_found(exc) from exc


@router.post(
    "/organizations/{organization_id}/workspaces",
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(
    organization_id: str,
    request: WorkspaceCreate,
):
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
def list_workspaces(organization_id: str):
    try:
        workspaces = tenant_store.list_workspaces(organization_id)
    except KeyError as exc:
        raise _not_found(exc) from exc
    return {"workspaces": workspaces}


@router.get("/workspaces/{workspace_id}")
def get_workspace(workspace_id: str):
    try:
        return tenant_store.get_workspace(workspace_id)
    except KeyError as exc:
        raise _not_found(exc) from exc


@router.post(
    "/workspaces/{workspace_id}/channels",
    status_code=status.HTTP_201_CREATED,
)
def create_channel(
    workspace_id: str,
    request: ChannelCreate,
):
    try:
        return tenant_store.create_channel(
            workspace_id=workspace_id,
            **request.model_dump(),
        )
    except KeyError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise _invalid(exc) from exc


@router.get("/workspaces/{workspace_id}/channels")
def list_channels(workspace_id: str):
    try:
        channels = tenant_store.list_channels(workspace_id)
    except KeyError as exc:
        raise _not_found(exc) from exc
    return {"channels": channels}


@router.get("/channels/{channel_id}")
def get_channel(channel_id: str):
    try:
        return tenant_store.get_channel(channel_id)
    except KeyError as exc:
        raise _not_found(exc) from exc

