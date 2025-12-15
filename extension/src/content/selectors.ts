const MAX_TEXT_LENGTH = 120;

export function getElementSelector(target: EventTarget | Node | null): string {
  if (!target || !(target instanceof Element)) {
    return 'unknown';
  }

  if (target.id) {
    return `#${cssEscape(target.id)}`;
  }

  const testId = target.getAttribute('data-testid') ?? target.getAttribute('data-test');
  if (testId) {
    return `[data-testid="${cssEscape(testId)}"]`;
  }

  const ariaLabel = target.getAttribute('aria-label');
  if (ariaLabel) {
    return `${target.tagName.toLowerCase()}[aria-label="${cssEscape(ariaLabel)}"]`;
  }

  const name = target.getAttribute('name');
  if (name) {
    return `${target.tagName.toLowerCase()}[name="${cssEscape(name)}"]`;
  }

  const parts: string[] = [];
  let element: Element | null = target;

  while (element && element.nodeType === Node.ELEMENT_NODE && parts.length < 5) {
    const tagName = element.tagName.toLowerCase();
    const className = Array.from(element.classList)
      .filter(Boolean)
      .slice(0, 2)
      .map((classPart) => `.${cssEscape(classPart)}`)
      .join('');
    const index = getElementIndex(element);
    parts.unshift(`${tagName}${className}:nth-of-type(${index})`);
    element = element.parentElement;
  }

  return parts.join(' > ') || target.tagName.toLowerCase();
}

export function getElementLabel(target: EventTarget | Node | null): string | undefined {
  if (!target || !(target instanceof Element)) {
    return undefined;
  }

  const label =
    target.getAttribute('aria-label') ??
    target.getAttribute('title') ??
    target.textContent ??
    undefined;

  if (!label) {
    return undefined;
  }

  const normalized = label.replace(/\s+/g, ' ').trim();
  return normalized ? normalized.slice(0, MAX_TEXT_LENGTH) : undefined;
}

function getElementIndex(element: Element): number {
  let index = 1;
  let previous = element.previousElementSibling;

  while (previous) {
    if (previous.tagName === element.tagName) {
      index += 1;
    }

    previous = previous.previousElementSibling;
  }

  return index;
}

function cssEscape(value: string): string {
  if ('CSS' in window && typeof window.CSS.escape === 'function') {
    return window.CSS.escape(value);
  }

  return value.replace(/["\\]/g, '\\$&');
}
