from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.dependencies.auth import get_optional_current_user, require_permission
from app.models import Category, Order, OrderDetail, OrderStatus, Product, ProductReview, User
from app.schemas import (
    CategoryOut,
    ProductBrief,
    ProductDetailOut,
    ProductReviewSummaryOut,
    ReviewCreate,
    ReviewOut,
)

router = APIRouter(prefix="/products", tags=["Products"])


def _serialize_review(review: ProductReview) -> ReviewOut:
    return ReviewOut(
        id=review.id,
        user_id=review.user_id,
        product_id=review.product_id,
        rating=review.rating,
        comment=review.comment,
        created_at=review.created_at,
        updated_at=review.updated_at,
        user_name=review.user.name,
        user_avatar=review.user.avatar,
    )


async def _get_public_product_or_404(db: AsyncSession, product_id: int) -> Product:
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.is_active == True,  # noqa: E712
            Product.is_deleted == False,  # noqa: E712
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


def _apply_product_filters(
    query,
    category_id: int | None,
    min_price: float | None,
    max_price: float | None,
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price must be less than or equal to max_price",
        )

    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)

    return query


async def _user_has_delivered_purchase(db: AsyncSession, user_id: int, product_id: int) -> bool:
    result = await db.execute(
        select(OrderDetail.id)
        .join(Order, Order.id == OrderDetail.order_id)
        .where(
            Order.user_id == user_id,
            Order.status == OrderStatus.DELIVERED.value,
            OrderDetail.product_id == product_id,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _build_review_summary(
    db: AsyncSession,
    product_id: int,
    current_user: User | None = None,
) -> ProductReviewSummaryOut:
    result = await db.execute(
        select(ProductReview)
        .options(selectinload(ProductReview.user))
        .where(ProductReview.product_id == product_id)
        .order_by(ProductReview.created_at.desc())
    )
    reviews = list(result.scalars().all())
    items = [_serialize_review(review) for review in reviews]
    review_count = len(items)
    average_rating = round(sum(review.rating for review in reviews) / review_count, 1) if review_count else 0

    my_review = None
    can_review = False
    if current_user:
        can_review = await _user_has_delivered_purchase(db, current_user.id, product_id)
        my_review = next((item for item in items if item.user_id == current_user.id), None)

    return ProductReviewSummaryOut(
        items=items,
        average_rating=average_rating,
        review_count=review_count,
        can_review=can_review,
        my_review=my_review,
    )


@router.get("/categories", response_model=list[CategoryOut])
async def list_public_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Category).where(Category.is_active == True)  # noqa: E712
    )
    return result.scalars().all()


@router.get("", response_model=dict)
async def list_products(
    category_id: int | None = Query(None, ge=1),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(
        Product.is_active == True,  # noqa: E712
        Product.is_deleted == False,  # noqa: E712
    )

    query = _apply_product_filters(query, category_id, min_price, max_price)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    products = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return {
        "items": [ProductBrief.model_validate(p) for p in products],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/search", response_model=dict)
async def search_products(
    q: str = Query(..., min_length=1),
    category_id: int | None = Query(None, ge=1),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).where(
        Product.is_active == True,  # noqa: E712
        Product.is_deleted == False,  # noqa: E712
        Product.name.ilike(f"%{q}%"),
    )

    query = _apply_product_filters(query, category_id, min_price, max_price)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    products = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return {
        "items": [ProductBrief.model_validate(p) for p in products],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{product_id}/reviews", response_model=ProductReviewSummaryOut)
async def get_product_reviews(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    await _get_public_product_or_404(db, product_id)
    return await _build_review_summary(db, product_id, current_user)


@router.post("/{product_id}/reviews", response_model=ProductReviewSummaryOut)
async def upsert_product_review(
    product_id: int,
    payload: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("reviews:create")),
):
    await _get_public_product_or_404(db, product_id)

    has_purchased = await _user_has_delivered_purchase(db, current_user.id, product_id)
    if not has_purchased:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chi nhung khach hang da mua va da nhan san pham moi duoc danh gia.",
        )

    result = await db.execute(
        select(ProductReview).where(
            ProductReview.product_id == product_id,
            ProductReview.user_id == current_user.id,
        )
    )
    review = result.scalar_one_or_none()

    if review is None:
        review = ProductReview(
            user_id=current_user.id,
            product_id=product_id,
            rating=payload.rating,
            comment=payload.comment,
        )
        db.add(review)
    else:
        review.rating = payload.rating
        review.comment = payload.comment

    await db.commit()
    return await _build_review_summary(db, product_id, current_user)


@router.get("/{product_id}", response_model=ProductDetailOut)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await _get_public_product_or_404(db, product_id)
    product.view_count += 1
    await db.flush()
    await db.refresh(product)
    return ProductDetailOut.model_validate(product)
