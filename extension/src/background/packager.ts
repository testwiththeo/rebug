import { encode } from '@msgpack/msgpack';
import { gzip } from 'pako';
import {
  getSession,
  getSessionEvents,
  savePackage,
} from '@/src/lib/storage';
import type {
  PackageSummary,
  PackagedSessionRecord,
  SessionPackagePayload,
} from '@/src/lib/types';

export async function packageSession(sessionId: string): Promise<PackageSummary> {
  const session = await getSession(sessionId);
  if (!session) {
    throw new Error(`Session not found: ${sessionId}`);
  }

  const events = await getSessionEvents(sessionId);
  const payload: SessionPackagePayload = {
    session_id: session.id,
    url: session.url,
    browser: session.browser,
    started_at: session.startedAt,
    ended_at: session.endedAt,
    duration_ms: session.durationMs,
    events,
  };

  const encoded = encode(payload);
  const compressed = gzip(encoded);
  const checksum = await sha256Hex(compressed);

  const packageRecord: PackagedSessionRecord = {
    id: crypto.randomUUID(),
    sessionId,
    createdAt: new Date().toISOString(),
    sizeBytes: compressed.byteLength,
    checksum,
    data: compressed,
  };

  await savePackage(packageRecord);

  return {
    id: packageRecord.id,
    sessionId,
    sizeBytes: packageRecord.sizeBytes,
    checksum: packageRecord.checksum,
    createdAt: packageRecord.createdAt,
  };
}

async function sha256Hex(data: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', data.slice().buffer);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}
