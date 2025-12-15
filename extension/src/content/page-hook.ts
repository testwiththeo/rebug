import { injectScript } from 'wxt/utils/inject-script';
import type { PageHookMessage } from '@/src/lib/types';

const PAGE_HOOK_PATH = '/page-hooks.js';
const PAGE_HOOK_ENABLE_EVENT = 'rebug:page-hook-enable';
const PAGE_HOOK_DISABLE_EVENT = 'rebug:page-hook-disable';

let injectionPromise: Promise<void> | null = null;

export async function enablePageHook(): Promise<void> {
  await ensurePageHookInjected();
  window.dispatchEvent(new CustomEvent(PAGE_HOOK_ENABLE_EVENT));
}

export function disablePageHook(): void {
  window.dispatchEvent(new CustomEvent(PAGE_HOOK_DISABLE_EVENT));
}

export function isPageHookMessage(data: unknown): data is PageHookMessage {
  return (
    typeof data === 'object' &&
    data !== null &&
    (data as PageHookMessage).source === 'rebug-page-hook' &&
    typeof (data as PageHookMessage).event === 'object'
  );
}

async function ensurePageHookInjected(): Promise<void> {
  if (!injectionPromise) {
    injectionPromise = injectScript(PAGE_HOOK_PATH, { keepInDom: true }).then(() => undefined);
  }

  await injectionPromise;
}
