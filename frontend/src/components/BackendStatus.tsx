"use client";

import { useEffect, useState } from "react";

import { checkBackendHealth } from "@/lib/api";

type Status = "loading" | "healthy" | "unhealthy";

const DOT: Record<Status, string> = {
  loading: "bg-rule",
  healthy: "bg-up",
  unhealthy: "bg-down",
};

const LABEL: Record<Status, string> = {
  loading: "Checking API",
  healthy: "API connected",
  unhealthy: "API unreachable",
};

export function BackendStatus() {
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    let mounted = true;

    checkBackendHealth()
      .then((healthy) => {
        if (mounted) setStatus(healthy ? "healthy" : "unhealthy");
      })
      .catch(() => {
        if (mounted) setStatus("unhealthy");
      });

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <span className="glass-chip flex items-center gap-2 px-3 py-1.5 text-[0.85rem] text-ink-soft">
      <span className={`h-2 w-2 rounded-full ${DOT[status]}`} aria-hidden />
      <span className="sr-only sm:not-sr-only">{LABEL[status]}</span>
    </span>
  );
}
