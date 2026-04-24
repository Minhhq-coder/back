import re
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, computed_field


_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ỵ0-9])")
_NUMBERED_ITEM_PATTERN = re.compile(r"(?<=[\.:;])\s+(?=(?:\d+\.\s))")
_BULLET_PREFIX_PATTERN = re.compile(r"^[\-\u2022\u2023\u25E6\u2043\u2219*]+\s*")
_MULTISPACE_PATTERN = re.compile(r"[ \t]{2,}")
_MULTINEWLINE_PATTERN = re.compile(r"\n{3,}")
_NUMBER_ONLY_PATTERN = re.compile(r"^\d+\.$")


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""

    text = value.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    text = _MULTISPACE_PATTERN.sub(" ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = _MULTINEWLINE_PATTERN.sub("\n\n", text)
    return text.strip()


def _strip_section_prefixes(text: str, prefixes: tuple[str, ...]) -> str:
    cleaned = text
    for prefix in prefixes:
        cleaned, count = re.subn(
            rf"^\s*{re.escape(prefix)}\s*[:\-]?\s*",
            "",
            cleaned,
            count=1,
            flags=re.IGNORECASE,
        )
        if count:
            break
    return cleaned.strip()


def _append_unique(items: list[str], value: str) -> None:
    normalized = value.casefold()
    if any(existing.casefold() == normalized for existing in items):
        return
    items.append(value)


def _split_text_lines(value: Optional[str], prefixes: tuple[str, ...] = ()) -> list[str]:
    text = _normalize_text(value)
    if not text:
        return []

    text = _strip_section_prefixes(text, prefixes)
    text = _NUMBERED_ITEM_PATTERN.sub("\n", text)
    text = re.sub(r"\s*[•●▪◦]\s*", "\n", text)

    raw_parts: list[str] = []
    for block in text.split("\n"):
        line = block.strip()
        if not line:
            continue

        sentence_parts = _SENTENCE_SPLIT_PATTERN.split(line) if len(line) > 180 else [line]
        raw_parts.extend(sentence_parts)

    lines: list[str] = []
    for part in raw_parts:
        line = _BULLET_PREFIX_PATTERN.sub("", part).strip(" -")
        line = _normalize_text(line)
        if line:
            _append_unique(lines, line)

    merged_lines: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if _NUMBER_ONLY_PATTERN.fullmatch(line) and index + 1 < len(lines):
            _append_unique(merged_lines, f"{line} {lines[index + 1]}")
            index += 2
            continue

        _append_unique(merged_lines, line)
        index += 1

    return merged_lines


def _split_list_lines(values: Optional[list[str]]) -> list[str]:
    lines: list[str] = []
    for value in values or []:
        for line in _split_text_lines(value):
            _append_unique(lines, line)
    return lines


def _stock_status_label(stock_status: str, quantity: int) -> str | None:
    mapping = {
        "in_stock": "Còn hàng",
        "low_stock": "Sắp hết hàng",
        "limited": "Số lượng có hạn",
        "out_of_stock": "Hết hàng",
        "sold_out": "Hết hàng",
    }

    if quantity <= 0:
        return "Hết hàng"

    return mapping.get((stock_status or "").strip().lower(), "Còn hàng")


def _format_volume(value: Optional[str]) -> Optional[str]:
    text = _normalize_text(value)
    if not text:
        return None
    return re.sub(r"\b(\d+)\.0\b", r"\1", text)


# ── Category ──────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


# ── Product ───────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    external_id: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    name: str = Field(..., min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=255)
    category_id: int
    subcategory: Optional[str] = Field(None, max_length=100)
    image1: Optional[str] = None
    image2: Optional[str] = None
    image3: Optional[str] = None
    image_url: Optional[str] = None
    price: float = Field(..., gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    currency: str = Field(default="VND", max_length=10)
    volume: Optional[str] = Field(None, max_length=100)
    quantity: int = Field(..., ge=0)
    stock_status: str = Field(default="unknown", max_length=50)
    description: Optional[str] = None
    usage: Optional[str] = None
    skin_type: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    product_url: Optional[str] = None
    source: Optional[str] = Field(None, max_length=50)
    last_updated: Optional[date] = None
    is_active: bool = True


class ProductUpdate(BaseModel):
    external_id: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=255)
    category_id: Optional[int] = None
    subcategory: Optional[str] = Field(None, max_length=100)
    image1: Optional[str] = None
    image2: Optional[str] = None
    image3: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = Field(None, max_length=10)
    volume: Optional[str] = Field(None, max_length=100)
    quantity: Optional[int] = Field(None, ge=0)
    stock_status: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    usage: Optional[str] = None
    skin_type: Optional[list[str]] = None
    concerns: Optional[list[str]] = None
    ingredients: Optional[list[str]] = None
    benefits: Optional[list[str]] = None
    product_url: Optional[str] = None
    source: Optional[str] = Field(None, max_length=50)
    last_updated: Optional[date] = None
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    external_id: Optional[str] = None
    slug: Optional[str] = None
    name: str
    brand: Optional[str] = None
    category_id: int
    subcategory: Optional[str] = None
    image1: Optional[str] = None
    image2: Optional[str] = None
    image3: Optional[str] = None
    image_url: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    currency: str
    volume: Optional[str] = None
    quantity: int
    stock_status: str
    description: Optional[str] = None
    usage: Optional[str] = None
    skin_type: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    product_url: Optional[str] = None
    source: Optional[str] = None
    last_updated: Optional[date] = None
    view_count: int
    purchased_count: int
    is_active: bool

    model_config = {"from_attributes": True}


class ProductDetailSectionOut(BaseModel):
    title: str
    lines: list[str] = Field(default_factory=list)


class ProductDetailOut(ProductOut):
    @computed_field(return_type=list[ProductDetailSectionOut])
    @property
    def detail_sections(self) -> list[ProductDetailSectionOut]:
        sections: list[ProductDetailSectionOut] = []

        quick_info_lines: list[str] = []
        if self.brand:
            quick_info_lines.append(f"Thương hiệu: {self.brand}")
        formatted_volume = _format_volume(self.volume)
        if formatted_volume:
            quick_info_lines.append(f"Dung tích: {formatted_volume}")

        stock_label = _stock_status_label(self.stock_status, self.quantity)
        if stock_label:
            quick_info_lines.append(f"Tình trạng: {stock_label}")

        if quick_info_lines:
            sections.append(
                ProductDetailSectionOut(
                    title="Thông tin nhanh",
                    lines=quick_info_lines,
                )
            )

        description_lines = _split_text_lines(
            self.description,
            prefixes=("Mô tả sản phẩm", "Thông tin sản phẩm", "Thông tin"),
        )
        if description_lines:
            sections.append(
                ProductDetailSectionOut(
                    title="Mô tả sản phẩm",
                    lines=description_lines,
                )
            )

        usage_lines = _split_text_lines(
            self.usage,
            prefixes=("Cách sử dụng", "Sử dụng", "Hướng dẫn sử dụng"),
        )
        if usage_lines:
            sections.append(
                ProductDetailSectionOut(
                    title="Cách sử dụng",
                    lines=usage_lines,
                )
            )

        ingredient_lines = _split_list_lines(self.ingredients)
        if ingredient_lines:
            sections.append(
                ProductDetailSectionOut(
                    title="Thành phần",
                    lines=ingredient_lines,
                )
            )

        benefit_lines = _split_list_lines(self.benefits)
        if benefit_lines:
            sections.append(
                ProductDetailSectionOut(
                    title="Công dụng nổi bật",
                    lines=benefit_lines,
                )
            )

        skin_type_lines = _split_list_lines(self.skin_type)
        if skin_type_lines:
            sections.append(
                ProductDetailSectionOut(
                    title="Loại da phù hợp",
                    lines=skin_type_lines,
                )
            )

        concern_lines = _split_list_lines(self.concerns)
        if concern_lines:
            sections.append(
                ProductDetailSectionOut(
                    title="Vấn đề quan tâm",
                    lines=concern_lines,
                )
            )

        return sections


class ProductBrief(BaseModel):
    id: int
    external_id: Optional[str] = None
    slug: Optional[str] = None
    name: str
    brand: Optional[str] = None
    image1: Optional[str] = None
    image_url: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    currency: str = "VND"
    volume: Optional[str] = None
    quantity: int
    purchased_count: int
    stock_status: str = "unknown"

    model_config = {"from_attributes": True}
