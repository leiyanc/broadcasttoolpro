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
CheckoutPlan = Literal[
    "programming_suite",
    "professional",
    "enterprise",
]


class CheckoutSessionCreate(BaseModel):
    plan_code: CheckoutPlan
    include_stream_monitoring: bool = False


class SubscriptionAdminUpdate(BaseModel):
    status: SubscriptionStatus | None = None
    billing_cycle: BillingCycle | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool | None = None
    lifecycle_note: str | None = Field(default=None, max_length=500)
