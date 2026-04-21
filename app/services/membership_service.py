from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderDetail, OrderStatus, PaymentStatus
from app.schemas.membership import MembershipSummaryOut, MembershipTierOut


@dataclass(frozen=True)
class MembershipTier:
    rank: str
    min_spent: int
    max_spent: Optional[int]
    benefits: tuple[str, ...]


MEMBERSHIP_TIERS: tuple[MembershipTier, ...] = (
    MembershipTier(
        rank="Member",
        min_spent=0,
        max_spent=999_999,
        benefits=(
            "Nhận thông tin khuyến mãi cơ bản",
            "Theo dõi ưu đãi và sản phẩm mới theo mùa",
        ),
    ),
    MembershipTier(
        rank="Silver",
        min_spent=1_000_000,
        max_spent=4_999_999,
        benefits=(
            "Giảm 3% cho đơn đủ điều kiện",
            "Ưu tiên nhận thông tin flash sale",
        ),
    ),
    MembershipTier(
        rank="Gold",
        min_spent=5_000_000,
        max_spent=14_999_999,
        benefits=(
            "Giảm 5% cho đơn đủ điều kiện",
            "Freeship cho một số đơn nổi bật",
        ),
    ),
    MembershipTier(
        rank="Platinum",
        min_spent=15_000_000,
        max_spent=29_999_999,
        benefits=(
            "Giảm 8% cho đơn đủ điều kiện",
            "Quà sinh nhật và ưu đãi thành viên thân thiết",
        ),
    ),
    MembershipTier(
        rank="Diamond",
        min_spent=30_000_000,
        max_spent=None,
        benefits=(
            "Giảm 10% cho đơn đủ điều kiện",
            "Ưu tiên hàng mới và quà sinh nhật đặc biệt",
        ),
    ),
)


def get_membership_rank(total_spent: int) -> str:
    return _get_membership_tier(total_spent).rank


def get_next_rank_info(total_spent: int) -> dict:
    current_tier = _get_membership_tier(total_spent)
    current_index = _get_tier_index(current_tier.rank)

    if current_index == len(MEMBERSHIP_TIERS) - 1:
        return {
            "next_rank": None,
            "amount_to_next_rank": 0,
            "progress_percent": 100.0,
            "is_top_tier": True,
        }

    next_tier = MEMBERSHIP_TIERS[current_index + 1]
    span = max(next_tier.min_spent - current_tier.min_spent, 1)
    progress = ((total_spent - current_tier.min_spent) / span) * 100
    progress = max(0.0, min(progress, 100.0))

    return {
        "next_rank": next_tier.rank,
        "amount_to_next_rank": max(next_tier.min_spent - total_spent, 0),
        "progress_percent": round(progress, 2),
        "is_top_tier": False,
    }


def build_membership_summary(total_spent: int) -> MembershipSummaryOut:
    current_tier = _get_membership_tier(total_spent)
    next_rank_info = get_next_rank_info(total_spent)

    tiers = [
        MembershipTierOut(
            rank=tier.rank,
            min_spent=tier.min_spent,
            max_spent=tier.max_spent,
            unlocked=total_spent >= tier.min_spent,
            current=tier.rank == current_tier.rank,
        )
        for tier in MEMBERSHIP_TIERS
    ]

    return MembershipSummaryOut(
        rank=current_tier.rank,
        total_spent=max(total_spent, 0),
        next_rank=next_rank_info["next_rank"],
        amount_to_next_rank=next_rank_info["amount_to_next_rank"],
        progress_percent=next_rank_info["progress_percent"],
        benefits=list(current_tier.benefits),
        is_top_tier=next_rank_info["is_top_tier"],
        tiers=tiers,
    )


async def get_user_membership_summary(db: AsyncSession, user_id: int) -> MembershipSummaryOut:
    amount_expr = OrderDetail.quantity * OrderDetail.product_price
    query = (
        select(func.coalesce(func.sum(amount_expr), 0.0))
        .select_from(OrderDetail)
        .join(Order, Order.id == OrderDetail.order_id)
        .where(
            Order.user_id == user_id,
            Order.status != OrderStatus.CANCELLED.value,
            or_(
                Order.is_paid.is_(True),
                Order.payment_status == PaymentStatus.PAID.value,
            ),
        )
    )
    total_spent_raw = await db.scalar(query)
    total_spent = int(round(float(total_spent_raw or 0)))
    return build_membership_summary(total_spent)


def _get_membership_tier(total_spent: int) -> MembershipTier:
    normalized_total = max(total_spent, 0)
    for tier in reversed(MEMBERSHIP_TIERS):
        if normalized_total >= tier.min_spent:
            return tier
    return MEMBERSHIP_TIERS[0]


def _get_tier_index(rank: str) -> int:
    for index, tier in enumerate(MEMBERSHIP_TIERS):
        if tier.rank == rank:
            return index
    return 0
