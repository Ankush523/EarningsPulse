"use client";

import { useEffect, useState } from "react";

import { formatDateTime, formatLatency } from "@/lib/format";
import type { SSEEvent, TraceEvent } from "@/lib/types";
import type { StreamStatus } from "@/hooks/usePlaybookStream";

interface RunPanelProps {
  status: StreamStatus;
  events: SSEEvent[];
  traceEvents: TraceEvent[];
  error: string | null;
  durationMs?: number | null;
}

const STATIONS = [
  { id: "research", label: "Research" },
  { id: "forecast", label: "Forecast" },
  { id: "reaction", label: "Reaction" },
  { id: "spillover", label: "Spillover" },
  { id: "synthesis", label: "Synthesis" },
] as const;

type StationState = "waiting" | "running" | "done" | "failed";

interface StationStatus {
  state: StationState;
  latencyMs: number | null;
}

type RunEvent = SSEEvent | TraceEvent;

function eventType(event: RunEvent): string {
  return "type" in event ? event.type : event.event_type;
}

function eventLabel(event: RunEvent): string {
  if (event.agent_name) return event.agent_name;
  if (event.tool_name) return event.tool_name;
  return ("message" in event && event.message) || eventType(event);
}

function eventKey(event: RunEvent): string {
  if ("event_id" in event && event.event_id) return event.event_id;
  if ("trace" in event && event.trace?.event_id) return event.trace.event_id;
  const timestamp = event.timestamp ?? "";
  const message = ("message" in event && event.message) || "";
  return `${eventType(event)}|${timestamp}|${event.agent_name ?? ""}|${event.tool_name ?? ""}|${message}`;
}

function describeType(type: string): string {
  switch (type) {
    case "run_started":
      return "Run started";
    case "run_completed":
    case "playbook_ready":
      return "Playbook ready";
    case "run_failed":
    case "error":
      return "Failed";
    case "agent_start":
    case "agent_started":
      return "Agent started";
    case "agent_complete":
    case "agent_completed":
      return "Agent finished";
    case "tool_call":
    case "tool_call_started":
      return "Tool call";
    case "tool_call_completed":
      return "Tool call finished";
    case "tool_call_failed":
      return "Tool call failed";
    case "confidence_updated":
      return "Confidence updated";
    default:
      return type.replace(/_/g, " ");
  }
}

function stationStatuses(
  events: RunEvent[],
  runStatus: StreamStatus
): Record<string, StationStatus> {
  const result: Record<string, StationStatus> = {};
  for (const station of STATIONS) {
    result[station.id] = { state: "waiting", latencyMs: null };
  }

  for (const event of events) {
    const agent = event.agent_name;
    if (!agent || !(agent in result)) continue;
    const type = eventType(event);
    if (type === "agent_start" || type === "agent_started") {
      result[agent] = { state: "running", latencyMs: null };
    } else if (type === "agent_complete" || type === "agent_completed") {
      result[agent] = {
        state: "done",
        latencyMs: ("latency_ms" in event ? event.latency_ms : null) ?? null,
      };
    } else if (type === "error" || type === "run_failed") {
      result[agent] = { state: "failed", latencyMs: null };
    }
  }

  if (runStatus === "completed") {
    for (const station of STATIONS) {
      if (result[station.id].state !== "failed") {
        result[station.id] = { ...result[station.id], state: "done" };
      }
    }
  }

  return result;
}

function useElapsedSeconds(active: boolean): number {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!active) return;
    const started = Date.now();
    const interval = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - started) / 1000));
    }, 1000);
    return () => window.clearInterval(interval);
  }, [active]);

  return elapsed;
}

