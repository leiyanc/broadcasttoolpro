from typing import Literal

from pydantic import BaseModel, Field, field_validator


RoleCode = Literal["owner", "admin", "operator", "viewer"]


def _normalized_email(value: str) -> str:
    email = value.strip().lower()
    if (
        len(email) > 254
        or "@" not in email
        or email.startswith("@")
        or email.endswith("@")
    ):
        raise ValueError("Enter a valid email address.")
    return email


class BootstrapRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    display_name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalized_email(value)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalized_email(value)


class EmailPreferencesUpdate(BaseModel):
    trial_reminders: bool = True


class PasswordResetRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalized_email(value)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=10, max_length=128)


class AccessRequestCreate(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    contact_name: str = Field(min_length=2, max_length=120)
    email: str
    requested_plan: Literal[
        "programming_suite", "professional", "enterprise"
    ] = "professional"
    include_stream_monitoring: bool = False
    billing_cycle: Literal["monthly"] = "monthly"
    message: str | None = Field(default=None, max_length=2000)

    @field_validator("include_stream_monitoring")
    @classmethod
    def validate_stream_monitoring(cls, value: bool, info):
        if value and info.data.get("requested_plan") != "professional":
            raise ValueError(
                "Stream Monitoring can only be added to Professional; "
                "Enterprise already includes it."
            )
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalized_email(value)


class SalesInquiryCreate(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    contact_name: str = Field(min_length=2, max_length=120)
    email: str
    message: str = Field(min_length=5, max_length=2000)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalized_email(value)


class AccountActivationConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=10, max_length=128)


class TrialRegistrationRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    display_name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalized_email(value)


class SignupRegistrationRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    display_name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=10, max_length=128)
    requested_plan: Literal[
        "programming_suite", "professional", "enterprise"
    ] = "professional"
    include_stream_monitoring: bool = False
    billing_cycle: Literal["monthly"] = "monthly"

    @field_validator("include_stream_monitoring")
    @classmethod
    def validate_stream_monitoring(cls, value: bool, info):
        if value and info.data.get("requested_plan") != "professional":
            raise ValueError(
                "Stream Monitoring can only be added to Professional; "
                "Enterprise already includes it."
            )
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalized_email(value)


class MemberCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=10, max_length=128)
    role: RoleCode = "operator"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalized_email(value)
