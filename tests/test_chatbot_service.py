from app.models import Product
from app.services.chatbot_service import (
    _build_small_talk_answer,
    _build_missing_info_answer,
    _build_single_product_answer,
    _chunk_text,
    _detect_small_talk_intent,
    _extract_order_code,
    _fold_text,
    _has_specific_product_terms,
    _should_search_product_context,
    _should_use_last_product_context,
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
    text = "mot hai ba bon nam sau bay"
    chunks = _chunk_text(text, 8)

    assert chunks
    assert all(len(chunk) <= 8 for chunk in chunks)
    assert "".join(chunks) == text


def test_should_use_last_product_context_for_generic_follow_up():
    message = "còn hàng không?"

    assert _should_use_last_product_context(_fold_text(message), message) is True


def test_should_use_last_product_context_for_add_to_cart_follow_up():
    message = "thêm vào giỏ giúp tôi"

    assert _should_use_last_product_context(_fold_text(message), message) is True


def test_should_not_use_last_product_context_when_message_names_product():
    message = "serum vitamin C còn hàng không?"

    assert _has_specific_product_terms(message) is True
    assert _should_use_last_product_context(_fold_text(message), message) is False


def test_should_skip_product_context_for_order_question_without_product_id():
    assert _should_search_product_context(_fold_text("đơn hàng của tôi tới đâu rồi"), None) is False


def test_should_search_product_context_for_price_follow_up_with_product_id():
    assert _should_search_product_context(_fold_text("giá bao nhiêu"), 10) is True


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
