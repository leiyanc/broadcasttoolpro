from typing import Literal

from pydantic import BaseModel, Field, model_validator


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
    request_type: Literal[
        "access",
        "correction",
        "export",
        "deletion",
        "retention",
    ] | None = None
    summary: str = Field(min_length=5, max_length=160)
    details: str = Field(min_length=10, max_length=4000)
    error_message: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_request_type(self):
        if self.category == "privacy" and self.request_type is None:
            raise ValueError(
                "Privacy requests must include a request type."
            )
        if self.category != "privacy" and self.request_type is not None:
            raise ValueError(
                "Request type is available only for privacy requests."
            )
        return self


class SupportMessageCreate(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
