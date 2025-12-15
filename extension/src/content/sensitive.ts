const CREDIT_CARD_PATTERN = /\b(?:\d[ -]*?){13,19}\b/;
const SENSITIVE_NAME_PATTERN =
  /(password|passcode|passwd|secret|token|credit|card|cc-|cvv|cvc|ssn|social.security|api.key|apikey|auth|bearer|jwt)/i;
const SENSITIVE_VALUE_PATTERNS = [
  /\b\d{3}-\d{2}-\d{4}\b/, // SSN
  /\b\d{16}\b/, // Credit card (no spaces)
  /\b(?:\d[ -]*?){13,19}\b/, // Credit card with spaces/dashes
  /^sk-[a-zA-Z0-9]{20,}$/, // API keys (OpenAI style)
  /^eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+$/, // JWT tokens
  /^Bearer\s+/i, // Bearer tokens
];

const SENSITIVE_SELECTORS = [
  'input[type="password"]',
  'input[type="hidden"]',
  'input[autocomplete^="cc-"]',
  'input[autocomplete^="current-password"]',
  'input[autocomplete^="new-password"]',
  'input[name*="password"]',
  'input[name*="credit"]',
  'input[name*="card"]',
  'input[name*="ssn"]',
  'input[name*="secret"]',
  'input[name*="token"]',
  'input[name*="api.key"]',
  'input[id*="password"]',
  'input[id*="credit"]',
  'input[id*="card"]',
];

/**
 * Check if an element matches sensitive field selectors.
 */
export function isSensitiveElement(element: Element): boolean {
  return SENSITIVE_SELECTORS.some((selector) => {
    try {
      return element.matches(selector);
    } catch {
      return false;
    }
  });
}

export function shouldMaskInput(target: EventTarget | null): boolean {
  if (
    !(
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement
    )
  ) {
    return false;
  }

  if (target instanceof HTMLInputElement) {
    const type = target.type.toLowerCase();
    if (["password", "hidden"].includes(type)) {
      return true;
    }
  }

  const nameParts = [
    target.name,
    target.id,
    target.getAttribute("autocomplete"),
    target.getAttribute("aria-label"),
    target.getAttribute("placeholder"),
  ].filter(Boolean);

  return nameParts.some((value) => SENSITIVE_NAME_PATTERN.test(String(value)));
}

export function sanitizeInputValue(target: EventTarget | null): {
  value: string | null;
  masked: boolean;
} {
  if (
    !(
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement
    )
  ) {
    return { value: null, masked: false };
  }

  if (shouldMaskInput(target) || CREDIT_CARD_PATTERN.test(target.value)) {
    return { value: "[masked]", masked: true };
  }

  return {
    value: target.value,
    masked: false,
  };
}

export function serializeBody(body: unknown): string | null {
  if (body == null) {
    return null;
  }

  if (typeof body === "string") {
    return maskSensitiveText(body);
  }

  if (body instanceof URLSearchParams) {
    return maskSensitiveText(body.toString());
  }

  if (body instanceof FormData) {
    const fields: Record<string, string> = {};
    body.forEach((value, key) => {
      fields[key] = SENSITIVE_NAME_PATTERN.test(key)
        ? "[masked]"
        : String(value);
    });
    return JSON.stringify(fields);
  }

  return "[binary or unsupported body]";
}

/**
 * Mask sensitive text content that may contain PII or credentials.
 */
export function maskSensitiveText(text: string): string {
  if (text.length > 10_000) {
    text = text.slice(0, 10_000);
  }

  for (const pattern of SENSITIVE_VALUE_PATTERNS) {
    if (pattern.test(text)) {
      return "[masked-sensitive-data]";
    }
  }

  return text;
}

/**
 * Mask sensitive attributes in HTML elements.
 */
export function maskElementAttributes(html: string): string {
  // Mask value attributes in password/hidden inputs
  return html
    .replace(
      /(<input[^>]*type=["'](?:password|hidden)["'][^>]*value=["'])([^"']+)(["'])/gi,
      "$1[masked]$3",
    )
    .replace(
      /(<input[^>]*value=["'])([^"']+)(["'][^>]*type=["'](?:password|hidden)["'])/gi,
      "$1[masked]$3",
    );
}
