from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import async_session, engine
from app.models import Product
from app.services.embedding_service import create_embedding
from app.services.rag_service import (
    build_product_embedding_content,
    ensure_product_embeddings_table,
    upsert_product_embedding,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index products into product_embeddings using pgvector.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of products to index.")
    parser.add_argument("--product-id", type=int, default=None, help="Index one product by id.")
    return parser.parse_args()


async def load_products(limit: int | None = None, product_id: int | None = None) -> list[Product]:
    query = (
        select(Product)
        .options(selectinload(Product.category))
        .where(
            Product.is_active == True,  # noqa: E712
            Product.is_deleted == False,  # noqa: E712
        )
        .order_by(Product.id.asc())
    )

    if product_id is not None:
        query = query.where(Product.id == product_id)
    elif limit is not None:
        query = query.limit(max(1, limit))

    async with async_session() as session:
        result = await session.execute(query)
        return list(result.scalars().all())


async def index_products(limit: int | None = None, product_id: int | None = None) -> int:
    async with engine.begin() as conn:
        if conn.dialect.name != "postgresql":
            raise RuntimeError("RAG product indexing requires PostgreSQL with the pgvector extension.")
        await ensure_product_embeddings_table(conn, strict=True)

    products = await load_products(limit=limit, product_id=product_id)
    if not products:
        print("No products found to index.")
        return 0

    indexed_count = 0
    async with async_session() as session:
        for product in products:
            content = build_product_embedding_content(product)
            if not content:
                print(f"Skip product {product.id}: empty content")
                continue

            embedding = await asyncio.to_thread(create_embedding, content)
            await upsert_product_embedding(session, product, embedding, content=content)
            indexed_count += 1
            print(f"Indexed product {product.id}: {product.name}")

        await session.commit()

    return indexed_count


async def main() -> None:
    args = parse_args()
    indexed_count = await index_products(limit=args.limit, product_id=args.product_id)
    print(f"Done. Indexed {indexed_count} products.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
