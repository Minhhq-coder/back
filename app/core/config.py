import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/cosmetics_db")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "mock_qr")
PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "change-payment-webhook-secret")
PAYMENT_EXPIRE_MINUTES = int(os.getenv("PAYMENT_EXPIRE_MINUTES", "15"))
