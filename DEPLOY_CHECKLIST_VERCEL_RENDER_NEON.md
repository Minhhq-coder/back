# Deploy Checklist: Vercel + Render + Neon

Tai lieu nay dung cho bo stack hien tai:

- Frontend: Vite + Vue, deploy tren Vercel
- Backend: FastAPI, deploy tren Render
- Database: PostgreSQL, dung Neon Free

## 1. Tong quan kien truc

- Frontend public: Vercel
- Backend API public: Render
- Database PostgreSQL: Neon

Ket noi:

1. Frontend goi API qua `VITE_API_BASE_URL`
2. Backend ket noi PostgreSQL qua `DATABASE_URL`
3. Backend CORS chi mo cho domain frontend

## 2. Viec can xong truoc khi deploy

- [ ] Frontend build thanh cong bang `npm run build`
- [ ] Backend compile thanh cong bang `python -m compileall app tests`
- [ ] Da co file env mau:
  - `C:\Users\minhhq\Desktop\front\.env.example`
  - `C:\Users\minhhq\Desktop\back\.env.example`
- [ ] Da co file deploy config:
  - `C:\Users\minhhq\Desktop\front\vercel.json`
  - `C:\Users\minhhq\Desktop\back\render.yaml`
- [ ] Code da push len GitHub

## 3. Deploy database tren Neon

### Tao project

1. Vao `https://neon.com/`
2. Dang ky / dang nhap
3. Tao project moi
4. Chon region gan nguoi dung nhat
5. Lay connection string PostgreSQL

### Chuyen connection string cho backend hien tai

Backend dang dung SQLAlchemy async + `asyncpg`, vi vay `DATABASE_URL` nen co dang:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/DBNAME?ssl=require
```

Neu Neon cung cap URL dang `postgresql://...` thi doi prefix thanh:

- tu `postgresql://`
- thanh `postgresql+asyncpg://`

### Kiem tra nhanh

- [ ] Co `HOST`
- [ ] Co `DBNAME`
- [ ] Co `USER`
- [ ] Co `PASSWORD`
- [ ] Co `?ssl=require`

## 4. Deploy backend tren Render

### Tao Web Service

1. Vao `https://render.com/`
2. Chon `New` -> `Web Service`
3. Ket noi GitHub repo chua backend
4. Neu repo tach rieng cho backend:
   - root directory de trong
5. Neu monorepo:
   - dat root directory la thu muc `back`

### Cau hinh service

- Runtime: `Python`
- Build Command:

```bash
pip install -r requirements.txt
```

- Start Command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

- Plan: `Free`

### Environment variables can them

Toi thieu:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/DBNAME?ssl=require
SECRET_KEY=mot-secret-key-rat-dai-va-kho-doan
CORS_ORIGINS=https://your-frontend.vercel.app
DATABASE_ECHO=false
```

Neu bat Google login:

```env
GOOGLE_CLIENT_ID=your_google_client_id
```

Neu dung QR/payment:

```env
PAYMENT_PROVIDER=mock_qr
PAYMENT_WEBHOOK_SECRET=change-payment-webhook-secret
PAYMENT_EXPIRE_MINUTES=15
```

Neu muon doi thu muc upload:

```env
UPLOAD_DIR=uploads
```

### Sau khi deploy backend

1. Mo URL Render
2. Kiem tra:
   - `/`
   - `/docs`
3. Dam bao app len duoc khong loi `DATABASE_URL`

### Kiem tra nhanh backend

- [ ] Render build pass
- [ ] Render start pass
- [ ] URL `/docs` mo duoc
- [ ] API `GET /` tra response

## 5. Deploy frontend tren Vercel

### Tao project

1. Vao `https://vercel.com/`
2. Chon `Add New` -> `Project`
3. Ket noi GitHub repo chua frontend
4. Neu repo tach rieng cho frontend:
   - root directory de trong
5. Neu monorepo:
   - dat root directory la `front`

### Cau hinh project

- Framework Preset: `Vite`
- Build Command:

```bash
npm run build
```

- Output Directory:

```bash
dist
```

### Environment variables can them

```env
VITE_API_BASE_URL=https://your-backend.onrender.com
```

Neu bat Google login:

```env
VITE_GOOGLE_CLIENT_ID=your_google_client_id
```

