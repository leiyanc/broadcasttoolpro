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


class TrialRegistrationRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=120)
    display_name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=10, max_length=128)

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
