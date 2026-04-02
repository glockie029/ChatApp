from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000000, description="Message body (supports E2EE Base64 images)")
    username: str = Field("Anonymous", max_length=50, description="Display name")

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("content must not be empty")
        return normalized

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip()
        return normalized or "Anonymous"


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    content: str
    created_at: datetime
    risk_tags: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    unsafe_routes_enabled: bool


class ModerationSummary(BaseModel):
    total_messages: int
    flagged_messages: int
    monitored_keywords: list[str]
