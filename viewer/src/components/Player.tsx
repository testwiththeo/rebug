'use client';

import { useEffect, useMemo, useRef } from 'react';
import type { eventWithTime } from 'rrweb';

import type { SessionEvent } from '@/lib/types';

interface PlayerProps {
  events: SessionEvent[];
  currentMs: number;
  isPlaying: boolean;
  speed: number;
}

export function Player({ events, currentMs, isPlaying, speed }: PlayerProps) {
  const playerTargetRef = useRef<HTMLDivElement | null>(null);
  const playerRef = useRef<any>(null);
  const rrwebEvents = useMemo(() => extractRrwebEvents(events), [events]);

  useEffect(() => {
    let cancelled = false;

    async function mountPlayer() {
      if (!playerTargetRef.current || rrwebEvents.length === 0) {
        return;
      }

      playerTargetRef.current.innerHTML = '';
      const module = await import('rrweb-player');
      if (cancelled || !playerTargetRef.current) {
        return;
      }

      const RrwebPlayer = module.default;
      playerRef.current = new RrwebPlayer({
        target: playerTargetRef.current,
        props: {
          events: rrwebEvents,
          autoPlay: false,
          showController: false,
          width: playerTargetRef.current.clientWidth,
          height: 460,
        },
      });
    }

    mountPlayer().catch(() => undefined);

    return () => {
      cancelled = true;
      playerRef.current = null;
      if (playerTargetRef.current) {
        playerTargetRef.current.innerHTML = '';
      }
    };
  }, [rrwebEvents]);

  useEffect(() => {
    const player = playerRef.current;
    if (!player) {
      return;
    }

    try {
      player.setSpeed?.(speed);
      if (isPlaying) {
        player.play?.();
      } else {
        player.pause?.();
      }
      player.goto?.(currentMs);
    } catch {
      // rrweb-player alpha APIs differ by release; the surrounding timeline remains source of truth.
    }
  }, [currentMs, isPlaying, speed]);

  if (rrwebEvents.length > 0) {
    return <div ref={playerTargetRef} className="min-h-[460px] overflow-hidden rounded-lg bg-white" />;
  }

  const currentEvent = findCurrentReplayEvent(events, currentMs);

  return (
    <div className="flex min-h-[460px] flex-col overflow-hidden rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <div className="text-sm font-semibold">DOM Event Stream</div>
        <div className="mt-1 text-xs text-muted-foreground">
          {formatTimestamp(currentMs)} / {events.length} events
        </div>
      </div>
      <div className="grid flex-1 grid-cols-[260px_minmax(0,1fr)]">
        <div className="border-r bg-secondary/50 p-3">
          <EventStack events={events} currentMs={currentMs} />
        </div>
        <div className="p-4">
          {currentEvent ? (
            <div className="space-y-3">
              <div>
                <div className="text-xs font-medium uppercase text-muted-foreground">
                  {currentEvent.event_type}
                </div>
                <div className="mt-1 text-sm font-semibold">
                  {currentEvent.category ?? `Event ${currentEvent.sequence}`}
                </div>
              </div>
              <pre className="max-h-[330px] overflow-auto rounded-md bg-slate-950 p-3 text-xs leading-5 text-slate-100">
                {JSON.stringify(currentEvent.data, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">No event at this timestamp.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function EventStack({ events, currentMs }: { events: SessionEvent[]; currentMs: number }) {
  const visibleEvents = events
    .filter((event) => event.timestamp_ms <= currentMs)
    .slice(-8)
    .reverse();

  return (
    <div className="space-y-2">
      {visibleEvents.length === 0 ? (
        <div className="text-xs text-muted-foreground">Waiting for first event</div>
      ) : (
        visibleEvents.map((event) => (
          <div key={event.id} className="rounded-md border bg-white p-2">
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="truncate font-medium">{event.category ?? event.event_type}</span>
              <span className="text-muted-foreground">{formatTimestamp(event.timestamp_ms)}</span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function extractRrwebEvents(events: SessionEvent[]): eventWithTime[] {
  return events
    .filter((event) => event.event_type === 'rrweb' || event.category === 'rrweb')
    .map((event) => {
      if ('rrweb_event' in event.data) {
        return event.data.rrweb_event as eventWithTime;
      }
      return event.data as eventWithTime;
    });
}

function findCurrentReplayEvent(events: SessionEvent[], currentMs: number): SessionEvent | undefined {
  return [...events].reverse().find((event) => event.timestamp_ms <= currentMs);
}

function formatTimestamp(timestampMs: number): string {
  const seconds = Math.floor(timestampMs / 1000);
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`;
}
