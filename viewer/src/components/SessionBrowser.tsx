'use client';

import { ExternalLink, RefreshCcw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { listSessions } from '@/lib/api';
import type { SessionResponse } from '@/lib/types';

export function SessionBrowser() {
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      setSessions(await listSessions(20));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : String(caughtError));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Recent Sessions</h2>
        <Button disabled={isLoading} onClick={load} size="sm" type="button" variant="ghost">
          <RefreshCcw className="mr-2 h-3 w-3" />
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
          Cannot load sessions. Check that the backend is running at the configured URL.
        </div>
      ) : null}

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 rounded-md border bg-card p-3">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-12 ml-auto" />
            </div>
          ))}
        </div>
      ) : sessions.length === 0 ? (
        <div className="rounded-md border border-dashed bg-card py-12 text-center text-sm text-muted-foreground">
          No sessions yet. Record a session with the Rebug extension to get started.
        </div>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => router.push(`/replay/${session.id}`)}
              className="flex w-full items-center gap-3 rounded-md border bg-card p-3 text-left transition-colors hover:bg-secondary/50"
              type="button"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium">
                    {hostnameFromUrl(session.url)}
                  </span>
                  <Badge variant={session.status === 'analyzed' ? 'success' : 'secondary'}>
                    {session.status}
                  </Badge>
                </div>
                <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{session.event_count} events</span>
                  {session.duration != null && <span>{formatDuration(session.duration)}</span>}
                  <span>{formatRelativeTime(session.created_at)}</span>
                </div>
              </div>
              <ExternalLink className="h-4 w-4 shrink-0 text-muted-foreground" />
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function hostnameFromUrl(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

function formatDuration(durationSec: number): string {
  const minutes = Math.floor(durationSec / 60);
  const seconds = durationSec % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}
