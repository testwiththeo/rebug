# Technical Architecture Review - Rebug
**Reviewer:** Steve, Technical Architect  
**Date:** 2026-06-15  
**Version:** MVP (pre-production)

---

## 1. Architecture Overview

### 1.1 System Context (C4 Context Diagram)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ┌─────────────┐                                                        │
│  │             │                                                        │
│  │  QA Engineer│                                                        │
│  │  (User)     │                                                        │
│  │             │                                                        │
│  └──────┬──────┘                                                        │
│         │                                                               │
│         │ Records bugs, views replays, files to Jira/Slack              │
│         ▼                                                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │                       REBUG SYSTEM                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │   Chrome    │  │   FastAPI   │  │    Next.js Viewer       │  │   │
│  │  │  Extension  │◄─►│   Backend   │◄─►│   (Session Replay)      │  │   │
│  │  └─────────────┘  └──────┬──────┘  └─────────────────────────┘  │   │
│  │                          │                                       │   │
│  └──────────────────────────┼───────────────────────────────────────┘   │
│                            │                                            │
└────────────────────────────┼────────────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │    Jira     │     │   Slack     │     │   OpenAI    │
  │  (OAuth2)   │     │  (OAuth2)   │     │  (API Key)  │
  └─────────────┘     └─────────────┘     └─────────────┘
         ▲
         │
         ▼
  ┌─────────────┐
  │ Browser APIs│
  │ (DOM, Fetch)│
  └─────────────┘
```

### 1.2 Container Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            BROWSER (Client Side)                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                      CHROME EXTENSION (WXT + React)                      │ │
│  │                                                                          │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────────┐  │ │
│  │  │   Popup    │  │  Content   │  │  Service   │  │   IndexedDB      │  │ │
│  │  │  (React)   │  │  Scripts   │  │  Worker    │  │   (Dexie.js)     │  │ │
│  │  │            │  │ (Recorder) │  │(Packager)  │  │                  │  │ │
│  │  └────────────┘  └────────────┘  └────────────┘  └──────────────────┘  │ │
│  │        │               │                │                              │ │
│  │        └───────────────┴────────────────┘                              │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS (gzip + msgpack)
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            BACKEND (Server Side)                              │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    FASTAPI (Python 3.12)                               │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │  │
│  │  │  Sessions  │  │ Analysis   │  │Integration │  │    Impact      │  │  │
│  │  │   Router   │  │   Agent    │  │   Router   │  │    Router      │  │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│  ┌─────────────────┐  ┌───────────────────┐  ┌──────────────────────────┐  │
│  │   PostgreSQL    │  │      Redis        │  │   MinIO / S3             │  │
│  │   (Sessions,    │  │ (Celery Broker,   │  │   (Session Packages)     │  │
│  │    Events)      │  │    Cache)         │  │                          │  │
│  └─────────────────┘  └───────────────────┘  └──────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    CELERY WORKERS                                      │  │
│  │  ┌────────────────────────────┐  ┌─────────────────────────────────┐  │  │
│  │  │  Analysis Worker           │  │  Beat Scheduler                 │  │  │
│  │  │  (AI analysis tasks)       │  │  (Impact scan every 15 min)     │  │  │
│  │  └────────────────────────────┘  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ SSR / API calls
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                      VIEWER (Next.js 14 App Router)                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────────┐ │
│  │  Session List  │  │  Replay Page   │  │  rrweb-player + Custom         │ │
│  │                │  │                │  │  Timeline/Console/Network      │ │
│  └────────────────┘  └────────────────┘  └────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Deployment Diagram

**Current (Docker Compose - Local Dev):**
```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                    │
│                                                             │
│  ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐  │
│  │   API   │   │  Worker  │   │  Beat   │   │ Postgres │  │
│  │ :8000   │   │          │   │         │   │  :5432   │  │
│  └────┬────┘   └────┬─────┘   └────┬────┘   └────┬─────┘  │
│       │             │              │              │         │
│       └─────────────┴──────────────┴──────────────┘         │
│                           │                                  │
│  ┌─────────┐        ┌─────────┐                             │
│  │  MinIO  │        │  Redis  │                             │
│  │ :9000   │        │  :6379  │                             │
│  └─────────┘        └─────────┘                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Host Machine                              │
│  ┌─────────────────┐   ┌─────────────────────────────────┐ │
│  │ Chrome Extension│   │ Next.js Viewer (localhost:3000) │ │
│  │ (unpacked)      │   │                                 │ │
│  └─────────────────┘   └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Target (Production):**
```
┌───────────────────┐     ┌──────────────────────────────────┐
│ Chrome Web Store  │     │        Vercel (Edge)             │
│ (Extension CRX)   │     │  ┌────────────────────────────┐  │
└───────────────────┘     │  │ Next.js Viewer (SSR)       │  │
                          │  └────────────────────────────┘  │
                          └──────────────┬───────────────────┘
                                         │
┌────────────────────────────────────────┼────────────────────┐
│           Railway / Fly.io              │                    │
│  ┌────────────────┐  ┌────────────────┐│                    │
│  │ API Container  │  │ Worker Process ││                    │
│  │ (FastAPI)      │  │ (Celery)       ││                    │
│  └───────┬────────┘  └───────┬────────┘│                    │
│          └───────────────────┘         │                    │
│                     │                  │                    │
│  ┌──────────────────▼──────────────────▼─────────────────┐ │
│  │              Managed PostgreSQL                        │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────┐  ┌─────────────────────────────────┐│
│  │ Managed Redis    │  │ Backblaze B2 / S3 (Packages)    ││
│  └──────────────────┘  └─────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘
```

