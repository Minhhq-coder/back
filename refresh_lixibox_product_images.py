import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_JSON_PATH = Path(r"C:\Users\minhhq\Desktop\crawl data\clean_lixibox_products.json")
SEARCH_URL_TEMPLATE = (
    "https://api.lixibox.com/web/search/optimizations/"
    "?keyword={keyword}&page=1&per_page=5&brands=&bids=&pl=&ph=&sort=&stock_status="
)


def fetch_json(url: str) -> dict:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )
    data = urlopen(req, timeout=30).read().decode("utf-8", errors="ignore")
    return json.loads(data)


def pick_image(box: dict) -> str | None:
    primary_picture_url = box.get("primary_picture_url")
    if primary_picture_url:
        return primary_picture_url

    primary_picture = box.get("primary_picture") or {}
    for key in ("large_url", "medium_url", "original_url", "thumb_url", "facebook_url"):
        if primary_picture.get(key):
            return primary_picture[key]

    primary_picture_webp = box.get("primary_picture_webp") or {}
    for key in ("large_url", "medium_url", "original_url", "thumb_url", "facebook_url"):
        if primary_picture_webp.get(key):
            return primary_picture_webp[key]

    for picture in box.get("pictures_webp") or []:
        for key in ("large_url", "medium_url", "original_url", "thumb_url", "url"):
            if picture.get(key):
                return picture[key]

    return None


def find_best_box(item: dict, boxes: list[dict]) -> dict | None:
    target_slug = item.get("slug")
    if not target_slug:
        return None

    for box in boxes:
        if box.get("slug") == target_slug:
            return box

    return boxes[0] if boxes else None


def update_images(json_path: Path) -> dict:
    items = json.loads(json_path.read_text(encoding="utf-8"))
    updated = 0
    missing = []

    for item in items:
        slug = item.get("slug")
        if not slug:
            missing.append({"slug": None, "reason": "missing slug"})
            continue

        keyword = quote(slug.replace("-", " "))
        url = SEARCH_URL_TEMPLATE.format(keyword=keyword)

        try:
            response = fetch_json(url)
        except Exception as error:
            missing.append({"slug": slug, "reason": f"request failed: {error}"})
            continue

        box = find_best_box(item, response.get("boxes") or [])
        if not box:
            missing.append({"slug": slug, "reason": "no search result"})
            continue

        image_url = pick_image(box)
        if not image_url:
            missing.append({"slug": slug, "reason": "no image field in matched box"})
            continue

        item["image_url"] = image_url
        updated += 1

    json_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "total": len(items),
        "updated": updated,
        "missing": missing,
    }


def main():
    parser = argparse.ArgumentParser(description="Refresh image_url fields in Lixibox JSON by querying Lixibox search API.")
    parser.add_argument("--json-path", type=Path, default=DEFAULT_JSON_PATH)
    args = parser.parse_args()

    summary = update_images(args.json_path)
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
