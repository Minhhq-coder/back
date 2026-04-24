import argparse
import asyncio
import html
import re
from datetime import date
from typing import Any
from urllib.parse import urlparse

import requests
from sqlalchemy import select

from app.core.database import async_session
from app.models import Product


API_BASE_URL = "https://api.lixibox.com/web/boxes"
PLACEHOLDER_DESCRIPTIONS = {
    "",
    "thông tin hot",
    "thong tin hot",
    "mô tả sản phẩm",
    "mo ta san pham",
}


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None

    text = html.unescape(value)
    text = text.replace("\r", "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</\s*(p|div|h[1-6])\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<\s*li[^>]*>", "- ", text, flags=re.IGNORECASE)
    text = re.sub(r"</\s*li\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text or None


def clean_name(value: str | None) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip()


def parse_ingredients(value: str | None) -> list[str]:
    text = clean_text(value)
    if not text:
        return []

    text = re.sub(r"^thành phần(?: chính)?\s*:\s*", "", text, flags=re.IGNORECASE)
    items = []
    for chunk in text.splitlines():
        item = chunk.strip(" -\t")
        if item:
            items.append(item)

    if items:
        return items
    return [text]


def extract_slug(product: Product) -> str | None:
    if product.slug:
        return product.slug.strip()

    if product.external_id and product.external_id.startswith("lixibox-"):
        return product.external_id.removeprefix("lixibox-").strip() or None

    if product.product_url:
        parsed = urlparse(product.product_url)
        slug = parsed.path.rstrip("/").split("/")[-1].strip()
        if slug:
            return slug

    return None


def should_refresh_description(current_description: str | None) -> bool:
    text = clean_text(current_description)
    if not text:
        return True
    return text.casefold() in PLACEHOLDER_DESCRIPTIONS or len(text) < 80


def build_update_payload(data: dict[str, Any]) -> dict[str, Any]:
    box = data.get("box") or {}
    box_products = box.get("box_products") or []
    product_payload = {}

    if box_products:
        nested_product = box_products[0].get("product") or {}
        if isinstance(nested_product, dict):
            product_payload = nested_product

    brand = product_payload.get("brand") or {}
    if isinstance(brand, dict):
        brand_name = clean_name(brand.get("name"))
    else:
        brand_name = clean_name(box.get("brand_name"))

    description = (
        clean_text(product_payload.get("description"))
        or clean_text(box.get("long_description"))
        or clean_text(box.get("short_description"))
        or clean_text((box_products[0] if box_products else {}).get("expert_description"))
    )

    usage = clean_text(product_payload.get("usage"))
    ingredients = parse_ingredients(product_payload.get("ingredients"))

    return {
        "name": clean_name(box.get("name")) or clean_name(product_payload.get("display_name")) or clean_name(product_payload.get("name")),
        "brand": brand_name,
        "description": description,
        "usage": usage,
        "ingredients": ingredients,
        "volume": clean_name(product_payload.get("capacity")),
    }


async def refresh_product_details(limit: int | None, force_description: bool) -> dict[str, Any]:
    async with async_session() as session:
        result = await session.execute(
            select(Product)
            .where(Product.source == "lixibox", Product.is_deleted == False)  # noqa: E712
            .order_by(Product.id)
        )
        products = list(result.scalars().all())

        if limit is not None:
            products = products[:limit]

        updated = 0
        skipped = 0
        failed: list[dict[str, Any]] = []

        http = requests.Session()
        http.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; ProductDetailsSync/1.0)",
                "Accept": "application/json",
            }
        )

        for product in products:
            slug = extract_slug(product)
            if not slug:
                skipped += 1
                failed.append({"id": product.id, "name": product.name, "reason": "missing slug"})
                continue

            url = f"{API_BASE_URL}/{slug}"

            try:
                response = http.get(url, timeout=30)
                response.raise_for_status()
                payload = response.json()
            except Exception as error:  # noqa: BLE001
                skipped += 1
                failed.append({"id": product.id, "name": product.name, "reason": str(error)})
                continue

            if not payload.get("success"):
                skipped += 1
                failed.append({"id": product.id, "name": product.name, "reason": "api returned success=false"})
                continue

            update_payload = build_update_payload(payload)

            if update_payload["name"]:
                product.name = update_payload["name"]
            if update_payload["brand"]:
                product.brand = update_payload["brand"]
            if update_payload["volume"]:
                product.volume = update_payload["volume"]
            if update_payload["usage"]:
                product.usage = update_payload["usage"]
            if update_payload["ingredients"]:
                product.ingredients = update_payload["ingredients"]

            if force_description or should_refresh_description(product.description):
                if update_payload["description"]:
                    product.description = update_payload["description"]

            product.last_updated = date.today()
            updated += 1

        await session.commit()

    return {
        "processed": len(products),
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Lixibox product details from the public API.")
    parser.add_argument("--limit", type=int, default=None, help="Only refresh the first N matching products.")
    parser.add_argument(
        "--force-description",
        action="store_true",
        help="Replace existing descriptions even if they are not empty.",
    )
    args = parser.parse_args()

    summary = asyncio.run(refresh_product_details(limit=args.limit, force_description=args.force_description))
    print(
        "Processed {processed} products | updated: {updated} | skipped: {skipped}".format(
            **summary
        )
    )
    if summary["failed"]:
        print("Failures:")
        for item in summary["failed"]:
            print(f"- ID {item['id']}: {item['name']} -> {item['reason']}")


if __name__ == "__main__":
    main()
