from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


_MOJIBAKE_MARKERS = ("Ã", "Ä", "Æ", "áº", "á»")


def _mojibake_score(value: str) -> int:
    marker_score = sum(value.count(marker) for marker in _MOJIBAKE_MARKERS)
    control_score = sum(1 for char in value if "\u0080" <= char <= "\u009f")
    return marker_score + control_score


def _repair_mojibake(value: str) -> str:
    if _mojibake_score(value) == 0:
        return value

    try:
        repaired = value.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return value

    return repaired if _mojibake_score(repaired) < _mojibake_score(value) else value


class NotificationOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    target_role: Optional[str] = None
    title: str
    message: str
    order_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    @field_validator("title", "message", mode="before")
    @classmethod
    def repair_notification_text(cls, value: str) -> str:
        if isinstance(value, str):
            return _repair_mojibake(value)
        return value

    model_config = {"from_attributes": True}
