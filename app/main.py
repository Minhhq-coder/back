from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.core.config import (
    CORS_ORIGINS,
    CHATBOT_SCOPE_FILE,
    LOCAL_ADMIN_EMAIL,
    LOCAL_ADMIN_PASSWORD,
    UPLOAD_DIR,
)
from app.core.database import Base, async_session, engine
from app.models import Order, Permission, UserType
from app.models import User
from app.core.security import hash_password
from app.routers import admin, auth, cart, chatbot, notifications, orders, payments, products, users
from app.services.order_code_service import generate_unique_order_code

PERMISSION_DESCRIPTIONS = {
    "admin:access": "Access the admin area.",
    "profile:read": "View own profile.",
    "profile:update": "Update own profile.",
    "profile:upload_avatar": "Upload own avatar.",
    "profile:delete": "Delete own account.",
    "cart:read": "View own cart.",
    "cart:write": "Modify own cart.",
    "orders:create": "Create orders from cart.",
    "orders:read": "Read own orders.",
    "orders:confirm": "Confirm order delivery.",
    "orders:cancel": "Cancel own eligible orders.",
    "notifications:read": "Read own notifications.",
    "payments:create": "Create or retry payment transactions.",
    "payments:read": "Read own payment status.",
    "reviews:create": "Create or update reviews for delivered products.",
    "categories:read": "View all categories in admin.",
    "categories:write": "Create and update categories.",
    "products:manage": "Manage products in admin.",
    "orders:manage": "Manage all orders in admin.",
    "statistics:read": "View admin statistics.",
    "users:read": "View users in admin.",
    "users:write": "Update users in admin.",
    "chatbot:manage": "Manage chatbot knowledge base and audit logs.",
}

ROLE_PERMISSIONS = {
    "admin": [
        "admin:access",
        "profile:read",
        "profile:update",
        "profile:upload_avatar",
        "notifications:read",
        "categories:read",
        "categories:write",
        "products:manage",
        "orders:manage",
        "statistics:read",
        "users:read",
        "users:write",
        "chatbot:manage",
    ],
    "customer": [
        "profile:read",
        "profile:update",
        "profile:upload_avatar",
        "profile:delete",
        "cart:read",
        "cart:write",
        "orders:create",
        "orders:read",
        "orders:confirm",
        "orders:cancel",
        "notifications:read",
        "payments:create",
        "payments:read",
        "reviews:create",
    ],
}

