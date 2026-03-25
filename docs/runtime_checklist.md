# Runtime Checklist

## Before First Run

- copy `backend/.env.example` to `backend/.env`
- copy `frontend/.env.local.example` to `frontend/.env.local`
- fill `DATABASE_PATH` in `backend/.env`
- fill Pinecone API key and index host in `backend/.env`
- fill OpenAI and Gemini API keys in `backend/.env`
- install backend dependencies from `backend/requirements.txt`
- install frontend dependencies from `frontend/package.json`

## Backend

- run `uv run python scripts/init_db.py` from `backend/` if you want to create the SQLite file before first boot
- run the API with `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` from `backend/`
- verify `GET /health`
- verify scheduler startup logs if `SCHEDULER_ENABLED=true`

## Frontend

- run `npm install`
- run `npm run dev` from `frontend/`
- confirm `NEXT_PUBLIC_API_URL` points to the backend

## Functional Checks

- capture URL, text, and PDF
- confirm SSE progress updates appear on the capture screen
- open the memories list and a memory detail page
- ask a chat question and confirm citations render
- confirm home dashboard stats populate
- confirm graph nodes and edges populate after multiple captures

## Nightly Jobs

- verify connection backfill runs at `CONNECTION_BACKFILL_HOUR_UTC`
- verify topic maintenance runs at `TOPIC_MAINTENANCE_HOUR_UTC`
- confirm logs show job completion counts
