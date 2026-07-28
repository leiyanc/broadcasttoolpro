from datetime import datetime
from typing import Literal

from pydantic import BaseModel


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

