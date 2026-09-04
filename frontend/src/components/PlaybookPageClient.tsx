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

      <main className="mx-auto w-full max-w-5xl flex-1 px-6 pb-8 pt-8">
        <div className="no-print mb-5 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2 text-[0.95rem] text-ink-soft">
          <Link
            href="/"
            className="underline decoration-rule underline-offset-4 transition hover:text-ink hover:decoration-ink"
          >
            Back to home
          </Link>
          {isDemo && <span>Cached demo playbook</span>}
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
    <div className="max-w-measure border-t-2 border-down pt-5">
      <h1 className="text-[1.75rem] font-medium leading-tight tracking-tight">
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
          className="rounded bg-ink px-4 py-2 text-[0.95rem] font-medium text-paper transition hover:bg-ink/90"
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
    <div aria-busy={running} className="border-b border-ink pb-8">
      {ticker && <p className="font-mono text-[1.05rem] text-ink-soft">{ticker}</p>}
      <h1 className="mt-1 text-[2.25rem] font-medium leading-[1.1] tracking-tight sm:text-[2.75rem]">
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
          <div key={i}>
            <span className="block h-4 w-12 rounded-sm bg-rule-soft" />
            <span className="mt-2 block h-10 w-20 rounded-sm bg-rule-soft" />
          </div>
        ))}
      </div>
      <div className="mt-5 h-2.5 w-full rounded-sm bg-rule-soft" aria-hidden />
    </div>
  );
}