function clock(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}:${rest.toString().padStart(2, "0")}`;
}

export function RunPanel({
  status,
  events,
  traceEvents,
  error,
  durationMs,
}: RunPanelProps) {
  const isRunning = status === "connecting" || status === "streaming";
  const elapsed = useElapsedSeconds(isRunning);
  const [logOpen, setLogOpen] = useState<boolean | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const displayEvents: RunEvent[] =
    events.length > 0 ? events.filter((e) => e.type !== "heartbeat") : traceEvents;
  const stations = stationStatuses(displayEvents, status);
  const showLog = logOpen ?? isRunning;

  let headline: string;
  if (status === "connecting") headline = "Connecting to the agents";
  else if (status === "streaming") headline = `Running, ${clock(elapsed)}`;
  else if (status === "completed")
    headline = durationMs != null ? `Done in ${formatLatency(durationMs)}` : "Done";
  else if (status === "failed") headline = "Run failed";
  else headline = "Waiting";

  return (
    <section
      aria-label="Agent run"
      className="no-print glass-panel-dark overflow-hidden"
    >
      <div className="flex flex-wrap items-center justify-between gap-x-8 gap-y-4 px-5 py-4 sm:px-6">
        <ol className="flex flex-wrap items-center gap-x-1 gap-y-2">
          {STATIONS.map((station, index) => {
            const { state, latencyMs } = stations[station.id];
            return (
              <li key={station.id} className="flex items-center">
                {index > 0 && (
                  <span
                    aria-hidden
                    className={`mx-2 hidden h-px w-5 sm:block ${
                      state === "waiting" ? "bg-panel-ink-rule" : "bg-panel-ink-soft"
                    }`}
                  />
                )}
                <span className="flex items-center gap-2">
                  <StationDot state={state} />
                  <span
                    className={`text-[0.95rem] ${
                      state === "waiting" ? "text-panel-ink-soft" : ""
                    }`}
                  >
                    {station.label}
                  </span>
                  {latencyMs != null && latencyMs > 0 && (
                    <span className="font-mono text-[0.75rem] text-panel-ink-soft">
                      {formatLatency(latencyMs)}
                    </span>
                  )}
                </span>
              </li>
            );
          })}
        </ol>

        <div className="flex items-center gap-5">
          <span
            className={`font-mono text-[0.85rem] ${
              status === "failed" ? "text-[#f2a49b]" : "text-panel-ink-soft"
            }`}
          >
            {headline}
          </span>
          <button
            type="button"
            onClick={() => setLogOpen(!showLog)}
            aria-expanded={showLog}
            className="cursor-pointer rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-[0.85rem] text-panel-ink-text transition hover:border-white/25 hover:bg-white/10"
          >
            {showLog ? "Hide log" : `Run log (${displayEvents.length})`}
          </button>
        </div>
      </div>

      {isRunning && elapsed >= 90 && (
        <p className="border-t border-panel-ink-rule px-5 py-3 text-[0.9rem] text-panel-ink-soft sm:px-6">
          Still running. External data sources are slow right now; most runs
          finish in under two minutes.
        </p>
      )}

      {error && (
        <p className="border-t border-panel-ink-rule px-5 py-3 text-[0.95rem] text-[#f2a49b] sm:px-6">
          {error}
        </p>
      )}

      {showLog && (
        <div className="max-h-80 overflow-y-auto border-t border-panel-ink-rule">
          {displayEvents.length === 0 ? (
            <p className="px-5 py-4 text-[0.9rem] text-panel-ink-soft sm:px-6">
              {isRunning ? "Waiting for the first event." : "No events were recorded for this run."}
            </p>
          ) : (
            <ol className="divide-y divide-panel-ink-rule">
              {displayEvents.map((event) => {
                const id = eventKey(event);
                const type = eventType(event);
                const latency = "latency_ms" in event ? event.latency_ms : null;
                const message = "message" in event ? event.message : undefined;
                const isExpanded = expandedId === id;
                const failed = type === "error" || type === "run_failed" || type === "tool_call_failed";

                return (
                  <li key={id}>
                    <button
                      type="button"
                      onClick={() => setExpandedId(isExpanded ? null : id)}
                      aria-expanded={isExpanded}
                      className="grid w-full grid-cols-[5.5rem_1fr_auto] items-baseline gap-x-4 px-5 py-2.5 text-left transition hover:bg-white/5 sm:px-6"
                    >
                      <span className="font-mono text-[0.75rem] text-panel-ink-soft">
                        {formatDateTime(event.timestamp).replace(/^[A-Za-z]+ \d+, /, "")}
                      </span>
                      <span className="min-w-0">
                        <span className={`text-[0.95rem] ${failed ? "text-[#f2a49b]" : ""}`}>
                          {eventLabel(event)}
                        </span>
                        <span className="ml-2 text-[0.85rem] text-panel-ink-soft">
                          {describeType(type)}
                        </span>
                        {isExpanded && message && (
                          <span className="mt-1 block text-[0.9rem] leading-relaxed text-panel-ink-soft">
                            {message}
                          </span>
                        )}
                      </span>
                      <span className="font-mono text-[0.75rem] text-panel-ink-soft">
                        {latency != null ? formatLatency(latency) : ""}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      )}
    </section>
  );
}

function StationDot({ state }: { state: StationState }) {
  switch (state) {
    case "waiting":
      return (
        <span
          aria-hidden
          className="h-2.5 w-2.5 rounded-full border border-panel-ink-soft"
        />
      );
    case "running":
      return (
        <span
          aria-hidden
          className="pulse-dot h-2.5 w-2.5 rounded-full bg-panel-ink-text"
        />
      );
    case "done":
      return (
        <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-panel-ink-text" />
      );
    case "failed":
      return <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-[#f2a49b]" />;
    default: {
      const exhaustive: never = state;
      return exhaustive;
    }
  }
}
