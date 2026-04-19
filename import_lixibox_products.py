import argparse
import asyncio
import json
from datetime import date
from pathlib import Path

from sqlalchemy import select, text

from app.core.database import async_session, engine
from app.models import Category, Product


DEFAULT_JSON_PATH = Path(r"C:\Users\minhhq\Desktop\crawl data\clean_lixibox_products.json")


def repair_text(value):
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)

    text = value.strip()
    if not text:
        return None

    if any(token in text for token in ("Ã", "Ä", "â", "Â")):
        try:
            repaired = text.encode("latin1").decode("utf-8")
            if repaired:
                text = repaired.strip()
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return text or None


def repair_list(values):
    if not values:
        return []
    cleaned = []
    for value in values:
        repaired = repair_text(value)
        if repaired:
            cleaned.append(repaired)
    return cleaned


def derive_quantity(stock_status):
    stock = (repair_text(stock_status) or "unknown").lower()
    if stock in {"out_of_stock", "sold_out", "unavailable"}:
        return 0
    if stock in {"low_stock", "limited"}:
        return 5
    return 100


def parse_date(value):
    repaired = repair_text(value)
    if not repaired:
        return None
    try:
        return date.fromisoformat(repaired)
    except ValueError:
        return None


def normalize_category_name(value):
    repaired = repair_text(value)
    if not repaired:
        return "Khác"
    return repaired[:1].upper() + repaired[1:]


def build_product_payload(item, category_id):
    stock_status = repair_text(item.get("stock_status")) or "unknown"
    image_url = repair_text(item.get("image_url"))
    price = float(item.get("price") or 0)
    original_price = float(item.get("original_price") or price or 0)
    quantity = derive_quantity(stock_status)

    return {
        "external_id": repair_text(item.get("id")),
        "slug": repair_text(item.get("slug")),
        "name": repair_text(item.get("name")) or "Sản phẩm chưa có tên",
        "brand": repair_text(item.get("brand")),
        "category_id": category_id,
        "subcategory": repair_text(item.get("subcategory")),
        "image1": image_url,
        "image_url": image_url,
        "price": price,
        "original_price": original_price if original_price > 0 else price,
        "currency": repair_text(item.get("currency")) or "VND",
        "volume": repair_text(item.get("volume")),
        "quantity": quantity,
        "stock_status": stock_status,
        "description": repair_text(item.get("description")),
        "usage": repair_text(item.get("usage")),
        "skin_type": repair_list(item.get("skin_type")),
        "concerns": repair_list(item.get("concerns")),
        "ingredients": repair_list(item.get("ingredients")),
        "benefits": repair_list(item.get("benefits")),
        "product_url": repair_text(item.get("product_url")),
        "source": repair_text(item.get("source")) or "lixibox",
        "last_updated": parse_date(item.get("last_updated")),
        "is_active": quantity > 0,
    }


async def import_products(json_path: Path, deactivate_missing: bool):
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    items = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("Expected the JSON file to contain a list of products.")

    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS external_id VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS slug VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS brand VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS subcategory VARCHAR(100)"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS original_price DOUBLE PRECISION"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS currency VARCHAR(10) NOT NULL DEFAULT 'VND'"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS volume VARCHAR(100)"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS stock_status VARCHAR(50) NOT NULL DEFAULT 'unknown'"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS usage TEXT"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS skin_type JSONB NOT NULL DEFAULT '[]'::jsonb"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS concerns JSONB NOT NULL DEFAULT '[]'::jsonb"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS ingredients JSONB NOT NULL DEFAULT '[]'::jsonb"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS benefits JSONB NOT NULL DEFAULT '[]'::jsonb"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS product_url VARCHAR(500)"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS source VARCHAR(50)"))
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS last_updated DATE"))
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ix_products_external_id
                ON products(external_id)
                WHERE external_id IS NOT NULL
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ix_products_slug
                ON products(slug)
                WHERE slug IS NOT NULL
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE products
                SET image_url = COALESCE(image_url, image1),
                    original_price = COALESCE(original_price, price)
                """
            )
        )

    async with async_session() as session:
        category_rows = (await session.execute(select(Category))).scalars().all()
        categories = {category.name.casefold(): category for category in category_rows}

        product_rows = (await session.execute(select(Product))).scalars().all()
        products_by_external_id = {
            product.external_id: product
            for product in product_rows
            if product.external_id
        }
        products_by_slug = {
            product.slug: product
            for product in product_rows
            if product.slug
        }

        imported_external_ids = set()
        created_count = 0
        updated_count = 0

        for item in items:
            category_name = normalize_category_name(item.get("category"))
            category = categories.get(category_name.casefold())
            if category is None:
                category = Category(name=category_name)
                session.add(category)
                await session.flush()
                categories[category_name.casefold()] = category

            payload = build_product_payload(item, category.id)
            external_id = payload["external_id"]
            slug = payload["slug"]

            product = None
            if external_id:
                product = products_by_external_id.get(external_id)
            if product is None and slug:
                product = products_by_slug.get(slug)

            if product is None:
                product = Product(**payload)
                session.add(product)
                created_count += 1
            else:
                for field, value in payload.items():
                    setattr(product, field, value)
                updated_count += 1

            if external_id:
                imported_external_ids.add(external_id)
                products_by_external_id[external_id] = product
            if slug:
                products_by_slug[slug] = product

        deactivated_count = 0
        if deactivate_missing:
            for product in product_rows:
                if product.source == "lixibox" and product.external_id and product.external_id not in imported_external_ids:
                    product.is_active = False
                    deactivated_count += 1

        await session.commit()

    return {
        "total_items": len(items),
        "created": created_count,
        "updated": updated_count,
        "deactivated": deactivated_count,
    }


def main():
    parser = argparse.ArgumentParser(description="Import Lixibox products into PostgreSQL.")
    parser.add_argument("--json-path", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument(
        "--deactivate-missing",
        action="store_true",
        help="Mark previously imported Lixibox products as inactive if they are missing from the current JSON file.",
    )
    args = parser.parse_args()

    summary = asyncio.run(import_products(args.json_path, args.deactivate_missing))
    print(
        "Imported {total_items} items | created: {created} | updated: {updated} | deactivated: {deactivated}".format(
            **summary
        )
    )


if __name__ == "__main__":
    main()
