"""
Fix ALL users with plain-text passwords - rehash them with bcrypt.
Run: python fix_all_passwords.py
"""
import asyncio
import bcrypt
from sqlalchemy import select
from app.core.database import async_session
from app.models import User


async def fix():
    async with async_session() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

        fixed = 0
        for user in users:
            # If password does NOT start with "$2b$", it's not a bcrypt hash
            if user.password and not user.password.startswith("$2b$"):
                plain = user.password  # current value IS the plain-text password
                hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                user.password = hashed
                fixed += 1
                print(f"  Fixed: {user.email} (plain: {plain!r} -> bcrypt hash)")

        if fixed > 0:
            await db.commit()
            print(f"\nDone! Rehashed {fixed} user(s).")
        else:
            print("All passwords are already bcrypt hashes. Nothing to fix.")


if __name__ == "__main__":
    asyncio.run(fix())
