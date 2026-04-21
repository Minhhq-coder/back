# Checklist Deploy Ngắn Gọn: Vercel + Render + Neon

## 1. Chuẩn bị trước khi deploy

- [ ] Code đã chạy ổn ở máy local
- [ ] Frontend build được bằng `npm run build`
- [ ] Backend compile được bằng `python -m compileall app tests`
- [ ] Đã push code lên GitHub
- [ ] Đã có các file:
  - `C:\Users\minhhq\Desktop\front\.env.example`
  - `C:\Users\minhhq\Desktop\front\vercel.json`
  - `C:\Users\minhhq\Desktop\back\.env.example`
  - `C:\Users\minhhq\Desktop\back\render.yaml`

## 2. Tạo database trên Neon

- [ ] Vào [Neon](https://neon.com/pricing)
- [ ] Tạo project PostgreSQL mới
- [ ] Lấy connection string
- [ ] Đổi prefix sang `postgresql+asyncpg://` nếu cần
- [ ] Giữ lại URL dạng:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/DBNAME?ssl=require
```

## 3. Deploy backend trên Render

- [ ] Vào [Render](https://render.com/docs/free)
- [ ] Tạo `Web Service`
- [ ] Trỏ tới repo backend hoặc thư mục `back`
- [ ] Build command:

```bash
pip install -r requirements.txt
```

- [ ] Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Biến môi trường backend

- [ ] `DATABASE_URL`
- [ ] `SECRET_KEY`
- [ ] `CORS_ORIGINS`
- [ ] `DATABASE_ECHO=false`
- [ ] `GOOGLE_CLIENT_ID` nếu dùng Google login

### Kiểm tra backend

- [ ] Mở được `/`
- [ ] Mở được `/docs`
- [ ] Không lỗi kết nối database

## 4. Deploy frontend trên Vercel

- [ ] Vào [Vercel](https://vercel.com/docs/plans/hobby)
- [ ] Import repo frontend hoặc thư mục `front`
- [ ] Chọn framework `Vite`
- [ ] Build command:

```bash
npm run build
```

- [ ] Output directory:

```bash
dist
```

### Biến môi trường frontend

- [ ] `VITE_API_BASE_URL=https://your-backend.onrender.com`
- [ ] `VITE_GOOGLE_CLIENT_ID` nếu dùng Google login

### Kiểm tra frontend

- [ ] Trang chủ mở được
- [ ] Route con như `/shop`, `/orders`, `/account` không bị 404 khi refresh
- [ ] Frontend gọi đúng API backend

## 5. Nối lại frontend và backend

- [ ] Lấy domain frontend từ Vercel
- [ ] Quay lại Render
- [ ] Sửa:

```env
CORS_ORIGINS=https://your-frontend.vercel.app
```

- [ ] Redeploy backend
- [ ] Test lại toàn bộ luồng

## 6. Những luồng bắt buộc phải test

### Customer

- [ ] Đăng nhập
- [ ] Xem sản phẩm
- [ ] Thêm vào giỏ
- [ ] Đặt hàng
- [ ] Xem đơn hàng
- [ ] Sửa hồ sơ

### Admin

- [ ] Đăng nhập admin
- [ ] Quản lý danh mục
- [ ] Quản lý sản phẩm
- [ ] Quản lý đơn hàng
- [ ] Xem thống kê

## 7. Lưu ý rất quan trọng

- [ ] Backend hiện đang lưu ảnh trong thư mục local `uploads/`
- [ ] Trên Render free, file local có thể mất sau restart hoặc redeploy
- [ ] Nếu muốn ổn định hơn, nên chuyển sang:
  - Cloudinary
  - Supabase Storage
  - S3-compatible storage

## 8. Thứ tự deploy khuyến nghị

1. Tạo database trên Neon
2. Deploy backend lên Render
3. Deploy frontend lên Vercel
4. Cập nhật lại `CORS_ORIGINS`
5. Test toàn bộ website
