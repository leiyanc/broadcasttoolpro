from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field


SubscriptionStatus = Literal[
    "trialing",
    "active",
    "past_due",
    "canceled",
]
BillingCycle = Literal["monthly", "annual"]


class SubscriptionAdminUpdate(BaseModel):
    status: SubscriptionStatus | None = None
    billing_cycle: BillingCycle | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool | None = None
    lifecycle_note: str | None = Field(default=None, max_length=500)
