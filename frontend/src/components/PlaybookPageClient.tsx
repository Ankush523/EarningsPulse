"use client";

import Link from "next/link";

import { AgentTracePanel } from "@/components/AgentTracePanel";
import { AppHeader } from "@/components/AppHeader";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { PlaybookView } from "@/components/PlaybookView";
import { usePlaybookStream } from "@/hooks/usePlaybookStream";

interface PlaybookPageClientProps {
  jobId: string;
}

export function PlaybookPageClient({ jobId }: PlaybookPageClientProps) {
  const { status, events, traceEvents, playbook, job, error, reconnect } =
    usePlaybookStream(jobId);

  const isRunning = status === "connecting" || status === "streaming";
  const ticker = playbook?.executive_summary.ticker ?? job?.ticker ?? "…";

  return (
    <div className="min-h-screen">
      <DisclaimerBanner />
      <AppHeader />

      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-8">
          <Link
            href="/"
            className="text-sm text-muted transition hover:text-accent"
          >
            ← Back to home
          </Link>
          <h1 className="mt-4 text-3xl font-bold">
            {isRunning ? "Generating Playbook…" : "Earnings Playbook"}
          </h1>
          <p className="mt-1 font-mono text-sm text-muted">
            {ticker} · Job {jobId}
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-[380px_1fr]">
          <AgentTracePanel
            status={status}
            events={events}
            traceEvents={traceEvents}
            error={error}
          />

          <div>
            {playbook ? (
              <PlaybookView playbook={playbook} />
            ) : isRunning ? (
              <PlaybookSkeleton ticker={ticker} />
            ) : status === "failed" ? (
              <div className="rounded-xl border border-danger/30 bg-danger/10 p-8 text-center">
                <p className="mb-4 text-danger">
                  {error ?? "Playbook generation failed."}
                </p>
                <button
                  type="button"
                  onClick={reconnect}
                  className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
                >
                  Retry stream
                </button>
              </div>
            ) : (
              <PlaybookSkeleton ticker={ticker} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function PlaybookSkeleton({ ticker }: { ticker: string }) {
  return (
    <div className="animate-pulse space-y-6">
      <div className="rounded-xl border border-card-border bg-card p-6">
        <div className="mb-4 h-4 w-24 rounded bg-card-border" />
        <div className="mb-2 h-8 w-64 rounded bg-card-border" />
        <div className="h-4 w-48 rounded bg-card-border" />
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