**Data Flow:**
1. Extension captures events → IndexedDB buffer
2. User clicks "Package" → gzip + msgpack → POST /sessions
3. Backend stores package in S3, events in Postgres
4. Celery worker runs AI analysis → stores results
5. User clicks "View" → Viewer fetches events → rrweb-player renders
6. User clicks "File Bug" → Jira/Slack API calls

---

## 2. Technical Review

### 2.1 Extension Architecture

**Content Script vs Service Worker Split:**

| Component | Location | Responsibility | Assessment |
|-----------|----------|----------------|------------|
| `recorder.ts` | Content Script | DOM capture, network intercept, console hook | ✓ Correct - needs DOM access |
| `packager.ts` | Service Worker | Compression, upload orchestration | ✓ Correct - no DOM needed |
| `storage.ts` | Both | IndexedDB abstraction | ✓ Correct - accessible from both |

**Verdict:** The split is correct. Content scripts handle page-level interception; service worker handles packaging and upload.

**Page Hooks Pattern (fetch/XHR/console capture):**

```typescript
// Current approach in network-capture.ts (inferred)
const originalFetch = window.fetch;
window.fetch = async (...args) => {
  const response = await originalFetch(...args);
  emit({ type: 'network_request', ... });
  return response;
};
```

**Pros:**
- Captures request/response data that PerformanceObserver cannot
- Works for both fetch and XMLHttpRequest
- Non-blocking (emits asynchronously)

**Cons:**
- Requires content script injection before page loads
- Can conflict with other extensions doing the same
- Does not capture service worker fetch events
- Performance overhead on every network call

**Recommendation:** This is acceptable for MVP, but consider `PerformanceObserver` for timing data only, and only monkey-patch when user is actively recording.

**IndexedDB Buffer (Dexie.js) - Offline Resilience:**

```typescript
// storage.ts
await db.events.add(storedEvent);
await db.sessions.update(event.sessionId, {
  eventCount: savedEvent.sequence,
});
```

**Strengths:**
- Transactional writes prevent data corruption
- Event counter updated atomically
- Can buffer thousands of events locally

