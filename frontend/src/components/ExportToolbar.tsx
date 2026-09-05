"use client";

import { useState } from "react";

import {
  buildClientSideBundle,
  downloadBlob,
  downloadJson,
  printPlaybook,
} from "@/lib/export";
import {
  getPlaybookBundleExportUrl,
  getPlaybookJsonExportUrl,
} from "@/lib/api";
import type { Playbook, TraceLog } from "@/lib/types";

interface ExportToolbarProps {
  jobId: string;
  ticker: string;
  playbook: Playbook;
  traceLog?: TraceLog | null;
}

type ExportKind = "json" | "bundle";

function exportUrl(kind: ExportKind, jobId: string): string {
  if (kind === "json") {
    return getPlaybookJsonExportUrl(jobId);
  }
  return getPlaybookBundleExportUrl(jobId);
}

function fallbackFilename(kind: ExportKind, ticker: string, jobId: string): string {
  const suffix = kind === "bundle" ? "-bundle" : "";
  return `earningspulse-${ticker.toLowerCase()}-${jobId}${suffix}.json`;
}

function saveLocalFallback(
  kind: ExportKind,
  jobId: string,
  ticker: string,
  playbook: Playbook,
  traceLog?: TraceLog | null
): void {
  const filename = fallbackFilename(kind, ticker, jobId);
  if (kind === "json") {
    downloadJson(filename, playbook);
    return;
  }
  downloadJson(
    filename,
    buildClientSideBundle(jobId, ticker, playbook, traceLog)
  );
}

async function downloadServerExport(
  kind: ExportKind,
  jobId: string,
  ticker: string
): Promise<void> {
  const response = await fetch(exportUrl(kind, jobId));
  if (!response.ok) {
    throw new Error(`Export failed (${response.status})`);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="(.+)"/);
  downloadBlob(match?.[1] ?? fallbackFilename(kind, ticker, jobId), blob);
}

export function ExportToolbar({
  jobId,
  ticker,
  playbook,
  traceLog,
}: ExportToolbarProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleServerExport = (kind: ExportKind) => {
    setLoading(kind);
    setError(null);
    void downloadServerExport(kind, jobId, ticker)
      .catch((err: unknown) => {
        saveLocalFallback(kind, jobId, ticker, playbook, traceLog);
        setError(
          err instanceof Error
            ? `${err.message}. Saved a local copy instead.`
            : "Saved a local copy instead."
        );
      })
      .finally(() => {
        setLoading(null);
      });
  };

  return (
    <div className="no-print flex flex-wrap items-center gap-x-3 gap-y-2">
      <span className="mr-1 text-[0.95rem] text-ink-soft">Export playbook</span>

      <button
        type="button"
        disabled={loading !== null}
        onClick={() => handleServerExport("json")}
        className="btn-secondary cursor-pointer rounded-xl px-3.5 py-1.5 text-[0.9rem] font-medium disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading === "json" ? "Exporting…" : "JSON"}
      </button>

      <button
        type="button"
        disabled={loading !== null}
        onClick={() => handleServerExport("bundle")}
        className="btn-secondary cursor-pointer rounded-xl px-3.5 py-1.5 text-[0.9rem] font-medium disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading === "bundle" ? "Exporting…" : "JSON + trace"}
      </button>

      <button
        type="button"
        onClick={printPlaybook}
        className="btn-primary cursor-pointer rounded-xl px-3.5 py-1.5 text-[0.9rem] font-semibold"
      >
        Print / PDF
      </button>

      {error && <p className="w-full text-[0.9rem] text-caution">{error}</p>}
    </div>
  );
}