LOCAL_ADMIN_NAME = "Local Admin"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOADS_PATH = PROJECT_ROOT / UPLOAD_DIR
CHATBOT_SCOPE_PATH = PROJECT_ROOT / CHATBOT_SCOPE_FILE
UPLOADS_PATH.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOADS_PATH.mkdir(parents=True, exist_ok=True)
    if CHATBOT_SCOPE_PATH.parent:
        CHATBOT_SCOPE_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "postgresql":
            await conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ADD COLUMN IF NOT EXISTS order_code VARCHAR(20)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_order_code ON orders(order_code)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ALTER COLUMN user_id DROP NOT NULL
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    DO $$
                    DECLARE constraint_name TEXT;
                    BEGIN
                        SELECT conname
                        INTO constraint_name
                        FROM pg_constraint
                        WHERE conrelid = 'orders'::regclass
                          AND contype = 'f'
                          AND confrelid = 'users'::regclass
                        LIMIT 1;

                        IF constraint_name IS NOT NULL THEN
                            EXECUTE format('ALTER TABLE orders DROP CONSTRAINT %I', constraint_name);
                        END IF;

                        ALTER TABLE orders
                        ADD CONSTRAINT fk_orders_user_id_users
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
                    EXCEPTION
                        WHEN duplicate_object THEN NULL;
                    END $$;
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    DO $$
                    DECLARE constraint_name TEXT;
                    BEGIN
                        SELECT conname
                        INTO constraint_name
                        FROM pg_constraint
                        WHERE conrelid = 'carts'::regclass
                          AND contype = 'f'
                          AND confrelid = 'users'::regclass
                        LIMIT 1;

                        IF constraint_name IS NOT NULL THEN
                            EXECUTE format('ALTER TABLE carts DROP CONSTRAINT %I', constraint_name);
                        END IF;

                        ALTER TABLE carts
                        ADD CONSTRAINT fk_carts_user_id_users
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
                    EXCEPTION
                        WHEN duplicate_object THEN NULL;
                    END $$;
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ADD COLUMN IF NOT EXISTS shipping_address VARCHAR(255) NOT NULL DEFAULT ''
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ADD COLUMN IF NOT EXISTS payment_method VARCHAR(20) NOT NULL DEFAULT 'cod'
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ADD COLUMN IF NOT EXISTS payment_status VARCHAR(20) NOT NULL DEFAULT 'unpaid'
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ADD COLUMN IF NOT EXISTS payment_provider VARCHAR(50)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ADD COLUMN IF NOT EXISTS payment_transaction_id VARCHAR(100)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP NULL
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE orders
                    ADD COLUMN IF NOT EXISTS inventory_reserved BOOLEAN NOT NULL DEFAULT FALSE
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE order_details
                    ALTER COLUMN product_id DROP NOT NULL
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    DO $$
                    DECLARE constraint_name TEXT;
                    BEGIN
                        SELECT conname
                        INTO constraint_name
                        FROM pg_constraint
                        WHERE conrelid = 'order_details'::regclass
                          AND contype = 'f'
                          AND confrelid = 'products'::regclass
                        LIMIT 1;

                        IF constraint_name IS NOT NULL THEN
                            EXECUTE format('ALTER TABLE order_details DROP CONSTRAINT %I', constraint_name);
                        END IF;

                        ALTER TABLE order_details
                        ADD CONSTRAINT fk_order_details_product_id_products
                        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL;
                    EXCEPTION
                        WHEN duplicate_object THEN NULL;
                    END $$;
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    DO $$
                    DECLARE constraint_name TEXT;
                    BEGIN
                        SELECT conname
                        INTO constraint_name
                        FROM pg_constraint
                        WHERE conrelid = 'cart_items'::regclass
                          AND contype = 'f'
                          AND confrelid = 'products'::regclass
                        LIMIT 1;

                        IF constraint_name IS NOT NULL THEN
                            EXECUTE format('ALTER TABLE cart_items DROP CONSTRAINT %I', constraint_name);
                        END IF;

                        ALTER TABLE cart_items
                        ADD CONSTRAINT fk_cart_items_product_id_products
                        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE;
                    EXCEPTION
                        WHEN duplicate_object THEN NULL;
                    END $$;
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    UPDATE orders
                    SET status = CASE
                        WHEN LOWER(status) = 'completed' THEN 'delivered'
                        WHEN LOWER(status) = 'canceled' THEN 'cancelled'
                        ELSE LOWER(status)
                    END
                    WHERE status IS NOT NULL
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS external_id VARCHAR(255)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS slug VARCHAR(255)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS brand VARCHAR(255)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS subcategory VARCHAR(100)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS original_price DOUBLE PRECISION
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS currency VARCHAR(10) NOT NULL DEFAULT 'VND'
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS volume VARCHAR(100)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS stock_status VARCHAR(50) NOT NULL DEFAULT 'unknown'
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS usage TEXT
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS skin_type JSONB NOT NULL DEFAULT '[]'::jsonb
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS concerns JSONB NOT NULL DEFAULT '[]'::jsonb
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS ingredients JSONB NOT NULL DEFAULT '[]'::jsonb
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS benefits JSONB NOT NULL DEFAULT '[]'::jsonb
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS product_url VARCHAR(500)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS source VARCHAR(50)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS last_updated DATE
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE
                    """
                )
            )
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
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP NULL
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS birth_date DATE NULL
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255) NULL
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub
                    ON users(google_sub)
                    WHERE google_sub IS NOT NULL
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    UPDATE products
                    SET image_url = COALESCE(image_url, image1),
                        original_price = COALESCE(original_price, price),
                        is_deleted = COALESCE(is_deleted, FALSE)
                    """
                )
            )

    async with async_session() as session:
        result = await session.execute(select(UserType))
        user_types = {user_type.name: user_type for user_type in result.scalars().all()}

        for user_type_id, role_name in ((1, "admin"), (2, "customer")):
            if role_name not in user_types:
                user_type = UserType(id=user_type_id, name=role_name)
                session.add(user_type)
                user_types[role_name] = user_type

        await session.flush()

        result = await session.execute(select(Permission))
        permissions = {permission.code: permission for permission in result.scalars().all()}

        for code, description in PERMISSION_DESCRIPTIONS.items():
            if code not in permissions:
                permission = Permission(code=code, description=description)
                session.add(permission)
                permissions[code] = permission

        await session.flush()

        result = await session.execute(
            select(UserType)
            .where(UserType.name.in_(ROLE_PERMISSIONS))
            .options(selectinload(UserType.permissions))
        )
        user_types = {user_type.name: user_type for user_type in result.scalars().all()}

        for role_name, permission_codes in ROLE_PERMISSIONS.items():
            user_type = user_types.get(role_name)
            if not user_type:
                continue

            existing_codes = {permission.code for permission in user_type.permissions}
            desired_codes = set(permission_codes)
            for code in permission_codes:
                if code not in existing_codes:
                    user_type.permissions.append(permissions[code])

            user_type.permissions[:] = [
                permission
                for permission in user_type.permissions
                if permission.code in desired_codes
            ]

        result = await session.execute(
            select(Order).where((Order.order_code.is_(None)) | (Order.order_code == ""))
        )
        for order in result.scalars().all():
            order.order_code = await generate_unique_order_code(session)

        if LOCAL_ADMIN_EMAIL and LOCAL_ADMIN_PASSWORD:
            result = await session.execute(
                select(User).where(User.email == LOCAL_ADMIN_EMAIL)
            )
            admin_user = result.scalar_one_or_none()
            if admin_user is None:
                admin_role = user_types.get("admin")
                if admin_role is not None:
                    session.add(
                        User(
                            name=LOCAL_ADMIN_NAME,
                            email=LOCAL_ADMIN_EMAIL,
                            password=hash_password(LOCAL_ADMIN_PASSWORD),
                            user_type_id=admin_role.id,
                            is_confirm=True,
                        )
                    )

        await session.commit()

    yield

    await engine.dispose()


app = FastAPI(
    title="Cosmetics Shop API",
    description="Backend API cho website ban my pham",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(f"/{UPLOAD_DIR}", StaticFiles(directory=str(UPLOADS_PATH)), name="uploads")

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(notifications.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(chatbot.router)


@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to Cosmetics Shop API", "docs": "/docs"}
