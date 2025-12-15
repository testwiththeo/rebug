import type { NetworkRequestData, PageHookMessage } from '@/src/lib/types';
import type { CaptureContext, CaptureController } from './capture';
import { enablePageHook, isPageHookMessage } from './page-hook';

export function startNetworkCapture(context: CaptureContext): CaptureController {
  const messageListener = (event: MessageEvent<unknown>) => {
    if (event.source !== window || !isPageHookMessage(event.data)) {
      return;
    }

    const message: PageHookMessage = event.data;
    if (message.event.type !== 'network_request') {
      return;
    }

    context.emit({
      type: 'network_request',
      category: message.event.category,
      data: message.event.data as NetworkRequestData,
    });
  };

  window.addEventListener('message', messageListener);
  enablePageHook().catch((error: unknown) => {
    context.emit({
      type: 'console_log',
      category: 'rebug_internal',
      data: {
        level: 'warn',
        message: `Unable to enable page network hook: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
    });
  });

  const performanceObserver = createPerformanceObserver(context);

  return {
    stop: () => {
      window.removeEventListener('message', messageListener);
      performanceObserver?.disconnect();
    },
  };
}

function createPerformanceObserver(context: CaptureContext): PerformanceObserver | null {
  if (!('PerformanceObserver' in window)) {
    return null;
  }

  try {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntriesByType('resource') as PerformanceResourceTiming[]) {
        if (entry.initiatorType === 'fetch' || entry.initiatorType === 'xmlhttprequest') {
          continue;
        }

        context.emit({
          type: 'network_request',
          category: `resource:${entry.initiatorType || 'unknown'}`,
          data: {
            method: 'GET',
            url: entry.name,
            status: getResponseStatus(entry),
            request_body: null,
            response_body: null,
            duration_ms: Math.round(entry.duration),
            is_error: false,
          },
        });
      }
    });

    observer.observe({ type: 'resource', buffered: false });
    return observer;
  } catch {
    return null;
  }
}

function getResponseStatus(entry: PerformanceResourceTiming): number | undefined {
  const status = (entry as PerformanceResourceTiming & { responseStatus?: number }).responseStatus;
  return typeof status === 'number' && status > 0 ? status : undefined;
}
