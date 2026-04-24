# CLAUDE.md

## Tổng Quan Dự Án

Repository này là backend FastAPI cho ứng dụng Cosmetics Shop.
Frontend đang hoạt động nằm ở `../front` và được xây bằng Vue 3 + Vite + Pinia.

Sản phẩm hiện tại là một website bán mỹ phẩm tiếng Việt với các nhóm tính năng chính:
- danh mục sản phẩm công khai, tìm kiếm, xem chi tiết sản phẩm
- đăng nhập email/password và Google login
- chỉnh sửa hồ sơ, upload avatar, hạng thành viên
- giỏ hàng, checkout, lịch sử đơn hàng
- thanh toán COD và QR
- thông báo trong ứng dụng
- khu vực admin cho danh mục, sản phẩm, đơn hàng, người dùng và thống kê

Nếu có điểm nào chưa chắc chắn, hãy xem frontend trong `../front` là nguồn tham chiếu chính về tính tương thích API.

## Contract Do Frontend Chi Phối

Trước khi thay đổi hành vi của backend, hãy đọc:
- `../front/src/services/api.js`
- các store liên quan trong `../front/src/stores`
- các view bị ảnh hưởng trong `../front/src/views`

Frontend hiện đang giả định rằng:
- API base mặc định là `http(s)://<hostname>:8000` nếu chưa set `VITE_API_BASE_URL`
- mọi response đều là JSON
- lỗi được trả qua field `detail`
- `401` có thể được phục hồi bằng `POST /auth/refresh`
- access token và refresh token được trả về dưới tên `access_token` và `refresh_token`
- đường dẫn ảnh có thể được resolve bằng cách nối với API base, ví dụ `/uploads/...`
- role của user có thể được đọc từ `user.role` hoặc `user.user_type_id`

Hãy giữ ổn định các giả định này, trừ khi frontend cũng được cập nhật trong cùng task.

## Bối Cảnh Sản Phẩm Và UX Từ Frontend

Ngôn ngữ storefront là tiếng Việt. Các nội dung backend trả về và đi thẳng ra UI nên bám cùng tông, đặc biệt là:
- tiêu đề và nội dung notification
- lỗi validation hiển thị trực tiếp trên giao diện
- thông điệp liên quan tới thanh toán và trạng thái đơn hàng

Giá tiền đang được hiển thị theo VND.
Các hạng thành viên mà UI hiện đang dùng là:
- `Member`
- `Silver`
- `Gold`
- `Platinum`
- `Diamond`

Favorites hiện chỉ là state localStorage ở frontend. Không thêm backend cho favorites nếu không có yêu cầu rõ ràng.

## Các Nhóm Endpoint Frontend Đang Dùng

### Auth và Hồ Sơ
- `POST /auth/login`
- `POST /auth/google`
- `POST /auth/register`
- `POST /auth/logout`
- `POST /auth/refresh`
- `GET /me`
- `PUT /me`
- `DELETE /me`
- `POST /me/avatar`
- `GET /me/membership`

### Danh Mục Sản Phẩm và Đánh Giá
- `GET /products`
- `GET /products/search`
- `GET /products/{id}`
- `GET /products/categories`
- `GET /products/{id}/reviews`
- `POST /products/{id}/reviews`

### Giỏ Hàng, Đơn Hàng, Thanh Toán, Thông Báo
- `GET /cart`
- `POST /cart/items`
- `PUT /cart/items/{item_id}`
- `DELETE /cart/items/{item_id}`
- `POST /orders`
- `GET /my-orders`
- `PUT /my-orders/{order_id}/confirm-received`
- `PUT /my-orders/{order_id}/cancel`
- `POST /payments/create-from-order/{order_id}`
- `GET /payments/order/{order_id}`
- `GET /payments/{transaction_code}/qr`
- `POST /payments/mock/{transaction_code}/paid`
- `GET /notifications/me`
- `PUT /notifications/{notification_id}/read`

### Admin
- `GET /admin/categories`
- `POST /admin/categories`
- `PUT /admin/categories/{category_id}`
- `DELETE /admin/categories/{category_id}`
- `GET /admin/products`
- `POST /admin/products`
- `PUT /admin/products/{product_id}`
- `DELETE /admin/products/{product_id}`
- `POST /admin/products/upload-image`
- `GET /admin/orders`
- `PUT /admin/orders/{order_id}/approve`
- `PUT /admin/orders/{order_id}/shipping`
- `PUT /admin/orders/{order_id}/cancel`
- `GET /admin/statistics`
- `GET /admin/users`
- `PUT /admin/users/{user_id}`

## Các Shape Dữ Liệu Frontend Đang Phụ Thuộc

### Danh sách sản phẩm và tìm kiếm
Frontend đang kỳ vọng response phân trang của sản phẩm có dạng:
- `items`
- `total`
- `page`
- `page_size`
- `total_pages`

Product card và trang chi tiết sản phẩm hiện dùng các field như:
- `id`
- `name`
- `price`
- `quantity`
- `category_id`
- `image1`
- `image2`
- `image3`
- `image_url`
- `description`
- `view_count`
- `purchased_count`

### Reviews
Frontend đang kỳ vọng response review sản phẩm có dạng:
- `items`
- `average_rating`
- `review_count`
- `can_review`
- `my_review`

Mỗi review item nên có:
- `id`
- `user_id`
- `product_id`
- `rating`
- `comment`
- `created_at`
- `updated_at`
- `user_name`
- `user_avatar`

