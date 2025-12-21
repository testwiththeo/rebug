export interface BrowserPayload {
  name: string;
  version: string;
  os: string;
  viewport?: {
    width?: number | null;
    height?: number | null;
  } | null;
  userAgent?: string | null;
}

export interface SessionResponse {
  id: string;
  url: string;
  browser: BrowserPayload;
  duration: number | null;
  event_count: number;
  status: string;
  storage_key: string | null;
  size_bytes: number | null;
  checksum: string | null;
  started_at: string;
  ended_at: string | null;
  created_at: string;
}

export type SessionEventType =
  | 'dom_mutation'
  | 'network_request'
  | 'console_log'
  | 'user_interaction'
  | 'screenshot'
  | 'bug_marker'
  | 'rrweb';

export interface SessionEvent {
  id: number;
  session_id: string;
  sequence: number;
  timestamp_ms: number;
  event_type: SessionEventType | string;
  category: string | null;
  data: Record<string, unknown>;
  masked: boolean;
}

export interface SessionEventsPage {
  items: SessionEvent[];
  total: number;
  limit: number;
  offset: number;
}

export interface ReplayPayload {
  session: SessionResponse;
  events: SessionEvent[];
}

export interface AnalysisTaskResponse {
  session_id: string;
  status: string;
  task_id: string | null;
}

export interface AnalysisResponse {
  id: string;
  session_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | string;
  confidence: number | null;
  summary: string | null;
  severity_suggestion: string | null;
  steps: Array<Record<string, unknown>>;
  root_cause: Record<string, unknown>;
  duplicate_check: {
    is_duplicate?: boolean;
    matches?: Array<Record<string, unknown>>;
    note?: string;
    [key: string]: unknown;
  };
  coverage_note: string | null;
  data_sensitivity_warning: string | null;
  error_message: string | null;
  task_id: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DuplicateCheckResponse {
  session_id: string;
  duplicate_check: AnalysisResponse['duplicate_check'];
}

export interface JiraTicketResponse {
  ticket_id: string;
  ticket_key: string;
  ticket_url: string;
}

export interface SlackNotifyResponse {
  channel: string | null;
  ts: string | null;
  message_url: string | null;
}

export interface FileBugResponse {
  session_id: string;
  bug_report_id: string | null;
  status: string;
  replay_url: string;
  jira: JiraTicketResponse | null;
  slack: SlackNotifyResponse | null;
  error_message: string | null;
  filed_at: string | null;
}

export interface ImpactLinkResponse {
  id: string;
  bug_report_id: string;
  session_id: string;
  bug_title: string;
  bug_status: string | null;
  jira_ticket_key: string | null;
  jira_url: string | null;
  replay_url: string | null;
  original_url: string;
  incident_title: string;
  incident_url: string;
  detected_at: string;
  match_score: number | null;
  match_reason: string | null;
  notification_status: string;
  notification_error: string | null;
  evidence: Record<string, unknown>;
}
