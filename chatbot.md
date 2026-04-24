# Chatbot - Các câu hỏi cần trả lời trước khi build

Tài liệu này dùng để chốt scope cho chatbot trước khi code. Bạn không cần trả lời quá dài, nhưng mỗi câu nên có câu trả lời cụ thể.

## 1. Mục tiêu kinh doanh

1. Chatbot này được tạo ra để giải quyết vấn đề gì? để tư vấn và trả lời các câu hỏi của khách hàng về sản phẩm, chính sách, hỗ trợ đặt hàng, hỗ trợ sau mua hàng
2. Mục tiêu chính là:
   - trả lời thông tin sản phẩm
   - trả lời chính sách
   - hỗ trợ đặt hàng
   - hỗ trợ sau mua hàng
   - giảm tải cho CSKH
   - tăng tỷ lệ chuyển đổi
3. Thành công được đo bằng chỉ số nào? được đo bằng số lượt user hỏi và chatbot trả lời thành công
4. Nếu chatbot không tồn tại, hiện tại team đang xử lý như thế nào? chưa có phương án xử lí
5. Chatbot này ưu tiên trả lời nhanh hay trả lời chính xác tối đa? trả lời chính xác tối đa

## 2. Người dùng và tình huống sử dụng

1. Người sẽ dùng chatbot là ai? là khách hàng 
2. Họ thường hỏi những gì? tất cả những điều có trong database, sản phẩm, chính sách, hỗ trợ đặt hàng, hỗ trợ sau mua hàng, về đơn hàng cụ thể của user, tư vấn theo nhu cầu của khách hàng
3. Những câu hỏi nào xuất hiện nhiều nhất? ví dụ : giá sản phẩm , da dầu, da mụn thì nên sử dụng sản phẩm gì
4. Người dùng đang ở giai đoạn nào:
   - trước khi mua 
   - đang mua
   - sau khi mua
5. Chatbot sẽ xuất hiện ở đâu:
   - website public
6. Chatbot có cần biết user đang đăng nhập hay không?
- có nhé

## 3. Phạm vi trả lời

1. Chatbot được phép trả lời những nhóm thông tin nào?
được trả lời tất cả các thông tin về sản phẩm và tư vấn
2. Chatbot không được phép trả lời những gì?
không được trả lời những tôi tin về tài khoản mật khẩu, những vấn đề bảo mật
3. Chatbot có được phép tư vấn sản phẩm hay chỉ được trích xuất thông tin có sẵn?
được tư vấn nhé
4. Chatbot có được phép gợi ý sản phẩm theo nhu cầu user không? có
5. Chatbot có được phép trả lời về đơn hàng cụ thể của user không? có
6. Chatbot có được phép tạo hành động hay không:
   - thêm vào giỏ hàng có
   - tạo đơn: không
   - hủy đơn: không
   - kiểm tra thanh toán: có
7. Khi không chắc chắn, chatbot phải:
   - xin thêm thông tin
   - chuyển người thật

## 4. Nguồn dữ liệu

1. Chatbot sẽ đọc dữ liệu từ đâu?
từ những nguồn dữ liệu hiện có
2. Các nguồn dữ liệu hiện có gồm:
   - bảng sản phẩm trong database
   - danh mục
   - bài viết / blog
   - FAQ
   - chính sách giao hàng
   - chính sách đổi trả
   - hướng dẫn thanh toán
   - nội dung trang web tĩnh
3. Nguồn nào là nguồn sự thật cao nhất khi có mâu thuẫn?
cơ sở dữ liệu, tiếp theo là bảng sản phẩm, tiếp theo là trang web tĩnh
4. Dữ liệu nào đã có trong database?
các dữ liệu về thông tin sản phẩm
5. Dữ liệu nào chỉ nằm trên website HTML? chính sách,mục giới thiệu, liên hệ
6. Dữ liệu có cần đồng bộ định kỳ vào database hay vector store không? có
7. Ai sẽ cập nhật nội dung khi chính sách thay đổi? admin
8. Tần suất cập nhật dữ liệu là bao lâu? mỗi tuần

## 5. Kiến trúc trả lời

1. Chatbot sẽ trả lời theo cách nào?
   - kết hợp nhiều cách
2. Có cần lưu lịch sử hội thoại không? không cần thiết, 
3. Có cần nhớ context trong 1 phiên chat không? có 
4. Có cần nhớ thông tin user giữa nhiều phiên không? không
5. Khi user hỏi về sản phẩm, chatbot có cần trả về: có
   - tên sản phẩm
   - giá
   - tồn kho
   - mô tả
   - hình ảnh
   - link sản phẩm
6. Khi user hỏi về chính sách, chatbot có cần đưa kèm link nguồn không? có
7. Chatbot có cần trả lời bằng tiếng Việt, tiếng Anh, hay cả hai? trả lời tiếng việt

## 6. Tích hợp AI

1. Bạn muốn dùng model nào? model nào miễn phí thì càng tốt
2. Bạn ưu tiên:
   - chi phí thấp
3. Chatbot có cần streaming không? có
4. Có cần fallback sang model khác khi lỗi không? hiện tại chưa cần
5. Có cần giới hạn độ dài câu trả lời không? có giới hạn 100 từ
6. Có cần prompt hệ thống riêng cho thương hiệu không?không
7. Chatbot có cần giữ văn phong:
   - tư vấn như nhân viên bán hàng
## 7. Bảo mật và quy tắc an toàn

