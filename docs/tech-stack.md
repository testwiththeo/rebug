# Tech Stack - Rebug

## Browser Extension

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | WXT (Vite + TypeScript) | Modern extension dev, HMR, multi-browser |
| UI | React 18 + Tailwind CSS | Familiar, fast, clean popup |
| State | Zustand | Lightweight, no boilerplate |
| DOM Capture | RRWeb (custom adapter) | Proven event format, already has a player |
| Network Capture | PerformanceObserver + fetch monkey-patch | Non-invasive, captures timing naturally |
| Compression | pako (gzip) + msgpack | Compact binary format for events |
| Storage | IndexedDB via Dexie.js | Large local buffer before upload |

## Backend

| Layer | Choice | Why |
|-------|--------|-----|
| Runtime | Python 3.12 | AI/ML ecosystem, LangChain |
| Framework | FastAPI + Uvicorn | Async, auto-docs, fast dev |
| ORM | SQLAlchemy 2.0 + Alembic | Mature, async support |
| Database | PostgreSQL 16 | JSONB for flexible event storage, robust |
| Queue | Celery + Redis | Async AI analysis tasks |
| Storage | S3-compatible (MinIO / Backblaze B2) | Cheap, scalable |
| AI Framework | LangChain | Prompt chaining, tool calling |
| LLM | GPT-4o | Best balance of speed + quality |
| Auth | PyJWT + OAuth2 (google-auth) | Stateless, standard |

## AI Agent (LangChain)

**Agent Tools:**
1. `analyze_session_events` - Reads session event log and identifies sequences
2. `generate_reproduction_steps` - Converts event timeline to numbered steps
3. `diagnose_root_cause` - Cross-references console errors with network failures
4. `check_duplicate` - Vector similarity search against existing bug reports
5. `check_test_coverage` - Compares flow against known test suites (optional)

**Agent Architecture:** ReAct agent with structured output (Pydantic schemas)

## Frontend (Session Viewer)

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | Next.js 14 (App Router) | SSR for immediate viewer load |
| UI | Tailwind CSS + shadcn/ui | Rapid development, consistent |
| State | Zustand | Lightweight |
| Player | RRWeb player (custom skin) | Battle-tested replay engine |
| Timeline | Custom Canvas-based | Need precise performance timeline |

## Infrastructure

| Layer | Choice |
|-------|--------|
| Hosting | Railway / Fly.io |
| Static files | Vercel |
| CDN | Cloudflare |
| CI/CD | GitHub Actions |
| Monitoring | Sentry (errors) + Grafana (metrics) |
| Secrets | Doppler |

## Development

| Tool | Purpose |
|------|---------|
| pnpm | Package manager |
| ESLint + Prettier | Linting/formatting |
| pytest + Playwright | Backend + E2E tests |
| Ruff | Python linter |
| Docker Compose | Local dev (API + DB + Redis) |
| ngrok | Extension webhook testing |
