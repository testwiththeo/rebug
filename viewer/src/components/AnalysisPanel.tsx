'use client';

import { AlertTriangle, RefreshCcw, Send, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { fileBug, getAnalysis, triggerAnalysis } from '@/lib/api';
import type { AnalysisResponse, FileBugResponse } from '@/lib/types';

interface AnalysisPanelProps {
  sessionId: string;
}

export function AnalysisPanel({ sessionId }: AnalysisPanelProps) {
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTriggering, setIsTriggering] = useState(false);
  const [isFiling, setIsFiling] = useState(false);
  const [fileResult, setFileResult] = useState<FileBugResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const nextAnalysis = await getAnalysis(sessionId);
        if (!cancelled) {
          setAnalysis(nextAnalysis);
          setError(null);
        }
      } catch (caughtError) {
        if (!cancelled) {
          setError(caughtError instanceof Error ? caughtError.message : String(caughtError));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    if (!analysis || !['queued', 'running'].includes(analysis.status)) {
      return undefined;
    }

    const interval = window.setInterval(async () => {
      const nextAnalysis = await getAnalysis(sessionId);
      setAnalysis(nextAnalysis);
    }, 2_000);

    return () => window.clearInterval(interval);
  }, [analysis, sessionId]);

  async function runAnalysis(force: boolean) {
    setIsTriggering(true);
    setError(null);
    try {
      await triggerAnalysis(sessionId, force);
      const nextAnalysis = await getAnalysis(sessionId);
      setAnalysis(nextAnalysis);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : String(caughtError));
    } finally {
      setIsTriggering(false);
    }
  }

  async function submitBug() {
    setIsFiling(true);
    setError(null);
    try {
      const result = await fileBug(sessionId);
      setFileResult(result);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : String(caughtError));
    } finally {
      setIsFiling(false);
    }
  }

  const duplicateMatches = analysis?.duplicate_check.matches ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">AI Analysis</div>
          <div className="text-xs text-muted-foreground">
            {analysis ? statusLabel(analysis.status) : isLoading ? 'Loading' : 'Not generated'}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {analysis?.status === 'completed' ? (
            <Button disabled={isFiling} onClick={submitBug} size="sm" type="button">
              <Send className="mr-2 h-4 w-4" />
              {isFiling ? 'Filing' : 'File Bug'}
            </Button>
          ) : null}
          <Button
            disabled={isTriggering || Boolean(analysis && ['queued', 'running'].includes(analysis.status))}
            onClick={() => runAnalysis(Boolean(analysis))}
            size="sm"
            type="button"
            variant={analysis ? 'outline' : 'default'}
          >
            {analysis ? <RefreshCcw className="mr-2 h-4 w-4" /> : <Sparkles className="mr-2 h-4 w-4" />}
            {analysis ? 'Regenerate' : 'Analyze'}
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {analysis?.duplicate_check.is_duplicate ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-900">
            <AlertTriangle className="h-4 w-4" />
            Possible duplicate
          </div>
          <div className="mt-2 space-y-1 text-sm text-amber-900">
            {duplicateMatches.map((match, index) => (
              <div key={String(match.id ?? index)}>
                {String(match.title ?? match.id)} ({String(match.similarity ?? 'n/a')})
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {fileResult ? (
        <section className="rounded-md border border-emerald-200 bg-emerald-50 p-3">
          <div className="text-sm font-semibold text-emerald-950">
            Bug filing {fileResult.status}
          </div>
          <div className="mt-2 space-y-1 text-sm text-emerald-900">
            {fileResult.jira ? (
              <a
                className="block underline underline-offset-2"
                href={fileResult.jira.ticket_url}
                rel="noreferrer"
                target="_blank"
              >
                Jira {fileResult.jira.ticket_key}
              </a>
            ) : null}
            {fileResult.slack?.message_url ? (
              <a
                className="block underline underline-offset-2"
                href={fileResult.slack.message_url}
                rel="noreferrer"
                target="_blank"
              >
                Slack notification
              </a>
            ) : fileResult.slack ? (
              <span className="block">Slack notification sent</span>
            ) : null}
            {fileResult.error_message ? (
              <span className="block text-amber-800">{fileResult.error_message}</span>
            ) : null}
          </div>
        </section>
      ) : null}

      {!analysis ? (
        <div className="rounded-md border bg-white p-3 text-sm text-muted-foreground">
          Run analysis to generate reproduction steps, root-cause evidence, and duplicate checks.
        </div>
      ) : null}

      {analysis?.status === 'failed' ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {analysis.error_message ?? 'Analysis failed.'}
        </div>
      ) : null}

      {analysis?.status === 'completed' ? (
        <>
          <section className="rounded-md border bg-white p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="text-sm font-semibold">{analysis.summary ?? 'Analysis complete'}</div>
              {analysis.confidence != null ? (
                <Badge variant="secondary">{Math.round(analysis.confidence * 100)}%</Badge>
              ) : null}
            </div>
            <div className="text-xs text-muted-foreground">
              Severity: {analysis.severity_suggestion ?? 'not suggested'}
            </div>
          </section>

          <section className="rounded-md border bg-white p-3">
            <div className="mb-2 text-sm font-semibold">Reproduction Steps</div>
            <ol className="space-y-2">
              {analysis.steps.map((step, index) => (
                <li className="grid grid-cols-[24px_minmax(0,1fr)] gap-2 text-sm" key={index}>
                  <span className="text-muted-foreground">{String(step.order ?? index + 1)}.</span>
                  <span>
                    <strong>{String(step.action ?? 'Step')}</strong>{' '}
                    <span>{String(step.value ?? '')}</span>
                    <span className="block text-xs text-muted-foreground">
                      Actual: {String(step.actual ?? 'n/a')}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          </section>

          <section className="rounded-md border bg-white p-3">
            <div className="mb-2 text-sm font-semibold">Root Cause</div>
            <div className="text-sm">{String(analysis.root_cause.summary ?? 'Unknown')}</div>
            <div className="mt-2 text-xs text-muted-foreground">
              Category: {String(analysis.root_cause.category ?? 'unknown')}
            </div>
            <div className="mt-3 space-y-2">
              {evidenceChain(analysis).map((item, index) => (
                <div className="rounded border bg-secondary/50 p-2 text-xs" key={index}>
                  <div className="font-medium">
                    {String(item.event_type ?? 'event')} @ {String(item.timestamp_ms ?? 'n/a')}ms
                  </div>
                  <div className="mt-1 text-muted-foreground">{String(item.detail ?? '')}</div>
                </div>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

function statusLabel(status: string): string {
  if (status === 'queued') {
    return 'Queued';
  }
  if (status === 'running') {
    return 'Running';
  }
  if (status === 'completed') {
    return 'Complete';
  }
  if (status === 'failed') {
    return 'Failed';
  }
  return status;
}

function evidenceChain(analysis: AnalysisResponse): Array<Record<string, unknown>> {
  const chain = analysis.root_cause.evidence_chain;
  return Array.isArray(chain) ? (chain as Array<Record<string, unknown>>) : [];
}
