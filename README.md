# Cosmetics Shop Backend

## Local Run

1. Create `.env` from `.env.example`
   - If your local Postgres password is not the sample value, update `DATABASE_URL`.
   - If you do not want Google login locally, leave `GOOGLE_CLIENT_ID` empty.
   - If the local database is empty, the app will seed `LOCAL_ADMIN_EMAIL` / `LOCAL_ADMIN_PASSWORD` on startup.
2. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Start the API:

```bash
uvicorn app.main:app --reload
```

The local `.env` should stay local-first. Keep Render or Neon values in the hosting dashboard instead of copying them back into your local file.

## Free Deploy

This backend is ready to deploy on a free Python host such as Render.

### Required environment variables

- `DATABASE_URL`
- `SECRET_KEY`
- `GOOGLE_CLIENT_ID` if Google login is enabled
- `CORS_ORIGINS`
- `CHATBOT_AI_API_KEY`, `CHATBOT_AI_BASE_URL`, `CHATBOT_AI_MODEL` if you want AI answers instead of DB-only fallback
- `CHATBOT_HOTLINE` if you want chatbot hand-off messages to include a hotline

## Chatbot

The backend now exposes a dedicated chatbot module:

- `POST /chatbot/messages`: standard response
- `POST /chatbot/messages/stream`: SSE streaming response
- `GET /chatbot/suggested-questions`: 5 sample prompts for the UI
- `POST /chatbot/messages/{message_id}/feedback`: helpful / not helpful feedback
- `GET|POST|PUT|DELETE /chatbot/admin/knowledge`: admin knowledge base management
- `GET /chatbot/admin/messages`: admin audit log feed

The chatbot is built from the scope in `chatbot.md`, reads product/order/payment data from the existing database, supports optional logged-in context, logs conversations for audit, and falls back to deterministic answers if no AI provider is configured.

### Render

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- A sample config is included in `render.yaml`

## Important Limitation

Uploaded files are stored in the local `uploads/` directory. On most free hosts, local storage is ephemeral, so uploaded avatars and product images can be lost after redeploy or restart. For stable production usage, move uploads to external storage such as Cloudinary, Supabase Storage, or S3-compatible storage.
