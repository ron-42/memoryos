# MemoryOS - Senior Implementation Spec for a Full-Stack Coding Agent

## How To Work

Read this document fully before writing code.

Before implementation, produce a written plan that covers:
- repository structure
- database schema and migrations
- auth flow across frontend, backend, and Supabase
- API routes with request and response contracts
- ingestion pipeline and failure handling
- frontend screen tree and shared state boundaries
- testing strategy and rollout order
- assumptions or scope cuts you are making

Then proceed autonomously unless a decision is genuinely blocked by missing product input.

Do not start with UI polish. Build in dependency order:
1. schema and migrations
2. backend skeleton and auth
3. ingestion pipeline
4. retrieval and chat
5. dashboard and graph APIs
6. frontend screens
7. background jobs and polish

If the repo already contains code, inspect it first and adapt this spec instead of blindly overwriting existing patterns.

---

## Product Summary

MemoryOS is a personal knowledge memory app. A user captures content from the internet or pasted text, the system extracts and enriches it, stores it as durable memory, and helps the user retrieve and connect what they have learned over time.

The emotional hook is progress:
- streaks
- XP
- topic growth
- surprising connections between past captures

This is not a generic notes app and not an ungrounded chatbot. The system should feel like a living memory layer built from the user's own captures.

Target users:
- curious professionals
- builders
- students
- researchers
- heavy content consumers who want retention and synthesis

---

## Product Scope

### V1 Must Ship
- capture from URL
- capture from pasted text
- capture from uploaded PDF
- content extraction and cleanup
- AI enrichment into summary, concepts, topic tags, and metadata
- semantic chunking and embeddings
- memory retrieval grounded only in the user's stored data
- dashboard with streak, XP, topics, and recent activity
- knowledge graph at topic level
- basic connection discovery between memories
- Google login via Supabase Auth

### V1 Nice To Have
- memory-level graph expansion
- realtime level-up toasts
- nightly reclustering
- "memory sparks" resurfacing old relevant captures

### Explicitly Out Of Scope For Initial Delivery
- browser extension
- collaborative workspaces
- public sharing
- OCR-heavy scanned PDF support
- generic web crawling
- multi-model orchestration

Senior engineering rule: ship a stable narrow product before adding intelligence layers that create operational drag.

---

## Core Product Principles

1. The backend never trusts `user_id` from the client.
2. All user-scoped reads and writes are derived from the authenticated Supabase JWT.
3. All APIs are async.
4. Streaming is required for long-running capture and chat flows.
5. External provider failures must degrade gracefully.
6. Every storage write should be idempotent where practical.
7. The app should remain useful even if connection discovery or clustering fails.
8. Retrieval must be grounded only in the authenticated user's memories.

---

## Non-Negotiable Stack

### Backend
- Python 3.11+
- FastAPI
- Supabase Python client
- `httpx`
- `python-dotenv`
- `PyMuPDF`
- `langchain-text-splitters`
- `openai` for embeddings only
- `google-generativeai` for enrichment and chat
- `apscheduler`
- `scikit-learn` for clustering if clustering is implemented in v1

### LLM
- Google Gemini 2.0 Flash
- Use structured JSON output for enrichment
- Add retry and backoff for rate limits and transient failures

### Embeddings
- OpenAI `text-embedding-3-small`
- dimension: 1536
- used for chunk retrieval and memory-level similarity

### Database
- Supabase Postgres
- `pgvector`
- RLS enabled on all user data tables
- Supabase Auth for Google OAuth

### Frontend
- Next.js 14 App Router
- TypeScript strict mode
- Tailwind CSS
- Zustand
- TanStack Query
- Framer Motion
- `react-force-graph`

### Hosting
- frontend on Vercel
- backend on Railway or Render
- database on Supabase

---

## Recommended Repository Layout

```text
memoryos/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── hooks/
│   └── styles/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── services/
│   │   ├── jobs/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── supabase/
│   └── migrations/
├── docs/
└── README.md
```

Use migrations, not hand-edited database state.

---

## Delivery Plan

