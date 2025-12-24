# Software Requirements Specification - Rebug

## 1. Introduction

### 1.1 Purpose
Rebug is a browser extension and AI agent system that captures, analyzes, and packages bug reproduction context into shareable, replayable sessions integrated with Jira and Slack.

### 1.2 Scope
The system consists of three major components: Browser Extension (recording), Backend Agent (processing + AI), and Web Viewer (replay).

---

## 2. Functional Requirements

### FR-01: Session Recording

| ID | Requirement | Priority |
|----|------------|----------|
| FR-01.1 | Extension shall record DOM mutations (add/remove/modify elements) in real-time | P0 |
| FR-01.2 | Extension shall capture all network requests (URL, method, status, headers, body) | P0 |
| FR-01.3 | Extension shall capture console logs (log, warn, error, info) | P0 |
| FR-01.4 | Extension shall record user interactions (click, input, scroll, navigation) | P0 |
| FR-01.5 | Extension shall take full-page screenshots on demand | P1 |
| FR-01.6 | Extension shall capture localStorage, sessionStorage, and cookies state | P1 |
| FR-01.7 | Extension shall mask password inputs and credit card fields automatically | P0 |
| FR-01.8 | Extension shall record without degrading page performance (> 5% overhead) | P0 |

### FR-02: Session Package

| ID | Requirement | Priority |
|----|------------|----------|
| FR-02.1 | One-click "Package Bug" shall compress all session data into a single file | P0 |
| FR-02.2 | Package shall include timestamp, URL, browser version, OS, viewport | P0 |
| FR-02.3 | Package shall be encrypted before upload | P1 |
| FR-02.4 | Package upload shall use resumable chunked transfer | P1 |

### FR-03: AI Analysis

| ID | Requirement | Priority |
|----|------------|----------|
| FR-03.1 | Agent shall analyze session data and generate step-by-step reproduction | P0 |
| FR-03.2 | Agent shall identify probable root cause (network error, race condition, etc.) | P1 |
| FR-03.3 | Agent shall detect duplicate bugs by comparing with existing sessions | P1 |
| FR-03.4 | Agent shall check if the bug scenario has existing test coverage | P2 |

### FR-04: Jira Integration

| ID | Requirement | Priority |
|----|------------|----------|
| FR-04.1 | System shall authenticate with Jira using OAuth2 | P0 |
| FR-04.2 | System shall create a Jira ticket with title, description, steps, environment, and replay link | P0 |
| FR-04.3 | System shall attach screenshot and session log as HTML comment | P1 |
| FR-04.4 | System shall link to related existing tickets if duplicate found | P1 |

### FR-05: Slack Integration

| ID | Requirement | Priority |
|----|------------|----------|
| FR-05.1 | System shall send Slack notification to configured channel | P0 |
| FR-05.2 | Notification shall include bug summary, severity, environment, and replay link | P0 |
| FR-05.3 | Slack message shall have interactive buttons (View, Assign, Dismiss) | P1 |

### FR-06: Session Viewer

| ID | Requirement | Priority |
|----|------------|----------|
| FR-06.1 | Web viewer shall replay recorded session step-by-step | P0 |
| FR-06.2 | Viewer shall show console logs synchronized with timeline | P0 |
| FR-06.3 | Viewer shall show network requests in a waterfall view | P1 |
| FR-06.4 | Viewer shall support seek, pause, and play controls | P1 |
| FR-06.5 | Viewer shall require no login for shared links (token-based) | P1 |

### FR-07: Impact Tracking

| ID | Requirement | Priority |
|----|------------|----------|
| FR-07.1 | System shall ingest production incidents through an API endpoint | P1 |
| FR-07.2 | System shall receive Jira status-change webhooks for filed bugs | P1 |
| FR-07.3 | System shall normalize "unable to reproduce" and "wontfix" Jira statuses | P1 |
| FR-07.4 | System shall match ignored bugs to incidents by URL pattern and error similarity | P1 |
| FR-07.5 | System shall post Slack notifications when production impact is linked | P1 |
| FR-07.6 | Viewer shall show an Impact dashboard with linked incidents | P1 |

---

## 3. Non-Functional Requirements

| ID | Requirement | Target |
|----|------------|--------|
| NFR-01 | Recording overhead | CPU < 5%, Memory < 200 MB |
| NFR-02 | Session upload time | < 5 seconds (10 MB session) |
| FR-03 | AI analysis latency | < 10 seconds |
| NFR-04 | Session viewer load time | < 3 seconds |
| NFR-05 | Availability | 99.5% uptime |
| NFR-06 | Security | Encryption at rest (AES-256) and in transit (TLS 1.3) |
| NFR-07 | Data retention | 90 days, auto-delete after |

---

## 4. System Interfaces

### 4.1 User Interfaces
- **Extension Popup**: Record button, session list, settings
- **Web Viewer**: Replay player with timeline, console, network panels

### 4.2 API Interfaces
- `POST /api/v1/sessions` - Upload session package
- `GET /api/v1/sessions/:id` - Retrieve session data
- `GET /api/v1/sessions/:id/replay` - Get replay viewer HTML
- `POST /api/v1/sessions/:id/analyze` - Trigger AI analysis
- `POST /api/v1/tickets/jira` - Create Jira ticket from session
- `POST /api/v1/notify/slack` - Send Slack notification
- `POST /api/v1/impact/incidents` - Ingest production incident
- `POST /api/v1/impact/jira-webhook` - Receive Jira status updates
- `GET /api/v1/impact/links` - List detected impact links

### 4.3 External Interfaces
- Jira Cloud REST API v3
- Slack Web API (chat.postMessage)
- OpenAI API (GPT-4o for analysis)
- Incident management webhooks (manual, Statuspage, PagerDuty, or custom)
