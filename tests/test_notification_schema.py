from datetime import datetime

from app.schemas.notification import NotificationOut


def _mojibake(value: str) -> str:
    return value.encode("utf-8").decode("latin1")


def test_notification_out_repairs_mojibake_text():
    notification = NotificationOut(
        id=1,
        title=_mojibake("Đặt hàng thành công"),
        message=_mojibake("Đơn hàng OD123 đã được tạo thành công."),
        order_id=10,
        is_read=False,
        created_at=datetime(2026, 4, 28),
    )

    assert notification.title == "Đặt hàng thành công"
    assert notification.message == "Đơn hàng OD123 đã được tạo thành công."


def test_notification_out_keeps_valid_unicode_text():
    notification = NotificationOut(
        id=1,
        title="Thanh toán thành công",
        message="Đơn hàng OD123 đã được thanh toán thành công.",
        order_id=10,
        is_read=False,
        created_at=datetime(2026, 4, 28),
    )

    assert notification.title == "Thanh toán thành công"
    assert notification.message == "Đơn hàng OD123 đã được thanh toán thành công."
