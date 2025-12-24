# Rebug

> **"Works on my machine" - not anymore.**

Rebug is a browser extension + AI agent that captures complete bug reproduction context and packages it into a replayable session posted directly to Jira/Slack.

## Problem

QA engineers spend 30-50% of their time *proving* bugs exist. "Can't reproduce" is the #1 reason bugs get closed unfixed - only to surface later as production incidents.

## Solution

One click to record. One click to package. AI writes the steps, finds the root cause, and files the ticket. Developers watch the exact session and fix it immediately.

## Quick Start

```bash
# Extension
cd extension && npm install && npm run dev

# Backend
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Viewer
cd viewer && npm install && npm run dev
```

## Docs

| Document | Link |
|----------|------|
| PRD | [docs/PRD.md](docs/PRD.md) |
| SRS | [docs/SRS.md](docs/SRS.md) |
| User Stories | [docs/user-stories.md](docs/user-stories.md) |
| Architecture | [docs/architecture.md](docs/architecture.md) |
| API Spec | [docs/api-spec.md](docs/api-spec.md) |
| Data Model | [docs/data-model.md](docs/data-model.md) |
| Tech Stack | [docs/tech-stack.md](docs/tech-stack.md) |
| MVP Scope | [docs/mvp-scope.md](docs/mvp-scope.md) |
| Glossary | [docs/glossary.md](docs/glossary.md) |

## Architecture

```
Extension (capture) → Backend (AI analysis) → Jira + Slack (submit)
                    ↘ Viewer (replay) ↗
```

## License

MIT
