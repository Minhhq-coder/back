from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import case, func, outerjoin, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import UPLOAD_DIR
from app.core.database import get_db
from app.dependencies.auth import require_permission
from app.models import (
    CartItem,
    Category,
    Order,
    OrderDetail,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    Product,
    User,
    UserType,
)
from app.schemas import (
    AdminUserOut,
    AdminUserUpdate,
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    DailyOrdersOut,
    OrderOut,
    ProductSalesOut,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    StatisticsOut,
)
from app.services.payment_service import cancel_open_payments, restore_inventory_for_order

router = APIRouter(prefix="/admin", tags=["Admin"])
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_IMAGE_DIR = PROJECT_ROOT / UPLOAD_DIR / "products"


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _normalize_product_payload(payload: dict) -> dict:
    if payload.get("image_url") and not payload.get("image1"):
        payload["image1"] = payload["image_url"]
    if payload.get("image1") and not payload.get("image_url"):
        payload["image_url"] = payload["image1"]
    if payload.get("original_price") is None and payload.get("price") is not None:
        payload["original_price"] = payload["price"]
    return payload


def _serialize_admin_user(user: User) -> AdminUserOut:
    permissions = sorted(
        getattr(user.user_type, "permissions", []),
        key=lambda permission: permission.code,
    )
    return AdminUserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        address=user.address,
        phone=user.phone,
        avatar=user.avatar,
        birth_date=user.birth_date,
        is_confirm=user.is_confirm,
        user_type_id=user.user_type_id,
        role=user.user_type.name,
        permissions=permissions,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    _: User = Depends(require_permission("categories:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category))
    return result.scalars().all()


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    _: User = Depends(require_permission("categories:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).where(Category.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Category name already exists")

    category = Category(name=data.name)
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


@router.put("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    _: User = Depends(require_permission("categories:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if data.name is not None:
        result = await db.execute(
            select(Category).where(Category.name == data.name, Category.id != category_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Category name already exists")
        category.name = data.name

    if data.is_active is not None:
        category.is_active = data.is_active

    await db.flush()
    await db.refresh(category)
    return category


@router.delete("/categories/{category_id}", response_model=dict)
async def delete_category(
    category_id: int,
    _: User = Depends(require_permission("categories:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    product_count = (
        await db.execute(
            select(func.count(Product.id)).where(
                Product.category_id == category_id,
                Product.is_deleted == False,  # noqa: E712
            )
        )
    ).scalar_one()

    if product_count:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete category while it still contains products",
        )

    await db.delete(category)
    await db.flush()
    return {"message": "Category deleted successfully."}


@router.get("/products", response_model=list[ProductOut])
async def list_all_products(
    _: User = Depends(require_permission("products:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.is_deleted == False))  # noqa: E712
    return result.scalars().all()


@router.post("/products/upload-image", status_code=status.HTTP_201_CREATED)
async def upload_product_image(
    file: UploadFile = File(...),
    _: User = Depends(require_permission("products:manage")),
):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image file is too large")

    PRODUCT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"product-{uuid4().hex}{extension}"
    destination = PRODUCT_IMAGE_DIR / filename
    destination.write_bytes(content)

    return {"image_url": f"/{UPLOAD_DIR}/products/{filename}".replace("\\", "/")}


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    _: User = Depends(require_permission("products:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Category).where(Category.id == data.category_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Category not found")

    product = Product(**_normalize_product_payload(data.model_dump()))
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    _: User = Depends(require_permission("products:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.is_deleted == False)  # noqa: E712
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = _normalize_product_payload(data.model_dump(exclude_unset=True))
    if "category_id" in update_data:
        result = await db.execute(
            select(Category).where(Category.id == update_data["category_id"])
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Category not found")

    for field, value in update_data.items():
        setattr(product, field, value)

    await db.flush()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}", response_model=dict)
async def delete_product(
    product_id: int,
    _: User = Depends(require_permission("products:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.is_deleted == False)  # noqa: E712
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cart_items = (
        await db.execute(select(CartItem).where(CartItem.product_id == product_id))
    ).scalars().all()
    for item in cart_items:
        await db.delete(item)

    await db.delete(product)
    await db.flush()
    return {
        "message": "Product deleted successfully.",
        "deleted": True,
        "archived": False,
    }


@router.get("/orders", response_model=list[OrderOut])
async def list_all_orders(
    order_status: str | None = Query(None, alias="status"),
    _: User = Depends(require_permission("orders:manage")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Order)
        .options(selectinload(Order.details), selectinload(Order.payments))
        .order_by(Order.date_order.desc())
    )

    if order_status:
        try:
            status_enum = OrderStatus(order_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Choose from: {[s.value for s in OrderStatus]}",
            )
        query = query.where(Order.status == status_enum)

    result = await db.execute(query)
    return result.scalars().all()


@router.put("/orders/{order_id}/approve", response_model=OrderOut)
async def approve_order(
    order_id: int,
    _: User = Depends(require_permission("orders:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).options(selectinload(Order.details), selectinload(Order.payments)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Only pending orders can be approved")

    order.status = OrderStatus.APPROVED
    await db.flush()
    await db.refresh(order)
    return order


@router.put("/orders/{order_id}/shipping", response_model=OrderOut)
async def set_shipping(
    order_id: int,
    _: User = Depends(require_permission("orders:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).options(selectinload(Order.details), selectinload(Order.payments)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only approved orders can be set to shipping")
    if order.payment_method == PaymentMethod.QR.value and order.payment_status != PaymentStatus.PAID.value:
        raise HTTPException(status_code=400, detail="QR orders must be paid before shipping")

    order.status = OrderStatus.SHIPPING
    order.date_ship = datetime.utcnow()
    await db.flush()
    await db.refresh(order)
    return order


@router.put("/orders/{order_id}/cancel", response_model=OrderOut)
async def cancel_order_as_admin(
    order_id: int,
    _: User = Depends(require_permission("orders:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).options(selectinload(Order.details), selectinload(Order.payments)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in {OrderStatus.DELIVERED, OrderStatus.CANCELLED}:
        raise HTTPException(
            status_code=400,
            detail="Delivered or cancelled orders cannot be cancelled again",
        )

    await restore_inventory_for_order(db, order)
    await cancel_open_payments(order)

    order.status = OrderStatus.CANCELLED
    order.is_paid = False
    if order.payment_method == PaymentMethod.QR.value:
        order.payment_status = PaymentStatus.CANCELLED.value
    await db.flush()
    await db.refresh(order)
    return order


@router.get("/statistics", response_model=StatisticsOut)
async def get_statistics(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    _: User = Depends(require_permission("statistics:read")),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if start_date:
        filters.append(Order.date_order >= start_date)
    if end_date:
        filters.append(Order.date_order <= end_date)

    counts_query = select(
        func.count(Order.id),
        func.coalesce(func.sum(case((Order.status == OrderStatus.PENDING, 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status == OrderStatus.APPROVED, 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status == OrderStatus.SHIPPING, 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status == OrderStatus.DELIVERED, 1), else_=0)), 0),
        func.coalesce(func.sum(case((Order.status == OrderStatus.CANCELLED, 1), else_=0)), 0),
    )
    if filters:
        counts_query = counts_query.where(*filters)

    counts_result = await db.execute(counts_query)
    (
        total_orders,
        pending_orders,
        approved_orders,
        shipping_orders,
        delivered_orders,
        cancelled_orders,
    ) = counts_result.one()

    revenue_join = outerjoin(Order, OrderDetail, Order.id == OrderDetail.order_id)
    revenue_query = select(
        func.coalesce(func.sum(OrderDetail.product_price * OrderDetail.quantity), 0.0)
    ).select_from(revenue_join).where(Order.status == OrderStatus.DELIVERED)
    if filters:
        revenue_query = revenue_query.where(*filters)

    total_revenue = (await db.execute(revenue_query)).scalar_one()

    product_sales_query = (
        select(
            func.coalesce(Product.id, -func.min(OrderDetail.id)),
            func.coalesce(Product.name, OrderDetail.product_name),
            Category.name,
            func.coalesce(Product.image1, OrderDetail.product_image),
            func.coalesce(func.sum(OrderDetail.quantity), 0),
            func.coalesce(func.sum(OrderDetail.product_price * OrderDetail.quantity), 0.0),
        )
        .select_from(OrderDetail)
        .join(Order, Order.id == OrderDetail.order_id)
        .outerjoin(Product, Product.id == OrderDetail.product_id)
        .outerjoin(Category, Category.id == Product.category_id)
        .where(Order.status == OrderStatus.DELIVERED)
        .group_by(
            Product.id,
            Product.name,
            OrderDetail.product_name,
            Category.name,
            Product.image1,
            OrderDetail.product_image,
        )
        .order_by(func.sum(OrderDetail.quantity).desc(), func.sum(OrderDetail.product_price * OrderDetail.quantity).desc())
        .limit(8)
    )
    if filters:
        product_sales_query = product_sales_query.where(*filters)

    product_sales_rows = (await db.execute(product_sales_query)).all()
    top_products = [
        ProductSalesOut(
            product_id=product_id,
            product_name=product_name,
            category_name=category_name,
            product_image=product_image,
            units_sold=int(units_sold or 0),
            revenue=float(revenue or 0.0),
        )
        for product_id, product_name, category_name, product_image, units_sold, revenue in product_sales_rows
    ]

    daily_orders_query = (
        select(
            func.date(Order.date_order).label("order_day"),
            func.count(Order.id).label("total_orders"),
        )
        .group_by(func.date(Order.date_order))
        .order_by(func.date(Order.date_order).asc())
    )
    if filters:
        daily_orders_query = daily_orders_query.where(*filters)

    daily_order_rows = (await db.execute(daily_orders_query)).all()
    daily_order_map = {
        order_day: int(total or 0)
        for order_day, total in daily_order_rows
        if order_day is not None
    }

    if daily_order_map:
        start_day = min(daily_order_map)
        end_day = max(daily_order_map)
        daily_orders = []
        current_day = start_day
        while current_day <= end_day:
            daily_orders.append(
                DailyOrdersOut(
                    order_date=current_day,
                    total_orders=daily_order_map.get(current_day, 0),
                )
            )
            current_day += timedelta(days=1)
    else:
        daily_orders = []

    return StatisticsOut(
        total_orders=total_orders,
        pending_orders=pending_orders,
        approved_orders=approved_orders,
        shipping_orders=shipping_orders,
        delivered_orders=delivered_orders,
        cancelled_orders=cancelled_orders,
        total_revenue=float(total_revenue or 0.0),
        top_products=top_products,
        daily_orders=daily_orders,
    )


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    _: User = Depends(require_permission("users:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_type).selectinload(UserType.permissions))
        .order_by(User.id.asc())
    )
    return [_serialize_admin_user(user) for user in result.scalars().all()]


@router.get("/users/{user_id}", response_model=AdminUserOut)
async def get_user_detail(
    user_id: int,
    _: User = Depends(require_permission("users:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_type).selectinload(UserType.permissions))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return _serialize_admin_user(user)


@router.put("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: int,
    data: AdminUserUpdate,
    _: User = Depends(require_permission("users:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_type).selectinload(UserType.permissions))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    normalized_email = _normalize_email(data.email) if data.email else None

    if normalized_email and normalized_email != _normalize_email(user.email):
        email_result = await db.execute(
            select(User).where(
                func.lower(User.email) == normalized_email,
                User.id != user_id,
            )
        )
        if email_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = normalized_email

    if data.user_type_id is not None and data.user_type_id != user.user_type_id:
        role_result = await db.execute(select(UserType).where(UserType.id == data.user_type_id))
        new_role = role_result.scalar_one_or_none()
        if not new_role:
            raise HTTPException(status_code=400, detail="User role not found")
        user.user_type_id = data.user_type_id

    update_data = data.model_dump(exclude_unset=True, exclude={"email", "user_type_id"})
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)

    result = await db.execute(
        select(User)
        .options(selectinload(User.user_type).selectinload(UserType.permissions))
        .where(User.id == user_id)
    )
    user = result.scalar_one()
    return _serialize_admin_user(user)
