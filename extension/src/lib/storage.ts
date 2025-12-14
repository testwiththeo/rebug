import Dexie, { type Table } from 'dexie';
import type {
  BrowserInfo,
  CaptureEventInput,
  PackagedSessionRecord,
  SessionRecord,
  StoredSessionEvent,
} from './types';

interface CreateSessionInput {
  id: string;
  url: string;
  title?: string;
  browser: BrowserInfo;
  startedAt: string;
}

interface SessionMetadataUpdate {
  url?: string;
  title?: string;
  browser?: BrowserInfo;
}

class RebugDatabase extends Dexie {
  sessions!: Table<SessionRecord, string>;
  events!: Table<StoredSessionEvent, number>;
  packages!: Table<PackagedSessionRecord, string>;

  constructor() {
    super('rebug');

    this.version(1).stores({
      sessions: '&id,status,startedAt,updatedAt',
      events: '++id,sessionId,[sessionId+sequence],type,timestampMs',
      packages: '&id,sessionId,createdAt',
    });
  }
}

export const db = new RebugDatabase();

export async function createSession(input: CreateSessionInput): Promise<SessionRecord> {
  const now = new Date().toISOString();
  const session: SessionRecord = {
    id: input.id,
    url: input.url,
    title: input.title,
    browser: input.browser,
    startedAt: input.startedAt,
    status: 'recording',
    eventCount: 0,
    createdAt: now,
    updatedAt: now,
  };

  await db.sessions.add(session);
  return session;
}

export async function updateSessionMetadata(
  sessionId: string,
  update: SessionMetadataUpdate,
): Promise<void> {
  await db.sessions.update(sessionId, {
    ...update,
    updatedAt: new Date().toISOString(),
  });
}

export async function appendSessionEvent(
  event: CaptureEventInput,
): Promise<StoredSessionEvent> {
  return db.transaction('rw', db.sessions, db.events, async () => {
    const session = await db.sessions.get(event.sessionId);
    if (!session) {
      throw new Error(`Session not found: ${event.sessionId}`);
    }

    const now = new Date().toISOString();
    const storedEvent: StoredSessionEvent = {
      ...event,
      sequence: session.eventCount + 1,
      createdAt: now,
    };

    const id = await db.events.add(storedEvent);
    const savedEvent = { ...storedEvent, id };

    await db.sessions.update(event.sessionId, {
      eventCount: savedEvent.sequence,
      updatedAt: now,
    });

    return savedEvent;
  });
}

export async function stopSession(sessionId: string): Promise<SessionRecord> {
  return db.transaction('rw', db.sessions, async () => {
    const session = await db.sessions.get(sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    const endedAt = new Date().toISOString();
    const durationMs = new Date(endedAt).getTime() - new Date(session.startedAt).getTime();

    const updates: Partial<SessionRecord> = {
      endedAt,
      durationMs,
      status: 'stopped',
      updatedAt: endedAt,
    };

    await db.sessions.update(sessionId, updates);
    return { ...session, ...updates };
  });
}

export async function markSessionError(sessionId: string): Promise<void> {
  await db.sessions.update(sessionId, {
    status: 'error',
    updatedAt: new Date().toISOString(),
  });
}

export async function markSessionPackaged(
  sessionId: string,
  packageRecord: Pick<PackagedSessionRecord, 'id' | 'sizeBytes' | 'checksum'>,
): Promise<void> {
  await db.sessions.update(sessionId, {
    status: 'packaged',
    packageId: packageRecord.id,
    sizeBytes: packageRecord.sizeBytes,
    checksum: packageRecord.checksum,
    updatedAt: new Date().toISOString(),
  });
}

export async function getSession(sessionId: string): Promise<SessionRecord | undefined> {
  return db.sessions.get(sessionId);
}

export async function getRecentSessions(limit = 8): Promise<SessionRecord[]> {
  return db.sessions.orderBy('startedAt').reverse().limit(limit).toArray();
}

export async function getSessionEvents(sessionId: string): Promise<StoredSessionEvent[]> {
  return db.events.where('sessionId').equals(sessionId).sortBy('sequence');
}

export async function savePackage(packageRecord: PackagedSessionRecord): Promise<void> {
  await db.packages.put(packageRecord);
  await markSessionPackaged(packageRecord.sessionId, packageRecord);
}

export async function getPackage(
  packageId: string,
): Promise<PackagedSessionRecord | undefined> {
  return db.packages.get(packageId);
}
