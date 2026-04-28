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
        if key == "channel_binding":
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
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "bank_qr").strip().lower()
PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "change-payment-webhook-secret")
PAYMENT_EXPIRE_MINUTES = int(os.getenv("PAYMENT_EXPIRE_MINUTES", "15"))
ENABLE_MOCK_PAYMENTS = os.getenv("ENABLE_MOCK_PAYMENTS", "false").lower() == "true"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
DATABASE_ECHO = os.getenv("DATABASE_ECHO", "false").lower() == "true"
LOCAL_ADMIN_EMAIL = os.getenv("LOCAL_ADMIN_EMAIL", "").strip().lower()
LOCAL_ADMIN_PASSWORD = os.getenv("LOCAL_ADMIN_PASSWORD", "")
CHATBOT_AI_API_KEY = (
    os.getenv("CHATBOT_AI_API_KEY", "").strip()
    or os.getenv("OPENROUTER_API_KEY", "").strip()
    or os.getenv("OPENAI_API_KEY", "").strip()
)
CHATBOT_AI_BASE_URL = os.getenv("CHATBOT_AI_BASE_URL", "").strip()
if not CHATBOT_AI_BASE_URL:
    if os.getenv("OPENROUTER_API_KEY", "").strip():
        CHATBOT_AI_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    elif os.getenv("OPENAI_API_KEY", "").strip():
        CHATBOT_AI_BASE_URL = "https://api.openai.com/v1/chat/completions"
CHATBOT_AI_MODEL = (
    os.getenv("CHATBOT_AI_MODEL", "").strip()
    or os.getenv("OPENROUTER_MODEL", "").strip()
    or os.getenv("OPENAI_MODEL", "").strip()
)
CHATBOT_AI_TIMEOUT_SECONDS = float(os.getenv("CHATBOT_AI_TIMEOUT_SECONDS", "30"))
CHATBOT_HOTLINE = os.getenv("CHATBOT_HOTLINE", "").strip()
CHATBOT_SCOPE_FILE = os.getenv("CHATBOT_SCOPE_FILE", "chatbot.md").strip() or "chatbot.md"
CHATBOT_MAX_HISTORY_MESSAGES = int(os.getenv("CHATBOT_MAX_HISTORY_MESSAGES", "8"))
CHATBOT_WORD_LIMIT = int(os.getenv("CHATBOT_WORD_LIMIT", "100"))
CHATBOT_STREAM_CHUNK_SIZE = int(os.getenv("CHATBOT_STREAM_CHUNK_SIZE", "24"))
CORS_ORIGINS = _parse_csv_env(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