### Phase 1 - Foundation
- create schema and RLS policies
- create backend app skeleton
- add config, logging, health check, auth dependency
- wire frontend auth with Supabase

### Phase 2 - Ingestion Backbone
- implement capture input modes
- implement content extraction
- implement enrichment, chunking, embeddings
- persist memory and chunk records
- stream progress to client

### Phase 3 - Retrieval And Core UX
- implement retrieval pipeline
- implement chat endpoint with grounded citations
- build capture screen, dashboard, memory list, memory detail

### Phase 4 - Connection And Graph Layer
- discover related memories
- aggregate topic graph data
- build graph screen
- add gamification surfaces

### Phase 5 - Background Jobs And Hardening
- nightly backfill jobs
- retries and observability
- tests for auth, ingestion, and retrieval
- deployment readiness

---

## Architecture Decisions

### Auth Model

Frontend uses Supabase Auth and sends the access token to the backend in the `Authorization` header.

Backend responsibilities:
- verify the JWT
- extract the current user id
- apply user scoping internally
- never accept `user_id` from request bodies for normal user actions

Service-role usage:
- allowed only for trusted server-side operations that need elevated access
- do not use service-role credentials for normal user-scoped API reads

### Capture Model

The product supports three capture inputs:
- URL
- pasted text
- PDF upload

Do not force all three through one ambiguous request shape. Separate them cleanly at the API layer.

### Topic Model

For v1, `topic_tags` produced during enrichment are the source of truth. The `topics` table is a derived aggregate per user.

Clustering is optional for initial launch. If implemented, it should refine discovery, not replace the user-visible topic model abruptly.

### Connection Model

Connection discovery should be best-effort:
- run a small synchronous pass after capture so the user sees immediate value
- run nightly backfill jobs for older unconnected memories

If connection generation fails, capture still succeeds.

---

## Data Flow

### URL Capture
1. authenticate request
2. detect source type
3. fetch and normalize content
4. validate minimum usable text length
5. enrich with Gemini
6. chunk content
7. embed chunks and memory summary
8. store memory and chunks in a transaction or logically idempotent sequence
9. update topics and XP
10. attempt lightweight connection discovery
11. stream completion payload

### Text Capture
1. authenticate request
2. normalize pasted text
3. enrich
4. chunk
5. embed
6. store
7. update topics and XP
8. stream completion payload

### PDF Capture
1. authenticate request
2. accept multipart upload
3. extract text with PyMuPDF
4. reject scanned or empty PDFs with a clear error
5. continue through the standard enrichment pipeline

### Chat
1. authenticate request
2. embed query
3. run dense retrieval
4. run keyword retrieval
5. fuse results
6. build grounded context
7. stream Gemini response
8. include citations to memory ids and titles

---

## Database Schema

Implement the schema below as the baseline. Add reasonable constraints and indexes where useful, but do not remove core product entities.

