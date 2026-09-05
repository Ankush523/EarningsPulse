"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppHeader } from "@/components/AppHeader";
import { RegenerateButton } from "@/components/DemoButton";
import { ExportToolbar } from "@/components/ExportToolbar";
import { PlaybookView } from "@/components/PlaybookView";
import { RunPanel } from "@/components/RunPanel";
import { SiteFooter } from "@/components/SiteFooter";
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
  const ticker = playbook?.executive_summary.ticker ?? job?.ticker ?? null;

  useEffect(() => {
    if (status !== "completed" && status !== "failed") return;

    fetchTraceLog(jobId)
      .then(setTraceLog)
      .catch(() => setTraceLog(null));
  }, [jobId, status]);

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />

      <main className="mx-auto w-full max-w-page flex-1 px-5 pb-10 pt-8 sm:px-6 lg:px-8">
        <div className="no-print mb-5 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2 text-[0.95rem] text-ink-soft">
          <Link href="/" className="link-glass font-medium">
            Back to home
          </Link>
          {isDemo && <span className="glass-chip px-3 py-1">Cached demo playbook</span>}
        </div>

        <RunPanel
          status={status}
          events={events}
          traceEvents={traceEvents}
          error={status === "failed" ? null : error}
          durationMs={playbook?.metadata.generation_time_ms ?? traceLog?.total_latency_ms}
        />

        <div className="mt-12">
          {playbook ? (
            <div className="reveal">
              <div className="mb-8 flex justify-end">
                <ExportToolbar
                  jobId={jobId}
                  ticker={ticker ?? ""}
                  playbook={playbook}
                  traceLog={traceLog}
                />
              </div>
              <div id="playbook-export">
                <PlaybookView playbook={playbook} />
              </div>
            </div>
          ) : status === "failed" ? (
            <ErrorPanel
              error={error}
              ticker={ticker}
              hasPartialTrace={traceEvents.length > 0}
              onRetryStream={reconnect}
            />
          ) : (
            <PlaybookSkeleton ticker={ticker} running={isRunning} />
          )}
        </div>
      </main>

      <SiteFooter />
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
  ticker: string | null;
  hasPartialTrace: boolean;
  onRetryStream: () => void;
}) {
  return (
    <div className="glass-panel max-w-measure border-t-2 border-down/60 p-6 sm:p-8">
      <h1 className="text-[1.75rem] font-semibold leading-tight tracking-tight">
        The playbook could not be finished
      </h1>
      <p className="mt-3 text-ink-soft">
        {error ?? "The run stopped before a playbook was written."}
      </p>
      {hasPartialTrace && (
        <p className="mt-2 text-ink-soft">
          The steps that did finish are in the run log above.
        </p>
      )}
      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onRetryStream}
          className="btn-primary cursor-pointer rounded-xl px-4 py-2 text-[0.95rem] font-semibold"
        >
          Reconnect
        </button>
        {ticker && <RegenerateButton ticker={ticker} />}
      </div>
    </div>
  );
}

function PlaybookSkeleton({
  ticker,
  running,
}: {
  ticker: string | null;
  running: boolean;
}) {
  return (
    <div aria-busy={running} className="glass-panel-strong p-6 sm:p-8">
      {ticker && <p className="font-mono text-[1.05rem] text-ink-soft">{ticker}</p>}
      <h1 className="mt-1 text-[2.25rem] font-semibold leading-[1.1] tracking-tight sm:text-[2.75rem]">
        {!running
          ? "Loading the playbook"
          : ticker
            ? `Writing the ${ticker} playbook`
            : "Writing the playbook"}
      </h1>
      <p className="mt-3 max-w-measure text-ink-soft">
        {running
          ? "The agents are reading filings, news and price history. The document appears here as soon as the synthesis step finishes."
          : "Fetching the saved run."}
      </p>
      <div className="mt-10 grid grid-cols-3 gap-4" aria-hidden>
        {[0, 1, 2].map((i) => (
          <div key={i} className="glass-chip rounded-2xl px-4 py-3">
            <span className="glass-skeleton block h-4 w-12" />
            <span className="glass-skeleton mt-2 block h-10 w-20" />
          </div>
        ))}
      </div>
      <div className="glass-skeleton mt-5 h-3 w-full rounded-full" aria-hidden />
    </div>
  );
}
