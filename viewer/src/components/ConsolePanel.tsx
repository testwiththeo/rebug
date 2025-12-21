import type { SessionEvent } from '@/lib/types';
import { Badge } from '@/components/ui/badge';

interface ConsolePanelProps {
  events: SessionEvent[];
  currentMs: number;
}

export function ConsolePanel({ events, currentMs }: ConsolePanelProps) {
  const consoleEvents = events.filter((event) => event.event_type === 'console_log');

  return (
    <div className="space-y-2">
      {consoleEvents.length === 0 ? (
        <div className="text-sm text-muted-foreground">No console events.</div>
      ) : (
        consoleEvents.map((event) => {
          const level = String(event.data.level ?? 'log');
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
                <Badge variant={level === 'error' ? 'destructive' : 'outline'}>{level}</Badge>
                <span className="text-xs text-muted-foreground">{formatTimestamp(event.timestamp_ms)}</span>
              </div>
              <div className="break-words text-sm">{String(event.data.message ?? '')}</div>
            </div>
          );
        })
      )}
    </div>
  );
}

function formatTimestamp(timestampMs: number): string {
  const seconds = Math.floor(timestampMs / 1000);
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`;
}
