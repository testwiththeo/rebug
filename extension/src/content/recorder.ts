import { browser } from 'wxt/browser';
import type {
  BackgroundRequest,
  RecorderStartPayload,
  RecorderStartResult,
  RecorderStopPayload,
} from '@/src/lib/types';
import type { CaptureContext, CaptureController, CaptureEmitInput } from './capture';
import { toCaptureEvent } from './capture';
import { startConsoleCapture } from './console-capture';
import { startDomCapture } from './dom-capture';
import { startInteractionCapture } from './interaction-capture';
import { startNetworkCapture } from './network-capture';
import { disablePageHook } from './page-hook';

class PageRecorder {
  private readonly sessionId: string;
  private readonly startedAt: string;
  private readonly startedPerformanceAt: number;
  private readonly controllers: CaptureController[] = [];

  constructor(payload: RecorderStartPayload) {
    this.sessionId = payload.sessionId;
    this.startedAt = payload.startedAt;
    this.startedPerformanceAt = performance.now();
  }

  start(): RecorderStartResult {
    const context: CaptureContext = {
      sessionId: this.sessionId,
      timestampMs: () => Math.max(0, Math.round(performance.now() - this.startedPerformanceAt)),
      emit: (event) => this.emit(event),
    };

    this.controllers.push(
      startDomCapture(context),
      startNetworkCapture(context),
      startConsoleCapture(context),
      startInteractionCapture(context),
    );

    this.emit({
      type: 'user_interaction',
      category: 'navigation',
      data: {
        action: 'navigation',
        value: window.location.href,
        target_selector: 'window.location',
      },
    });

    return this.getPageState();
  }

  stop(): void {
    while (this.controllers.length > 0) {
      this.controllers.pop()?.stop();
    }

    disablePageHook();
  }

  matches(sessionId: string): boolean {
    return this.sessionId === sessionId;
  }

  private emit(event: CaptureEmitInput): void {
    const request: BackgroundRequest = {
      type: 'REBUG_CAPTURE_EVENT',
      event: toCaptureEvent(
        {
          sessionId: this.sessionId,
          timestampMs: () => Math.max(0, Math.round(performance.now() - this.startedPerformanceAt)),
          emit: () => undefined,
        },
        event,
      ),
    };

    browser.runtime.sendMessage(request).catch(() => {
      // The background worker may be restarting; dropping one event is preferable
      // to blocking the page under test.
    });
  }

  private getPageState(): RecorderStartResult {
    return {
      url: window.location.href,
      title: document.title,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
    };
  }
}

export function installRecorderMessageHandler(): void {
  let recorder: PageRecorder | null = null;

  browser.runtime.onMessage.addListener((message: unknown) => {
    if (isStartPayload(message)) {
      recorder?.stop();
      recorder = new PageRecorder(message);
      return Promise.resolve(recorder.start());
    }

    if (isStopPayload(message)) {
      if (recorder?.matches(message.sessionId)) {
        recorder.stop();
        recorder = null;
      }

      return Promise.resolve({ stopped: true });
    }

    return undefined;
  });
}

function isStartPayload(message: unknown): message is RecorderStartPayload {
  return (
    typeof message === 'object' &&
    message !== null &&
    (message as RecorderStartPayload).type === 'REBUG_CONTENT_START' &&
    typeof (message as RecorderStartPayload).sessionId === 'string' &&
    typeof (message as RecorderStartPayload).startedAt === 'string'
  );
}

function isStopPayload(message: unknown): message is RecorderStopPayload {
  return (
    typeof message === 'object' &&
    message !== null &&
    (message as RecorderStopPayload).type === 'REBUG_CONTENT_STOP' &&
    typeof (message as RecorderStopPayload).sessionId === 'string'
  );
}
