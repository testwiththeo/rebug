# Data Model - Rebug

## Entity Relationship Diagram

```
users 1───* sessions
sessions 1───* session_events
sessions 1───0..1 bug_reports
bug_reports 1───0..1 jira_tickets
bug_reports 1───0..1 slack_messages
```

---

## Tables

### users
| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| email | VARCHAR(255) UNIQUE | |
| name | VARCHAR(255) | |
| avatar_url | TEXT | |
| jira_auth | JSONB | Encrypted OAuth2 tokens |
| slack_auth | JSONB | Encrypted OAuth2 tokens |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### sessions
| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| project | VARCHAR(255) | Auto-detected or user-set |
| url | TEXT | Page URL when recording started |
| browser_name | VARCHAR(50) | chrome, firefox, edge |
| browser_version | VARCHAR(20) | |
| os | VARCHAR(50) | |
| viewport_width | INT | |
| viewport_height | INT | |
| started_at | TIMESTAMP | |
| ended_at | TIMESTAMP | |
| duration_sec | INT | Computed |
| event_count | INT | |
| storage_key | TEXT | S3 object key |
| size_bytes | INT | |
| status | ENUM | recording → packaged → analyzed → submitted → archived |
| checksum | VARCHAR(64) | SHA-256 of raw data |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### session_events
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL PK | |
| session_id | UUID FK → sessions | |
| sequence | INT | Order within session |
| timestamp_ms | INT | Milliseconds from session start |
| event_type | ENUM | dom_mutation, network_request, console_log, user_interaction, screenshot, bug_marker |
| category | VARCHAR(50) | click, input, navigation, xhr, fetch, console_error, etc. |
| data | JSONB | Event-specific payload |
| masked | BOOLEAN | Whether sensitive data was masked |

**Event Types - data payload:**

`dom_mutation`:
```json
{
  "type": "childList|attributes|characterData",
  "target": "css-selector",
  "added": ["<node>..."],
  "removed": ["<node>..."],
  "attribute_name": "class",
  "old_value": "btn",
  "new_value": "btn active"
}
```

`network_request`:
```json
{
  "method": "POST",
  "url": "https://api.example.com/cart/add",
  "request_headers": {"content-type": "application/json"},
  "request_body": "{\"product_id\": 123}",
  "response_status": 500,
  "response_headers": {},
  "response_body": "{\"error\": \"session expired\"}",
  "duration_ms": 2340
}
```

`console_log`:
```json
{
  "level": "error",
  "message": "TypeError: Cannot read properties of null",
  "stack": "at Object.addToCart (app.js:123:45)",
  "timestamp": 45200
}
```

`user_interaction`:
```json
{
  "type": "click|input|scroll|navigation",
  "target": "css-selector",
  "value": "entered text (if input)",
  "coordinates": {"x": 350, "y": 200},
  "scroll_position": {"top": 0, "left": 0}
}
```

### bug_reports
| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| session_id | UUID FK → sessions | |
| user_id | UUID FK → users | |
| title | VARCHAR(500) | User-provided or AI-generated |
| severity | ENUM | trivial, minor, major, critical, blocker |
| steps | JSONB | AI-generated numbered steps |
| root_cause | JSONB | AI analysis result |
| coverage_gaps | JSONB | Missing tests for this flow |
| duplicate_of | UUID FK → bug_reports | Self-referencing for dupe chain |
| duplicate_score | DECIMAL(3,2) | 0.00–1.00 |
| jira_ticket_id | VARCHAR(50) | e.g. PROJ-1234 |
| jira_url | TEXT | |
| slack_channel | VARCHAR(100) | |
| slack_ts | VARCHAR(50) | Slack message timestamp |
| jira_status | VARCHAR(255) | Last Jira status name |
| final_status | ENUM | open, accepted, in_progress, fixed, wontfix, unable_to_repro |
| filed_at | TIMESTAMP | |
| resolved_at | TIMESTAMP | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### integrations
| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| type | ENUM | jira, slack |
| config | JSONB | Workspace URL, default project, default channel |
| credentials | JSONB | Encrypted OAuth tokens |
| enabled | BOOLEAN | |
| created_at | TIMESTAMP | |

### impact_links
| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| bug_report_id | UUID FK → bug_reports | The originally ignored bug |
| incident_id | UUID FK → production_incidents | Matched incident record |
| incident_title | TEXT | Production incident name |
| incident_url | TEXT | Link to postmortem/incident report |
| detected_at | TIMESTAMP | When the agent found the match |
| match_score | DECIMAL(4,3) | URL + error similarity score |
| match_reason | TEXT | Human-readable match explanation |
| notification_status | VARCHAR(32) | pending, sent, failed |
| evidence | JSONB | URL patterns, error text, embedding score |
| created_at | TIMESTAMP | |

### production_incidents
| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| title | TEXT | Incident title |
| incident_url | TEXT | Status page, PagerDuty, postmortem, or runbook URL |
| affected_url | TEXT | User-facing URL or route pattern affected |
| error_message | TEXT | Primary production error |
| source | VARCHAR(64) | manual, statuspage, pagerduty, webhook |
| payload | JSONB | Original webhook payload |
| occurred_at | TIMESTAMP | Incident timestamp if provided |
| created_at | TIMESTAMP | |

---

## Indexes

| Table | Index | Type | Purpose |
|-------|-------|------|---------|
| sessions | (user_id, status) | B-tree | List active sessions per user |
| sessions | (created_at) | B-tree | Time-based queries |
| session_events | (session_id, sequence) | B-tree | Ordered event replay |
| session_events | (session_id, event_type) | B-tree | Filter by type |
| bug_reports | (user_id, final_status) | B-tree | User's bug report list |
| bug_reports | (jira_ticket_id) | B-tree | Jira lookup |
| bug_reports | (duplicate_of) | B-tree | Duplicate chains |
| impact_links | (bug_report_id) | B-tree | Impact tracking |
| production_incidents | (incident_url) | B-tree | De-dupe/manual lookup |

---

## Data Retention

| Data | Retention | Action |
|------|-----------|--------|
| Raw session events | 90 days | Hard delete |
| Bug reports | 1 year | Soft delete then hard delete |
| User accounts | Until deletion request | Soft delete |
| Integration tokens | Until integration removed | Hard delete |
| Impact links | Indefinite | Kept for proof/audit |
