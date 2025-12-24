# API Specification - Rebug

**Base URL**: `https://api.rebug.dev/api/v1`

**Auth**: Bearer token in `Authorization` header

---

## Sessions

### Create Session
```http
POST /sessions
Content-Type: application/json

{
  "url": "https://example.com/products",
  "browser": {
    "name": "Chrome",
    "version": "125.0.0.0",
    "os": "macOS 14.5",
    "viewport": "1440x900"
  }
}
```

**Response** `201`
```json
{
  "id": "uuid-here",
  "upload_url": "https://storage.rebug.dev/sessions/uuid-here",
  "expires_at": "2026-06-15T10:00:00Z"
}
```

---

### Upload Session Data
```http
PUT /sessions/{id}/data
Content-Type: application/octet-stream
Body: <compressed session package>
```

**Response** `200`
```json
{
  "status": "uploaded",
  "size_bytes": 1024000
}
```

---

### Get Session
```http
GET /sessions/{id}
```

**Response** `200`
```json
{
  "id": "uuid-here",
  "url": "https://example.com/products",
  "browser": { ... },
  "duration": 180,
  "event_count": 452,
  "status": "analyzed",
  "created_at": "2026-06-14T09:30:00Z"
}
```

---

## Analysis

### Analyze Session
```http
POST /sessions/{id}/analyze
```

**Response** `200`
```json
{
  "steps": [
    "1. Navigate to https://example.com/products",
    "2. Click 'Add to Cart' on product 'Widget A'",
    "3. Observe: cart shows '0 items' instead of '1 item'"
  ],
  "root_cause": {
    "confidence": 0.92,
    "summary": "POST /api/cart returns 500 due to missing session token",
    "evidence": [
      {"type": "console_error", "message": "TypeError: Cannot read properties of null", "timestamp": 45200},
      {"type": "network", "url": "https://api.example.com/cart/add", "status": 500, "timestamp": 45100}
    ]
  },
  "duplicate": null
}
```

---

## Bug Reports

### Create Bug Report
```http
POST /bug-reports
Content-Type: application/json

{
  "session_id": "uuid-here",
  "title": "Add to Cart fails when session expires",
  "severity": "major",
  "project": "PROJ"
}
```

**Response** `201`
```json
{
  "id": "uuid-here",
  "jira": {
    "ticket_id": "PROJ-1234",
    "url": "https://company.atlassian.net/browse/PROJ-1234"
  },
  "replay_url": "https://replay.rebug.dev/s/uuid-here?token=abc123"
}
```

---

### Create Jira Ticket
```http
POST /integrations/jira
Content-Type: application/json

{
  "bug_report_id": "uuid-here",
  "fields": {
    "project": "PROJ",
    "issuetype": "Bug",
    "priority": "High"
  }
}
```

**Response** `200`
```json
{
  "ticket_id": "PROJ-1234",
  "url": "https://company.atlassian.net/browse/PROJ-1234"
}
```

---

### Send Slack Notification
```http
POST /integrations/slack
Content-Type: application/json

{
  "bug_report_id": "uuid-here",
  "channel": "#qa-bugs"
}
```

**Response** `200`
```json
{
  "channel": "#qa-bugs",
  "ts": "1234567890.123456",
  "message_url": "https://company.slack.com/archives/C123/p1234567890123456"
}
```

---

## Impact Tracking

### Ingest Production Incident
```http
POST /impact/incidents
Content-Type: application/json

{
  "title": "Checkout outage for expired sessions",
  "incident_url": "https://status.example.com/incidents/checkout-2026-06-15",
  "affected_url": "https://app.example.com/checkout",
  "error_message": "POST /api/checkout returned 500 session token missing",
  "source": "manual"
}
```

**Response** `200`
```json
{
  "incident": {
    "id": "uuid-here",
    "title": "Checkout outage for expired sessions",
    "incident_url": "https://status.example.com/incidents/checkout-2026-06-15",
    "affected_url": "https://app.example.com/checkout",
    "error_message": "POST /api/checkout returned 500 session token missing",
    "source": "manual",
    "occurred_at": null,
    "created_at": "2026-06-15T10:00:00Z"
  },
  "matches": []
}
```

### Jira Status Webhook
```http
POST /impact/jira-webhook
Content-Type: application/json

{
  "issue": {
    "key": "PROJ-1234",
    "fields": {
      "status": { "name": "Unable to Reproduce" }
    }
  }
}
```

**Response** `200`
```json
{
  "jira_ticket_key": "PROJ-1234",
  "status": "Unable to Reproduce",
  "final_status": "unable_to_repro",
  "matched_links": 1
}
```

### List Impact Links
```http
GET /impact/links
```

**Response** `200`
```json
[
  {
    "id": "uuid-here",
    "bug_report_id": "uuid-here",
    "session_id": "uuid-here",
    "bug_title": "Checkout fails when session expires",
    "bug_status": "unable_to_repro",
    "jira_ticket_key": "PROJ-1234",
    "jira_url": "https://company.atlassian.net/browse/PROJ-1234",
    "replay_url": "https://replay.example.com/replay/uuid-here",
    "incident_title": "Checkout outage for expired sessions",
    "incident_url": "https://status.example.com/incidents/checkout-2026-06-15",
    "match_score": 0.87,
    "match_reason": "URL pattern score 1.00; error similarity 0.74",
    "notification_status": "sent"
  }
]
```

---

### Check Duplicate
```http
POST /sessions/{id}/check-duplicate
```

**Response** `200`
```json
{
  "is_duplicate": true,
  "matches": [
    {
      "bug_report_id": "uuid-here",
      "similarity": 0.94,
      "jira_ticket": "PROJ-1198",
      "title": "Checkout fails on expired session"
    }
  ]
}
```

---

## Webhook Events

Rebug sends webhooks to your configured endpoint:

### `bug.filed`
```json
{
  "event": "bug.filed",
  "bug_report_id": "uuid-here",
  "jira_ticket": "PROJ-1234",
  "title": "Add to Cart fails when session expires",
  "severity": "major",
  "replay_url": "https://replay.rebug.dev/s/uuid-here?token=abc123"
}
```

### `bug.impact_detected`
```json
{
  "event": "bug.impact_detected",
  "original_bug": {
    "id": "uuid-here",
    "jira_ticket": "PROJ-1198",
    "status": "unable_to_repro"
  },
  "related_incident": {
    "id": "uuid-here",
    "title": "Cart outage - all users affected",
    "severity": "critical"
  }
}
```

---

## Error Codes

| Status | Code | Meaning |
|--------|------|---------|
| 400 | INVALID_SESSION | Session data malformed or missing required fields |
| 401 | UNAUTHORIZED | Missing or invalid auth token |
| 403 | FORBIDDEN | Token valid but insufficient permissions |
| 404 | NOT_FOUND | Session or bug report not found |
| 413 | PAYLOAD_TOO_LARGE | Session exceeds 50 MB limit |
| 429 | RATE_LIMITED | Too many requests, retry after X seconds |
| 500 | INTERNAL_ERROR | Server error, contact support |
