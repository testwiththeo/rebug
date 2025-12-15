import type { ConsoleLogData, PageHookMessage } from '@/src/lib/types';
import type { CaptureContext, CaptureController } from './capture';
import { enablePageHook, isPageHookMessage } from './page-hook';

export function startConsoleCapture(context: CaptureContext): CaptureController {
  const messageListener = (event: MessageEvent<unknown>) => {
    if (event.source !== window || !isPageHookMessage(event.data)) {
      return;
    }

    const message: PageHookMessage = event.data;
    if (message.event.type !== 'console_log') {
      return;
    }

    context.emit({
      type: 'console_log',
      category: message.event.category,
      data: message.event.data as ConsoleLogData,
    });
  };

  window.addEventListener('message', messageListener);
  enablePageHook().catch((error: unknown) => {
    context.emit({
      type: 'console_log',
      category: 'rebug_internal',
      data: {
        level: 'warn',
        message: `Unable to enable page console hook: ${
          error instanceof Error ? error.message : String(error)
        }`,
      },
    });
  });

  return {
    stop: () => window.removeEventListener('message', messageListener),
  };
}
