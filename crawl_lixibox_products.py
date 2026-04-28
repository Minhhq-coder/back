import argparse
import html
import json
import re
import time
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests


SEARCH_URL = "https://api.lixibox.com/web/search/optimizations/"
DETAIL_URL_TEMPLATE = "https://api.lixibox.com/web/boxes/{slug}"
PRODUCT_URL_TEMPLATE = "https://www.lixibox.com/shop/{slug}"
DEFAULT_OUTPUT_PATH = Path(r"C:\Users\minhhq\Desktop\crawl data\clean_lixibox_products.json")

CATEGORY_SKINCARE = "Ch\u0103m s\u00f3c da"
CATEGORY_MAKEUP = "Trang \u0111i\u1ec3m"
CATEGORY_PERSONAL_CARE = "Ch\u0103m s\u00f3c c\u00e1 nh\u00e2n"
CATEGORY_OTHER = "Kh\u00e1c"

DEFAULT_KEYWORDS = (
    "skincare",
    "makeup",
    "hair",
    "body",
    "cleanser",
    "serum",
    "toner",
    "cream",
    "sunscreen",
    "mask",
    "lipstick",
    "perfume",
    "cham soc da",
    "trang diem",
    "cham soc ca nhan",
    "sua rua mat",
    "kem duong",
    "son moi",
    "nuoc hoa",
)


JsonDict = dict[str, Any]


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dict, list, tuple, set)):
        return None

    text = html.unescape(str(value))
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


def clean_name(value: Any) -> str | None:
    text = clean_text(value)
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip() or None


def strip_accents(value: str | None) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return ascii_text.casefold()


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        text = clean_name(value)
        if not text:
            continue
        key = strip_accents(text)
        if key in seen:
            continue
        seen.add(key)
        items.append(text)
    return items


