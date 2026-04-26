# Đề xuất chức năng bổ sung cho website mỹ phẩm

Tài liệu này sắp xếp các chức năng nên bổ sung theo mức độ ưu tiên, dựa trên tình trạng backend hiện tại: đã có sản phẩm, danh mục, giỏ hàng, đơn hàng, thanh toán, đánh giá, chatbot, thông báo và admin.

## 1. Sắp xếp sản phẩm

**Mục tiêu:** Giúp người dùng tìm sản phẩm nhanh hơn sau khi đã có lọc theo danh mục và khoảng giá.

**Nên hỗ trợ:**

- Giá thấp đến cao
- Giá cao đến thấp
- Bán chạy nhất
- Xem nhiều nhất
- Mới cập nhật

**Backend cần bổ sung:**

- Query param `sort` cho API `GET /products`
- Có thể dùng các giá trị:
  - `price_asc`
  - `price_desc`
  - `best_selling`
  - `most_viewed`
  - `newest`

**Frontend cần hiển thị:**

- Dropdown sắp xếp trên trang danh sách sản phẩm
- Khi người dùng đổi sắp xếp, giữ lại các filter đang có như `category_id`, `min_price`, `max_price`

**Độ ưu tiên:** Rất cao

## 2. Wishlist / Sản phẩm yêu thích

**Mục tiêu:** Cho phép người dùng lưu sản phẩm muốn mua sau. Chức năng này phù hợp với website mỹ phẩm vì khách thường cần so sánh nhiều sản phẩm trước khi mua.

**Backend cần bổ sung:**

- Bảng `wishlists` hoặc `favorite_products`
- Mỗi bản ghi gồm:
  - `id`
  - `user_id`
  - `product_id`
  - `created_at`

**API nên có:**

- `GET /wishlist`: lấy danh sách sản phẩm yêu thích của user
- `POST /wishlist/{product_id}`: thêm sản phẩm vào yêu thích
- `DELETE /wishlist/{product_id}`: xóa sản phẩm khỏi yêu thích

**Frontend cần hiển thị:**

- Nút trái tim trên card sản phẩm
- Trang "Sản phẩm yêu thích" trong tài khoản người dùng
- Trang chi tiết sản phẩm có nút thêm/xóa khỏi yêu thích

**Độ ưu tiên:** Cao

## 3. Voucher / Mã giảm giá

**Mục tiêu:** Tăng khả năng chốt đơn bằng khuyến mãi và giúp admin chủ động tạo chiến dịch bán hàng.

**Backend cần bổ sung:**

- Bảng `coupons`
- Các trường nên có:
  - `code`
  - `discount_type`: `percent` hoặc `fixed`
  - `discount_value`
  - `min_order_value`
  - `max_discount`
  - `start_at`
  - `end_at`
  - `usage_limit`
  - `used_count`
  - `is_active`

**API nên có:**

- Public/user:
  - `POST /coupons/validate`: kiểm tra mã giảm giá trước khi đặt hàng
- Admin:
  - `GET /admin/coupons`
  - `POST /admin/coupons`
  - `PUT /admin/coupons/{coupon_id}`
  - `DELETE /admin/coupons/{coupon_id}`

**Frontend cần hiển thị:**

- Ô nhập mã giảm giá ở trang checkout
- Hiển thị số tiền giảm và tổng tiền cuối cùng
- Màn hình admin quản lý voucher

**Độ ưu tiên:** Cao

## 4. Theo dõi trạng thái đơn hàng chi tiết hơn

**Mục tiêu:** Làm trải nghiệm sau mua rõ ràng hơn, giảm việc khách phải hỏi shop về tình trạng đơn.

**Trạng thái nên có:**

- Chờ xác nhận
- Đã xác nhận
- Đang chuẩn bị hàng
- Đang giao
- Đã giao
- Đã hủy

**Backend cần bổ sung:**

- Kiểm tra enum/trạng thái đơn hàng hiện có
- Nếu chưa đủ, mở rộng `OrderStatus`
- Có thể thêm bảng lịch sử trạng thái `order_status_history`

**API nên có:**

- `GET /orders/{order_id}/timeline`: lấy tiến trình đơn hàng
- Admin cập nhật trạng thái đơn hàng

**Frontend cần hiển thị:**

- Timeline trên trang chi tiết đơn hàng
- Badge trạng thái đơn trên danh sách đơn hàng
- Thông báo khi đơn hàng được cập nhật trạng thái

**Độ ưu tiên:** Trung bình cao

## 5. Địa chỉ giao hàng đã lưu

**Mục tiêu:** Giảm thao tác khi đặt hàng lần sau, đặc biệt với user đã mua nhiều lần.

**Backend cần bổ sung:**

- Bảng `user_addresses`
- Các trường nên có:
  - `user_id`
  - `full_name`
  - `phone`
  - `address_line`
  - `ward`
  - `district`
  - `province`
  - `is_default`

