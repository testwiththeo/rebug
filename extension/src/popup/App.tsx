import { useEffect, useMemo, useState } from 'react';
import { browser } from 'wxt/browser';
import type {
  BackgroundRequest,
  PackageSummary,
  PopupState,
  RuntimeResponse,
  SessionRecord,
} from '@/src/lib/types';
import './App.css';

type BusyAction = 'record' | 'stop' | 'package' | null;
type PopupView = 'recorder' | 'settings';
type OAuthProvider = 'jira' | 'slack';

interface IntegrationStatusItem {
  type: OAuthProvider | string;
  configured: boolean;
  connected: boolean;
  enabled: boolean;
  needs_reauth: boolean;
  display_name: string | null;
  detail: string | null;
}

interface IntegrationStatusResponse {
  items: IntegrationStatusItem[];
}

interface OAuthStartResponse {
  auth_url: string;
  state: string;
}

const API_BASE_URL_KEY = 'rebug.apiBaseUrl';
const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1';

function App() {
  const [popupState, setPopupState] = useState<PopupState>({
    activeRecording: null,
    sessions: [],
  });
  const [view, setView] = useState<PopupView>('recorder');
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const [packageSummary, setPackageSummary] = useState<PackageSummary | null>(null);
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_API_BASE_URL);
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatusItem[]>([]);
  const [settingsBusy, setSettingsBusy] = useState<OAuthProvider | 'status' | 'save' | null>(null);
  const [settingsMessage, setSettingsMessage] = useState<string | null>(null);

  const activeSession = useMemo(() => {
    return popupState.sessions.find(
      (session) => session.id === popupState.activeRecording?.sessionId,
    );
  }, [popupState.activeRecording?.sessionId, popupState.sessions]);

  const selectedSession = useMemo(() => {
    return popupState.sessions.find((session) => session.id === selectedSessionId) ?? null;
  }, [popupState.sessions, selectedSessionId]);

  useEffect(() => {
    refreshState().catch(setDisplayError);
    loadSettings().catch(setDisplayError);
  }, []);

  useEffect(() => {
    if (!popupState.activeRecording) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      refreshState().catch(setDisplayError);
    }, 1_000);

    return () => window.clearInterval(timer);
  }, [popupState.activeRecording]);

  useEffect(() => {
    if (selectedSessionId && popupState.sessions.some((session) => session.id === selectedSessionId)) {
      return;
    }

    setSelectedSessionId(popupState.sessions[0]?.id ?? null);
  }, [popupState.sessions, selectedSessionId]);

  async function refreshState(): Promise<void> {
    const state = await sendBackgroundRequest<PopupState>({
      type: 'REBUG_GET_STATE',
    });
    setPopupState(state);
  }

  async function loadSettings(): Promise<void> {
    const stored = await browser.storage.local.get(API_BASE_URL_KEY);
    const value = stored[API_BASE_URL_KEY];
    const nextApiBaseUrl =
      typeof value === 'string' && value ? value.replace(/\/$/, '') : DEFAULT_API_BASE_URL;
    setApiBaseUrl(nextApiBaseUrl);
    await refreshIntegrationStatus(nextApiBaseUrl);
  }

  async function refreshIntegrationStatus(baseUrl = apiBaseUrl): Promise<void> {
    setSettingsBusy('status');
    setSettingsMessage(null);
    try {
      const statusResponse = await fetchJson<IntegrationStatusResponse>(
        `${baseUrl.replace(/\/$/, '')}/integrations/status`,
      );
      setIntegrationStatus(statusResponse.items);
    } finally {
      setSettingsBusy(null);
    }
  }

  async function saveApiBaseUrl(): Promise<void> {
    setSettingsBusy('save');
    setSettingsMessage(null);
    try {
      const normalized = apiBaseUrl.replace(/\/$/, '');
      await browser.storage.local.set({ [API_BASE_URL_KEY]: normalized });
      setApiBaseUrl(normalized);
      setSettingsMessage('Settings saved.');
      await refreshIntegrationStatus(normalized);
    } catch (caughtError) {
      setDisplayError(caughtError);
    } finally {
      setSettingsBusy(null);
    }
  }

  async function startOAuth(provider: OAuthProvider): Promise<void> {
    setSettingsBusy(provider);
    setSettingsMessage(null);
    try {
      const response = await fetchJson<OAuthStartResponse>(
        `${apiBaseUrl.replace(/\/$/, '')}/integrations/${provider}/auth`,
        { method: 'POST' },
      );
      await browser.tabs.create({ url: response.auth_url });
      setSettingsMessage(`Opened ${providerName(provider)} authorization.`);
    } catch (caughtError) {
      setDisplayError(caughtError);
    } finally {
      setSettingsBusy(null);
    }
  }

  async function startRecording(): Promise<void> {
    await runAction('record', async () => {
      const state = await sendBackgroundRequest<PopupState>({
        type: 'REBUG_START_RECORDING',
      });
      setPopupState(state);
      setSelectedSessionId(state.activeRecording?.sessionId ?? state.sessions[0]?.id ?? null);
      setPackageSummary(null);
    });
  }

  async function stopRecording(): Promise<void> {
    await runAction('stop', async () => {
      await sendBackgroundRequest<SessionRecord | null>({
        type: 'REBUG_STOP_RECORDING',
      });
      await refreshState();
    });
  }

  async function packageSession(): Promise<void> {
    if (!selectedSessionId) {
      return;
    }

    await runAction('package', async () => {
      const summary = await sendBackgroundRequest<PackageSummary>({
        type: 'REBUG_PACKAGE_SESSION',
        sessionId: selectedSessionId,
      });
      setPackageSummary(summary);
      await refreshState();
    });
  }

  async function runAction(action: BusyAction, task: () => Promise<void>): Promise<void> {
    setBusyAction(action);
    setError(null);

    try {
      await task();
    } catch (caughtError) {
      setDisplayError(caughtError);
    } finally {
      setBusyAction(null);
    }
  }

  function setDisplayError(caughtError: unknown): void {
    setError(caughtError instanceof Error ? caughtError.message : String(caughtError));
  }

  const isRecording = Boolean(popupState.activeRecording);
  const packageDisabled = !selectedSession || busyAction !== null;

  return (
    <main className="popup-shell">
      <header className="popup-header">
        <div>
          <h1>Rebug</h1>
          <p>{view === 'recorder' ? (isRecording ? 'Recording' : 'Idle') : 'Settings'}</p>
        </div>
        <span className={isRecording ? 'status-dot is-recording' : 'status-dot'} />
      </header>

      <nav className="view-tabs" aria-label="Popup views">
        <button
          className={view === 'recorder' ? 'tab-button is-active' : 'tab-button'}
          onClick={() => setView('recorder')}
          type="button"
        >
          Recorder
        </button>
        <button
          className={view === 'settings' ? 'tab-button is-active' : 'tab-button'}
          onClick={() => setView('settings')}
          type="button"
        >
          Settings
        </button>
      </nav>

      {view === 'recorder' ? (
        <>
          <section className="metrics-grid" aria-label="Session status">
            <Metric
              label="Duration"
              value={formatDuration(
                activeSession?.startedAt,
                activeSession?.endedAt,
                activeSession?.durationMs,
              )}
            />
            <Metric label="Events" value={String(activeSession?.eventCount ?? 0)} />
          </section>

          <section className="action-row" aria-label="Recording controls">
            <button
              className="button primary"
              disabled={isRecording || busyAction !== null}
              onClick={startRecording}
              type="button"
            >
              {busyAction === 'record' ? 'Starting' : 'Record'}
            </button>
            <button
              className="button danger"
              disabled={!isRecording || busyAction !== null}
              onClick={stopRecording}
              type="button"
            >
              {busyAction === 'stop' ? 'Stopping' : 'Stop'}
            </button>
            <button
              className="button secondary"
              disabled={packageDisabled}
              onClick={packageSession}
              type="button"
            >
              {busyAction === 'package' ? 'Packing' : 'Package'}
            </button>
          </section>

          {error ? <p className="message error">{error}</p> : null}
          {packageSummary ? (
            <p className="message success">
              Package {formatBytes(packageSummary.sizeBytes)} -{' '}
              {packageSummary.checksum.slice(0, 12)}
              {packageSummary.upload ? (
                <>
                  <br />
                  <a href={packageSummary.upload.replayUrl} rel="noreferrer" target="_blank">
                    Open replay
                  </a>
                </>
              ) : null}
            </p>
          ) : null}

          <section className="session-section" aria-label="Recent sessions">
            <div className="section-heading">
              <h2>Sessions</h2>
              <button className="ghost-button" onClick={refreshState} type="button">
                Refresh
              </button>
            </div>

            <div className="session-list">
              {popupState.sessions.length === 0 ? (
                <p className="empty-state">No sessions</p>
              ) : (
                popupState.sessions.map((session) => (
                  <button
                    className={
                      session.id === selectedSessionId ? 'session-row is-selected' : 'session-row'
                    }
                    key={session.id}
                    onClick={() => setSelectedSessionId(session.id)}
                    type="button"
                  >
                    <span>
                      <strong>{session.title || hostnameFromUrl(session.url)}</strong>
                      <small>{session.status}</small>
                    </span>
                    <span className="session-meta">
                      {session.eventCount} events
                      {session.sizeBytes ? ` / ${formatBytes(session.sizeBytes)}` : ''}
                    </span>
                  </button>
                ))
              )}
            </div>
          </section>
        </>
      ) : (
        <SettingsView
          apiBaseUrl={apiBaseUrl}
          error={error}
          integrationStatus={integrationStatus}
          onApiBaseUrlChange={setApiBaseUrl}
          onRefresh={() => refreshIntegrationStatus().catch(setDisplayError)}
          onSave={saveApiBaseUrl}
          onStartOAuth={startOAuth}
          settingsBusy={settingsBusy}
          settingsMessage={settingsMessage}
        />
      )}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

interface SettingsViewProps {
  apiBaseUrl: string;
  error: string | null;
  integrationStatus: IntegrationStatusItem[];
  settingsBusy: OAuthProvider | 'status' | 'save' | null;
  settingsMessage: string | null;
  onApiBaseUrlChange: (value: string) => void;
  onSave: () => Promise<void>;
  onRefresh: () => void;
  onStartOAuth: (provider: OAuthProvider) => Promise<void>;
}

function SettingsView({
  apiBaseUrl,
  error,
  integrationStatus,
  settingsBusy,
  settingsMessage,
  onApiBaseUrlChange,
  onSave,
  onRefresh,
  onStartOAuth,
}: SettingsViewProps) {
  const jiraStatus = statusFor(integrationStatus, 'jira');
  const slackStatus = statusFor(integrationStatus, 'slack');

  return (
    <section className="settings-section" aria-label="Integration settings">
      <label className="field">
        <span>Backend API</span>
        <input
          onChange={(event) => onApiBaseUrlChange(event.target.value)}
          spellCheck={false}
          type="url"
          value={apiBaseUrl}
        />
      </label>

      <div className="settings-actions">
        <button
          className="ghost-button"
          disabled={settingsBusy === 'save'}
          onClick={() => onSave()}
          type="button"
        >
          {settingsBusy === 'save' ? 'Saving' : 'Save'}
        </button>
        <button
          className="ghost-button"
          disabled={settingsBusy === 'status'}
          onClick={onRefresh}
          type="button"
        >
          {settingsBusy === 'status' ? 'Checking' : 'Check'}
        </button>
      </div>

      {error ? <p className="message error">{error}</p> : null}
      {settingsMessage ? <p className="message success">{settingsMessage}</p> : null}

      <IntegrationCard
        busy={settingsBusy === 'jira'}
        onConnect={() => onStartOAuth('jira')}
        provider="jira"
        status={jiraStatus}
      />
      <IntegrationCard
        busy={settingsBusy === 'slack'}
        onConnect={() => onStartOAuth('slack')}
        provider="slack"
        status={slackStatus}
      />
    </section>
  );
}

function IntegrationCard({
  busy,
  onConnect,
  provider,
  status,
}: {
  busy: boolean;
  onConnect: () => Promise<void>;
  provider: OAuthProvider;
  status: IntegrationStatusItem | null;
}) {
  const connected = Boolean(status?.connected);
  return (
    <div className="integration-card">
      <div>
        <strong>{providerName(provider)}</strong>
        <small>{status?.detail ?? 'Not checked'}</small>
      </div>
      <div className="integration-actions">
        <span className={connected ? 'connection-pill is-connected' : 'connection-pill'}>
          {connected ? 'Connected' : 'Disconnected'}
        </span>
        <button className="ghost-button" disabled={busy} onClick={() => onConnect()} type="button">
          {busy ? 'Opening' : connected ? 'Reconnect' : 'Connect'}
        </button>
      </div>
    </div>
  );
}

async function sendBackgroundRequest<T>(request: BackgroundRequest): Promise<T> {
  const response = (await browser.runtime.sendMessage(request)) as RuntimeResponse<T>;
  if (!response?.ok) {
    throw new Error(response?.error ?? 'Background request failed.');
  }

  return response.data;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      accept: 'application/json',
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${await response.text()}`);
  }

  return (await response.json()) as T;
}

function formatDuration(startedAt?: string, endedAt?: string, storedDurationMs?: number): string {
  if (storedDurationMs != null) {
    return formatDurationMs(storedDurationMs);
  }

  if (!startedAt) {
    return '0:00';
  }

  const end = endedAt ? new Date(endedAt).getTime() : Date.now();
  return formatDurationMs(Math.max(0, end - new Date(startedAt).getTime()));
}

function formatDurationMs(durationMs: number): string {
  const totalSeconds = Math.round(durationMs / 1_000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function formatBytes(bytes: number): string {
  if (bytes < 1_024) {
    return `${bytes} B`;
  }

  if (bytes < 1_048_576) {
    return `${(bytes / 1_024).toFixed(1)} KB`;
  }

  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

function hostnameFromUrl(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

function statusFor(
  items: IntegrationStatusItem[],
  provider: OAuthProvider,
): IntegrationStatusItem | null {
  return items.find((item) => item.type === provider) ?? null;
}

function providerName(provider: OAuthProvider): string {
  return provider === 'jira' ? 'Jira' : 'Slack';
}

export default App;