def parse_list_text(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            if isinstance(item, dict):
                items.extend(
                    parse_list_text(
                        item.get("name")
                        or item.get("title")
                        or item.get("value")
                        or item.get("label")
                    )
                )
            else:
                items.extend(parse_list_text(item))
        return unique_strings(items)

    text = clean_text(value)
    if not text:
        return []

    text = re.sub(r"\s*[\u2022\u25cf\u25aa\u25e6]\s*", "\n", text)
    text = text.replace(";", "\n")

    items = []
    for line in text.splitlines():
        item = line.strip(" -\t")
        if item:
            items.append(item)

    return unique_strings(items or [text])


def to_float(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        number = float(value)
        return number if number > 0 else None

    text = clean_name(value)
    if not text:
        return None

    text = re.sub(r"[^\d,.\-]", "", text)
    if not text or text in {"-", ".", ","}:
        return None

    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        number = float(text)
        return number if number > 0 else None

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            normalized = text.replace(".", "").replace(",", ".")
        else:
            normalized = text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        if len(parts) == 2 and len(parts[-1]) in {1, 2}:
            normalized = ".".join(parts)
        else:
            normalized = "".join(parts)
    elif "." in text:
        parts = text.split(".")
        if len(parts) > 2 or len(parts[-1]) == 3:
            normalized = "".join(parts)
        else:
            normalized = text
    else:
        normalized = text

    try:
        number = float(normalized)
    except ValueError:
        return None

    return number if number > 0 else None


def first_clean(*values: Any) -> str | None:
    for value in values:
        text = clean_name(value)
        if text:
            return text
    return None


def first_float(*values: Any) -> float | None:
    for value in values:
        number = to_float(value)
        if number is not None:
            return number
    return None


def as_dict(value: Any) -> JsonDict:
    return value if isinstance(value, dict) else {}


def nested_product(box: JsonDict) -> JsonDict:
    direct_product = as_dict(box.get("product"))
    if direct_product:
        return direct_product

    box_products = box.get("box_products") or []
    if isinstance(box_products, list):
        for item in box_products:
            product = as_dict(as_dict(item).get("product"))
            if product:
                return product

    products = box.get("products") or []
    if isinstance(products, list):
        for item in products:
            product = as_dict(item)
            if product:
                return product

    return {}


def nested_brand_name(value: Any) -> str | None:
    if isinstance(value, dict):
        return first_clean(
            value.get("name"),
            value.get("display_name"),
            value.get("title"),
            value.get("slug"),
        )
    return clean_name(value)


def extract_brand(box: JsonDict, product: JsonDict) -> str | None:
    return first_clean(
        nested_brand_name(product.get("brand")),
        nested_brand_name(box.get("brand")),
        product.get("brand_name"),
        box.get("brand_name"),
        box.get("vendor_name"),
    )


def collect_picture_urls(container: JsonDict) -> list[str]:
    urls: list[str] = []

    for key in (
        "primary_picture_url",
        "picture_url",
        "image_url",
        "image",
        "thumbnail_url",
        "thumbnail",
        "photo_url",
    ):
        text = clean_name(container.get(key))
        if text and text.startswith("http"):
            urls.append(text)

    for key in (
        "primary_picture",
        "primary_picture_webp",
        "picture",
        "picture_webp",
        "photo",
    ):
        picture = as_dict(container.get(key))
        for url_key in (
            "large_url",
            "medium_url",
            "original_url",
            "thumb_url",
            "facebook_url",
            "url",
        ):
            text = clean_name(picture.get(url_key))
            if text and text.startswith("http"):
                urls.append(text)

    for key in (
        "pictures_webp",
        "pictures",
        "images",
        "photos",
        "gallery",
    ):
        pictures = container.get(key) or []
        if not isinstance(pictures, list):
            continue
        for picture in pictures:
            if isinstance(picture, str):
                text = clean_name(picture)
                if text and text.startswith("http"):
                    urls.append(text)
                continue

            picture_dict = as_dict(picture)
            for url_key in (
                "large_url",
                "medium_url",
                "original_url",
                "thumb_url",
                "facebook_url",
                "url",
            ):
                text = clean_name(picture_dict.get(url_key))
                if text and text.startswith("http"):
                    urls.append(text)

    return unique_strings(urls)


def pick_images(box: JsonDict, product: JsonDict) -> list[str]:
    return unique_strings(collect_picture_urls(box) + collect_picture_urls(product))[:3]


def normalize_external_id(box: JsonDict, product: JsonDict, slug: str | None) -> str | None:
    raw_id = first_clean(
        box.get("id"),
        box.get("box_id"),
        box.get("product_id"),
        product.get("id"),
        product.get("product_id"),
        box.get("external_id"),
        product.get("external_id"),
    )

    if raw_id:
        return raw_id if raw_id.startswith("lixibox-") else f"lixibox-{raw_id}"

    if slug:
        return f"lixibox-{slug}"

    return None


def normalize_stock_status(box: JsonDict, product: JsonDict) -> str:
    bool_candidates = (
        box.get("is_saleable"),
        box.get("saleable"),
        box.get("available"),
        product.get("is_saleable"),
        product.get("available"),
    )
    for value in bool_candidates:
        if isinstance(value, bool):
            return "in_stock" if value else "out_of_stock"

    raw = first_clean(
        box.get("stock_status"),
        product.get("stock_status"),
        box.get("availability"),
        product.get("availability"),
        box.get("status"),
        product.get("status"),
    )
    stock = strip_accents(raw)

    if not stock:
        return "unknown"
    if any(token in stock for token in ("out_of_stock", "sold_out", "unavailable", "het hang")):
        return "out_of_stock"
    if any(token in stock for token in ("low_stock", "limited", "sap het")):
        return "low_stock"
    if any(token in stock for token in ("in_stock", "available", "saleable", "con hang")):
        return "in_stock"
    return stock[:50]


def derive_quantity(stock_status: str) -> int:
    stock = stock_status.strip().lower()
    if stock in {"out_of_stock", "sold_out", "unavailable"}:
        return 0
    if stock in {"low_stock", "limited"}:
        return 5
    return 100


def collect_category_values(box: JsonDict, product: JsonDict) -> list[str]:
    values: list[str] = []

    for container in (box, product):
        for key in (
            "category",
            "category_name",
            "main_category",
            "main_category_name",
            "subcategory",
            "sub_category",
            "sub_category_name",
            "box_type",
        ):
            value = container.get(key)
            if isinstance(value, dict):
                text = first_clean(value.get("name"), value.get("title"), value.get("slug"))
            else:
                text = clean_name(value)
            if text:
                values.append(text)

        for key in ("categories", "category_names", "tags"):
            value = container.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        text = first_clean(item.get("name"), item.get("title"), item.get("slug"))
                    else:
                        text = clean_name(item)
                    if text:
                        values.append(text)

    return unique_strings(values)


def normalize_category(box: JsonDict, product: JsonDict, name: str | None) -> tuple[str, str | None]:
    category_values = collect_category_values(box, product)
    haystack = strip_accents(" ".join(category_values + [name or ""]))

    skincare_tokens = (
        "skincare",
        "skin care",
        "cham soc da",
        "sua rua mat",
        "tay trang",
        "cleanser",
        "toner",
        "serum",
        "cream",
        "sunscreen",
        "sun screen",
        "mask",
        "duong da",
        "exfol",
        "treatment",
        "facial",
    )
    makeup_tokens = (
        "makeup",
        "make up",
        "trang diem",
        "lipstick",
        "son",
        "foundation",
        "cushion",
        "mascara",
        "eyeliner",
        "eyebrow",
        "blush",
        "powder",
        "phan",
        "kem nen",
    )
    personal_tokens = (
        "hair",
        "toc",
        "duong toc",
        "dau goi",
        "body",
        "co the",
        "sua tam",
        "perfume",
        "fragrance",
        "nuoc hoa",
        "personal care",
        "cham soc ca nhan",
        "shampoo",
        "conditioner",
        "shower",
        "deodorant",
        "oral",
        "toothpaste",
        "scalp",
    )

    if any(token in haystack for token in personal_tokens):
        category = CATEGORY_PERSONAL_CARE
    elif any(token in haystack for token in makeup_tokens):
        category = CATEGORY_MAKEUP
    elif any(token in haystack for token in skincare_tokens):
        category = CATEGORY_SKINCARE
    else:
        category = CATEGORY_OTHER

    subcategory = category_values[0] if category_values else None
    return category, subcategory


def parse_detail_payload(payload: JsonDict) -> JsonDict:
    data = as_dict(payload.get("data"))
    return as_dict(payload.get("box")) or as_dict(data.get("box")) or payload


def extract_boxes(payload: Any) -> list[JsonDict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    data = as_dict(payload.get("data"))
    candidates = (
        payload.get("boxes"),
        payload.get("items"),
        payload.get("results"),
        payload.get("products"),
        data.get("boxes"),
        data.get("items"),
        data.get("results"),
        data.get("products"),
    )
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]

    box = payload.get("box") or data.get("box")
    if isinstance(box, dict):
        return [box]

    return []


def response_total_pages(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None

    containers = [
        payload,
        as_dict(payload.get("data")),
        as_dict(payload.get("meta")),
        as_dict(payload.get("pagination")),
    ]
    for container in containers:
        for key in ("total_pages", "last_page", "pages", "total_page"):
            value = container.get(key)
            if isinstance(value, int) and value > 0:
                return value
            number = to_float(value)
            if number:
                return int(number)

    return None


def map_box_to_product(box: JsonDict) -> JsonDict | None:
    product = nested_product(box)
    slug = first_clean(box.get("slug"), product.get("slug"))
    name = first_clean(
        box.get("name"),
        box.get("display_name"),
        product.get("display_name"),
        product.get("name"),
        product.get("english_name"),
    )
    price = first_float(
        box.get("price"),
        box.get("current_price"),
        box.get("sale_price"),
        box.get("selling_price"),
        box.get("final_price"),
        product.get("price"),
        product.get("current_price"),
        product.get("sale_price"),
    )
    if not name or price is None:
        return None

    original_price = first_float(
        box.get("original_price"),
        box.get("listed_price"),
        box.get("market_price"),
        box.get("retail_price"),
        product.get("original_price"),
        product.get("listed_price"),
        product.get("market_price"),
        price,
    )
    if original_price is None or original_price < price:
        original_price = price

    brand = extract_brand(box, product)
    stock_status = normalize_stock_status(box, product)
    quantity = derive_quantity(stock_status)
    category, subcategory = normalize_category(box, product, name)
    images = pick_images(box, product)
    image_url = images[0] if images else None
    external_id = normalize_external_id(box, product, slug)

    box_products = box.get("box_products") or []
    first_box_product = as_dict(box_products[0]) if isinstance(box_products, list) and box_products else {}
    description = (
        clean_text(product.get("description"))
        or clean_text(box.get("long_description"))
        or clean_text(box.get("short_description"))
        or clean_text(first_box_product.get("expert_description"))
    )

    usage = clean_text(
        product.get("usage")
        or product.get("how_to_use")
        or box.get("usage")
        or box.get("how_to_use")
    )

    ingredients = parse_list_text(product.get("ingredients") or box.get("ingredients"))
    benefits = parse_list_text(
        product.get("benefits")
        or product.get("product_benefits")
        or box.get("benefits")
    )
    skin_type = parse_list_text(
        product.get("skin_type")
        or product.get("skin_types")
        or box.get("skin_type")
        or box.get("skin_types")
    )
    concerns = parse_list_text(
        product.get("concerns")
        or product.get("skin_concerns")
        or box.get("concerns")
        or box.get("skin_concerns")
    )

    product_url = first_clean(
        box.get("product_url"),
        box.get("url"),
        product.get("product_url"),
        product.get("url"),
    )
    if not product_url and slug:
        product_url = PRODUCT_URL_TEMPLATE.format(slug=slug)

    payload: JsonDict = {
        "id": external_id,
        "external_id": external_id,
        "slug": slug,
        "name": name,
        "brand": brand,
        "category": category,
        "subcategory": subcategory,
        "image_url": image_url,
        "image1": images[0] if len(images) > 0 else None,
        "image2": images[1] if len(images) > 1 else None,
        "image3": images[2] if len(images) > 2 else None,
        "price": price,
        "original_price": original_price,
        "currency": "VND",
        "volume": first_clean(product.get("capacity"), product.get("volume"), box.get("capacity"), box.get("volume")),
        "quantity": quantity,
        "stock_status": stock_status,
        "description": description,
        "usage": usage,
        "skin_type": skin_type,
        "concerns": concerns,
        "ingredients": ingredients,
        "benefits": benefits,
        "product_url": product_url,
        "source": "lixibox",
        "last_updated": date.today().isoformat(),
        "is_active": quantity > 0,
    }

    return payload


def merge_product(base: JsonDict, detail: JsonDict) -> JsonDict:
    merged = dict(base)

    for key, value in detail.items():
        if key in {"id", "external_id", "slug", "source", "last_updated"}:
            continue
        if isinstance(value, list):
            if value:
                merged[key] = value
        elif value is not None and value != "":
            merged[key] = value

    for key in ("id", "external_id", "slug"):
        if not merged.get(key):
            merged[key] = detail.get(key)

    if merged.get("original_price") is None or merged["original_price"] < merged["price"]:
        merged["original_price"] = merged["price"]

    stock_status = clean_name(merged.get("stock_status")) or "unknown"
    merged["stock_status"] = stock_status
    merged["quantity"] = derive_quantity(stock_status)
    merged["is_active"] = merged["quantity"] > 0
    merged["source"] = "lixibox"
    merged["last_updated"] = date.today().isoformat()
    return merged


def fetch_json(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float,
    retries: int,
    delay: float,
) -> JsonDict:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object response")
            return payload
        except Exception as error:  # noqa: BLE001
            last_error = error
            if attempt == retries:
                break
            time.sleep(delay * attempt)

    raise RuntimeError(f"Request failed after {retries} attempts: {last_error}")


def fetch_detail(
    session: requests.Session,
    slug: str,
    *,
    timeout: float,
    retries: int,
    delay: float,
) -> JsonDict | None:
    url = DETAIL_URL_TEMPLATE.format(slug=quote(slug, safe=""))
    payload = fetch_json(session, url, timeout=timeout, retries=retries, delay=delay)
    if payload.get("success") is False:
        return None

    detail_box = parse_detail_payload(payload)
    return map_box_to_product(detail_box)


def dedupe_key(product: JsonDict) -> str:
    return clean_name(product.get("external_id")) or clean_name(product.get("slug")) or clean_name(product.get("name")) or ""


def crawl_products(
    *,
    keywords: list[str],
    per_page: int,
    max_pages: int | None,
    delay: float,
    include_detail: bool,
    timeout: float,
    retries: int,
    limit: int | None,
) -> tuple[list[JsonDict], list[JsonDict]]:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; LixiboxProductCrawler/1.0)",
            "Accept": "application/json",
        }
    )

    products_by_key: dict[str, JsonDict] = {}
    errors: list[JsonDict] = []

    for keyword in keywords:
        page = 1
        while True:
            if max_pages is not None and page > max_pages:
                break
            if limit is not None and len(products_by_key) >= limit:
                break

            params = {
                "keyword": keyword,
                "page": page,
                "per_page": per_page,
                "brands": "",
                "bids": "",
                "pl": "",
                "ph": "",
                "sort": "",
                "stock_status": "",
            }

            try:
                payload = fetch_json(
                    session,
                    SEARCH_URL,
                    params=params,
                    timeout=timeout,
                    retries=retries,
                    delay=delay,
                )
            except Exception as error:  # noqa: BLE001
                errors.append({"keyword": keyword, "page": page, "reason": str(error)})
                break

            boxes = extract_boxes(payload)
            if not boxes:
                break

            for box in boxes:
                product = map_box_to_product(box)
                if not product:
                    errors.append(
                        {
                            "keyword": keyword,
                            "page": page,
                            "slug": clean_name(box.get("slug")),
                            "reason": "missing required name or price",
                        }
                    )
                    continue

                if include_detail and product.get("slug"):
                    try:
                        detail = fetch_detail(
                            session,
                            product["slug"],
                            timeout=timeout,
                            retries=retries,
                            delay=delay,
                        )
                    except Exception as error:  # noqa: BLE001
                        detail = None
                        errors.append(
                            {
                                "keyword": keyword,
                                "page": page,
                                "slug": product.get("slug"),
                                "reason": f"detail failed: {error}",
                            }
                        )

                    if detail:
                        product = merge_product(product, detail)

                    time.sleep(delay)

                key = dedupe_key(product)
                if key:
                    products_by_key[key] = product

                if limit is not None and len(products_by_key) >= limit:
                    break

            print(
                "keyword={keyword} page={page} boxes={boxes} unique={unique}".format(
                    keyword=keyword or "<empty>",
                    page=page,
                    boxes=len(boxes),
                    unique=len(products_by_key),
                )
            )

            total_pages = response_total_pages(payload)
            if total_pages is not None and page >= total_pages:
                break
            if len(boxes) < per_page:
                break

            page += 1
            time.sleep(delay)

        if limit is not None and len(products_by_key) >= limit:
            break

    products = sorted(
        products_by_key.values(),
        key=lambda item: (clean_name(item.get("category")) or "", clean_name(item.get("name")) or ""),
    )
    return products, errors


