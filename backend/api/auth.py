from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Response,
    status,
)

from backend.models.identity import (
    BootstrapRequest,
    LoginRequest,
    MemberCreate,
)
from backend.services.identity_store import identity_store


SESSION_COOKIE = "btp_session"

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


@router.get("/status")
def authentication_status():
    return {
        "bootstrap_required": not identity_store.has_users(),
    }


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=12 * 60 * 60,
        httponly=True,
        samesite="strict",
        secure=False,
        path="/",
    )


def current_user(
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE,
    ),
) -> dict:
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )
    user = identity_store.user_from_session(session_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The session is invalid or has expired.",
        )
    return user


def require_organization_role(
    user_id: str,
    organization_id: str,
    minimum_role: str = "viewer",
) -> dict:
    try:
        return identity_store.require_role(
            user_id,
            organization_id,
            minimum_role,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/bootstrap", status_code=status.HTTP_201_CREATED)
def bootstrap_platform(request: BootstrapRequest, response: Response):
    try:
        user, organization, token = identity_store.bootstrap(
            **request.model_dump()
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _set_session_cookie(response, token)
    return {
        "user": user,
        "organizations": [organization],
    }


@router.post("/login")
def login(request: LoginRequest, response: Response):
    try:
        user, token = identity_store.authenticate(
            request.email,
            request.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _set_session_cookie(response, token)
    return {
        "user": user,
        "organizations": identity_store.organizations_for_user(user["id"]),
    }


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {
        "user": user,
        "organizations": identity_store.organizations_for_user(user["id"]),
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session_token: str | None = Cookie(
        default=None,
        alias=SESSION_COOKIE,
    ),
):
    if session_token:
        identity_store.revoke_session(session_token)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.post(
    "/organizations/{organization_id}/members",
    status_code=status.HTTP_201_CREATED,
)
def create_member(
    organization_id: str,
    request: MemberCreate,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    if request.role == "owner":
        require_organization_role(user["id"], organization_id, "owner")
    try:
        return identity_store.create_member(
            organization_id=organization_id,
            **request.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/organizations/{organization_id}/members")
def list_members(
    organization_id: str,
    user: dict = Depends(current_user),
):
    require_organization_role(user["id"], organization_id, "admin")
    return {
        "members": identity_store.list_members(organization_id),
    }
