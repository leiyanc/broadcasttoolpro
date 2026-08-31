import os
import sqlite3
from uuid import uuid4

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Response,
    status,
)

from backend.models.identity import (
    AccountActivationConfirm,
    BootstrapRequest,
    EmailPreferencesUpdate,
    LoginRequest,
    MemberCreate,
    PasswordResetConfirm,
    PasswordResetRequest,
    SalesInquiryCreate,
    SignupRegistrationRequest,
)
from backend.services.billing_store import billing_store
from backend.services.identity_store import (
    AuthenticationLockedError,
    identity_store,
)
from backend.services.entitlements import entitlement_store
from backend.services.email_outbox import email_outbox_store


SESSION_COOKIE = "btp_session"
REMEMBERED_SESSION_DAYS = 30
PASSWORD_RESET_RESPONSE = (
    "If an active account matches that email address, password reset "
    "instructions have been queued."
)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


@router.get("/status")
def authentication_status():
    return {
        "bootstrap_required": (
            not identity_store.has_users()
            and _web_bootstrap_allowed()
        ),
    }


def _web_bootstrap_allowed() -> bool:
    explicit = os.getenv("BTP_ALLOW_WEB_BOOTSTRAP", "").strip().lower()
    if explicit:
        return explicit in {"1", "true", "yes"}
    return os.getenv("BTP_ENV", "development").strip().lower() in {
        "development",
        "local",
        "test",
    }


def _set_session_cookie(
    response: Response,
    token: str,
    *,
    remember_me: bool = False,
) -> None:
    cookie_options = {
        "key": SESSION_COOKIE,
        "value": token,
        "httponly": True,
        "samesite": "strict",
        "secure": (
            os.getenv("BTP_COOKIE_SECURE", "").lower()
            in {"1", "true", "yes"}
            or os.getenv("BTP_ENV", "").lower() == "production"
        ),
        "path": "/",
    }
    if remember_me:
        cookie_options["max_age"] = REMEMBERED_SESSION_DAYS * 24 * 60 * 60
    response.set_cookie(**cookie_options)


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


def require_module(module_code: str):
    def dependency(user: dict = Depends(current_user)) -> dict:
        organizations = identity_store.organizations_for_user(user["id"])
        for organization in organizations:
            if organization["status"] != "active":
                continue
            entitlements = entitlement_store.effective_entitlements(
                organization["id"]
            )
            if entitlements["modules"].get(module_code, {}).get("enabled"):
                return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f'Access to "{module_code}" is not enabled for '
                "this organization."
            ),
        )

    return dependency


def access_for_user(user: dict) -> dict:
    organizations = identity_store.organizations_for_user(user["id"])
    if not organizations:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organization is assigned to this account.",
        )
    organization = organizations[0]
    entitlements = entitlement_store.effective_entitlements(
        organization["id"]
    )
    return {
        "organization": organization,
        "entitlements": entitlements,
        "trial": entitlements.get("access", {}).get("type") == "trial",
    }


def is_trial_user(user: object) -> bool:
    return isinstance(user, dict) and access_for_user(user)["trial"]


def require_active_organization(
    user: dict = Depends(current_user),
) -> dict:
    organizations = identity_store.organizations_for_user(user["id"])
    if any(
        organization["status"] == "active"
        for organization in organizations
    ):
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This organization is suspended.",
    )


@router.post("/bootstrap", status_code=status.HTTP_201_CREATED)
def bootstrap_platform(request: BootstrapRequest, response: Response):
    if not _web_bootstrap_allowed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Web-based platform bootstrap is disabled. "
                "Initialize the administrator through the deployment process."
            ),
        )
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
            session_hours=(
                REMEMBERED_SESSION_DAYS * 24
                if request.remember_me
                else 12
            ),
        )
    except AuthenticationLockedError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _set_session_cookie(
        response,
        token,
        remember_me=request.remember_me,
    )
    return {
        "user": user,
        "organizations": identity_store.organizations_for_user(user["id"]),
    }


@router.get("/email-preferences")
def email_preferences(user: dict = Depends(current_user)):
    return email_outbox_store.preferences_for(user["email"])


