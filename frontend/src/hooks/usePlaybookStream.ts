"use client";

import { useEffect, useState } from "react";

import { fetchPlaybookJob, fetchTraceLog, getPlaybookStreamUrl } from "@/lib/api";
import type { JobStatus, Playbook, SSEEvent, TraceEvent } from "@/lib/types";

export type StreamStatus = "idle" | "connecting" | "streaming" | "completed" | "failed";

interface UsePlaybookStreamResult {
  status: StreamStatus;
  events: SSEEvent[];
  traceEvents: TraceEvent[];
  playbook: Playbook | null;
  job: JobStatus | null;
  error: string | null;
  reconnect: () => void;
}

function extractTraceEvent(event: SSEEvent): TraceEvent | null {
  if (event.trace) return event.trace;
  if (
    event.type === "run_started" ||
    event.type === "run_completed" ||
    event.type === "agent_start" ||
    event.type === "agent_complete" ||
    event.type === "tool_call" ||
    event.type === "error"
  ) {
    return {
      event_id: `${event.type}-${event.timestamp ?? Date.now()}`,
      job_id: event.job_id ?? "",
      event_type: mapSseTypeToTraceType(event.type),
      timestamp: event.timestamp ?? new Date().toISOString(),
      agent_name: event.agent_name,
      tool_name: event.tool_name,
      message: event.message ?? event.type,
      latency_ms: event.latency_ms,
      error: event.error,
    };
  }
  return null;
}

function mapSseTypeToTraceType(
  sseType: string
): TraceEvent["event_type"] {
  switch (sseType) {
    case "run_started":
      return "run_started";
    case "run_completed":
      return "run_completed";
    case "agent_start":
      return "agent_started";
    case "agent_complete":
      return "agent_completed";
    case "tool_call":
      return "tool_call_started";
    case "error":
      return "run_failed";
    default:
      return "agent_started";
  }
}

function isTerminalJob(status: JobStatus["status"]): boolean {
  return status === "completed" || status === "failed";
}

export function usePlaybookStream(jobId: string): UsePlaybookStreamResult {
  const [status, setStatus] = useState<StreamStatus>("connecting");
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([]);
  const [playbook, setPlaybook] = useState<Playbook | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reconnectToken, setReconnectToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let finished = false;
    let allowStreamStatus = false;
    const source = new EventSource(getPlaybookStreamUrl(jobId));

    const closeSource = () => {
      finished = true;
      source.close();
    };

    source.onopen = () => {
      if (cancelled || finished || !allowStreamStatus) return;
      setStatus("streaming");
    };

    source.onmessage = (message) => {
      if (cancelled || finished) return;
      try {
        const parsed: SSEEvent = JSON.parse(message.data);
        if (parsed.type === "heartbeat") return;

        setEvents((prev) => [...prev, parsed]);

        const trace = extractTraceEvent(parsed);
        if (trace) {
          setTraceEvents((prev) => {
            if (prev.some((e) => e.event_id === trace.event_id)) return prev;
            return [...prev, trace];
          });
        }

        if (parsed.type === "playbook_ready") {
          closeSource();
          setStatus("completed");
          void fetchPlaybookJob(jobId)
            .then((jobStatus) => {
              if (cancelled) return;
              setJob(jobStatus);
              if (jobStatus.playbook) {
                setPlaybook(jobStatus.playbook);
              }
            })
            .catch(() => {
              /* playbook_ready already marked the run complete */
            });
        }

        if (parsed.type === "error") {
          closeSource();
          setStatus("failed");
          setError(parsed.error ?? parsed.message ?? "Generation failed");
          void fetchPlaybookJob(jobId)
            .then((jobStatus) => {
              if (cancelled) return;
              setJob(jobStatus);
              if (jobStatus.playbook) {
                setPlaybook(jobStatus.playbook);
              }
            })
            .catch(() => {
              /* stream error already recorded */
            });
        }
      } catch {
        // Ignore malformed SSE payloads
      }
    };

    source.onerror = () => {
      if (cancelled || finished) return;
      closeSource();
      void fetchPlaybookJob(jobId)
        .then((jobStatus) => {
          if (cancelled) return;
          setJob(jobStatus);
          if (jobStatus.playbook) {
            setPlaybook(jobStatus.playbook);
          }
          if (jobStatus.status === "completed") {
            setStatus("completed");
          } else if (jobStatus.status === "failed") {
            setStatus("failed");
            setError(jobStatus.error ?? "Playbook generation failed");
          } else {
            setError("Lost connection to agent stream");
            setStatus("failed");
          }
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setError(
            err instanceof Error ? err.message : "Lost connection to agent stream"
          );
          setStatus("failed");
        });
    };

    void fetchPlaybookJob(jobId)
      .then((jobStatus) => {
        if (cancelled) return;
        setJob(jobStatus);
        if (jobStatus.playbook) {
          setPlaybook(jobStatus.playbook);
        }
        if (isTerminalJob(jobStatus.status)) {
          if (jobStatus.status === "failed") {
            setStatus("failed");
            setError(jobStatus.error ?? "Playbook generation failed");
          } else {
            setStatus("completed");
          }
          closeSource();
          void fetchTraceLog(jobId)
            .then((log) => {
              if (cancelled) return;
              setTraceEvents(log.events);
            })
            .catch(() => {
              /* completed jobs can still render without a stored trace */
            });
          return;
        }
        allowStreamStatus = true;
        if (source.readyState === EventSource.OPEN) {
          setStatus("streaming");
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        closeSource();
        setError(
          err instanceof Error ? err.message : "Failed to load job status"
        );
        setStatus("failed");
      });

    return () => {
      cancelled = true;
      source.close();
    };
  }, [jobId, reconnectToken]);

  const reconnect = () => {
    setEvents([]);
    setTraceEvents([]);
    setPlaybook(null);
    setError(null);
    setStatus("connecting");
    setReconnectToken((token) => token + 1);
  };

  return {
    status,
    events,
    traceEvents,
    playbook,
    job,
    error,
    reconnect,
  };
}
