from typing import Literal

from pydantic import BaseModel, Field


class SupportRequestCreate(BaseModel):
    module: str = Field(min_length=2, max_length=80)
    category: Literal[
        "technical",
        "validation",
        "export",
        "billing",
        "account",
        "privacy",
        "other",
    ]
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    summary: str = Field(min_length=5, max_length=160)
    details: str = Field(min_length=10, max_length=4000)
    error_message: str | None = Field(default=None, max_length=2000)


class SupportMessageCreate(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