```sql
create extension if not exists vector;

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  display_name text,
  avatar_url text,
  total_xp integer not null default 0,
  current_streak integer not null default 0,
  longest_streak integer not null default 0,
  last_capture_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.memories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  source_type text not null,
  source_url text,
  source_title text,
  raw_content text not null,
  title text,
  summary text,
  key_concepts text[] not null default '{}',
  topic_tags text[] not null default '{}',
  content_type text,
  importance_score double precision,
  estimated_read_time integer,
  embedding vector(1536),
  xp_awarded integer not null default 0,
  enriched_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint memories_source_type_check
    check (source_type in ('article', 'pdf', 'tweet', 'reddit', 'text'))
);

create table public.chunks (
  id uuid primary key default gen_random_uuid(),
  memory_id uuid not null references public.memories(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  chunk_index integer not null,
  chunk_text text not null,
  embedding vector(1536),
  created_at timestamptz not null default now(),
  unique (memory_id, chunk_index)
);

create table public.topics (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  name text not null,
  memory_count integer not null default 0,
  total_xp integer not null default 0,
  level integer not null default 1,
  color text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, name)
);

create table public.connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  memory_a uuid not null references public.memories(id) on delete cascade,
  memory_b uuid not null references public.memories(id) on delete cascade,
  similarity_score double precision not null,
  connection_label text,
  discovered_at timestamptz not null default now(),
  constraint connections_not_same_memory check (memory_a <> memory_b)
);

create table public.xp_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  event_type text not null,
  xp_amount integer not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index idx_memories_user_id on public.memories(user_id);
create index idx_memories_created_at on public.memories(user_id, created_at desc);
create index idx_chunks_user_id on public.chunks(user_id);
create index idx_chunks_memory_id on public.chunks(memory_id);
create index idx_topics_user_id on public.topics(user_id);
create index idx_connections_user_id on public.connections(user_id);
create index idx_xp_events_user_id on public.xp_events(user_id);

create index idx_memories_topic_tags_gin on public.memories using gin (topic_tags);
create index idx_memories_key_concepts_gin on public.memories using gin (key_concepts);

create index idx_chunks_embedding_hnsw
  on public.chunks using hnsw (embedding vector_cosine_ops);

create index idx_memories_embedding_hnsw
  on public.memories using hnsw (embedding vector_cosine_ops);

alter table public.profiles enable row level security;
alter table public.memories enable row level security;
alter table public.chunks enable row level security;
alter table public.topics enable row level security;
alter table public.connections enable row level security;
alter table public.xp_events enable row level security;

create policy "profiles_select_own"
  on public.profiles for select using (auth.uid() = id);
create policy "profiles_update_own"
  on public.profiles for update using (auth.uid() = id);

create policy "memories_own_all"
  on public.memories for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "chunks_own_all"
  on public.chunks for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "topics_own_all"
  on public.topics for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "connections_own_all"
  on public.connections for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "xp_events_own_all"
  on public.xp_events for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
```

### Required Schema Notes
- store `updated_at` on mutable tables
- add application-level canonical ordering for `memory_a` and `memory_b` before insert
- add a unique index on `(user_id, memory_a, memory_b)` after canonical ordering is enforced
- create a Postgres full-text index on `chunks.chunk_text` if keyword search is implemented
- if using triggers for `updated_at`, keep them consistent across tables

---

## Supabase RPC

Use a vector match function for chunk retrieval:

```sql
create or replace function public.match_chunks(
  query_embedding vector(1536),
  match_user_id uuid,
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  memory_id uuid,
  chunk_text text,
  similarity float
)
language sql
stable
as $$
  select
    c.id,
    c.memory_id,
    c.chunk_text,
    1 - (c.embedding <=> query_embedding) as similarity
  from public.chunks c
  where c.user_id = match_user_id
    and 1 - (c.embedding <=> query_embedding) >= match_threshold
  order by c.embedding <=> query_embedding
  limit match_count;
$$;
```

Do not name a function argument `user_id` if a table column already uses that name and could confuse SQL readability.

---

## Backend Structure

```text
backend/
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   ├── capture.py
│   │   ├── memories.py
│   │   ├── chat.py
│   │   ├── graph.py
│   │   ├── topics.py
│   │   └── stats.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── security.py
│   ├── db/
│   │   └── supabase.py
│   ├── models/
│   │   ├── capture.py
│   │   ├── chat.py
│   │   ├── graph.py
│   │   └── memory.py
│   ├── services/
│   │   ├── fetcher.py
│   │   ├── enrichment.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   ├── repository.py
│   │   ├── retriever.py
│   │   ├── connections.py
│   │   ├── topics.py
│   │   └── gamification.py
│   ├── jobs/
│   │   └── scheduler.py
│   └── main.py
├── tests/
└── requirements.txt
```

Keep routers thin. Push provider calls and business rules into services.

---

## API Contracts

All authenticated endpoints require:

```http
Authorization: Bearer <supabase_access_token>
```

### `POST /capture/url`

Request:
```json
{
  "url": "https://example.com/article"
}
```

Response:
- SSE stream of progress events

Event shape:
```json
{
  "type": "progress",
  "stage": "fetching",
  "message": "Reading content"
}
```

Final event:
```json
{
  "type": "completed",
  "memory_id": "uuid",
  "xp_awarded": 30,
  "topics_updated": ["AI/ML"],
  "connections_found": 2
}
```

