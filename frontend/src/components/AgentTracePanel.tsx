"use client";

import { useState } from "react";

import { formatDateTime, formatLatency } from "@/lib/format";
import type { SSEEvent, TraceEvent } from "@/lib/types";
import type { StreamStatus } from "@/hooks/usePlaybookStream";

interface AgentTracePanelProps {
  status: StreamStatus;
  events: SSEEvent[];
  traceEvents: TraceEvent[];
  error: string | null;
}

const STATUS_LABEL: Record<StreamStatus, string> = {
  idle: "Waiting",
  connecting: "Connecting",
  streaming: "Running",
  completed: "Complete",
  failed: "Failed",
};

const STATUS_COLOR: Record<StreamStatus, string> = {
  idle: "bg-muted",
  connecting: "bg-warning",
  streaming: "bg-accent animate-pulse",
  completed: "bg-success",
  failed: "bg-danger",
};

function eventIcon(type: string): string {
  switch (type) {
    case "agent_start":
    case "agent_started":
      return "◆";
    case "agent_complete":
    case "agent_completed":
      return "✓";
    case "tool_call":
    case "tool_call_started":
    case "tool_call_completed":
      return "⚙";
    case "run_started":
      return "▶";
    case "run_completed":
    case "playbook_ready":
      return "★";
    case "error":
    case "run_failed":
      return "✕";
    default:
      return "·";
  }
}

function eventLabel(event: SSEEvent | TraceEvent): string {
  if ("type" in event && event.type) {
    const sse = event as SSEEvent;
    if (sse.agent_name) return sse.agent_name;
    if (sse.tool_name) return sse.tool_name;
    return sse.message ?? sse.type;
  }
  const trace = event as TraceEvent;
  if (trace.agent_name) return trace.agent_name;
  if (trace.tool_name) return trace.tool_name;
  return trace.message;
}

function eventTimestamp(event: SSEEvent | TraceEvent): string {
  const ts =
    "timestamp" in event && event.timestamp
      ? event.timestamp
      : "timestamp" in event
        ? (event as TraceEvent).timestamp
        : undefined;
  return formatDateTime(ts);
}

export function AgentTracePanel({
  status,
  events,
  traceEvents,
  error,
}: AgentTracePanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const displayEvents: Array<SSEEvent | TraceEvent> =
    events.length > 0
      ? events.filter((e) => e.type !== "heartbeat")
      : traceEvents;

  return (
    <section className="rounded-xl border border-card-border bg-card">
      <div className="flex items-center justify-between border-b border-card-border px-5 py-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">
            Agent Trace
          </h2>
          <p className="mt-0.5 text-xs text-muted">PRISM-compatible observability</p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${STATUS_COLOR[status]}`}
            aria-hidden
          />
          <span className="font-mono text-xs text-muted">
            {STATUS_LABEL[status]}
          </span>
        </div>
      </div>

      <div className="max-h-[520px] overflow-y-auto p-4">
        {error && (
          <div className="mb-4 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
            {error}
          </div>
        )}

        {displayEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="mb-3 h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
            <p className="text-sm text-muted">Waiting for agent events…</p>
          </div>
        ) : (
          <ol className="space-y-2">
            {displayEvents.map((event, index) => {
              const id =
                "event_id" in event
                  ? event.event_id
                  : `${event.type}-${index}`;
              const type =
                "type" in event ? event.type : (event as TraceEvent).event_type;
              const isExpanded = expandedId === id;
              const latency =
                "latency_ms" in event ? event.latency_ms : undefined;
              const message =
                "message" in event ? event.message : undefined;

              return (
                <li key={id}>
                  <button
                    type="button"
                    onClick={() =>
                      setExpandedId(isExpanded ? null : id)
                    }
                    className="flex w-full items-start gap-3 rounded-lg border border-card-border bg-background/50 px-3 py-2.5 text-left transition hover:border-accent/40"
                  >
                    <span className="mt-0.5 font-mono text-xs text-accent">
                      {eventIcon(type)}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-sm font-medium">
                          {eventLabel(event)}
                        </p>
                        <span className="shrink-0 font-mono text-[10px] text-muted">
                          {eventTimestamp(event)}
                        </span>
                      </div>
                      <p className="mt-0.5 truncate font-mono text-[10px] uppercase text-muted">
                        {type.replace(/_/g, " ")}
                        {latency != null && ` · ${formatLatency(latency)}`}
                      </p>
                      {isExpanded && message && (
                        <p className="mt-2 text-xs leading-relaxed text-muted">
                          {message}
                        </p>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </section>
  );
}
