import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()


def _parse_csv_env(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _normalize_database_url(raw_url: str) -> str:
    normalized_url = raw_url.strip()
    if normalized_url.startswith("postgres://"):
        normalized_url = "postgresql://" + normalized_url[len("postgres://") :]
    if normalized_url.startswith("postgresql://"):
        normalized_url = "postgresql+asyncpg://" + normalized_url[len("postgresql://") :]

    parts = urlsplit(normalized_url)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    normalized_query_items: list[tuple[str, str]] = []
    ssl_value: str | None = None

    for key, value in query_items:
        if key == "sslmode":
            ssl_value = ssl_value or value
            continue
        normalized_query_items.append((key, value))

    if ssl_value is not None and not any(key == "ssl" for key, _ in normalized_query_items):
        normalized_query_items.append(("ssl", ssl_value))

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(normalized_query_items, doseq=True),
            parts.fragment,
        )
    )


DATABASE_URL = _normalize_database_url(
    os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/cosmetics_db",
    )
)
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "mock_qr")
PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "change-payment-webhook-secret")
PAYMENT_EXPIRE_MINUTES = int(os.getenv("PAYMENT_EXPIRE_MINUTES", "15"))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
DATABASE_ECHO = os.getenv("DATABASE_ECHO", "false").lower() == "true"
CORS_ORIGINS = _parse_csv_env(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
