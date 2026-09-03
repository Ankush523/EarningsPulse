"use client";

import { useEffect, useState } from "react";

interface GenerationProgressProps {
  isRunning: boolean;
  eventCount: number;
}

export function GenerationProgress({
  isRunning,
  eventCount,
}: GenerationProgressProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isRunning) return;

    setElapsed(0);
    const started = Date.now();
    const interval = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - started) / 1000));
    }, 1000);

    return () => window.clearInterval(interval);
  }, [isRunning]);

  if (!isRunning) return null;

  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;
  const timeLabel =
    minutes > 0
      ? `${minutes}m ${seconds.toString().padStart(2, "0")}s`
      : `${seconds}s`;

  const slowWarning = elapsed >= 90;

  return (
    <div className="no-print mb-6 rounded-xl border border-accent/20 bg-accent/5 p-4 transition-opacity duration-300">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium">Agent pipeline running</p>
          <p className="mt-0.5 text-xs text-muted">
            {eventCount} trace events · Elapsed {timeLabel}
          </p>
        </div>
        <div className="h-2 w-32 overflow-hidden rounded-full bg-card-border">
          <div className="h-full w-1/2 animate-pulse rounded-full bg-accent" />
        </div>
      </div>
      {slowWarning && (
        <p className="mt-3 text-xs text-warning">
          Taking longer than usual — external APIs may be slow. Typical runs
          finish under 2 minutes.
        </p>
      )}
    </div>
  );
}
