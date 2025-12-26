'use client';

import { Pause, Play, RotateCcw } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import type { ReplayPayload, SessionEvent } from '@/lib/types';
import { ConsolePanel } from './ConsolePanel';
import { AnalysisPanel } from './AnalysisPanel';
import { NetworkPanel } from './NetworkPanel';
import { Player } from './Player';
import { Timeline } from './Timeline';

const SPEEDS = [0.5, 1, 2];

export function SessionReplay({ payload }: { payload: ReplayPayload }) {
  const { session, events } = payload;
  const durationMs = useMemo(() => getDurationMs(session.duration, events), [session.duration, events]);
  const [currentMs, setCurrentMs] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);

  const counts = useMemo(() => getEventCounts(events), [events]);

  useEffect(() => {
    if (!isPlaying) {
      return undefined;
    }

    const interval = window.setInterval(() => {
      setCurrentMs((value) => {
        const next = value + 250 * speed;
        if (next >= durationMs) {
          setIsPlaying(false);
          return durationMs;
        }
        return next;
      });
    }, 250);

    return () => window.clearInterval(interval);
  }, [durationMs, isPlaying, speed]);

  function seek(timestampMs: number) {
    setCurrentMs(Math.max(0, Math.min(durationMs, timestampMs)));
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-4 px-4 py-4 lg:px-6">
        <header className="flex flex-col gap-3 border-b pb-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="truncate text-xl font-semibold">{hostnameFromUrl(session.url)}</h1>
              <Badge variant="success">{session.status}</Badge>
            </div>
            <div className="mt-1 truncate text-sm text-muted-foreground">{session.url}</div>
          </div>
          <div className="grid grid-cols-4 gap-2 text-right text-sm">
            <Metric label="Events" value={String(session.event_count)} />
            <Metric label="Console" value={String(counts.console)} />
            <Metric label="Network" value={String(counts.network)} />
            <Metric label="Duration" value={formatDuration(durationMs)} />
          </div>
        </header>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
          <div className="min-w-0 space-y-4">
            <Card>
              <CardContent className="p-3">
                <Player events={events} currentMs={currentMs} isPlaying={isPlaying} speed={speed} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle>Timeline</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Timeline
                  currentMs={currentMs}
                  durationMs={durationMs}
                  events={events}
                  onSeek={seek}
                />
                <div className="grid gap-3 lg:grid-cols-[auto_minmax(0,1fr)_auto] lg:items-center">
                  <div className="flex items-center gap-2">
                    <Button
                      aria-label={isPlaying ? 'Pause' : 'Play'}
                      onClick={() => setIsPlaying((value) => !value)}
                      size="icon"
                      title={isPlaying ? 'Pause' : 'Play'}
                      type="button"
                    >
                      {isPlaying ? <Pause size={16} /> : <Play size={16} />}
                    </Button>
                    <Button
                      aria-label="Restart"
                      onClick={() => {
                        setCurrentMs(0);
                        setIsPlaying(false);
                      }}
                      size="icon"
                      title="Restart"
                      type="button"
                      variant="outline"
                    >
                      <RotateCcw size={16} />
                    </Button>
                  </div>
                  <Slider
                    max={durationMs}
                    min={0}
                    onValueChange={([value]) => seek(value)}
                    step={100}
                    value={[currentMs]}
                  />
                  <div className="flex items-center justify-between gap-3">
                    <span className="w-20 text-sm tabular-nums text-muted-foreground">
                      {formatDuration(currentMs)}
                    </span>
                    <div className="flex rounded-md border bg-card p-1" role="radiogroup" aria-label="Playback speed">
                      {SPEEDS.map((speedOption) => (
                        <button
                          aria-checked={speed === speedOption}
                          className={
                            speed === speedOption
                              ? 'rounded bg-primary px-2 py-1 text-xs font-medium text-primary-foreground'
                              : 'rounded px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-secondary'
                          }
                          key={speedOption}
                          onClick={() => setSpeed(speedOption)}
                          role="radio"
                          type="button"
                        >
                          {speedOption}x
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <aside className="grid content-start gap-4">
            <Card>
              <CardContent className="p-4">
                <AnalysisPanel sessionId={session.id} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Console</CardTitle>
              </CardHeader>
              <CardContent className="max-h-[360px] overflow-auto">
                <ConsolePanel currentMs={currentMs} events={events} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Network</CardTitle>
              </CardHeader>
              <CardContent className="max-h-[420px] overflow-auto">
                <NetworkPanel currentMs={currentMs} events={events} />
              </CardContent>
            </Card>
          </aside>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-white px-3 py-2">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="font-semibold tabular-nums">{value}</div>
    </div>
  );
}

function getDurationMs(durationSec: number | null, events: SessionEvent[]): number {
  const eventDuration = events.reduce((max, event) => Math.max(max, event.timestamp_ms), 0);
  return Math.max(durationSec ? durationSec * 1000 : 0, eventDuration, 1);
}

function getEventCounts(events: SessionEvent[]) {
  return events.reduce(
    (counts, event) => {
      if (event.event_type === 'console_log') {
        counts.console += 1;
      }
      if (event.event_type === 'network_request') {
        counts.network += 1;
      }
      if (event.event_type === 'user_interaction') {
        counts.user += 1;
      }
      return counts;
    },
    { console: 0, network: 0, user: 0 },
  );
}

function formatDuration(durationMs: number): string {
  const totalSeconds = Math.floor(durationMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

function hostnameFromUrl(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}