### SPA rewrite

Project da co san file:

- `C:\Users\minhhq\Desktop\front\vercel.json`

File nay giup route Vue nhu `/shop`, `/orders`, `/account` khong bi 404 khi refresh trang.

### Sau khi deploy frontend

1. Mo URL Vercel
2. Kiem tra:
   - trang chu
   - shop
   - login
   - refresh tren route con

### Kiem tra nhanh frontend

- [ ] Build pass
- [ ] Mo trang chu duoc
- [ ] Refresh route con khong 404
- [ ] Goi API dung URL backend

## 6. Noi lai backend va frontend

Sau khi da co domain that:

1. Lay domain frontend tu Vercel
2. Quay lai Render
3. Sua:

```env
CORS_ORIGINS=https://your-frontend.vercel.app
```

Neu co nhieu origin:

```env
CORS_ORIGINS=https://your-frontend.vercel.app,https://www.yourdomain.com
```

4. Redeploy backend
5. Test lai frontend

## 7. Cau hinh Google login neu can

1. Vao Google Cloud Console
2. Tao `OAuth Client ID` loai `Web application`
3. Them Authorized JavaScript Origins:
   - `http://localhost:5173`
   - `https://your-frontend.vercel.app`
4. Lay `Client ID`
5. Dat:
   - `GOOGLE_CLIENT_ID` cho backend
   - `VITE_GOOGLE_CLIENT_ID` cho frontend

## 8. Cac luong can test sau deploy

### Customer

- [ ] Dang ky
- [ ] Dang nhap
- [ ] Dang nhap Google
- [ ] Xem san pham
- [ ] Them vao gio
- [ ] Dat hang
- [ ] Xem don hang
- [ ] Sua ho so

### Admin

- [ ] Dang nhap admin
- [ ] Quan ly danh muc
- [ ] Quan ly san pham
- [ ] Quan ly don hang
- [ ] Xem thong ke
- [ ] Quan ly tai khoan

### He thong

- [ ] Upload avatar
- [ ] Upload anh san pham
- [ ] Notification
- [ ] Review / rating
- [ ] Membership card

## 9. Gioi han cua host mien phi

### Render Free

- Service co the sleep khi idle
- Request dau tien sau idle co the cham
- Filesystem local la tam thoi

### Neon Free

- Tot cho hobby/demo
- Khong nen coi la production cap cao

### Vercel Hobby

- Phu hop frontend hobby/personal
- Can dat dung env production

## 10. Canh bao quan trong cua du an hien tai

Backend dang luu file upload o local:

- `C:\Users\minhhq\Desktop\back\uploads`

Dieu nay co nghia la:

- tren may local: van on
- tren Render free: avatar va anh san pham co the mat sau restart / redeploy / spin-down

Neu muon chay on dinh hon, can doi sang:

- Cloudinary
- Supabase Storage
- S3-compatible storage

## 11. Thu tu deploy de xac suat loi thap nhat

1. Deploy Neon
2. Lay `DATABASE_URL`
3. Deploy Render backend voi `DATABASE_URL`
4. Lay URL backend Render
5. Deploy Vercel frontend voi `VITE_API_BASE_URL`
6. Lay URL frontend Vercel
7. Quay lai Render sua `CORS_ORIGINS`
8. Redeploy backend
9. Test full flow

## 12. Bien moi truong mau de dien nhanh

### Backend

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/DBNAME?ssl=require
SECRET_KEY=replace-with-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
UPLOAD_DIR=uploads
PAYMENT_PROVIDER=mock_qr
PAYMENT_WEBHOOK_SECRET=change-payment-webhook-secret
PAYMENT_EXPIRE_MINUTES=15
GOOGLE_CLIENT_ID=
DATABASE_ECHO=false
CORS_ORIGINS=https://your-frontend.vercel.app
```

### Frontend

```env
VITE_API_BASE_URL=https://your-backend.onrender.com
VITE_GOOGLE_CLIENT_ID=
```

## 13. Link tai lieu chinh thuc

- Vercel Hobby: https://vercel.com/docs/plans/hobby
- Render Free Deploy: https://render.com/docs/free
- Neon Pricing: https://neon.com/pricing
- Supabase Free Plan: https://supabase.com/docs/guides/platform/billing-on-supabase
