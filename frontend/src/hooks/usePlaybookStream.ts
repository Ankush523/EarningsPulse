"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { fetchPlaybookJob, getPlaybookStreamUrl } from "@/lib/api";
import type { JobStatus, Playbook, SSEEvent, TraceEvent } from "@/lib/types";

export type StreamStatus = "idle" | "connecting" | "streaming" | "completed" | "failed";

export interface UsePlaybookStreamResult {
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

export function usePlaybookStream(jobId: string): UsePlaybookStreamResult {
  const [status, setStatus] = useState<StreamStatus>("idle");
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([]);
  const [playbook, setPlaybook] = useState<Playbook | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);
  const completedRef = useRef(false);

  const loadJob = useCallback(async () => {
    try {
      const jobStatus = await fetchPlaybookJob(jobId);
      setJob(jobStatus);
      if (jobStatus.playbook) {
        setPlaybook(jobStatus.playbook);
      }
      if (jobStatus.status === "completed") {
        setStatus("completed");
        completedRef.current = true;
      } else if (jobStatus.status === "failed") {
        setStatus("failed");
        setError(jobStatus.error ?? "Playbook generation failed");
        completedRef.current = true;
      }
      return jobStatus;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load job status";
      setError(message);
      setStatus("failed");
      return null;
    }
  }, [jobId]);

  const connect = useCallback(() => {
    if (completedRef.current) return;

    sourceRef.current?.close();
    setStatus("connecting");
    setError(null);

    const source = new EventSource(getPlaybookStreamUrl(jobId));
    sourceRef.current = source;

    source.onopen = () => {
      setStatus("streaming");
    };

    source.onmessage = (message) => {
      try {
        const parsed: SSEEvent = JSON.parse(message.data);
        if (parsed.type === "heartbeat") return;

        setEvents((prev) => [...prev, parsed]);

        const trace = extractTraceEvent(parsed);
        if (trace) {
          setTraceEvents((prev) => {
            const exists = prev.some((e) => e.event_id === trace.event_id);
            if (exists) return prev;
            return [...prev, trace];
          });
        }

        if (parsed.type === "playbook_ready") {
          completedRef.current = true;
          setStatus("completed");
          source.close();
          void loadJob();
        }

        if (parsed.type === "error") {
          completedRef.current = true;
          setStatus("failed");
          setError(parsed.error ?? parsed.message ?? "Generation failed");
          source.close();
          void loadJob();
        }
      } catch {
        // Ignore malformed SSE payloads
      }
    };

    source.onerror = () => {
      source.close();
      if (!completedRef.current) {
        void loadJob().then((jobStatus) => {
          if (jobStatus?.status === "completed") {
            completedRef.current = true;
            setStatus("completed");
          } else if (jobStatus?.status === "failed") {
            completedRef.current = true;
            setStatus("failed");
          } else if (!completedRef.current) {
            setError("Lost connection to agent stream");
            setStatus("failed");
          }
        });
      }
    };
  }, [jobId, loadJob]);

  useEffect(() => {
    completedRef.current = false;
    setEvents([]);
    setTraceEvents([]);
    setPlaybook(null);
    setJob(null);
    setError(null);

    void loadJob().then((jobStatus) => {
      if (jobStatus?.status === "completed" || jobStatus?.status === "failed") {
        return;
      }
      connect();
    });

    return () => {
      sourceRef.current?.close();
    };
  }, [connect, jobId, loadJob]);

  const reconnect = useCallback(() => {
    completedRef.current = false;
    setEvents([]);
    setTraceEvents([]);
    setPlaybook(null);
    setError(null);
    connect();
  }, [connect]);

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