### `POST /capture/text`

Request:
```json
{
  "text": "user pasted content",
  "title": "optional title"
}
```

Response:
- SSE stream matching the URL capture event model

### `POST /capture/pdf`

Request:
- `multipart/form-data`
- file field: `file`

Response:
- SSE stream matching the URL capture event model

### `GET /memories`

Query params:
- `cursor`
- `limit`
- `topic`
- `content_type`
- `q`

Returns paginated user memories.

### `GET /memories/{memory_id}`

Returns:
- memory detail
- related connections
- topic tags
- selected chunks if needed for detail view

### `POST /chat`

Request:
```json
{
  "query": "What do I know about retrieval augmented generation?"
}
```

Response:
- SSE token stream from Gemini
- final citation payload referencing memory ids and titles

### `GET /graph`

Returns topic-level graph data:
```json
{
  "nodes": [
    {
      "id": "AI/ML",
      "label": "AI/ML",
      "level": 4,
      "memory_count": 12,
      "color": "#4F46E5"
    }
  ],
  "edges": [
    {
      "source": "AI/ML",
      "target": "Startups",
      "strength": 0.71
    }
  ]
}
```

### `GET /topics`

Returns per-topic progress cards for the current user.

### `GET /stats`

Returns:
- current streak
- longest streak
- total XP
- XP today
- recent captures
- recent connections

---

## Enrichment Contract

Gemini enrichment should return normalized JSON like:

```json
{
  "title": "string",
  "summary": "2-3 sentence summary",
  "key_concepts": ["string"],
  "topic_tags": ["AI/ML", "Startups"],
  "content_type": "technical",
  "importance_score": 7.5,
  "estimated_read_time": 8
}
```

Rules:
- maximum 8 `key_concepts`
- maximum 3 `topic_tags`
- `topic_tags` should be broad and reusable, not hyper-specific
- `content_type` must be one of `technical`, `opinion`, `research`, `news`, `tutorial`
- if enrichment partially fails, store the memory with safe fallbacks instead of dropping the capture

---

## Ingestion Rules

### Source Detection
- `twitter.com` or `x.com` -> social content path
- `reddit.com` -> Reddit content path
- `.pdf` or `application/pdf` -> PDF extraction path
- everything else -> reader fallback path

### Extraction Strategy
- use the cleanest text source available
- normalize whitespace aggressively
- preserve headings and paragraph boundaries where possible
- reject captures that remain too short after cleanup

### Idempotency

At minimum, prevent obvious duplicate URL captures for the same user within a reasonable window.

Preferred approach:
- normalize URL
- hash normalized URL plus user id
- check for an existing recent memory before creating a new one

Do not make the dedupe system so aggressive that it blocks intentional re-captures after content changes.

---

## Retrieval Strategy

Use a pragmatic hybrid pipeline for v1:

1. embed the user query
2. dense search through `match_chunks`
3. keyword search through Postgres full-text search on chunks
4. merge using reciprocal rank fusion
5. pick the top results
6. build a grounded prompt with chunk excerpts and memory metadata
7. stream Gemini response with citations

Do not add a cross-encoder reranker unless performance and latency remain acceptable after measurement. It is optional, not foundational.

The answer must:
- stay grounded in retrieved memories
- cite source memories clearly
- avoid pretending knowledge outside stored data

---

## Connection Discovery

Immediate discovery after capture:
- compare the new memory embedding against the user's nearest existing memories
- examine top 5 candidates
- require a similarity threshold, for example `> 0.75`
- skip same-source duplicates
- skip already-linked pairs

If a candidate passes:
- ask Gemini for a one-line explanation of the connection
- insert a canonical pair into `connections`

Nightly backfill:
- scan older memories with few or no links
- run the same logic in batches

Connection discovery is best-effort. Capture success must not depend on it.

---

## Gamification

### XP Rules

```text
Capture article or tweet: 20 XP
Capture YouTube video:    30 XP
Capture PDF or paper:     50 XP
Connection discovered:    15 XP each
Daily chat session:       10 XP
7-day streak bonus:       100 XP
Topic level-up bonus:     50 XP
```

