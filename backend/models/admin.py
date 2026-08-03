from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


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
    payment_confirmed: bool = False
    waive_payment: bool = False
    access_expires_at: datetime | None = None
    waiver_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_payment_decision(self):
        if self.payment_confirmed == self.waive_payment:
            raise ValueError(
                "Confirm payment or approve complimentary access, "
                "but not both."
            )
        return self
