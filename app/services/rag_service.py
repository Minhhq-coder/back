from __future__ import annotations

import asyncio
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product
from app.services.embedding_service import create_embedding

PRODUCT_EMBEDDINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS product_embeddings (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_product_embeddings_product_id UNIQUE (product_id)
)
"""

PRODUCT_EMBEDDINGS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS ix_product_embeddings_embedding_cosine
ON product_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100)
"""


async def ensure_product_embeddings_table(executor: Any, strict: bool = False) -> bool:
    available_result = await executor.execute(
        text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    )
    if available_result.scalar_one_or_none() is None:
        message = (
            "pgvector extension is not installed on this PostgreSQL server. "
            "Install pgvector or use a PostgreSQL/Neon database that supports it."
        )
        if strict:
            raise RuntimeError(message)
        return False

    await executor.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await executor.execute(text(PRODUCT_EMBEDDINGS_TABLE_SQL))
    await executor.execute(text(PRODUCT_EMBEDDINGS_INDEX_SQL))
    return True


def _format_list(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _format_price(value: float | None, currency: str | None) -> str:
    if value is None:
        return ""
    formatted = f"{value:,.0f}".replace(",", ".")
    return f"{formatted} {currency or 'VND'}".strip()


def _stock_text(product: Product) -> str:
    if product.quantity <= 0:
        return "Hết hàng"
    status = (product.stock_status or "").strip()
    if status:
        return f"{status}, còn {product.quantity} sản phẩm"
    return f"Còn {product.quantity} sản phẩm"


def build_product_embedding_content(product: Product) -> str:
    category_name = getattr(getattr(product, "category", None), "name", None)
    lines = [
        f"Tên sản phẩm: {product.name}",
        f"Thương hiệu: {product.brand}" if product.brand else "",
        f"Danh mục: {category_name}" if category_name else "",
        f"Danh mục con: {product.subcategory}" if product.subcategory else "",
        f"Giá: {_format_price(product.price, product.currency)}",
        f"Tình trạng kho: {_stock_text(product)}",
        f"Dung tích: {product.volume}" if product.volume else "",
        f"Mô tả: {product.description}" if product.description else "",
        f"Công dụng: {_format_list(product.benefits)}" if product.benefits else "",
        f"Thành phần: {_format_list(product.ingredients)}" if product.ingredients else "",
        f"Loại da phù hợp: {_format_list(product.skin_type)}" if product.skin_type else "",
        f"Vấn đề da: {_format_list(product.concerns)}" if product.concerns else "",
        f"Cách dùng: {product.usage}" if product.usage else "",
        f"Nguồn sản phẩm: {product.product_url}" if product.product_url else "",
    ]
    return "\n".join(line for line in lines if line).strip()


def serialize_embedding(embedding: list[float]) -> str:
    return json.dumps([float(value) for value in embedding], separators=(",", ":"))


async def upsert_product_embedding(
    db: AsyncSession,
    product: Product,
    embedding: list[float],
    content: str | None = None,
) -> None:
    product_content = content or build_product_embedding_content(product)
    await db.execute(
        text(
            """
            INSERT INTO product_embeddings (product_id, title, content, embedding, created_at)
            VALUES (:product_id, :title, :content, CAST(:embedding AS vector), NOW())
            ON CONFLICT (product_id) DO UPDATE
            SET title = EXCLUDED.title,
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                created_at = NOW()
            """
        ),
        {
            "product_id": product.id,
            "title": product.name,
            "content": product_content,
            "embedding": serialize_embedding(embedding),
        },
    )


async def search_relevant_products(
    db: AsyncSession,
    question: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    cleaned_question = " ".join(str(question or "").split())
    if not cleaned_question:
        return []

    safe_limit = max(1, min(int(limit or 5), 20))
    try:
        readiness_result = await db.execute(
            text(
                """
                SELECT
                    EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')
                    AND to_regclass('public.product_embeddings') IS NOT NULL
                """
            )
        )
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "RAG search is not ready. Ensure pgvector is installed and run `python index_products.py`."
        ) from exc

    if not readiness_result.scalar_one():
        raise RuntimeError(
            "RAG search is not ready. Ensure pgvector is installed and run `python index_products.py`."
        )

    embedding = await asyncio.to_thread(create_embedding, cleaned_question)
    embedding_value = serialize_embedding(embedding)

    try:
        result = await db.execute(
            text(
                """
                SELECT
                    pe.id,
                    pe.product_id,
                    pe.title,
                    pe.content,
                    pe.created_at,
                    (pe.embedding <=> CAST(:embedding AS vector)) AS distance,
                    1 - (pe.embedding <=> CAST(:embedding AS vector)) AS score
                FROM product_embeddings pe
                JOIN products p ON p.id = pe.product_id
                WHERE p.is_active = TRUE
                  AND COALESCE(p.is_deleted, FALSE) = FALSE
                ORDER BY pe.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
                """
            ),
            {"embedding": embedding_value, "limit": safe_limit},
        )
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "RAG search is not ready. Ensure pgvector is installed and run `python index_products.py`."
        ) from exc

    return [
        {
            "id": row["id"],
            "product_id": row["product_id"],
            "title": row["title"],
            "content": row["content"],
            "created_at": row["created_at"],
            "distance": float(row["distance"]) if row["distance"] is not None else None,
            "score": float(row["score"]) if row["score"] is not None else None,
        }
        for row in result.mappings().all()
    ]