### Topic Levels

```text
Level 1: 0
Level 2: 50
Level 3: 150
Level 4: 300
Level 5: 500
Level 6: 800
Level 7: 1200
Level 8: 1800
Level 9: 2600
Level 10: 3500
```

### Streak Rules
- if the user captures at least one memory today, today counts as active
- if the previous capture was yesterday, increment streak
- if there was a gap of more than one day, reset streak to 1 on the next successful capture
- update `longest_streak` when appropriate

Persist every XP change in `xp_events`.

---

## Frontend Product Direction

Keep the interface dark, focused, and premium. Avoid noisy dashboards and generic startup gradients.

### Design Rules
- background near-black
- restrained accent color
- high contrast typography
- generous spacing
- motion only where it explains progress or reward
- no component-library look

### App Routes

```text
app/
├── page.tsx
├── (auth)/
│   └── login/page.tsx
├── (app)/
│   ├── layout.tsx
│   ├── home/page.tsx
│   ├── capture/page.tsx
│   ├── graph/page.tsx
│   ├── memories/page.tsx
│   ├── memories/[id]/page.tsx
│   └── chat/page.tsx
```

### Screen Priorities

#### Home
- streak front and center
- XP today
- top topics with progress bars
- recent captures
- recent connections
- quick capture input

#### Capture
- single obvious input area
- support URL, pasted text, and PDF upload
- live progress feed from SSE
- success state showing XP, topics, and discovered connections

#### Memories
- searchable list or grid
- filters by topic and content type
- clean detail page with summary, concepts, and related memories

#### Chat
- grounded memory chat
- citations always visible
- desktop split view: answer and sources

#### Graph
- topic-level graph first
- hover details
- click-through into filtered memories or chat

---

## Background Jobs

### Connection Backfill
- run nightly
- process users in batches
- skip users with too little data

### Topic Rebuild
- recompute topic aggregates nightly or after meaningful write events
- if clustering exists, only run it for users with enough memories to avoid noisy output

Do not make APScheduler the only source of truth for correctness. Core aggregates should still be correct after synchronous write paths.

---

## Error Handling Standards

Never return opaque provider errors directly to the UI.

Handle these cases explicitly:
- article fetch failed
- transcript unavailable
- PDF had no extractable text
- Gemini timeout or rate limit
- embedding provider failure
- malformed Supabase response
- SSE stream interrupted mid-run

Preferred behavior:
- emit a clear stage-specific error event
- preserve partial progress if safe
- log enough detail for debugging without leaking secrets

---

## Testing Requirements

Minimum required tests:
- auth dependency rejects missing or invalid tokens
- user A cannot access user B data
- URL capture persists memory and chunks
- failed enrichment falls back safely
- retrieval only returns current user's chunks
- streak logic handles same-day, next-day, and skipped-day cases
- connection inserts avoid duplicate pairs

If time is limited, prioritize backend correctness tests over UI snapshot tests.

---

## Environment Variables

```bash
# Supabase
SUPABASE_URL=
SUPABASE_SECRET_KEY=

# OpenAI embeddings
OPENAI_API_KEY=

# Gemini
GEMINI_API_KEY=

# Frontend
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Do not hardcode secrets, environment-specific URLs, or provider model names in arbitrary files.

---

## Acceptance Criteria

The implementation is acceptable only if all of the following are true:
- a user can sign in with Google
- a user can capture a URL, text, and PDF
- capture streams progress to the UI
- memory records, chunks, topics, and XP events are stored correctly
- chat answers only from the user's own memories and cites them
- graph and dashboard load meaningful real data
- the system behaves sanely when one provider fails
- another user cannot read or query someone else's memories

---

## Final Build Guidance

- choose reliability over novelty
- simplify before abstracting
- keep provider boundaries isolated
- do not mix auth concerns into business logic everywhere
- avoid premature microservices or queue infrastructure
- build the ingestion backbone first because every major feature depends on it

If you need to cut scope to ship, cut advanced discovery and visual flourish before you cut correctness, auth, or retrieval quality.
