# MVP Scope - Rebug

## What We Build First

The MVP targets the core loop: **Record → Package → Analyze → Submit**

### Phase 1: Core Recording (Week 1-2)

**Deliverables:**
- Chrome extension with WXT scaffold
- Record/Stop/Package buttons in popup
- DOM mutation capture (RRWeb events)
- Network request capture (fetch/XHR monkey-patch)
- Console log capture (console wrapper)
- IndexedDB storage with Dexie.js

**Cut:**
- No screenshots yet
- No sensitive field masking (manual skip)
- No multi-tab support

### Phase 2: Session Upload & Viewer (Week 3-4)

**Deliverables:**
- FastAPI backend with session endpoints
- S3 upload + storage
- Basic session replay viewer (RRWeb player)
- Timeline with console/network overlay

**Cut:**
- No audio/video recording
- No auth (single-user mode)
- No Jira/Slack integration yet

### Phase 3: AI Analysis (Week 5-6)

**Deliverables:**
- LangChain agent with GPT-4o
- Step generation from session events
- Root cause analysis
- Duplicate detection (vector similarity)
- Analysis results displayed in viewer

**Cut:**
- No test coverage checking
- No auto-fix generation

### Phase 4: Integrations (Week 7-8)

**Deliverables:**
- Jira OAuth2 + ticket creation
- Slack notification with buttons
- Token-based share links with expiry
- Auth system (JWT)

**Cut:**
- No team dashboard
- No "I told you so" impact linking
- No analytics

---

## MVP File Structure (Final)

```
rebug/
├── extension/                    # Chrome extension (WXT)
│   ├── src/
│   │   ├── popup/               # React popup UI
│   │   │   ├── App.tsx
│   │   │   ├── RecordButton.tsx
│   │   │   ├── SessionList.tsx
│   │   │   └── Settings.tsx
│   │   ├── content/             # Content scripts
│   │   │   ├── recorder.ts      # Main recording orchestrator
│   │   │   ├── dom-capture.ts   # MutationObserver wrapper
│   │   │   ├── network-capture.ts
│   │   │   ├── console-capture.ts
│   │   │   └── sensitive-mask.ts
│   │   ├── background/          # Service worker
│   │   │   ├── packager.ts      # Compress + encrypt
│   │   │   └── uploader.ts      # Upload to backend
│   │   └── lib/
│   │       ├── storage.ts       # IndexedDB helper
│   │       └── types.ts
│   ├── wxt.config.ts
│   ├── package.json
│   └── tsconfig.json
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── sessions.py
│   │   │   ├── analysis.py
│   │   │   └── integrations.py
│   │   ├── services/
│   │   │   ├── storage.py       # S3 upload/download
│   │   │   ├── analysis.py      # LangChain agent
│   │   │   ├── jira.py
│   │   │   └── slack.py
│   │   ├── models/
│   │   │   ├── session.py
│   │   │   ├── event.py
│   │   │   └── bug_report.py
│   │   └── config.py
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── viewer/                      # Session replay (Next.js)
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx
│   │   │   └── replay/[id]/page.tsx
│   │   ├── components/
│   │   │   ├── Player.tsx
│   │   │   ├── Timeline.tsx
│   │   │   ├── ConsolePanel.tsx
│   │   │   └── NetworkPanel.tsx
│   │   └── lib/
│   │       └── api.ts
│   ├── package.json
│   └── next.config.js
├── docs/                        # Documentation
│   ├── PRD.md
│   ├── SRS.md
│   ├── user-stories.md
│   ├── architecture.md
│   ├── api-spec.md
│   ├── data-model.md
│   └── tech-stack.md
├── docker-compose.yml
└── README.md
```
