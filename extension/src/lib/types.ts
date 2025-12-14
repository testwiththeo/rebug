export type SessionStatus = 'recording' | 'stopped' | 'packaged' | 'uploaded' | 'error';

export type SessionEventType =
  | 'dom_mutation'
  | 'network_request'
  | 'console_log'
  | 'user_interaction'
  | 'screenshot'
  | 'bug_marker';

export type ConsoleLevel = 'log' | 'warn' | 'error' | 'info';

export interface BrowserInfo {
  name: string;
  version: string;
  os: string;
  viewport: {
    width: number;
    height: number;
  };
  userAgent: string;
}

export interface SessionRecord {
  id: string;
  url: string;
  title?: string;
  browser: BrowserInfo;
  startedAt: string;
  endedAt?: string;
  durationMs?: number;
  status: SessionStatus;
  eventCount: number;
  sizeBytes?: number;
  checksum?: string;
  packageId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface DomMutationData {
  type: MutationRecord['type'];
  target_selector: string;
  attribute_name?: string | null;
  old_value?: string | null;
  new_value?: string | null;
  added_nodes?: string[];
  removed_nodes?: string[];
}

export interface NetworkRequestData {
  method: string;
  url: string;
  status?: number;
  request_body?: string | null;
  response_body?: string | null;
  duration_ms: number;
  is_error: boolean;
}

export interface ConsoleLogData {
  level: ConsoleLevel;
  message: string;
  stack_trace?: string;
}

export interface UserInteractionData {
  action: 'click' | 'input' | 'scroll' | 'navigation';
  target_selector?: string;
  value?: string | null;
  coordinates?: {
    x: number;
    y: number;
  };
  scroll_position?: {
    top: number;
    left: number;
  };
  label?: string;
}

export interface BugMarkerData {
  note: string;
}

export type SessionEventData =
  | DomMutationData
  | NetworkRequestData
  | ConsoleLogData
  | UserInteractionData
  | BugMarkerData
  | Record<string, unknown>;

export interface CaptureEventInput<TData extends SessionEventData = SessionEventData> {
  sessionId: string;
  timestampMs: number;
  type: SessionEventType;
  category?: string;
  data: TData;
  masked?: boolean;
}

export interface StoredSessionEvent<TData extends SessionEventData = SessionEventData>
  extends CaptureEventInput<TData> {
  id?: number;
  sequence: number;
  createdAt: string;
}

export interface SessionPackagePayload {
  session_id: string;
  url: string;
  browser: BrowserInfo;
  started_at: string;
  ended_at?: string;
  duration_ms?: number;
  events: StoredSessionEvent[];
}

export interface PackagedSessionRecord {
  id: string;
  sessionId: string;
  createdAt: string;
  sizeBytes: number;
  checksum: string;
  data: Uint8Array;
}

export interface PackageSummary {
  id: string;
  sessionId: string;
  sizeBytes: number;
  checksum: string;
  createdAt: string;
  upload?: {
    status: 'uploaded';
    packageId: string;
    sessionId: string;
    sizeBytes: number;
    replayUrl: string;
  };
}

export interface ActiveRecordingState {
  sessionId: string;
  tabId: number;
  url: string;
  startedAt: string;
}

export interface RecorderStartPayload {
  type: 'REBUG_CONTENT_START';
  sessionId: string;
  startedAt: string;
}

export interface RecorderStopPayload {
  type: 'REBUG_CONTENT_STOP';
  sessionId: string;
}

export interface RecorderStartResult {
  url: string;
  title: string;
  viewport: BrowserInfo['viewport'];
}

export type BackgroundRequest =
  | { type: 'REBUG_START_RECORDING' }
  | { type: 'REBUG_STOP_RECORDING' }
  | { type: 'REBUG_GET_STATE' }
  | { type: 'REBUG_PACKAGE_SESSION'; sessionId: string }
  | { type: 'REBUG_CAPTURE_EVENT'; event: CaptureEventInput };

export type RuntimeResponse<TData = unknown> =
  | {
      ok: true;
      data: TData;
    }
  | {
      ok: false;
      error: string;
    };

export interface PopupState {
  activeRecording: ActiveRecordingState | null;
  sessions: SessionRecord[];
}

export interface PageHookEvent {
  type: SessionEventType;
  category?: string;
  data: SessionEventData;
}

export interface PageHookMessage {
  source: 'rebug-page-hook';
  event: PageHookEvent;
}
