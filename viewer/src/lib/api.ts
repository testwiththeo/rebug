import type {
  AnalysisResponse,
  AnalysisTaskResponse,
  DuplicateCheckResponse,
  FileBugResponse,
  ImpactLinkResponse,
  ReplayPayload,
  SessionEventsPage,
  SessionResponse,
} from './types';

const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1';

export function getApiBaseUrl(): string {
  return (
    process.env.REBUG_API_BASE_URL ??
    process.env.NEXT_PUBLIC_REBUG_API_BASE_URL ??
    DEFAULT_API_BASE_URL
  ).replace(/\/$/, '');
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  return fetchJson<SessionResponse>(`${getApiBaseUrl()}/sessions/${sessionId}`);
}

export async function getSessionEvents(
  sessionId: string,
  limit = 2_000,
  offset = 0,
): Promise<SessionEventsPage> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return fetchJson<SessionEventsPage>(`${getApiBaseUrl()}/sessions/${sessionId}/events?${params}`);
}

export async function getReplayPayload(sessionId: string): Promise<ReplayPayload> {
  const session = await getSession(sessionId);
  const events = [];
  let offset = 0;
  const limit = 2_000;
  let total = 0;

  do {
    const page = await getSessionEvents(sessionId, limit, offset);
    events.push(...page.items);
    total = page.total;
    offset += page.items.length;
  } while (offset < total && offset > 0);

  return { session, events };
}

export async function getAnalysis(sessionId: string): Promise<AnalysisResponse | null> {
  try {
    return await fetchJson<AnalysisResponse>(`${getApiBaseUrl()}/sessions/${sessionId}/analysis`);
  } catch (error) {
    if (error instanceof Error && error.message.startsWith('404')) {
      return null;
    }
    throw error;
  }
}

export async function triggerAnalysis(
  sessionId: string,
  force = false,
): Promise<AnalysisTaskResponse> {
  const params = new URLSearchParams({ force: String(force) });
  return fetchJson<AnalysisTaskResponse>(
    `${getApiBaseUrl()}/sessions/${sessionId}/analyze?${params}`,
    { method: 'POST' },
  );
}

export async function checkDuplicate(sessionId: string): Promise<DuplicateCheckResponse> {
  return fetchJson<DuplicateCheckResponse>(
    `${getApiBaseUrl()}/sessions/${sessionId}/check-duplicate`,
    { method: 'POST' },
  );
}

export async function fileBug(sessionId: string): Promise<FileBugResponse> {
  return fetchJson<FileBugResponse>(`${getApiBaseUrl()}/sessions/${sessionId}/file`, {
    method: 'POST',
  });
}

export async function getImpactLinks(limit = 100): Promise<ImpactLinkResponse[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  return fetchJson<ImpactLinkResponse[]>(`${getApiBaseUrl()}/impact/links?${params}`);
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      accept: 'application/json',
      ...init?.headers,
    },
    cache: 'no-store',
    ...init,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }

  return (await response.json()) as T;
}
