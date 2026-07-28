from typing import Literal

from pydantic import BaseModel


class OrganizationAdminUpdate(BaseModel):
    plan: Literal["professional", "enterprise"] | None = None
    status: Literal["active", "suspended"] | None = None


class AddonAdminUpdate(BaseModel):
    enabled: bool

