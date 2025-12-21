'use client';

import { Activity, PlayCircle } from 'lucide-react';
import { useState } from 'react';

import { ImpactDashboard } from '@/components/ImpactDashboard';
import { OpenReplayForm } from '@/components/OpenReplayForm';
import { Button } from '@/components/ui/button';

type DashboardTab = 'replay' | 'impact';

export function DashboardShell() {
  const [tab, setTab] = useState<DashboardTab>('replay');

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-8">
      <header className="mb-8 flex flex-col gap-4 border-b pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-normal">Rebug</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Works on my machine? Not anymore.
          </p>
        </div>
        <div className="flex rounded-md border bg-white p-1">
          <Button
            onClick={() => setTab('replay')}
            size="sm"
            type="button"
            variant={tab === 'replay' ? 'secondary' : 'ghost'}
          >
            <PlayCircle className="mr-2 h-4 w-4" />
            Replay
          </Button>
          <Button
            onClick={() => setTab('impact')}
            size="sm"
            type="button"
            variant={tab === 'impact' ? 'secondary' : 'ghost'}
          >
            <Activity className="mr-2 h-4 w-4" />
            Impact
          </Button>
        </div>
      </header>

      {tab === 'replay' ? (
        <section className="max-w-2xl">
          <div className="mb-3 text-sm font-semibold">Open Replay</div>
          <OpenReplayForm />
        </section>
      ) : (
        <ImpactDashboard />
      )}
    </div>
  );
}
