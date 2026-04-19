from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ReviewOut(BaseModel):
    id: int
    user_id: int
    product_id: int
    rating: int
    comment: str | None = None
    created_at: datetime
    updated_at: datetime
    user_name: str
    user_avatar: str | None = None


class ProductReviewSummaryOut(BaseModel):
    items: list[ReviewOut] = Field(default_factory=list)
    average_rating: float = 0
    review_count: int = 0
    can_review: bool = False
    my_review: ReviewOut | None = None
