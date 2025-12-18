import { browser, type Browser } from 'wxt/browser';
import { packageSession } from './packager';
import { uploadSessionPackage } from './uploader';
import {
  appendSessionEvent,
  createSession,
  getRecentSessions,
  markSessionError,
  stopSession,
  updateSessionMetadata,
} from '@/src/lib/storage';
import type {
  ActiveRecordingState,
  BackgroundRequest,
  BrowserInfo,
  PopupState,
  RecorderStartPayload,
  RecorderStartResult,
  RecorderStopPayload,
  RuntimeResponse,
  SessionRecord,
} from '@/src/lib/types';

const ACTIVE_RECORDING_KEY = 'rebug.activeRecording';
const BADGE_RECORDING_TEXT = 'REC';

let activeRecording: ActiveRecordingState | null = null;
let activeRecordingLoaded = false;

export function installBackgroundHandlers(): void {
  browser.runtime.onMessage.addListener((message, sender) => {
    return handleRuntimeMessage(message, sender)
      .then((data): RuntimeResponse => ({ ok: true, data }))
      .catch((error: unknown): RuntimeResponse => ({
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      }));
  });

  browser.runtime.onInstalled.addListener(() => {
    ensureActiveRecordingLoaded().then(() => updateBadge()).catch(() => undefined);
  });

  ensureActiveRecordingLoaded().then(() => updateBadge()).catch(() => undefined);
}

async function handleRuntimeMessage(
  message: unknown,
  sender: Browser.runtime.MessageSender,
): Promise<unknown> {
  if (!isBackgroundRequest(message)) {
    return undefined;
  }

  await ensureActiveRecordingLoaded();

  switch (message.type) {
    case 'REBUG_START_RECORDING':
      return startRecording();
    case 'REBUG_STOP_RECORDING':
      return stopActiveRecording();
    case 'REBUG_PACKAGE_SESSION':
      return packageRequestedSession(message.sessionId);
    case 'REBUG_GET_STATE':
      return getPopupState();
    case 'REBUG_CAPTURE_EVENT':
      return captureEvent(message, sender);
    default:
      return undefined;
  }
}

async function startRecording(): Promise<PopupState> {
  if (activeRecording) {
    throw new Error('A recording is already active.');
  }

  const tab = await getActiveTab();
  if (!tab.id || !isRecordableUrl(tab.url)) {
    throw new Error('Open a regular http or https page before recording.');
  }

  const startedAt = new Date().toISOString();
  const sessionId = crypto.randomUUID();
  const initialUrl = tab.url ?? 'about:blank';

  await createSession({
    id: sessionId,
    url: initialUrl,
    title: tab.title,
    browser: getBrowserInfo({ width: 0, height: 0 }),
    startedAt,
  });

  activeRecording = {
    sessionId,
    tabId: tab.id,
    url: initialUrl,
    startedAt,
  };

  await persistActiveRecording(activeRecording);
  await updateBadge();

  try {
    const pageState = await browser.tabs.sendMessage(tab.id, {
      type: 'REBUG_CONTENT_START',
      sessionId,
      startedAt,
    } satisfies RecorderStartPayload);

    const typedPageState = pageState as RecorderStartResult;
    await updateSessionMetadata(sessionId, {
      url: typedPageState.url,
      title: typedPageState.title,
      browser: getBrowserInfo(typedPageState.viewport),
    });
  } catch (error) {
    await markSessionError(sessionId);
    await clearActiveRecording();
    await updateBadge();
    throw new Error(
      `Unable to start the recorder on this page: ${
        error instanceof Error ? error.message : String(error)
      }`,
    );
  }

  return getPopupState();
}

async function stopActiveRecording(): Promise<SessionRecord | null> {
  if (!activeRecording) {
    return null;
  }

  const recording = activeRecording;
  const stopPayload: RecorderStopPayload = {
    type: 'REBUG_CONTENT_STOP',
    sessionId: recording.sessionId,
  };

  try {
    await browser.tabs.sendMessage(recording.tabId, stopPayload);
  } catch {
    // The tab may have navigated or closed; the session still needs to close.
  }

  const stoppedSession = await stopSession(recording.sessionId);
  await clearActiveRecording();
  await updateBadge();
  return stoppedSession;
}

