'use client';

import { ExternalLink, RefreshCcw } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getImpactLinks } from '@/lib/api';
import type { ImpactLinkResponse } from '@/lib/types';

export function ImpactDashboard() {
  const [links, setLinks] = useState<ImpactLinkResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setIsLoading(true);
    try {
      setLinks(await getImpactLinks());
      setError(null);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : String(caughtError));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const stats = useMemo(() => {
    const sent = links.filter((link) => link.notification_status === 'sent').length;
    const failed = links.filter((link) => link.notification_status === 'failed').length;
    return { total: links.length, sent, failed };
  }, [links]);

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="grid grid-cols-3 gap-3">
          <ImpactMetric label="Links" value={stats.total} />
          <ImpactMetric label="Notified" value={stats.sent} />
          <ImpactMetric label="Failed" value={stats.failed} />
        </div>
        <Button disabled={isLoading} onClick={load} size="sm" type="button" variant="outline">
          <RefreshCcw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-md border bg-white">
        <div className="hidden grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)_120px_160px] gap-3 border-b bg-secondary/50 px-4 py-3 text-xs font-semibold uppercase text-muted-foreground md:grid">
          <span>Incident</span>
          <span>Original Bug</span>
          <span>Match</span>
          <span>Status</span>
        </div>
        {isLoading ? (
          <div className="px-4 py-8 text-sm text-muted-foreground">Loading impact links</div>
        ) : links.length === 0 ? (
          <div className="px-4 py-8 text-sm text-muted-foreground">No production impact linked yet</div>
        ) : (
          links.map((link) => <ImpactRow key={link.id} link={link} />)
        )}
      </div>
    </section>
  );
}

function ImpactMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="min-w-24 rounded-md border bg-white px-3 py-2">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-xl font-semibold">{value}</div>
    </div>
  );
}

function ImpactRow({ link }: { link: ImpactLinkResponse }) {
  return (
    <div className="grid grid-cols-1 gap-3 border-b px-4 py-3 text-sm last:border-b-0 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)_120px_160px]">
      <div className="min-w-0">
        <a
          className="font-medium text-primary underline-offset-2 hover:underline"
          href={link.incident_url}
          rel="noreferrer"
          target="_blank"
        >
          {link.incident_title}
        </a>
        <div className="mt-1 truncate text-xs text-muted-foreground">{link.original_url}</div>
      </div>
      <div className="min-w-0">
        <div className="truncate font-medium">{link.bug_title}</div>
        <div className="mt-1 flex flex-wrap gap-2">
          {link.jira_url ? (
            <a
              className="inline-flex items-center gap-1 text-xs text-primary underline-offset-2 hover:underline"
              href={link.jira_url}
              rel="noreferrer"
              target="_blank"
            >
              {link.jira_ticket_key ?? 'Jira'}
              <ExternalLink className="h-3 w-3" />
            </a>
          ) : null}
          {link.replay_url ? (
            <a
              className="inline-flex items-center gap-1 text-xs text-primary underline-offset-2 hover:underline"
              href={link.replay_url}
              rel="noreferrer"
              target="_blank"
            >
              Replay
              <ExternalLink className="h-3 w-3" />
            </a>
          ) : null}
        </div>
      </div>
      <div>
        <Badge variant="secondary">{formatScore(link.match_score)}</Badge>
        <div className="mt-1 line-clamp-2 text-xs text-muted-foreground">
          {link.match_reason ?? 'URL and error similarity'}
        </div>
      </div>
      <div>
        <Badge variant={link.notification_status === 'sent' ? 'success' : 'outline'}>
          {link.notification_status}
        </Badge>
        <div className="mt-1 text-xs text-muted-foreground">{link.bug_status ?? 'unknown'}</div>
      </div>
    </div>
  );
}

function formatScore(score: number | null): string {
  if (score == null) {
    return 'n/a';
  }
  return `${Math.round(score * 100)}%`;
}
