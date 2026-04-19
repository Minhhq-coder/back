import asyncio

from sqlalchemy import select

from app.core.database import async_session
from app.models import Category, Product


TARGET_CATEGORIES = {
    "trang điểm": "Trang điểm",
    "chăm sóc da": "Chăm sóc da",
    "chăm sóc cá nhân": "Chăm sóc cá nhân",
}

LEGACY_MAPPING = {
    "Son môi": "Trang điểm",
    "Kem dưỡng da": "Chăm sóc da",
    "Sữa rửa mặt": "Chăm sóc da",
    "Nước hoa": "Chăm sóc cá nhân",
    "Codex Category": "Chăm sóc da",
}


async def sync_categories():
    async with async_session() as session:
        category_rows = (await session.execute(select(Category))).scalars().all()
        categories_by_name = {category.name.casefold(): category for category in category_rows}

        for key, display_name in TARGET_CATEGORIES.items():
            if key not in categories_by_name:
                category = Category(name=display_name, is_active=True)
                session.add(category)
                await session.flush()
                categories_by_name[key] = category

        moved_products = 0
        deleted_categories = 0

        for legacy_name, target_name in LEGACY_MAPPING.items():
            legacy_category = categories_by_name.get(legacy_name.casefold())
            target_category = categories_by_name.get(target_name.casefold())
            if not legacy_category or not target_category or legacy_category.id == target_category.id:
                continue

            products = (
                await session.execute(select(Product).where(Product.category_id == legacy_category.id))
            ).scalars().all()

            for product in products:
                product.category_id = target_category.id
                moved_products += 1

            await session.flush()
            await session.delete(legacy_category)
            deleted_categories += 1

        for target_name in TARGET_CATEGORIES.values():
            category = categories_by_name[target_name.casefold()]
            category.is_active = True

        await session.commit()

    return {
        "moved_products": moved_products,
        "deleted_categories": deleted_categories,
    }


def main():
    summary = asyncio.run(sync_categories())
    print(summary)


if __name__ == "__main__":
    main()