**Weaknesses:**
- No maximum storage limit enforced (could fill disk)
- No automatic purge of old sessions
- No encryption at rest (sensitive data in plaintext on disk)

**Recommendation:** Add a max storage quota (e.g., 500MB) and implement LRU eviction for sessions older than 7 days.

**Sensitive Field Masking:**

The MVP cuts this from scope ("No sensitive field masking - manual skip"). This is a **critical gap**.

**Risk:** Passwords, credit cards, auth tokens, and PII are captured and stored in plaintext in IndexedDB, uploaded to S3, and stored in PostgreSQL JSONB.

**Recommendation:** Implement client-side masking BEFORE the heuristic fallback. At minimum:
```typescript
const SENSITIVE_SELECTORS = [
  'input[type="password"]',
  'input[autocomplete="cc-number"]',
  'input[name*="credit"]',
  'input[name*="ssn"]',
];
```

**Performance Impact:**

| Capture Type | Overhead | Mitigation |
|--------------|----------|------------|
| MutationObserver | 2-5% CPU | Batching with `requestAnimationFrame` |
| Network monkey-patch | 1-2% per request | Only active during recording |
| Console wrapper | Negligible | Direct passthrough when not recording |

**Verdict:** Performance target (< 5% overhead) is achievable, but must be validated with real-world pages (SPA frameworks, heavy DOM updates).

---

### 2.2 Backend Architecture

**FastAPI + SQLAlchemy Async Patterns:**

```python
# sessions.py
async def create_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SessionIngestResponse:
    package_bytes = await request.body()
    service = SessionIngestService(db=db, settings=settings)
    session = await service.ingest_package(package_bytes)
```

**Strengths:**
- Proper async/await usage throughout
- Dependency injection for DB sessions and settings
- Clean separation of concerns (router → service → models)

**Weaknesses:**
- No request size validation at API level (relies on nginx/server config)
- No rate limiting on upload endpoint
- No authentication/authorization in MVP (single-user mode cut)

**Session Ingest Pipeline (gzip + msgpack):**

```python
# session_ingest.py
def decode_session_package(package_bytes: bytes) -> SessionPackageInput:
    unpacked = gzip.decompress(package_bytes)
    payload = msgpack.unpackb(unpacked, raw=False)
    return SessionPackageInput.model_validate(payload)
```

**Strengths:**
- Proper error handling with custom exceptions
- Pydantic validation for schema enforcement
- Checksum verification prevents duplicate uploads

**Weaknesses:**
- Entire package loaded into memory (50MB limit)
- No streaming decompression for large sessions
- Events inserted in batch (could OOM with 10K+ events)

**Recommendation:** For sessions approaching 50MB, consider streaming the event list to a temp file during insertion.

**Analysis Agent: LangChain ReAct vs Direct LLM Call:**

```python
# analysis_agent.py
async def analyze_session(self, session_id: UUID) -> dict[str, Any]:
    context = await self.load_session_context(session_id)
    if self.settings.openai_api_key:
        return await self.run_langchain_agent(context, existing_reports)
    return self.run_heuristic_pipeline(context, existing_reports)
```

**Current Implementation:**
- Uses LangChain for structured output
- Falls back to heuristic pipeline when OpenAI unavailable
- Samples max 1,000 events to stay within context limits

**Is LangChain Worth It?**

| Aspect | With LangChain | Without LangChain |
|--------|---------------|-------------------|
| Complexity | High (abstraction layer) | Low (direct API call) |
| Flexibility | Easy to swap models | Requires code changes |
| Debugging | Harder (multiple layers) | Easier (direct response) |
| Tool calling | Built-in | Must implement manually |

**Verdict:** For MVP with a single LLM provider (OpenAI), LangChain adds unnecessary complexity. The abstraction would be valuable if you planned to support multiple models (Claude, Gemini) or complex tool chains, but the current implementation only uses structured output.