### Orders
Checkout hiện gửi dữ liệu tạo đơn theo dạng:
- `shipping_address`
- `payment_method` thuộc `cod | qr`

Frontend đang kỳ vọng payload đơn hàng có:
- `id`
- `order_code`
- `shipping_address`
- `date_order`
- `status`
- `payment_method`
- `payment_status`
- `details`
- `latest_payment`

### Payments
Checkout QR đang phụ thuộc vào `latest_payment` và cơ chế polling trạng thái thanh toán.
Frontend hiện dùng các field như:
- `transaction_code`
- `provider`
- `amount`
- `status`
- `qr_payload`
- `expires_at`
- `image_data_url` từ endpoint QR

### Notifications
Notification store đang giả định notification mới nhất nằm ở đầu danh sách.
Nếu thứ tự này thay đổi thì flash notification và polling ở frontend sẽ hỏng.

## Các Enum Trạng Thái Cần Giữ Ổn Định

Order status mà frontend đang dùng:
- `pending`
- `approved`
- `shipping`
- `delivered`
- `cancelled`

Payment method mà frontend đang dùng:
- `cod`
- `qr`

Payment status mà frontend đang dùng:
- `unpaid`
- `pending`
- `paid`
- `failed`
- `expired`
- `cancelled`

Nếu đổi bất kỳ giá trị nào ở trên, phải cập nhật frontend tương ứng.

## Cấu Trúc Backend

- `app/main.py`: khởi tạo app, CORS, mount static uploads, patch schema lúc startup, seed role/permission, seed local admin
- `app/core`: config, database, security helpers
- `app/dependencies`: auth và các dependency kiểm tra quyền
- `app/models`: model SQLAlchemy và enum
- `app/schemas`: schema Pydantic cho input/output
- `app/routers`: bề mặt HTTP API
- `app/services`: business logic như auth, cart, product, order, payment, membership
- `app/utils`: helper nhỏ
- `tests`: test hiện có

Giữ router mỏng. Những business rule có thể tái sử dụng nên nằm trong `app/services` hoặc dependency, không nên nhét trực tiếp vào route handler.

## Các Quy Ước Quan Trọng Của Backend

### Thay đổi schema ở thời điểm startup
Project này hiện chưa dùng công cụ migration chính thức.
`app/main.py` đang áp dụng nhiều câu `ALTER TABLE` của PostgreSQL trong lúc app khởi động.

Nếu cần thêm field hoặc constraint mới vào database, hãy đi theo cách migration lúc startup đang có, trừ khi project được yêu cầu chuyển hẳn sang Alembic.

### Roles và permissions
Role đang được seed lúc startup gồm:
- admin
- customer

Permissions cũng được seed và đồng bộ lúc startup.
Ưu tiên kiểm tra quyền qua `app.dependencies.auth`.

### Uploads
Avatar và ảnh sản phẩm được phục vụ qua `/<UPLOAD_DIR>`.
Trong môi trường local, cách này ổn.
Trên các nền tảng free hosting, local file storage là tạm thời.
Không được giả định file upload sẽ còn nguyên sau mỗi lần redeploy ở production.

### Payments
QR payment là một phần của flow checkout đang dùng thật.
Mock payment chỉ hoạt động khi `ENABLE_MOCK_PAYMENTS=true`.
Polling thanh toán QR ở frontend phụ thuộc vào việc trạng thái thanh toán đổi đúng qua các enum đang được UI map sẵn.

## Phát Triển Local

Các lệnh thường dùng:

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Các biến môi trường quan trọng trong `.env` / `.env.example`:
- `DATABASE_URL`
- `SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `UPLOAD_DIR`
- `PAYMENT_PROVIDER`
- `PAYMENT_WEBHOOK_SECRET`
- `PAYMENT_EXPIRE_MINUTES`
- `ENABLE_MOCK_PAYMENTS`
- `GOOGLE_CLIENT_ID`
- `LOCAL_ADMIN_EMAIL`
- `LOCAL_ADMIN_PASSWORD`
- `CORS_ORIGINS`

Ứng dụng hiện có normalize `postgres://` và `postgresql://` sang format async SQLAlchemy mà runtime đang dùng.

## Testing Và Xác Minh

Test hiện tại còn khá nhẹ và nằm trong `tests/`.
Chúng chủ yếu cover:
- normalize config
- logic hạng thành viên

Nếu thay đổi các contract quan trọng, không được chỉ tin vào test hiện có.
Hãy kiểm tra thêm các store và view tương ứng ở frontend.

## Các Script Bảo Trì

Repository này cũng có các script vận hành riêng như:
- `import_lixibox_products.py`
- `refresh_lixibox_product_images.py`
- `sync_product_categories.py`
- `fix_all_passwords.py`

Hãy xem chúng là script vận hành, không phải một phần của request/response path chính của ứng dụng.

## Quy Tắc Thực Dụng Cho Các Thay Đổi Sau Này

- Không đổi tên hoặc xóa các field API mà frontend đang render, nếu frontend không được sửa cùng task.
- Không đổi enum của order hoặc payment nếu chưa cập nhật map label và các điều kiện UI ở frontend.
- Giữ danh sách notification theo thứ tự mới nhất trước.
- Giữ error message đủ cụ thể để có thể hiển thị trực tiếp lên UI.
- Giữ các field ảnh tương thích với `resolveAssetUrl` ở frontend.
- Giữ router gọn, chuyển business logic không tầm thường vào service.
- Nếu thay đổi ảnh hưởng tới checkout, payment, auth hoặc admin, hãy kiểm tra view frontend liên quan trước khi coi task là xong.
