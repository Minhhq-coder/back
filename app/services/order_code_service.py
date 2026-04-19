import secrets
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order

ALPHABET = string.ascii_uppercase
DIGITS = string.digits
ALPHANUM = ALPHABET + DIGITS


def _build_order_code() -> str:
    chars = [
        secrets.choice(ALPHABET),
        secrets.choice(DIGITS),
        *[secrets.choice(ALPHANUM) for _ in range(6)],
    ]
    secrets.SystemRandom().shuffle(chars)
    return f"OD{''.join(chars)}"


async def generate_unique_order_code(db: AsyncSession) -> str:
    while True:
        code = _build_order_code()
        result = await db.execute(select(Order.id).where(Order.order_code == code))
        if result.scalar_one_or_none() is None:
            return code