**Recommendation:** Replace LangChain with direct `openai` library calls + Pydantic model parsing. Save ~200 lines of abstraction code.

**Celery Task Design:**

```python
# tasks/analysis.py
@celery_app.task(name="analysis.run_session_analysis", bind=True)
def run_session_analysis(self, session_id: str) -> dict[str, str]:
    return asyncio.run(run_session_analysis_async(UUID(session_id), self.request.id))
```

**Strengths:**
- Task tracking enabled (`task_track_started=True`)
- JSON serialization (compatible with Redis)
- Proper async wrapper

**Weaknesses:**
- No retry configuration (`max_retries`, `retry_backoff`)
- No dead letter queue for failed analyses
- No idempotency key (duplicate analysis possible)

**Recommendation:**
```python
@celery_app.task(
    bind=True,
    max_retries=3,
    retry_backoff=60,
    retry_backoff_max=300,
)
def run_session_analysis(self, session_id: str) -> dict[str, str]:
    ...
```

**OAuth Token Encryption (Fernet):**

```python
# config.py
token_encryption_secret: str = "dev-insecure-change-me"
```

**Critical Issue:** The default value is a placeholder. In production, if this secret is rotated, all existing OAuth tokens become undecryptable.

**Recommendation:**
1. Document rotation procedure clearly
2. Implement key versioning (store key ID with encrypted token)
3. Add migration script to re-encrypt tokens with new key

**Impact Linking (Celery Beat vs Event-Driven):**

Current: Celery beat scans every 15 minutes.

```python
# celery_app.py
beat_schedule={
    "impact-scan-every-15-minutes": {
        "task": "impact.scan_impact_links",
        "schedule": 15 * 60,
    },
},
```

**Trade-offs:**
- Polling approach is simpler to implement
- Misses real-time correlation (up to 15 min delay)
- Scales poorly as incident count grows

**Recommendation:** For MVP, this is acceptable. For v2, consider event-driven webhooks from incident sources (Statuspage, PagerDuty).

---

### 2.3 Data Architecture

**Session Events Stored as JSONB:**

```sql
-- session_events table
data JSONB  -- Event-specific payload
```

**Query Performance at Scale (10K+ events per session):**

| Query Pattern | Index | Performance |
|---------------|-------|-------------|
| Sequential replay | `(session_id, sequence)` | ✓ Excellent |
| Filter by event type | `(session_id, event_type)` | ✓ Good |
| Search within JSONB | None | ✗ Poor (full scan) |

**Issue:** No GIN index on `data` column. Queries like "find all network requests with status 500" require a full scan.

**Recommendation:**
```sql
CREATE INDEX idx_session_events_data_gin ON session_events USING GIN (data);
```

Or extract commonly queried fields into dedicated columns:
```sql
ALTER TABLE session_events ADD COLUMN network_status INT;
ALTER TABLE session_events ADD COLUMN network_url TEXT;
```

**Analysis Results JSONB:**

```sql
-- No vector column for duplicate detection
```

**Issue:** Duplicate detection uses text similarity (Jaccard/cosine) on summaries, not vector embeddings.

```python
# analysis_agent.py (inferred)
def compute_duplicate_check(...):
    # Uses text-based similarity, not embeddings
```

**Recommendation:** Add a vector column for session embeddings:
```sql
ALTER TABLE analysis_results ADD COLUMN summary_embedding vector(1536);
CREATE INDEX ON analysis_results USING ivfflat (summary_embedding vector_cosine_ops);
```

Use `text-embedding-3-small` for cost efficiency.

**Data Retention:**

| Data | Retention | Implementation |
|------|-----------|----------------|
| Raw session events | 90 days | Not implemented |
| Bug reports | 1 year | Not implemented |
| Impact links | Indefinite | N/A |

**Critical Gap:** No automated cleanup jobs.

**Recommendation:** Add Celery beat task:
```python
@celery_app.task
def purge_expired_sessions():
    cutoff = datetime.utcnow() - timedelta(days=90)
    delete_session_events_before(cutoff)
```

