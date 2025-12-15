import type { CaptureContext, CaptureController } from './capture';
import { getElementLabel, getElementSelector } from './selectors';
import { sanitizeInputValue } from './sensitive';

const INPUT_DEBOUNCE_MS = 300;
const SCROLL_THROTTLE_MS = 500;

export function startInteractionCapture(context: CaptureContext): CaptureController {
  const inputTimers = new WeakMap<Element, number>();
  let lastScrollCapturedAt = 0;

  const clickListener = (event: MouseEvent) => {
    context.emit({
      type: 'user_interaction',
      category: 'click',
      data: {
        action: 'click',
        target_selector: getElementSelector(event.target),
        coordinates: {
          x: event.clientX,
          y: event.clientY,
        },
        label: getElementLabel(event.target),
      },
    });
  };

  const inputListener = (event: Event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    const previousTimer = inputTimers.get(event.target);
    if (previousTimer) {
      window.clearTimeout(previousTimer);
    }

    const timer = window.setTimeout(() => {
      const sanitized = sanitizeInputValue(event.target);
      context.emit({
        type: 'user_interaction',
        category: 'input',
        data: {
          action: 'input',
          target_selector: getElementSelector(event.target),
          value: sanitized.value,
          label: getElementLabel(event.target),
        },
        masked: sanitized.masked,
      });
    }, INPUT_DEBOUNCE_MS);

    inputTimers.set(event.target, timer);
  };

  const scrollListener = () => {
    const now = Date.now();
    if (now - lastScrollCapturedAt < SCROLL_THROTTLE_MS) {
      return;
    }

    lastScrollCapturedAt = now;
    context.emit({
      type: 'user_interaction',
      category: 'scroll',
      data: {
        action: 'scroll',
        scroll_position: {
          top: window.scrollY,
          left: window.scrollX,
        },
      },
    });
  };

  const navigationListener = () => {
    context.emit({
      type: 'user_interaction',
      category: 'navigation',
      data: {
        action: 'navigation',
        value: window.location.href,
      },
    });
  };

  document.addEventListener('click', clickListener, true);
  document.addEventListener('input', inputListener, true);
  window.addEventListener('scroll', scrollListener, { capture: true, passive: true });
  window.addEventListener('popstate', navigationListener);
  window.addEventListener('hashchange', navigationListener);

  return {
    stop: () => {
      document.removeEventListener('click', clickListener, true);
      document.removeEventListener('input', inputListener, true);
      window.removeEventListener('scroll', scrollListener, true);
      window.removeEventListener('popstate', navigationListener);
      window.removeEventListener('hashchange', navigationListener);
    },
  };
}