@router.put("/email-preferences")
def update_email_preferences(
    request: EmailPreferencesUpdate,
    user: dict = Depends(current_user),
):
    return email_outbox_store.update_preferences(
        user["email"],
        trial_reminders=request.trial_reminders,
    )


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(request: PasswordResetRequest):
    reset = identity_store.create_password_reset(request.email)
    if reset:
        account, token = reset
        application_url = os.getenv(
            "BTP_APPLICATION_URL",
            "http://127.0.0.1:8000/app",
        ).rstrip("/")
        email_outbox_store.schedule_password_reset(
            organization_id=account["organization_id"],
            recipient_email=account["email"],
            reset_url=f"{application_url}?mode=reset&token={token}",
        )
    return {"message": PASSWORD_RESET_RESPONSE}


@router.post("/password-reset/confirm")
def confirm_password_reset(request: PasswordResetConfirm):
    try:
        identity_store.reset_password(request.token, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "message": (
            "Password updated. Sign in again with your new password."
        )
    }


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def register_customer(
    request: SignupRegistrationRequest,
    response: Response,
):
    amount_cents = {
        "programming_suite": 3900,
        "professional": 9900,
        "enterprise": 19900,
    }[request.requested_plan]
    if request.include_stream_monitoring:
        amount_cents += 5900
    try:
        user, organization, token = identity_store.register_customer(
            organization_name=request.organization_name,
            channel_name=request.channel_name,
            channel_stream_monitoring=(
                request.include_stream_monitoring
                or request.requested_plan == "enterprise"
            ),
            display_name=request.display_name,
            email=request.email,
            password=request.password,
            plan_code=request.requested_plan,
        )
        subscription = billing_store.create_pending_stripe_subscription(
            organization["id"],
            plan_code=request.requested_plan,
            amount_cents=amount_cents,
            billing_cycle=request.billing_cycle,
        )
        try:
            email_outbox_store.schedule_self_service_signup(
                organization_id=organization["id"],
                recipient_email=user["email"],
                administrator_emails=[
                    target["email"]
                    for target in identity_store.superuser_notification_targets()
                ],
                organization_name=organization["name"],
                plan_code=request.requested_plan,
                include_stream_monitoring=request.include_stream_monitoring,
            )
        except sqlite3.Error:
            # Account creation and Checkout must not be rolled back merely
            # because a non-critical notification could not be queued.
            pass
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _set_session_cookie(response, token)
    return {
        "user": user,
        "organizations": [organization],
        "subscription": subscription,
        "checkout": {
            "plan_code": request.requested_plan,
            "include_stream_monitoring": request.include_stream_monitoring,
        },
    }


@router.post("/sales-inquiries", status_code=status.HTTP_202_ACCEPTED)
def create_sales_inquiry(request: SalesInquiryCreate):
    notification_targets = identity_store.superuser_notification_targets()
    if not notification_targets:
        raise HTTPException(
            status_code=503,
            detail="Sales contact is temporarily unavailable.",
        )
    reference = f"SALES-{uuid4().hex[:10].upper()}"
    sales_email = (
        os.getenv("BTP_SALES_EMAIL", "").strip()
        or notification_targets[0]["email"]
    )
    try:
        messages = email_outbox_store.schedule_sales_inquiry(
            notification_organization_id=(
                notification_targets[0]["organization_id"]
            ),
            reference=reference,
            organization_name=request.organization_name,
            contact_name=request.contact_name,
            requester_email=request.email,
            request_message=request.message,
            sales_email=sales_email,
        )
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="The sales inquiry could not be queued.",
        ) from exc
    return {
        "reference": reference,
        "communications_scheduled": len(messages),
        "message": "Your sales inquiry was received.",
    }


@router.post("/activate-account")
def activate_account(
    request: AccountActivationConfirm,
    response: Response,
):
    try:
        user, token = identity_store.activate_account(
            request.token,
            request.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        samesite="strict",
        secure=(
            os.getenv("BTP_COOKIE_SECURE", "").lower()
            in {"1", "true", "yes"}
            or os.getenv("BTP_ENV", "").lower() == "production"
        ),
    )


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