**Migration Strategy (Alembic):**

No issues detected, but note: JSONB columns are schema-flexible. Schema changes to event payloads are handled at the application layer (Pydantic), not database layer.

---

### 2.4 API Design

**RESTful Maturity Level:** Level 2 (Resources + HTTP verbs)

**Strengths:**
- Consistent resource naming (`/sessions`, `/sessions/{id}/events`)
- Proper use of HTTP status codes (201, 400, 404, 409)
- Versioned API (`/api/v1`)

**Weaknesses:**
- No HATEOAS (hypermedia links in responses)
- Inconsistent error format (detail string vs structured object)

**Pagination Strategy:**

```python
# sessions.py
@router.get("/{session_id}/events", response_model=SessionEventsPage)
async def get_session_events(
    session_id: UUID,
    limit: int = Query(default=500, ge=1, le=2_000),
    offset: int = Query(default=0, ge=0),
) -> SessionEventsPage:
```

**Strengths:**
- Cursor-based would be better for real-time, but offset is fine for replay
- Limit capped at 2,000 (prevents abuse)
- Returns total count

**Recommendation:** For sessions with >10,000 events, consider cursor-based pagination to avoid offset degradation.

**Error Handling Consistency:**

```python
# Current
raise HTTPException(status_code=400, detail="Session package is empty.")

# Recommended
raise HTTPException(
    status_code=400,
    detail={
        "code": "INVALID_SESSION",
        "message": "Session package is empty.",
        "field": "package_bytes",
    }
)
```

**Rate Limiting:** Not implemented.

**Critical Gap:** AI analysis endpoint has no rate limiting. A single user could trigger unlimited GPT-4o calls.

**Recommendation:** Add `slowapi` or custom middleware:
```python
@app.middleware("http")
async def rate_limit_analysis(request: Request, call_next):
    if "/analyze" in request.url.path:
        # Check Redis for user's analysis count
        ...
```

---

## 3. Non-Functional Requirements Assessment

### 3.1 Performance

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Recording overhead | CPU < 5%, Mem < 200MB | Not measured | ⚠ Unknown |
| Session upload (10MB) | < 5 sec | Not measured | ⚠ Unknown |
| AI analysis latency | < 10 sec | ~5-15 sec (GPT-4o) | ✓ Acceptable |
| Viewer load time | < 3 sec | Not measured | ⚠ Unknown |
| DB query (session list) | < 100ms | Not measured | ⚠ Unknown |

**Critical Gap:** No performance benchmarks exist.

**Recommendation:** Add performance tests to CI:
```yaml
# .github/workflows/performance.yml
- name: Session upload benchmark
  run: pytest tests/performance/test_upload.py --benchmark-only
```

### 3.2 Security

| Requirement | Status | Issue |
|-------------|--------|-------|
| OAuth token encryption | ⚠ Partial | No key rotation strategy |
| TLS 1.3 in transit | ✓ OK | Handled by platform |
| AES-256 at rest | ✗ Missing | S3 objects not encrypted |
| Sensitive field masking | ✗ Missing | Cut from MVP |
| CORS configuration | ⚠ Partial | Allows any chrome-extension:// |
| Rate limiting | ✗ Missing | No protection on AI endpoints |

**Critical Vulnerabilities:**

1. **No authentication on session upload** - Anyone can POST sessions
2. **S3 objects unencrypted** - Session data (potentially sensitive) stored in plaintext
3. **No sensitive field masking** - Passwords, tokens captured as-is

**Recommendation:**
```python
# Enable S3 server-side encryption
self.client.put_object(
    ...,
    ServerSideEncryption='AES256',
)
```

### 3.3 Scalability

