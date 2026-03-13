# Architecture Notes
### AI-Assisted Journal System

*My thoughts on scaling, rate limits, caching, and security.*

---

## 1. How would I scale this to 100k users?

The current setup uses SQLite with a single FastAPI process. That works fine for development, but SQLite only allows one writer at a time — so under real traffic it becomes a bottleneck fast.

**Database**
- Replace SQLite with **PostgreSQL** — handles concurrent reads/writes, supports connection pooling via PgBouncer, and can add read replicas as traffic grows
- Switch to **asyncpg** so FastAPI doesn't block a thread waiting for every DB query
- Add indexes on `journals(user_id, created_at)` and `journal_analysis(journal_id)` — without these, queries do a full-scan as data grows

**API**
- Run **multiple uvicorn workers** behind nginx or a load balancer. The app is already stateless (JWT cookies) so horizontal scaling is straightforward
- **Move the LLM call to a background task** using FastAPI's `BackgroundTasks` or a Celery + Redis queue. Right now every `POST /api/journal` blocks for 2–5 seconds waiting for the model — that holds a worker thread. Return the `journal_id` immediately and deliver analysis when it's ready

> 🔑 The single biggest win is decoupling the LLM call from the HTTP response. Everything else is standard scaling work.

---

## 2. How would I handle LLM rate limits at scale?

`gpt-oss-20b` on HuggingFace's free Inference API has no per-token cost — so "cost" isn't the real problem here. The real problem is **rate limits**. The free tier throttles requests, and at 100k users writing entries daily, we'd hit those limits constantly.

**Short term — work within the free tier**
- Queue all LLM calls through **Celery + Redis** with a concurrency limit that respects HuggingFace's rate limit. Requests wait in the queue rather than failing
- Add **retry with exponential backoff** on 429 responses. Right now the code has no retry logic — a single rate-limit error returns a failed analysis permanently
- **Cache results aggressively** (see Section 3) — every cache hit is one fewer API call against the rate limit

**Long term — escape the rate limit**
- **Self-host the model on a GPU** — a single A10G instance runs the model with no rate limit. At high volume this is the only real solution
- A smaller 7B model (Mistral-7B, Llama-3-8B) handles emotion + keyword extraction just as well and is cheaper to self-host

> 💡 The free HuggingFace tier is great for prototyping but not designed for production traffic. The architecture should treat the LLM endpoint as an unreliable external service and handle failures gracefully from day one.

---

## 3. How would I cache repeated analysis?

Many journal entries are short and emotionally similar — *"felt calm today"*, *"the rain helped me relax"*, etc. We can skip the LLM entirely for these repeats and return a cached result instantly.

**Layer 1 — Exact hash cache (Redis)**
- Before calling the LLM, normalise the text (lowercase, strip whitespace) and compute a SHA-256 hash
- Check Redis for that hash — on a hit, return the cached result with zero LLM call. TTL: 7 days
- Expected hit rate: ~20–30% of entries, especially common short phrases

**Layer 2 — Semantic similarity cache (pgvector)**
- Embed the entry text with a small local model like `all-MiniLM-L6-v2` (runs on CPU, no API needed)
- Query pgvector for the nearest stored embedding — if cosine similarity > 0.92, reuse that analysis
- Catches paraphrases of the same idea, adds another ~10–15% hit rate on top of the hash cache

**Layer 3 — Insight aggregate cache (Redis)**
- `GET /api/journal/insights/:userId` runs 3 SQL aggregation queries on every request
- Cache the result per user with a 60-second TTL, invalidated whenever they post a new entry

> ⚡ Layers 1 and 3 are easy to add and immediately reduce pressure on both the LLM and the database. Layer 2 is optional — worth it only if Layer 1 hit rates aren't enough.

---

## 4. How would I protect sensitive journal data?

Journal entries are personal — people write things here they wouldn't say out loud. The threat model isn't just *"what if someone gets the database"* — it's also *"what if logs are exposed"* or *"what does HuggingFace do with the text we send them"*.

**Encryption**
- **Encrypt journal text before writing to the DB** using AES-256-GCM. Store the key in AWS KMS or HashiCorp Vault — never in `.env` in production
- Enable **TLS on the database connection** — any production setup needs encrypted transit between the API and PostgreSQL

**Authentication hardening**
- **Flip `secure=False` → `secure=True`** on the JWT cookie in `auth.py` — this is the most urgent fix. Right now the cookie travels in plain HTTP
- Add `SameSite=Strict` to the cookie to prevent CSRF attacks
- **Rate-limit `/login` and `/register`** — 10 req/min per IP is enough to block brute-force attempts
- Load `SECRET_KEY` from a secret manager at runtime, not from a `.env` file that could be committed accidentally

**LLM data leakage**
- **Never log raw journal text** — only log `journal_id`. Application logs are often the weakest link
- Check HuggingFace's data retention policy for the Inference API. If they store inputs, consider stripping names/locations before sending (a quick spaCy NER pass)
- If self-hosting the model, this concern disappears — text never leaves your infrastructure

**User rights**
- Add a `DELETE /api/user/:id` endpoint that removes all journals, analysis rows, and cache entries. Basic GDPR compliance and just good practice

> 🔒 The most urgent fix is `secure=False → True` in `auth.py`. That one line actively weakens security in any production deployment.

---

## Priority Order

1. Fix `secure=False` in `auth.py`
2. Migrate SQLite → PostgreSQL
3. Add async LLM queue with retry logic (Celery + Redis)
4. Add hash cache for LLM results (Redis)
5. Encrypt journal text at rest (AES-256-GCM + KMS)