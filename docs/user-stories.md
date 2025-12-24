# User Stories - Rebug

## Epic 1: Session Recording

### Story 1.1 - Start Recording
**As a** QA engineer
**I want** to start recording my test session with one click
**So that** I capture everything without disrupting my workflow

**Acceptance Criteria:**
- Click extension icon → dropdown with "Start Recording" button
- Extension badge shows red dot + timer when recording
- No visible performance lag during recording
- Recording persists across page navigations within the same domain

---

### Story 1.2 - Capture Bug Context
**As a** QA engineer
**I want** to capture a screenshot + full state when I discover a bug
**So that** I don't lose critical evidence

**Acceptance Criteria:**
- Click "Mark Bug" or use keyboard shortcut (Ctrl+Shift+B)
- Takes full-page screenshot automatically
- Captures current DOM snapshot, network log, console errors
- Stores all data in the session timeline with a bug marker

---

### Story 1.3 - Stop and Package
**As a** QA engineer
**I want** to stop recording and package everything into a single file
**So that** I can share the bug context instantly

**Acceptance Criteria:**
- Click "Stop Recording" → packages all data
- Shows progress bar during packaging
- Estimates file size before upload
- Auto-detects and masks sensitive fields

---

## Epic 2: AI Analysis

### Story 2.1 - Generate Steps
**As a** QA engineer
**I want** AI to generate reproduction steps from my session
**So that** I don't have to retrace and write them manually

**Acceptance Criteria:**
- AI reads recorded interactions and outputs numbered steps
- Steps include specific data values used (URLs, button text, input values)
- Steps are editable before submission
- Confidence score displayed for generated steps

---

### Story 2.2 - Root Cause Suggestion
**As a** QA engineer
**I want** AI to suggest probable root cause
**So that** developers have a starting point for the fix

**Acceptance Criteria:**
- AI analyzes console errors, network status codes, and DOM state
- Outputs top 3 probable causes with evidence
- Highlights anomalous network requests or console errors

---

### Story 2.3 - Duplicate Detection
**As a** QA engineer
**I want** the system to check if this bug was already reported
**So that** I don't waste time filing duplicates

**Acceptance Criteria:**
- Agent compares session fingerprint with existing sessions
- Returns list of similar tickets with similarity score
- If > 90% match, prompts to link instead of create new

---

## Epic 3: Integrations

### Story 3.1 - Create Jira Ticket
**As a** QA engineer
**I want** to create a Jira ticket with all bug context from one button
**So that** I never type a bug report again

**Acceptance Criteria:**
- Click "Send to Jira" from extension or web viewer
- Auto-fills summary, description, steps to reproduce, environment
- Attaches session replay link as a custom field
- Confirms ticket creation with link back to Jira

---

### Story 3.2 - Notify Slack
**As a** QA engineer
**I want** to notify the team on Slack with the bug report
**So that** developers see it immediately, not in a Jira backlog

**Acceptance Criteria:**
- Click "Share to Slack" → selects channel → sends
- Message includes: title, severity, environment, replay link
- Contains action buttons: "View Replay", "Assign to Me"
- Thread includes ticket link after Jira creation

---

## Epic 4: Session Replay

### Story 4.1 - Watch Replay
**As a** developer
**I want** to watch the exact session where the bug occurred
**So that** I see the bug with my own eyes, not guess from text

**Acceptance Criteria:**
- Opens in any browser without install
- Shows mouse movements, clicks, inputs, page navigation
- Console errors highlighted in red on timeline
- Playback speed controls (0.5x, 1x, 2x)

---

### Story 4.2 - Debug with Data
**As a** developer
**I want** to inspect network requests and console logs during replay
**So that** I can understand what went wrong without asking QA

**Acceptance Criteria:**
- Click on timeline → shows corresponding console + network state
- Network waterfall with timing breakdown
- Console log search/filter
- Copy request/response data

---

## Epic 5: Tracking & Proof

### Story 5.1 - Bug Impact Dashboard
**As a** QA engineer
**I want** to see how many bugs I reported that were accepted vs. closed
**So that** I can prove my value and improve my reporting

**Acceptance Criteria:**
- Dashboard shows: total bugs filed, accepted, "can't repro", fixed
- Trend over time chart
- Sorting by project/team

---

### Story 5.2 - "I Told You So" Alert
**As a** QA engineer
**I want** the system to auto-link closed "can't repro" bugs to related production incidents
**So that** I have data-backed proof when ignored bugs hit prod

**Acceptance Criteria:**
- Agent monitors Jira for closed "unable to reproduce" tickets
- Cross-references with production incident reports periodically
- When match found: creates Slack post referencing original ticket + incident
- Dashboard shows linkage count
