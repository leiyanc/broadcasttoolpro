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
    plan: Literal["programming_suite", "professional", "enterprise"]
    include_stream_monitoring: bool = False
    payment_method: Literal["stripe", "complimentary"] = "stripe"
    access_expires_at: datetime | None = None
    waiver_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_payment_decision(self):
        if self.include_stream_monitoring and self.plan != "professional":
            raise ValueError(
                "Stream Monitoring can only be added to Professional; "
                "Enterprise already includes it."
            )
        if self.payment_method == "complimentary":
            if self.access_expires_at is None:
                raise ValueError(
                    "Complimentary access requires an expiration date."
                )
            if len((self.waiver_reason or "").strip()) < 3:
                raise ValueError(
                    "Complimentary access requires an internal reason."
                )
        return self
