from typing import Literal

from pydantic import BaseModel, Field


PlanCode = Literal["starter", "professional", "enterprise"]


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    plan: PlanCode = "starter"


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
        max_length=12,
        pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$",
    )

