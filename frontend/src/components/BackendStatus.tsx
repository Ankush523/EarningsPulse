"use client";

import { useEffect, useState } from "react";

import { checkBackendHealth } from "@/lib/api";

type Status = "loading" | "healthy" | "unhealthy";

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

  const color =
    status === "healthy"
      ? "bg-success"
      : status === "unhealthy"
        ? "bg-danger"
        : "bg-warning";

  const label =
    status === "healthy"
      ? "API Online"
      : status === "unhealthy"
        ? "API Offline"
        : "Checking...";

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={`h-2 w-2 rounded-full ${color}`} aria-hidden />
      <span className="font-mono text-muted">{label}</span>
    </div>
  );
}
