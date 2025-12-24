# Rebug Portfolio Notes

## One-Line Pitch

Rebug turns "cannot reproduce" into a replay, a root-cause timeline, and eventually a production-impact receipt.

## Why

QA teams spend too much time defending valid reports. Developers often receive incomplete steps, missing console logs, missing network context, or screen recordings that show symptoms without causes.

The deeper problem is organizational memory. A bug closed as "unable to reproduce" can disappear from attention until the same failure causes an outage.

## How

I built Rebug as a full-stack browser recording and analysis system:
- A Chrome extension records DOM mutations, network requests, console logs, and user interactions.
- A local IndexedDB buffer keeps recording resilient before upload.
- A FastAPI backend stores sessions, queues AI analysis, and manages integrations.
- A LangChain agent reads the raw timeline and returns strict JSON: steps, root cause, duplicate status, and confidence.
- A Next.js viewer replays the session and shows the event timeline.
- Jira and Slack integrations file the bug directly.
- Impact Linking watches ignored Jira bugs and production incidents, then links matches by URL pattern and error similarity.

## What

Rebug delivers the core loop:

Record -> Package -> Analyze -> Replay -> File Bug -> Notify Slack -> Track Impact

## Role

Solo builder:
- Product scope and PRD
- Extension architecture
- Backend API and database schema
- AI prompt and analysis pipeline
- Jira/Slack OAuth integration
- Session replay viewer
- Deployment and portfolio packaging

## Hard Parts

### Python Packaging and Workers

The backend uses FastAPI, SQLAlchemy async sessions, Celery workers, and Celery beat. The tricky part was keeping import paths, migrations, and async service boundaries clean across API requests and worker processes, including an esoteric Python packaging issue when combining Celery workers with Alpine-style container constraints.

### RRWeb vs Custom Event Format

The extension captures a custom event stream that overlaps with RRWeb concepts but is not a pure RRWeb recording. The viewer had to support replay and timeline inspection while preserving the original captured evidence.

### OAuth and Token Safety

Jira and Slack require separate OAuth flows and token shapes. Tokens are encrypted before storage with a server-side secret. OAuth state is persisted and validated before token exchange.

### Impact Linking

The differentiator required joining product bugs, Jira lifecycle state, and production incidents. The matcher uses normalized URL patterns plus error-message similarity, with optional embeddings when OpenAI credentials are configured.

## Impact

Rebug aims to eliminate the "cannot reproduce" closure reason by making every report replayable, searchable, and tied to downstream production cost.

The Impact tab gives managers a concrete audit trail: which ignored bugs later caused incidents, what they matched on, and where the original evidence lives.
