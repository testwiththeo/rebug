# Chrome Web Store Listing

## Name

Rebug

## Short Description

Record reproducible bug sessions and file Jira tickets with replay, logs, network data, and AI-generated steps.

## Detailed Description

Rebug captures the proof developers need when a bug is hard to reproduce.

With one click, QA engineers can record DOM mutations, network requests, console logs, and user interactions. Rebug packages the session, uploads it to a replay viewer, generates reproduction steps and root-cause evidence, then files a Jira ticket and posts a Slack notification.

What makes Rebug different:
- Replayable browser sessions, not just screenshots.
- AI-generated reproduction steps grounded in the actual event timeline.
- Root-cause evidence from network and console failures.
- Duplicate detection against prior bug reports.
- Impact Linking: when a bug closed as unable to reproduce later matches a production incident, Rebug links them and notifies Slack.

## Category

Developer Tools

## Screenshots To Capture

1. Extension popup while recording.
2. Session replay viewer with timeline markers.
3. AI Analysis panel with reproduction steps.
4. File Bug result showing Jira and Slack links.
5. Impact tab showing an ignored bug tied to a production incident.

## Privacy Summary

Rebug records page interaction data only when the user starts recording. Sensitive fields are masked client-side before upload. OAuth tokens for Jira and Slack are encrypted before storage.