| Component | Stateless? | Scaling Strategy |
|-----------|------------|------------------|
| FastAPI API | ✓ Yes | Horizontal (add containers) |
| Celery workers | ✓ Yes | Horizontal (add workers) |
| PostgreSQL | ✗ No | Vertical / read replicas |
| Redis | ✗ No | Clustering (complex) |
| S3 | ✓ Yes | Unlimited |

**Database Bottleneck:**

`session_events` grows unbounded: 10K events × 1KB avg = 10MB per session. 1,000 sessions/day = 10GB/day.

**Recommendation:**
1. Partition `session_events` by `session_id` hash
2. Implement archival to S3 after 90 days
3. Consider TimescaleDB for time-series optimization

### 3.4 Reliability

| Failure Mode | Handling | Status |
|--------------|----------|--------|
| Upload failure | No retry logic | ✗ Missing |
| Celery task failure | No retries | ✗ Missing |
| DB connection pool | Not configured | ⚠ Default |
| OpenAI API down | Fallback to heuristic | ✓ Good |

**Upload Retry Logic:**

Current implementation:
```typescript
// recorder.ts
browser.runtime.sendMessage(request).catch(() => {
  // Dropping one event is preferable to blocking the page
});
```

Events are silently dropped if the service worker is unavailable.

**Recommendation:** Implement exponential backoff with local queue:
```typescript
const MAX_RETRIES = 5;
for (let i = 0; i < MAX_RETRIES; i++) {
  try {
    await browser.runtime.sendMessage(request);
    break;
  } catch {
    await sleep(100 * Math.pow(2, i));
  }
}
```

---

## 4. Recommendations

### 4.1 Critical (Must Fix Before Production)

1. **Add authentication to session upload endpoint**
   - Risk: Anyone can flood your database with sessions
   - Effort: 1-2 days

2. **Implement sensitive field masking**
   - Risk: Passwords and PII stored in plaintext
   - Effort: 2-3 days

3. **Enable S3 server-side encryption**
   - Risk: Session data readable by anyone with S3 access
   - Effort: 1 day

4. **Add rate limiting to analysis endpoint**
   - Risk: Unlimited GPT-4o API costs
   - Effort: 1 day

5. **Document OAuth token rotation procedure**
   - Risk: Production outage if key rotated incorrectly
   - Effort: 1 day

### 4.2 Important (Should Address Within 3 Months)

1. **Add Celery task retry configuration**
   - Impact: Lost analyses on transient failures

2. **Implement session archival (90-day retention)**
   - Impact: Database growth unbounded

3. **Add GIN index on session_events.data**
   - Impact: Slow searches on event payloads

4. **Add performance benchmarks to CI**
   - Impact: Unknown performance regressions

5. **Implement event upload retry logic**
   - Impact: Silent event loss during recording

### 4.3 Nice-to-Have (Future Roadmap)

1. **Replace LangChain with direct OpenAI calls**
   - Benefit: Simpler codebase, easier debugging

2. **Add vector embeddings for duplicate detection**
   - Benefit: Better semantic matching

3. **Implement cursor-based pagination for large sessions**
   - Benefit: Consistent performance at scale

4. **Add TimescaleDB for session_events**
   - Benefit: Better time-series query performance

5. **Implement event-driven impact detection**
   - Benefit: Real-time incident correlation

---

## 5. Technology Radar

| Technology | Rating | Rationale |
|------------|--------|-----------|
| **WXT** | **Adopt** | Modern extension framework with HMR and multi-browser support. Significant improvement over raw manifest.json. |
| **FastAPI** | **Adopt** | Excellent async support, auto-docs, type safety. Industry standard for Python APIs. |
| **SQLAlchemy 2.0 async** | **Adopt** | Mature ORM with proper async support. 2.0 release is production-ready. |
| **LangChain** | **Trial** | Overkill for single-provider LLM usage. Adds abstraction complexity. Consider removing for MVP. |
| **Celery** | **Adopt** | Battle-tested task queue. Well-understood operational patterns. |
| **RRWeb** | **Trial** | Session replay format is solid, but player is alpha-quality. Custom skin required. |
| **Next.js 14** | **Adopt** | App Router + SSR is ideal for viewer. Vercel deployment is seamless. |
| **Fernet** | **Trial** | Simple encryption, but lacks key versioning. Consider `aws-encryption-sdk` for production. |
| **MinIO / S3** | **Adopt** | Standard object storage. S3-compatible API is portable. |