def parse_keywords(value: str | None) -> list[str]:
    if value is None:
        return list(DEFAULT_KEYWORDS)

    return [item.strip() for item in value.split(",")]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl Lixibox products into a normalized JSON file.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Output JSON path.")
    parser.add_argument("--errors-output", type=Path, default=None, help="Optional JSON path for crawl errors.")
    parser.add_argument("--keywords", default=None, help="Comma-separated search keywords.")
    parser.add_argument("--per-page", type=int, default=20, help="Search result page size.")
    parser.add_argument("--max-pages", type=int, default=None, help="Maximum pages per keyword.")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between requests in seconds.")
    parser.add_argument("--timeout", type=float, default=30, help="HTTP timeout in seconds.")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retries per request.")
    parser.add_argument("--limit", type=int, default=None, help="Stop after N unique products.")
    parser.add_argument(
        "--no-detail",
        dest="detail",
        action="store_false",
        help="Skip detail endpoint calls and only use search data.",
    )
    parser.set_defaults(detail=True)
    args = parser.parse_args()

    if args.per_page <= 0:
        raise ValueError("--per-page must be greater than 0")
    if args.delay < 0:
        raise ValueError("--delay must be greater than or equal to 0")
    if args.retries <= 0:
        raise ValueError("--retries must be greater than 0")

    products, errors = crawl_products(
        keywords=parse_keywords(args.keywords),
        per_page=args.per_page,
        max_pages=args.max_pages,
        delay=args.delay,
        include_detail=args.detail,
        timeout=args.timeout,
        retries=args.retries,
        limit=args.limit,
    )

    write_json(args.output, products)
    if args.errors_output:
        write_json(args.errors_output, errors)

    print(
        "Wrote {count} products to {path}. Errors: {errors}".format(
            count=len(products),
            path=args.output,
            errors=len(errors),
        )
    )


if __name__ == "__main__":
    main()
