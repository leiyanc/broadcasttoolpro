from typing import Literal

from pydantic import BaseModel, Field


PlanCode = Literal["professional", "enterprise"]


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    plan: PlanCode = "professional"


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    default_timezone: str = Field(
        default="America/New_York",
        min_length=1,
        max_length=64,
    )


class ChannelCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    channel_code: str | None = Field(default=None, max_length=80)
    timezone: str = Field(
        default="America/New_York",
        min_length=1,
        max_length=64,
    )
    primary_language: str = Field(
        default="en",
        min_length=2,
        max_length=35,
        pattern=(
            r"^[A-Za-z]{2,3}(?:-[A-Za-z]{4})?"
            r"(?:-(?:[A-Za-z]{2}|[0-9]{3}))?"
            r"(?:-[A-Za-z0-9]{5,8})*$"
        ),
    )


class ChannelProfileUpdate(BaseModel):
    primary_language: str = Field(
        min_length=2,
        max_length=35,
        pattern=(
            r"^[A-Za-z]{2,3}(?:-[A-Za-z]{4})?"
            r"(?:-(?:[A-Za-z]{2}|[0-9]{3}))?"
            r"(?:-[A-Za-z0-9]{5,8})*$"
        ),
    )
