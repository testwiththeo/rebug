# Architecture Document - Rebug

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (Client Side)                   │
│  ┌─────────────────────────────────────────────────────┐│
│  │              Chrome Extension                         ││
│  │  ┌─────────┐  ┌──────────┐  ┌───────────────────┐  ││
│  │  │ Popup   │  │ Recorder  │  │ Session Packager  │  ││
│  │  │ (React) │  │ (TS)     │  │ (Compress/Encrypt)│  ││
│  │  └─────────┘  └──────────┘  └───────────────────┘  ││
│  │  ┌──────────────────────────────────────────────┐   ││
│  │  │ DOM Observer | Network Capture | Console Hook │   ││
│  │  └──────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────┘│
│                          │ HTTPS                         │
└──────────────────────────┼──────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────┐
│                    Backend (Server Side)                  │
│                          │                                │
│  ┌───────────────────────┴──────────────────────────┐   │
│  │              API Gateway (FastAPI)                 │   │
│  │  POST /sessions │ POST /analyze │ POST /tickets   │   │
│  └───────────────────────┬──────────────────────────┘   │
│                          │                                │
│  ┌───────────────────────┼──────────────────────────┐   │
│  │         ┌─────────────┴─────────────┐            │   │
│  │         │       AI Agent            │            │   │
│  │         │  ┌─────────────────────┐  │            │   │
│  │         │  │ Step Generator      │  │            │   │
│  │         │  │ Root Cause Analyzer │  │            │   │
│  │         │  │ Duplicate Detector  │  │            │   │
│  │         │  │ Coverage Checker    │  │            │   │
│  │         │  └─────────────────────┘  │            │   │
│  │         └───────────────────────────┘            │   │
│  │                                                    │   │
│  │  ┌────────────────┐  ┌────────────────────────┐    │   │
│  │  │ Session Store   │  │ Integration Layer       │   │   │
│  │  │ (PostgreSQL)    │  │ Jira API │ Slack API    │   │   │
│  │  └────────────────┘  └────────────────────────┘    │   │
│  └────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Browser Extension

| Module | Technology | Responsibility |
|--------|-----------|---------------|
| Popup UI | React + Tailwind | Record button, settings, session list |
| Recorder | TypeScript (Content Script) | DOM observer, network capture, console hook |
| Session Packager | TypeScript (Service Worker) | Compress, encrypt, upload session |
| Storage | IndexedDB (local) | Session buffer before upload |

#### Data Capture Strategy
- **DOM**: MutationObserver on `document.body`, record operations as RRWeb-style events
- **Network**: `PerformanceObserver` + fetch/XMLHttpRequest monkey-patching
- **Console**: Wrap `console.log/warn/error/info`
- **Screenshot**: `html2canvas` or `Canvas.drawWindow`

### 2. Backend (FastAPI)

| Module | Stack | Responsibility |
|--------|-------|---------------|
| API Gateway | FastAPI + Uvicorn | Request routing, auth, rate limiting |
| Session Service | Python | Decompress, validate, store sessions |
| AI Agent | LangChain + GPT-4o | Step generation, root cause analysis |
| Integration Service | Python httpx | Jira REST API, Slack Web API |
| Auth | JWT + OAuth2 | Extension authentication |

### 3. Session Viewer (Web)

- **Frontend**: React + Timeline component
- **Replay Engine**: Custom player that reads event log and reconstructs DOM state
- **Timeline**: Console errors (red), network (blue), user interactions (green)

### 4. Data Model

```
sessions
├── id: UUID (PK)
├── user_id: UUID (FK)
├── project_id: UUID (FK)
├── url: string
├── browser: { name, version, os, viewport }
├── started_at: timestamp
├── ended_at: timestamp
├── duration: integer (seconds)
├── status: enum [recording, packaged, analyzed, submitted]
├── storage_key: string (S3 path)
├── size_bytes: integer
├── created_at: timestamp

session_events
├── id: UUID (PK)
├── session_id: UUID (FK)
├── type: enum [dom_mutation, network_request, console_log, user_interaction, screenshot, bug_marker]
├── timestamp: integer (ms offset)
├── data: JSONB
└── sequence: integer

bug_reports
├── id: UUID (PK)
├── session_id: UUID (FK)
├── jira_ticket_id: string (nullable)
├── slack_ts: string (nullable)
├── steps: JSONB (AI generated)
├── root_cause: JSONB (AI generated)
├── duplicate_of: UUID (FK, nullable)
├── created_at: timestamp
└── status: enum [open, accepted, wontfix, unable_to_repro, fixed]
```

## Security Architecture

- **Data in transit**: TLS 1.3
- **Data at rest**: AES-256 encryption
- **Sensitive field masking**: Client-side regex detection for password/credit card fields
- **Auth**: OAuth2 for extension, JWT for API
- **Session access**: Token-based share links with expiration

## Deployment

```
Extension → Chrome Web Store (signed CRX)
Backend → Docker + Railway/Render/Fly.io
Database → PostgreSQL (Railway/Render)
Storage → S3-compatible (Backblaze B2)
Viewer → Vercel (static site)
```