1. Chatbot có được truy cập thông tin cá nhân không?
không
2. Chatbot có được đọc thông tin đơn hàng của user không?
có nhưng chỉ được đọc thông tin của tài khoản đó đăng nhập thôi
3. Nếu có, làm sao xác thực đúng user? khi user đăng nhập thì chatbot sẽ biết được user đó là ai
4. Có thông tin nào tuyệt đối không được đưa vào prompt không? không
5. Chatbot có được tiết lộ logic nội bộ, token, API key, hay dữ liệu admin không? không
6. Khi gặp câu hỏi nhạy cảm, chatbot phải xử lý như thế nào? thông báo vi phạm chính sách phát ngôn của website
7. Có cần log lại câu hỏi và câu trả lời để audit không? có

## 8. Hand-off sang người thật

1. Khi nào chatbot phải chuyển sang nhân viên thật?
2. Chuyển bằng cách nào:
   - hiện số hotline
3. Có cần lưu lý do chat không giải quyết được không? hiện tại chưa cần
4. Có cần đánh dấu các câu hỏi chatbot trả lời sai để cải tiến sau không? hiện chưa cần

## 9. API và frontend

1. Frontend sẽ gọi endpoint nào? sẽ có 1 endpoint riêng để gọi chatbot
2. Cần request/response như thế nào?
3. Có cần gửi kèm metadata không:
   - user_id: có
   - session_id: có
   - page hiện tại: không cần
   - product_id hiện tại: có
4. Có cần nút gợi ý câu hỏi mẫu không? có 5 câu
5. Có cần hiển thị nguồn tham khảo trong UI không? có cần
6. Có cần rating "có hữu ích / không hữu ích" cho từng câu trả lời không? có cần

## 10. Vận hành và đo lường

1. Ai sẽ theo dõi chatbot sau khi release? sau khi release sẽ theo dõi trong 1-2 tuần đầu 
2. Cần đo những metric nào:
   - số lượt chat
   - tỷ lệ trả lời thành công
   - tỷ lệ chuyển người thật
   - tỷ lệ user hỏi lại cùng một vấn đề
   - số câu trả lời sai
3. Có cần dashboard hay báo cáo định kỳ không? chưa cần
4. Có cần cảnh báo khi chatbot lỗi hoặc API AI fail không? có cần

## 11. Quyết định kỹ thuật cần chốt

1. Bạn muốn build nhanh bản đầu hay build đúng kiến trúc mở rộng ngay từ đầu? build đúng kiến trúc mở rộng ngay từ đầu
2. Chatbot sẽ là:
   - module trong backend hiện tại
3. Dữ liệu cho chatbot sẽ nằm ở đâu:
   - đọc trực tiếp DB hiện tại
   - bảng knowledge_base riêng
   - file JSON/Markdown
   - vector database
4. Có cần job đồng bộ nội dung website vào hệ thống không? không
5. Có cần tạo admin page để quản lý FAQ/nội dung chatbot không? có thì tốt , hiện luôn tại tài khoản của admin

## 12. Các câu hỏi bắt buộc phải trả lời trước khi code

Nếu muốn bắt đầu nhanh, tối thiểu bạn cần chốt 12 câu này:

1. Chatbot dùng để làm gì? hỗ trợ khách hàng
2. Chatbot được phép trả lời những gì? trả lời những câu hỏi liên quan đến sản phẩm và chính sách
3. Chatbot không được phép trả lời những gì? không được trả lời những câu hỏi nhạy cảm hoặc không liên quan đến sản phẩm
4. Nguồn dữ liệu chính là gì? các bảng trong database
5. Dữ liệu đang nằm trong DB hay nằm trên website? DB và cả wensite nữa
6. Chatbot có cần đọc thông tin đơn hàng/user đang đăng nhập không? có 
7. Có cần lưu lịch sử hội thoại không? có 
8. Cần tiếng Việt hay đa ngôn ngữ? tiếng việt
9. Cần trả lời có link nguồn hay không? có 
10. Khi chatbot không biết thì phải làm gì? sẽ thông báo vi phạm chính sách phát ngôn của website
11. Frontend sẽ gọi endpoint nào? 
12. Ai là người cập nhật dữ liệu và kiểm tra câu trả lời sai? admin

## 13. Mẫu trả lời ngắn gọn

Bạn có thể copy mẫu dưới đây và điền nhanh:

```md
## Mục tiêu
- Chatbot dùng để:
- KPI chính:

## Người dùng
- Đối tượng chính:
- Các câu hỏi phổ biến:

## Phạm vi
- Được phép trả lời:
- Không được phép trả lời:

## Dữ liệu
- Nguồn dữ liệu chính:
- Dữ liệu nằm trong:
- Tần suất cập nhật:

## Tích hợp
- Model AI:
- Có lưu lịch sử không:
- Có cần link nguồn không:

## Bảo mật
- Có đọc dữ liệu user/đơn hàng không:
- Cách xác thực:

## Hand-off
- Khi nào chuyển người thật:
- Cách chuyển:

## Kỹ thuật
- Làm chung backend hay tách service:
- Endpoint dự kiến:
```

## 14. Gợi ý cách làm cho case hiện tại

Với repo hiện tại, cách khởi đầu an toàn nhất thường là:

1. Phase 1: chatbot chỉ trả lời từ dữ liệu sản phẩm + FAQ + chính sách
2. Phase 2: thêm context theo trang đang xem, ví dụ `product_id` hoặc `current_page`
3. Phase 3: nếu cần, mới thêm lịch sử hội thoại, đơn hàng user, và hand-off sang người thật

Nếu bạn trả lời xong file này, lúc đó mới dễ quyết định:

- có cần RAG hay không
- có cần vector database hay không
- có cần project riêng hay chỉ là module trong backend
- endpoint và database schema nên thiết kế thế nào
