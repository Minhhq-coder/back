from app.models import Product
from app.services.chatbot_service import (
    _build_small_talk_answer,
    _build_missing_info_answer,
    _build_single_product_answer,
    _chunk_text,
    _detect_small_talk_intent,
    _extract_order_code,
    _fold_text,
    _truncate_words,
)


def test_extract_order_code_returns_uppercase_code():
    assert _extract_order_code("kiem tra don od1a2b3c4") == "OD1A2B3C4"


def test_truncate_words_limits_word_count():
    text = "mot hai ba bon nam sau bay tam chin muoi"

    assert _truncate_words(text, 5) == "mot hai ba bon nam..."


def test_build_missing_info_answer_for_policy_requires_handoff():
    answer, handoff_required, handoff_message = _build_missing_info_answer(
        _fold_text("chinh sach doi tra nhu the nao"),
        current_user=None,
    )

    assert "chinh sach" not in answer.lower()
    assert handoff_required is True
    assert handoff_message is not None


def test_detect_small_talk_intent_for_greeting_only_message():
    assert _detect_small_talk_intent(_fold_text("xin chao shop")) == "greeting"


def test_detect_small_talk_intent_ignores_greeting_plus_real_product_question():
    assert _detect_small_talk_intent(_fold_text("chao shop serum nay gia bao nhieu")) is None


def test_build_small_talk_answer_for_greeting_is_conversational():
    answer = _build_small_talk_answer("greeting")

    assert "Xin chào" in answer
    assert "sản phẩm" in answer


def test_chunk_text_splits_into_small_segments():
    chunks = _chunk_text("mot hai ba bon nam sau bay", 8)

    assert chunks
    assert all(len(chunk) <= 8 for chunk in chunks)


def test_build_single_product_answer_contains_price_and_stock():
    product = Product(
        id=1,
        category_id=1,
        name="Serum A",
        price=199000,
        currency="VND",
        quantity=5,
        stock_status="in_stock",
        description="Cap am nhe cho da dau",
        benefits=["cap am", "lam diu"],
    )

    answer = _build_single_product_answer(product, _fold_text("gia san pham nay bao nhieu"))

    assert "Serum A" in answer
    assert "199.000 VND" in answer
    assert "còn hàng" in answer
