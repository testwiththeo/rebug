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
        <div className="py-8 text-center text-sm text-muted-foreground">No console events.</div>
      ) : (
        consoleEvents.map((event) => {
          const level = String(event.data.level ?? 'log');
          const isActive = event.timestamp_ms <= currentMs;
          return (
            <div
              className={
                isActive
                  ? 'rounded-md border bg-card p-3'
                  : 'rounded-md border bg-card/60 p-3 opacity-55'
              }
              key={event.id}
            >
              <div className="mb-2 flex items-center justify-between gap-3">
                <Badge variant={level === 'error' ? 'destructive' : level === 'warn' ? 'warning' : 'outline'}>{level}</Badge>
                <span className="text-xs text-muted-foreground">{formatTimestamp(event.timestamp_ms)}</span>
              </div>
              <pre className="whitespace-pre-wrap break-words font-mono text-xs leading-5">{String(event.data.message ?? '')}</pre>
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
