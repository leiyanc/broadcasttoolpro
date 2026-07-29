from typing import Literal

from pydantic import BaseModel, Field


class OrganizationAdminUpdate(BaseModel):
    plan: Literal["professional", "enterprise"] | None = None
    status: Literal["active", "suspended"] | None = None


class AddonAdminUpdate(BaseModel):
    enabled: bool


class IncidentStatusUpdate(BaseModel):
    status: Literal["open", "investigating", "resolved"]
    resolution: str | None = Field(default=None, max_length=4000)


class IncidentMessageCreate(BaseModel):
    visibility: Literal["customer", "internal"]
    message: str = Field(min_length=2, max_length=4000)


class AccessRequestApproval(BaseModel):
    plan: Literal["professional", "enterprise"]
