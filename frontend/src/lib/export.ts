"use client";

import type { Playbook, TraceLog } from "@/lib/types";

export function downloadJson(filename: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  triggerDownload(filename, blob);
}

export function downloadBlob(filename: string, blob: Blob): void {
  triggerDownload(filename, blob);
}

function triggerDownload(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function buildClientSideBundle(
  jobId: string,
  ticker: string,
  playbook: Playbook,
  trace?: TraceLog | null
): Record<string, unknown> {
  return {
    exported_at: new Date().toISOString(),
    job_id: jobId,
    ticker,
    playbook,
    trace: trace ?? null,
  };
}

export function printPlaybook(): void {
  window.print();
}
