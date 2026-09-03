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

export function ExportToolbar({
  jobId,
  ticker,
  playbook,
  traceLog,
}: ExportToolbarProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleServerExport = async (kind: "json" | "bundle") => {
    setLoading(kind);
    setError(null);
    try {
      const url =
        kind === "json"
          ? getPlaybookJsonExportUrl(jobId)
          : getPlaybookBundleExportUrl(jobId);
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Export failed (${response.status})`);
      }
      const blob = await response.blob();
      const disposition = response.headers.get("content-disposition") ?? "";
      const match = disposition.match(/filename="(.+)"/);
      const filename =
        match?.[1] ??
        `earningspulse-${ticker.toLowerCase()}-${jobId}${kind === "bundle" ? "-bundle" : ""}.json`;

      downloadBlob(filename, blob);
    } catch (err) {
      if (kind === "json") {
        downloadJson(
          `earningspulse-${ticker.toLowerCase()}-${jobId}.json`,
          playbook
        );
      } else {
        downloadJson(
          `earningspulse-${ticker.toLowerCase()}-${jobId}-bundle.json`,
          buildClientSideBundle(jobId, ticker, playbook, traceLog)
        );
      }
      setError(
        err instanceof Error
          ? `${err.message} — saved locally instead`
          : "Saved locally instead"
      );
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="no-print mb-6 flex flex-wrap items-center gap-3 rounded-xl border border-card-border bg-card p-4">
      <p className="mr-auto text-sm font-medium">Export playbook</p>

      <button
        type="button"
        disabled={loading !== null}
        onClick={() => handleServerExport("json")}
        className="rounded-lg border border-card-border bg-background px-4 py-2 text-sm transition hover:border-accent disabled:opacity-50"
      >
        {loading === "json" ? "Exporting…" : "JSON"}
      </button>

      <button
        type="button"
        disabled={loading !== null}
        onClick={() => handleServerExport("bundle")}
        className="rounded-lg border border-card-border bg-background px-4 py-2 text-sm transition hover:border-accent disabled:opacity-50"
      >
        {loading === "bundle" ? "Exporting…" : "JSON + Trace"}
      </button>

      <button
        type="button"
        onClick={printPlaybook}
        className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-accent-hover"
      >
        Print / PDF
      </button>

      {error && (
        <p className="w-full text-xs text-warning">{error}</p>
      )}
    </div>
  );
}