---

## 6. Technical Debt Log

| Priority | Item | Impact | Effort |
|----------|------|--------|--------|
| P0 | No authentication on API | Security critical | 2 days |
| P0 | Sensitive field masking | Compliance/security | 3 days |
| P0 | S3 encryption | Security | 1 day |
| P1 | No test coverage metrics | Quality assurance | 1 week |
| P1 | No observability (Sentry/Grafana) | Operations | 3 days |
| P1 | LangChain abstraction debt | Maintainability | 1 week |
| P2 | No API documentation (beyond OpenAPI) | Developer experience | 2 days |
| P2 | No database migration rollback tests | Risk of failed deploys | 1 day |
| P3 | Extension built without source maps | Debugging production issues | 1 day |
| P3 | No E2E tests for recording flow | Regression prevention | 1 week |

**Test Coverage Priority:**
1. Session upload + ingest pipeline
2. AI analysis (with mocked OpenAI)
3. Celery task execution
4. Extension recorder event emission
5. Viewer replay rendering

**Missing Observability:**
1. Request tracing (OpenTelemetry)
2. Error tracking (Sentry)
3. Metrics (Prometheus + Grafana)
4. Log aggregation (Loki or CloudWatch)
5. Celery task monitoring (Flower)

---

## 7. Final Verdict

### Is the architecture production-ready?

**No.** The MVP architecture is technically sound, but critical security gaps prevent production deployment:

1. No authentication allows unrestricted session uploads
2. Sensitive data is captured and stored unencrypted
3. No rate limiting exposes unlimited AI API costs

The core design decisions (extension architecture, backend services, data model) are appropriate. The implementation quality is good for a junior team. However, security cannot be an afterthought for a tool that captures user interactions.

**Estimated time to production-ready:** 2-3 weeks with focused effort on the critical items.

### What is the single biggest technical risk?

**Data growth in `session_events` table.**

Each session generates 5-15KB of event data. At 1,000 sessions/day, the table grows 5-15MB/day. Within 6 months, query performance will degrade significantly without partitioning or archival.

This is a "silent" risk—you won't notice until users complain about slow replays.

### What is the single biggest technical advantage over competitors?

**The heuristic fallback for AI analysis.**

When OpenAI is unavailable or the user has no API key, the system still produces useful reproduction steps and root cause analysis. Competitors like jam.dev and capture.dev require their backend to process sessions.

This allows offline-first usage and reduces operational dependency on third-party AI services.

### If I were building this, what would I do differently?

1. **Start with authentication, not cut it from MVP.** Building auth retroactively is painful and often introduces security holes.

2. **Use vector embeddings from day one.** The duplicate detection problem is fundamentally a similarity search problem. Text-based Jaccard similarity will disappoint.

3. **Drop LangChain.** For a single-provider LLM integration, it adds more complexity than value. Direct API calls are simpler and more debuggable.

4. **Stream session upload.** Loading 50MB into memory for every upload will cause OOM errors at scale. Use streaming decompression.

5. **Add observability before writing code.** Without metrics, you're flying blind. Set up Sentry, Prometheus, and logging infrastructure first.

---

**Summary:** The team has built a functional MVP with a solid foundation. The architecture decisions are defensible. The code quality is acceptable. But security cannot be deferred, and the team needs to invest in operational tooling before scaling. With 2-3 weeks of focused work on critical items, this could be production-ready.

---

*Review completed. Questions? I'm available for follow-up discussion.*
