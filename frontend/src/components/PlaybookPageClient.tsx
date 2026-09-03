"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AgentTracePanel } from "@/components/AgentTracePanel";
import { AppHeader } from "@/components/AppHeader";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { ExportToolbar } from "@/components/ExportToolbar";
import { GenerationProgress } from "@/components/GenerationProgress";
import { RegenerateButton } from "@/components/DemoButton";
import { PlaybookView } from "@/components/PlaybookView";
import { fetchTraceLog } from "@/lib/api";
import { usePlaybookStream } from "@/hooks/usePlaybookStream";
import type { TraceLog } from "@/lib/types";

interface PlaybookPageClientProps {
  jobId: string;
}

export function PlaybookPageClient({ jobId }: PlaybookPageClientProps) {
  const { status, events, traceEvents, playbook, job, error, reconnect } =
    usePlaybookStream(jobId);
  const [traceLog, setTraceLog] = useState<TraceLog | null>(null);

  const isRunning = status === "connecting" || status === "streaming";
  const isDemo = jobId.startsWith("demo_");
  const ticker = playbook?.executive_summary.ticker ?? job?.ticker ?? "…";

  useEffect(() => {
    if (status !== "completed" && status !== "failed") return;

    fetchTraceLog(jobId)
      .then(setTraceLog)
      .catch(() => setTraceLog(null));
  }, [jobId, status]);

  return (
    <div className="min-h-screen">
      <DisclaimerBanner />
      <AppHeader />

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="no-print mb-8">
          <Link
            href="/"
            className="text-sm text-muted transition hover:text-accent"
          >
            ← Back to home
          </Link>
          <h1 className="mt-4 text-2xl font-bold sm:text-3xl">
            {isRunning ? "Generating Playbook…" : "Earnings Playbook"}
          </h1>
          <p className="mt-1 font-mono text-sm text-muted">
            {ticker} · Job {jobId}
            {isDemo && " · Demo"}
          </p>
        </div>

        <GenerationProgress
          isRunning={isRunning}
          eventCount={events.length || traceEvents.length}
        />

        <div className="grid gap-8 lg:grid-cols-[minmax(280px,380px)_1fr]">
          <div className="no-print">
            <AgentTracePanel
              status={status}
              events={events}
              traceEvents={traceEvents}
              error={error}
            />
          </div>

          <div className="min-w-0">
            {playbook ? (
              <div className="animate-fade-in">
                <ExportToolbar
                  jobId={jobId}
                  ticker={ticker}
                  playbook={playbook}
                  traceLog={traceLog}
                />
                <div id="playbook-export">
                  <PlaybookView playbook={playbook} />
                </div>
              </div>
            ) : isRunning ? (
              <PlaybookSkeleton ticker={ticker} />
            ) : status === "failed" ? (
              <ErrorPanel
                error={error}
                ticker={ticker}
                hasPartialTrace={traceEvents.length > 0}
                onRetryStream={reconnect}
              />
            ) : (
              <PlaybookSkeleton ticker={ticker} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function ErrorPanel({
  error,
  ticker,
  hasPartialTrace,
  onRetryStream,
}: {
  error: string | null;
  ticker: string;
  hasPartialTrace: boolean;
  onRetryStream: () => void;
}) {
  return (
    <div className="rounded-xl border border-danger/30 bg-danger/10 p-8">
      <h3 className="mb-2 text-lg font-semibold text-danger">
        Playbook generation failed
      </h3>
      <p className="mb-4 text-sm text-muted">
        {error ?? "An unexpected error occurred."}
      </p>
      {hasPartialTrace && (
        <p className="mb-4 text-sm text-muted">
          Partial agent trace is available in the panel — some steps completed
          before the failure.
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onRetryStream}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
        >
          Retry stream
        </button>
        <RegenerateButton ticker={ticker} />
      </div>
    </div>
  );
}

function PlaybookSkeleton({ ticker }: { ticker: string }) {
  return (
    <div className="animate-pulse space-y-6">
      <div className="rounded-xl border border-card-border bg-card p-6">
        <div className="mb-4 h-4 w-24 rounded bg-card-border" />
        <div className="mb-2 h-8 w-64 max-w-full rounded bg-card-border" />
        <div className="h-4 w-48 max-w-full rounded bg-card-border" />
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-lg bg-card-border/60" />
          ))}
        </div>
      </div>
      <p className="text-center text-sm text-muted">
        Building playbook for {ticker}…
      </p>
    </div>
  );
}
