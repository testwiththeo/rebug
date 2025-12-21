import type { SessionEvent } from '@/lib/types';
import { Badge } from '@/components/ui/badge';

interface NetworkPanelProps {
  events: SessionEvent[];
  currentMs: number;
}

export function NetworkPanel({ events, currentMs }: NetworkPanelProps) {
  const networkEvents = events.filter((event) => event.event_type === 'network_request');

  return (
    <div className="space-y-2">
      {networkEvents.length === 0 ? (
        <div className="text-sm text-muted-foreground">No network events.</div>
      ) : (
        networkEvents.map((event) => {
          const status = Number(event.data.status ?? 0);
          const isError = Boolean(event.data.is_error) || status >= 400;
          const isActive = event.timestamp_ms <= currentMs;
          return (
            <div
              className={
                isActive
                  ? 'rounded-md border bg-white p-3'
                  : 'rounded-md border bg-white/60 p-3 opacity-55'
              }
              key={event.id}
            >
              <div className="mb-2 flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                  <Badge variant={isError ? 'destructive' : 'secondary'}>
                    {String(event.data.method ?? 'GET')}
                  </Badge>
                  <span className="truncate text-sm font-medium">{shortUrl(String(event.data.url ?? ''))}</span>
                </div>
                <span className="text-xs text-muted-foreground">{formatTimestamp(event.timestamp_ms)}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground">
                <span>Status {status || 'n/a'}</span>
                <span>{String(event.data.duration_ms ?? 0)} ms</span>
                <span>{event.category ?? 'request'}</span>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

function shortUrl(url: string): string {
  try {
    const parsed = new URL(url);
    return `${parsed.pathname}${parsed.search}`;
  } catch {
    return url;
  }
}

function formatTimestamp(timestampMs: number): string {
  const seconds = Math.floor(timestampMs / 1000);
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`;
}
