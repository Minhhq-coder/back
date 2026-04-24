from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ChatbotSourceOut(BaseModel):
    type: Literal["product", "order", "payment", "knowledge", "system"]
    title: str
    snippet: str | None = None
    url: str | None = None
    source_id: str | None = None


class ChatbotActionOut(BaseModel):
    type: Literal["add_to_cart", "handoff", "login_required", "payment_status", "policy_guard"]
    status: Literal["completed", "skipped", "failed", "not_allowed"]
    label: str
    detail: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class ChatbotMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, max_length=100)
    product_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Message cannot be empty")
        return cleaned

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ChatbotMessageResponse(BaseModel):
    session_id: str
    user_message_id: int
    assistant_message_id: int
    answer: str
    sources: list[ChatbotSourceOut] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    actions: list[ChatbotActionOut] = Field(default_factory=list)
    handoff_required: bool = False
    handoff_message: str | None = None
    used_fallback: bool = False
    created_at: datetime


class ChatbotFeedbackIn(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    helpful: bool
    note: str | None = Field(default=None, max_length=500)

    @field_validator("session_id")
    @classmethod
    def normalize_session_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Session id is required")
        return cleaned


class ChatbotSuggestedQuestionsOut(BaseModel):
    items: list[str] = Field(default_factory=list)


class ChatbotKnowledgeItemCreate(BaseModel):
    kind: Literal["faq", "policy", "page", "blog"] = "faq"
    slug: str | None = Field(default=None, max_length=255)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    source_label: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list)
    priority: int = 0
    is_active: bool = True


class ChatbotKnowledgeItemUpdate(BaseModel):
    kind: Literal["faq", "policy", "page", "blog"] | None = None
    slug: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    source_label: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = None
    priority: int | None = None
    is_active: bool | None = None


class ChatbotKnowledgeItemOut(BaseModel):
    id: int
    kind: str
    slug: str | None = None
    title: str
    content: str
    source_label: str | None = None
    source_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatbotAuditMessageOut(BaseModel):
    id: int
    session_id: str
    user_id: int | None = None
    role: str
    content: str
    sources: list[ChatbotSourceOut] = Field(default_factory=list)
    actions: list[ChatbotActionOut] = Field(default_factory=list)
    helpful: bool | None = None
    feedback_note: str | None = None
    is_fallback: bool = False
    error_reason: str | None = None
    created_at: datetime


class ChatbotAuditPageOut(BaseModel):
    items: list[ChatbotAuditMessageOut] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int
