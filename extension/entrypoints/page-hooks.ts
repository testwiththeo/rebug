export default defineUnlistedScript(() => {
  const HOOK_FLAG = '__REBUG_PAGE_HOOK__';
  const ENABLE_EVENT = 'rebug:page-hook-enable';
  const DISABLE_EVENT = 'rebug:page-hook-disable';
  const MAX_BODY_LENGTH = 20_000;
  const SENSITIVE_PATTERN = /(password|passcode|passwd|secret|token|credit|card|cc-|cvv|cvc)/i;
  const CREDIT_CARD_PATTERN = /\b(?:\d[ -]*?){13,19}\b/;

  type HookedWindow = Window & {
    [HOOK_FLAG]?: boolean;
  };

  type HookEvent =
    | {
        type: 'network_request';
        category: 'fetch' | 'xhr';
        data: {
          method: string;
          url: string;
          status?: number;
          request_body?: string | null;
          response_body?: string | null;
          duration_ms: number;
          is_error: boolean;
        };
      }
    | {
        type: 'console_log';
        category: 'console_log' | 'console_warn' | 'console_error' | 'console_info';
        data: {
          level: 'log' | 'warn' | 'error' | 'info';
          message: string;
          stack_trace?: string;
        };
      };

  const hookedWindow = window as HookedWindow;
  if (hookedWindow[HOOK_FLAG]) {
    return;
  }

  hookedWindow[HOOK_FLAG] = true;
  let enabled = false;

  window.addEventListener(ENABLE_EVENT, () => {
    enabled = true;
  });

  window.addEventListener(DISABLE_EVENT, () => {
    enabled = false;
  });

  function postEvent(event: HookEvent): void {
    if (!enabled) {
      return;
    }

    window.postMessage(
      {
        source: 'rebug-page-hook',
        event,
      },
      '*',
    );
  }

  function sanitizeBody(body: unknown): string | null {
    if (body == null) {
      return null;
    }

    let value: string;
    if (typeof body === 'string') {
      value = body;
    } else if (body instanceof URLSearchParams) {
      value = body.toString();
    } else if (body instanceof FormData) {
      const fields: Record<string, string> = {};
      body.forEach((fieldValue, key) => {
        fields[key] = SENSITIVE_PATTERN.test(key) ? '[masked]' : String(fieldValue);
      });
      value = JSON.stringify(fields);
    } else {
      return '[binary or unsupported body]';
    }

    return SENSITIVE_PATTERN.test(value) || CREDIT_CARD_PATTERN.test(value)
      ? '[masked]'
      : value.slice(0, MAX_BODY_LENGTH);
  }

  async function readResponseBody(response: Response): Promise<string | null> {
    const contentType = response.headers.get('content-type') ?? '';
    if (
      !contentType.includes('json') &&
      !contentType.includes('text') &&
      !contentType.includes('xml') &&
      !contentType.includes('html')
    ) {
      return null;
    }

    try {
      const text = await response.clone().text();
      return sanitizeBody(text);
    } catch {
      return null;
    }
  }

  function getFetchUrl(input: RequestInfo | URL): string {
    if (typeof input === 'string') {
      return input;
    }

    if (input instanceof URL) {
      return input.href;
    }

    return input.url;
  }

  function getFetchMethod(input: RequestInfo | URL, init?: RequestInit): string {
    if (init?.method) {
      return init.method.toUpperCase();
    }

    if (input instanceof Request) {
      return input.method.toUpperCase();
    }

    return 'GET';
  }

  const originalFetch = window.fetch;
  window.fetch = function rebugFetch(input: RequestInfo | URL, init?: RequestInit) {
    const startedAt = performance.now();
    const method = getFetchMethod(input, init);
    const url = getFetchUrl(input);
    const requestBody = sanitizeBody(init?.body);

    return originalFetch
      .call(this, input, init)
      .then((response) => {
        const durationMs = Math.round(performance.now() - startedAt);
        readResponseBody(response).then((responseBody) => {
          postEvent({
            type: 'network_request',
            category: 'fetch',
            data: {
              method,
              url,
              status: response.status,
              request_body: requestBody,
              response_body: responseBody,
              duration_ms: durationMs,
              is_error: response.status >= 400,
            },
          });
        });

        return response;
      })
      .catch((error: unknown) => {
        postEvent({
          type: 'network_request',
          category: 'fetch',
          data: {
            method,
            url,
            request_body: requestBody,
            response_body: error instanceof Error ? error.message : String(error),
            duration_ms: Math.round(performance.now() - startedAt),
            is_error: true,
          },
        });

        throw error;
      });
  };

  const xhrMeta = new WeakMap<
    XMLHttpRequest,
    {
      method: string;
      url: string;
      requestBody: string | null;
      startedAt: number;
    }
  >();
  const originalOpen = XMLHttpRequest.prototype.open as (
    this: XMLHttpRequest,
    method: string,
    url: string | URL,
    async?: boolean,
    username?: string | null,
    password?: string | null,
  ) => void;
  const originalSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function rebugXhrOpen(
    method: string,
    url: string | URL,
    asyncFlag: boolean = true,
    username?: string | null,
    password?: string | null,
  ) {
    xhrMeta.set(this, {
      method: method.toUpperCase(),
      url: String(url),
      requestBody: null,
      startedAt: 0,
    });

    return originalOpen.call(this, method, url, asyncFlag, username, password);
  };

  XMLHttpRequest.prototype.send = function rebugXhrSend(body?: XMLHttpRequestBodyInit | Document | null) {
    const meta = xhrMeta.get(this);
    if (meta) {
      meta.startedAt = performance.now();
      meta.requestBody = sanitizeBody(body);
    }

    this.addEventListener(
      'loadend',
      () => {
        const currentMeta = xhrMeta.get(this);
        if (!currentMeta) {
          return;
        }

        let responseBody: string | null = null;
        try {
          responseBody =
            typeof this.responseText === 'string' ? sanitizeBody(this.responseText) : null;
        } catch {
          responseBody = null;
        }

        postEvent({
          type: 'network_request',
          category: 'xhr',
          data: {
            method: currentMeta.method,
            url: currentMeta.url,
            status: this.status,
            request_body: currentMeta.requestBody,
            response_body: responseBody,
            duration_ms: Math.round(performance.now() - currentMeta.startedAt),
            is_error: this.status === 0 || this.status >= 400,
          },
        });
      },
      { once: true },
    );

    return originalSend.call(this, body);
  };

  const consoleCategoryByLevel = {
    log: 'console_log',
    warn: 'console_warn',
    error: 'console_error',
    info: 'console_info',
  } as const;

  (['log', 'warn', 'error', 'info'] as const).forEach((level) => {
    const original = console[level];

    console[level] = function rebugConsole(...args: unknown[]) {
      original.apply(console, args);

      const firstError = args.find((arg): arg is Error => arg instanceof Error);
      postEvent({
        type: 'console_log',
        category: consoleCategoryByLevel[level],
        data: {
          level,
          message: args.map(formatConsoleArg).join(' '),
          stack_trace: firstError?.stack,
        },
      });
    };
  });

  function formatConsoleArg(arg: unknown): string {
    if (arg instanceof Error) {
      return arg.message;
    }

    if (typeof arg === 'string') {
      return arg;
    }

    try {
      return JSON.stringify(arg);
    } catch {
      return String(arg);
    }
  }
});