async function packageRequestedSession(sessionId: string): Promise<unknown> {
  if (activeRecording?.sessionId === sessionId) {
    await stopActiveRecording();
  }

  const packageSummary = await packageSession(sessionId);
  const upload = await uploadSessionPackage(packageSummary.id);

  return {
    ...packageSummary,
    upload,
  };
}

async function captureEvent(
  message: Extract<BackgroundRequest, { type: 'REBUG_CAPTURE_EVENT' }>,
  sender: Browser.runtime.MessageSender,
): Promise<{ stored: boolean; id?: number }> {
  if (!activeRecording || message.event.sessionId !== activeRecording.sessionId) {
    return { stored: false };
  }

  if (sender.tab?.id && sender.tab.id !== activeRecording.tabId) {
    return { stored: false };
  }

  const storedEvent = await appendSessionEvent(message.event);
  return {
    stored: true,
    id: storedEvent.id,
  };
}

async function getPopupState(): Promise<PopupState> {
  return {
    activeRecording,
    sessions: await getRecentSessions(),
  };
}

async function getActiveTab(): Promise<Browser.tabs.Tab> {
  const [tab] = await browser.tabs.query({
    active: true,
    currentWindow: true,
  });

  if (!tab) {
    throw new Error('No active tab found.');
  }

  return tab;
}

async function ensureActiveRecordingLoaded(): Promise<void> {
  if (activeRecordingLoaded) {
    return;
  }

  const stored = await browser.storage.local.get(ACTIVE_RECORDING_KEY);
  const value = stored[ACTIVE_RECORDING_KEY];
  activeRecording = isActiveRecordingState(value) ? value : null;
  activeRecordingLoaded = true;
}

async function persistActiveRecording(recording: ActiveRecordingState): Promise<void> {
  await browser.storage.local.set({
    [ACTIVE_RECORDING_KEY]: recording,
  });
}

async function clearActiveRecording(): Promise<void> {
  activeRecording = null;
  await browser.storage.local.remove(ACTIVE_RECORDING_KEY);
}

async function updateBadge(): Promise<void> {
  await browser.action.setBadgeText({
    text: activeRecording ? BADGE_RECORDING_TEXT : '',
  });

  if (activeRecording) {
    await browser.action.setBadgeBackgroundColor({
      color: '#c2410c',
    });
  }
}

function getBrowserInfo(viewport: BrowserInfo['viewport']): BrowserInfo {
  const userAgent = navigator.userAgent;
  const chromeVersion = userAgent.match(/(?:Chrome|Chromium)\/([\d.]+)/)?.[1] ?? 'unknown';

  return {
    name: 'Chrome',
    version: chromeVersion,
    os: getOperatingSystem(userAgent),
    viewport,
    userAgent,
  };
}

function getOperatingSystem(userAgent: string): string {
  if (userAgent.includes('Windows')) {
    return 'Windows';
  }

  if (userAgent.includes('Mac OS X')) {
    return 'macOS';
  }

  if (userAgent.includes('Android')) {
    return 'Android';
  }

  if (userAgent.includes('iPhone') || userAgent.includes('iPad')) {
    return 'iOS';
  }

  if (userAgent.includes('Linux')) {
    return 'Linux';
  }

  return 'unknown';
}

function isRecordableUrl(url: string | undefined): boolean {
  return Boolean(url && /^https?:\/\//i.test(url));
}

function isBackgroundRequest(message: unknown): message is BackgroundRequest {
  if (typeof message !== 'object' || message === null || !('type' in message)) {
    return false;
  }

  return String((message as { type: string }).type).startsWith('REBUG_');
}

function isActiveRecordingState(value: unknown): value is ActiveRecordingState {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as ActiveRecordingState).sessionId === 'string' &&
    typeof (value as ActiveRecordingState).tabId === 'number' &&
    typeof (value as ActiveRecordingState).url === 'string' &&
    typeof (value as ActiveRecordingState).startedAt === 'string'
  );
}
