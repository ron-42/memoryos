# MemoryOS

MemoryOS is a personal knowledge memory app with a FastAPI backend, Next.js frontend, a local SQLite metadata store, and Pinecone for dense vector search.

## Current State

This repo is currently set up as a single-user weekend project:
- one fixed local project user
- SQLite for relational metadata
- Pinecone for dense chunk retrieval
- no frontend login flow

## Structure

```text
frontend/   Next.js application
backend/    FastAPI application
docs/       implementation notes
```

## Environment Files

- backend config lives in `backend/.env`
- frontend config lives in `frontend/.env.local`
- starter templates are `backend/.env.example` and `frontend/.env.local.example`
- backend uses a local SQLite database file for metadata
- backend also uses Pinecone credentials for vector search
- frontend only needs the API URL

## Project Scope

This is intentionally narrowed for a weekend build:
- no user auth or session handling
- one fixed local project user on the backend
- SQLite only for relational metadata
- Pinecone for dense vector search
- capture scope limited to article URLs, PDFs, and pasted text

## Local Setup

### Backend

1. Create and activate a virtualenv in `backend/`.
2. Install dependencies:

```bash
cd backend
uv pip install -r requirements.txt
```

3. Add config to `backend/.env`, including:

```bash
DATABASE_PATH=data/memoryos.db
PINECONE_API_KEY=...
PINECONE_INDEX_HOST=...
PINECONE_NAMESPACE=memoryos
OPENAI_API_KEY=...
GEMINI_API_KEY=...
```

4. Start the API:

```bash
cd backend
uv run python scripts/init_db.py
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

1. Put frontend config in `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

2. Install and run:

```bash
cd frontend
npm install
npm run dev
```
