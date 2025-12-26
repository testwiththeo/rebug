'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { PointerEvent } from 'react';

import type { SessionEvent } from '@/lib/types';

interface TimelineProps {
  events: SessionEvent[];
  currentMs: number;
  durationMs: number;
  onSeek: (timestampMs: number) => void;
}

const MARKER_COLORS: Record<string, string> = {
  console_log: 'hsl(0 84% 60%)',
  network_request: 'hsl(221 83% 53%)',
  user_interaction: 'hsl(142 71% 45%)',
  bug_marker: 'hsl(38 92% 50%)',
  dom_mutation: 'hsl(220 9% 46%)',
};

const LEGEND_ITEMS = [
  { type: 'console_log', label: 'Console', color: MARKER_COLORS.console_log },
  { type: 'network_request', label: 'Network', color: MARKER_COLORS.network_request },
  { type: 'user_interaction', label: 'Interaction', color: MARKER_COLORS.user_interaction },
  { type: 'bug_marker', label: 'Bug', color: MARKER_COLORS.bug_marker },
  { type: 'dom_mutation', label: 'DOM', color: MARKER_COLORS.dom_mutation },
];

export function Timeline({ events, currentMs, durationMs, onSeek }: TimelineProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(800);

  const markers = useMemo(() => {
    return events.filter((event) =>
      ['console_log', 'network_request', 'user_interaction', 'bug_marker', 'dom_mutation'].includes(
        event.event_type,
      ),
    );
  }, [events]);

  useEffect(() => {
    if (!containerRef.current) {
      return undefined;
    }

    const observer = new ResizeObserver(([entry]) => {
      setWidth(Math.max(320, Math.round(entry.contentRect.width)));
    });
    observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const height = 88;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }

    context.scale(ratio, ratio);
    context.clearRect(0, 0, width, height);
    context.fillStyle = 'hsl(0 0% 100%)';
    context.fillRect(0, 0, width, height);

    drawLane(context, width, 18, 'console_log', 'Console');
    drawLane(context, width, 38, 'network_request', 'Network');
    drawLane(context, width, 58, 'user_interaction', 'User');
    drawLane(context, width, 78, 'dom_mutation', 'DOM');

    for (const marker of markers) {
      const x = positionFor(marker.timestamp_ms, durationMs, width);
      const y = laneFor(marker);
      context.fillStyle = colorFor(marker);
      context.beginPath();
      context.arc(x, y, marker.event_type === 'bug_marker' ? 5 : 3.5, 0, Math.PI * 2);
      context.fill();
    }

    const currentX = positionFor(currentMs, durationMs, width);
    context.strokeStyle = 'hsl(0 84% 60%)';
    context.lineWidth = 2;
    context.beginPath();
    context.moveTo(currentX, 6);
    context.lineTo(currentX, height - 6);
    context.stroke();
  }, [currentMs, durationMs, markers, width]);

  function handlePointerDown(event: PointerEvent<HTMLCanvasElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = (event.clientX - rect.left) / rect.width;
    onSeek(Math.round(Math.max(0, Math.min(1, ratio)) * durationMs));
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLCanvasElement>) {
    const step = durationMs * 0.05;
    if (event.key === 'ArrowLeft') {
      onSeek(Math.max(0, currentMs - step));
    } else if (event.key === 'ArrowRight') {
      onSeek(Math.min(durationMs, currentMs + step));
    }
  }

  return (
    <div className="space-y-2">
      <div ref={containerRef} className="overflow-hidden rounded-lg border bg-card">
        <canvas
          ref={canvasRef}
          className="block cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          onPointerDown={handlePointerDown}
          onKeyDown={handleKeyDown}
          tabIndex={0}
          role="slider"
          aria-label="Timeline scrubber"
          aria-valuemin={0}
          aria-valuemax={durationMs}
          aria-valuenow={currentMs}
        />
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {LEGEND_ITEMS.map((item) => (
          <div key={item.type} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: item.color }}
            />
            {item.label}
          </div>
        ))}
      </div>
    </div>
  );
}

function drawLane(
  context: CanvasRenderingContext2D,
  width: number,
  y: number,
  type: string,
  label: string,
) {
  context.strokeStyle = 'hsl(220 13% 85%)';
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(76, y);
  context.lineTo(width - 10, y);
  context.stroke();

  context.fillStyle = MARKER_COLORS[type] ?? 'hsl(220 9% 46%)';
  context.font = '11px Inter, sans-serif';
  context.fillText(label, 10, y + 4);
}

function laneFor(event: SessionEvent): number {
  if (event.event_type === 'console_log') {
    return 18;
  }
  if (event.event_type === 'network_request') {
    return 38;
  }
  if (event.event_type === 'user_interaction') {
    return 58;
  }
  return 78;
}

function colorFor(event: SessionEvent): string {
  if (event.event_type === 'console_log') {
    const level = event.data.level;
    return level === 'error' ? 'hsl(0 84% 60%)' : 'hsl(38 92% 50%)';
  }
  return MARKER_COLORS[event.event_type] ?? 'hsl(220 9% 46%)';
}

function positionFor(timestampMs: number, durationMs: number, width: number): number {
  if (durationMs <= 0) {
    return 80;
  }

  return 80 + (Math.min(timestampMs, durationMs) / durationMs) * Math.max(1, width - 92);
}
