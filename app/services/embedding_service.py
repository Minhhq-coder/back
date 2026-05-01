from __future__ import annotations

from functools import lru_cache

from app.core.config import CHATBOT_EMBEDDING_MODEL

EMBEDDING_DIMENSION = 1024


@lru_cache(maxsize=1)
def _get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - depends on deployment packages
        raise RuntimeError(
            "sentence-transformers is required for RAG embeddings. "
            "Install it with `pip install -r requirements.txt`."
        ) from exc

    return SentenceTransformer(CHATBOT_EMBEDDING_MODEL)


def create_embedding(text: str) -> list[float]:
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        raise ValueError("Text is required to create an embedding.")

    model = _get_embedding_model()
    embedding = model.encode(cleaned, normalize_embeddings=True, convert_to_numpy=True)
    values = [float(value) for value in embedding.tolist()]

    if len(values) != EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"Embedding model {CHATBOT_EMBEDDING_MODEL} returned {len(values)} dimensions; "
            f"expected {EMBEDDING_DIMENSION}."
        )

    return values
