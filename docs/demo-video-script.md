# 30-Second Demo Video Script

## Setup

- API running at `http://localhost:8000`
- Viewer running at `http://localhost:3000`
- Extension loaded from `extension/.output/chrome-mv3`
- A demo web app open in Chrome
- Jira and Slack credentials configured, or use a local demo environment with mocked credentials

## Script

0:00 - 0:04
Open the extension popup and click Record.

0:04 - 0:09
Use the demo app and trigger a visible bug. Click Mark Bug if the marker control is available.

0:09 - 0:13
Open the extension popup, click Stop, then Package. The replay link appears.

0:13 - 0:18
Open the replay viewer. Show the timeline with network, console, and interaction markers.

0:18 - 0:23
Click Analyze. Show generated reproduction steps and root-cause evidence.

0:23 - 0:27
Click File Bug. Show Jira ticket URL and Slack notification result.

0:27 - 0:30
Switch to the Impact tab. Show a production incident linked to an earlier ignored bug.

## Voiceover

"Rebug records the browser evidence behind a bug, generates reproduction steps and root cause, files Jira and Slack automatically, and later proves when an ignored bug caused production impact."
