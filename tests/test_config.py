from urllib.parse import parse_qs, urlsplit

from app.core.config import _normalize_database_url


def test_normalize_database_url_converts_postgresql_scheme_to_asyncpg():
    normalized = _normalize_database_url(
        "postgresql://user:pass@db.example.com/shop?sslmode=require"
    )

    assert normalized.startswith("postgresql+asyncpg://user:pass@db.example.com/shop")
    assert parse_qs(urlsplit(normalized).query)["ssl"] == ["require"]


def test_normalize_database_url_converts_postgres_short_scheme():
    normalized = _normalize_database_url("postgres://user:pass@db.example.com/shop")

    assert normalized == "postgresql+asyncpg://user:pass@db.example.com/shop"


def test_normalize_database_url_keeps_existing_asyncpg_urls():
    raw_url = "postgresql+asyncpg://user:pass@db.example.com/shop?ssl=require"

    assert _normalize_database_url(raw_url) == raw_url


def test_normalize_database_url_preserves_other_query_params():
    normalized = _normalize_database_url(
        "postgresql://user:pass@db.example.com/shop?sslmode=require&application_name=render"
    )

    query = parse_qs(urlsplit(normalized).query)
    assert query["ssl"] == ["require"]
    assert query["application_name"] == ["render"]
    assert "sslmode" not in query