**API nên có:**

- `GET /users/me/addresses`
- `POST /users/me/addresses`
- `PUT /users/me/addresses/{address_id}`
- `DELETE /users/me/addresses/{address_id}`
- `PUT /users/me/addresses/{address_id}/default`

**Frontend cần hiển thị:**

- Quản lý địa chỉ trong trang tài khoản
- Chọn địa chỉ có sẵn trong checkout
- Nút đặt làm địa chỉ mặc định

**Độ ưu tiên:** Trung bình cao

## 6. Đánh giá sản phẩm có hình ảnh

**Mục tiêu:** Tăng độ tin cậy của review và giúp người mua mới xem kết quả thực tế.

**Backend cần bổ sung:**

- Thêm bảng `review_images` hoặc thêm trường JSON `images` vào review
- Endpoint upload ảnh đánh giá
- Giới hạn số ảnh, dung lượng và định dạng ảnh

**API nên có:**

- `POST /products/{product_id}/reviews/images`
- Hoặc tích hợp upload ảnh vào API tạo/cập nhật review

**Frontend cần hiển thị:**

- Upload ảnh khi viết đánh giá
- Gallery ảnh trong phần review
- Preview ảnh trước khi gửi

**Độ ưu tiên:** Trung bình

## 7. Trang chi tiết sản phẩm nâng cấp

**Mục tiêu:** Tăng chất lượng thông tin, giúp khách quyết định mua dễ hơn.

**Nên bổ sung:**

- Sản phẩm liên quan cùng danh mục
- Sản phẩm đã xem gần đây
- Hiển thị rõ:
  - Thương hiệu
  - Dung tích
  - Tình trạng còn hàng
  - Giá gốc và giá hiện tại
  - Công dụng nổi bật
  - Loại da phù hợp

**Backend cần bổ sung:**

- `GET /products/{product_id}/related`
- Có thể gợi ý sản phẩm cùng `category_id`, sau này nâng cấp theo `skin_type` và `benefits`

**Frontend cần hiển thị:**

- Khu vực "Sản phẩm liên quan"
- Khu vực "Có thể bạn cũng thích"

**Độ ưu tiên:** Trung bình

## 8. Admin dashboard nâng cấp

**Mục tiêu:** Giúp admin nắm tình hình kinh doanh nhanh hơn.

**Chỉ số nên có:**

- Doanh thu hôm nay
- Doanh thu theo tháng
- Số đơn hàng mới
- Số đơn chờ xử lý
- Top sản phẩm bán chạy
- Sản phẩm sắp hết hàng
- Khách hàng mới

**Backend cần bổ sung:**

- Các endpoint thống kê riêng cho dashboard
- Tổng hợp dữ liệu từ orders, products, users

**API nên có:**

- `GET /admin/dashboard/summary`
- `GET /admin/dashboard/revenue`
- `GET /admin/dashboard/top-products`
- `GET /admin/dashboard/low-stock-products`

**Frontend cần hiển thị:**

- Cards tổng quan
- Biểu đồ doanh thu
- Bảng top sản phẩm
- Danh sách cần xử lý nhanh

**Độ ưu tiên:** Trung bình

## 9. SEO cho sản phẩm

**Mục tiêu:** Giúp website dễ được tìm thấy trên Google nếu muốn phát triển bán hàng lâu dài.

**Backend cần bổ sung:**

- Hỗ trợ lấy sản phẩm bằng `slug`
- Đảm bảo mỗi sản phẩm có `slug` duy nhất

**API nên có:**

- `GET /products/slug/{slug}`

**Frontend cần hiển thị:**

- URL dạng `/products/ten-san-pham`
- Meta title theo tên sản phẩm
- Meta description từ mô tả sản phẩm
- Ảnh đại diện dùng cho social preview

**Độ ưu tiên:** Trung bình thấp nếu chưa tập trung SEO

## Thứ tự nên triển khai

Nếu muốn làm theo hướng thực tế và tác động rõ đến người dùng, nên đi theo thứ tự:

1. Sắp xếp sản phẩm
2. Wishlist / Sản phẩm yêu thích
3. Voucher / Mã giảm giá
4. Theo dõi trạng thái đơn hàng chi tiết hơn
5. Địa chỉ giao hàng đã lưu
6. Đánh giá sản phẩm có hình ảnh
7. Trang chi tiết sản phẩm nâng cấp
8. Admin dashboard nâng cấp
9. SEO cho sản phẩm

## Gợi ý phiên bản gần nhất nên làm

Nên chọn 3 chức năng sau cho lần nâng cấp tiếp theo:

1. **Sắp xếp sản phẩm**: nhỏ, dễ làm, tác động trực tiếp đến trang danh sách sản phẩm.
2. **Wishlist**: tăng khả năng giữ chân người dùng.
3. **Voucher**: phù hợp với thương mại điện tử và có giá trị kinh doanh rõ ràng.

