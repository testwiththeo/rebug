import type { CaptureEventInput, SessionEventData, SessionEventType } from '@/src/lib/types';

export interface CaptureEmitInput<TData extends SessionEventData = SessionEventData> {
  type: SessionEventType;
  category?: string;
  data: TData;
  masked?: boolean;
}

export interface CaptureContext {
  sessionId: string;
  timestampMs: () => number;
  emit: (event: CaptureEmitInput) => void;
}

export interface CaptureController {
  stop: () => void;
}

export function toCaptureEvent(
  context: CaptureContext,
  event: CaptureEmitInput,
): CaptureEventInput {
  return {
    sessionId: context.sessionId,
    timestampMs: context.timestampMs(),
    ...event,
  };
}
