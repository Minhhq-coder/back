from typing import Optional

from pydantic import BaseModel


class MembershipTierOut(BaseModel):
    rank: str
    min_spent: int
    max_spent: Optional[int] = None
    unlocked: bool
    current: bool


class MembershipSummaryOut(BaseModel):
    rank: str
    total_spent: int
    next_rank: Optional[str] = None
    amount_to_next_rank: int
    progress_percent: float
    benefits: list[str]
    is_top_tier: bool
    tiers: list[MembershipTierOut]
