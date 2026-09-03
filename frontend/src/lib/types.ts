/** TypeScript types mirroring backend Pydantic models. */

export type ConfidenceTier = "high" | "medium" | "low";

export type ReportOutcome = "beat" | "inline" | "miss";

export type ReactionArchetype =
  | "dip_then_rally"
  | "immediate_rip"
  | "sell_the_news"
  | "gap_and_hold"
  | "volatility_pin"
  | "insufficient_data";

export type PeerRelationship =
  | "direct_peer"
  | "supplier"
  | "customer"
  | "thematic";

export type PlaybookStatus = "pending" | "running" | "completed" | "failed";

export type TraceEventType =
  | "run_started"
  | "run_completed"
  | "run_failed"
  | "agent_started"
  | "agent_completed"
  | "tool_call_started"
  | "tool_call_completed"
  | "tool_call_failed"
  | "confidence_updated";

export interface Source {
  title: string;
  url: string;
  source_type: string;
  accessed_at: string;
}

export interface ExecutiveSummary {
  ticker: string;
  company_name?: string | null;
  earnings_date?: string | null;
  is_after_hours: boolean;
  beat_probability: number;
  inline_probability: number;
  miss_probability: number;
  primary_pattern: ReactionArchetype;
  primary_pattern_description: string;
  overall_confidence: ConfidenceTier;
  top_drivers: string[];
  sources: Source[];
}

export interface PlaybookMetadata {
  job_id: string;
  generated_at: string;
  generation_time_ms?: number | null;
  model_version: string;
  data_sources_used: string[];
}

export interface Playbook {
  metadata: PlaybookMetadata;
  executive_summary: ExecutiveSummary;
  report_forecast: Record<string, unknown>;
  reaction_analysis: Record<string, unknown>;
  spillover_map: Record<string, unknown>;
  action_playbook: Record<string, unknown>;
  all_sources: Source[];
  trace_id?: string | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment?: string;
  timestamp: string;
}

export interface ReadinessResponse extends HealthResponse {
  checks: {
    api: boolean;
    openai_configured: boolean;
    tavily_configured: boolean;
    finnhub_configured: boolean;
    prism_enabled: boolean;
  };
}

export interface TraceEvent {
  event_id: string;
  job_id: string;
  event_type: TraceEventType;
  timestamp: string;
  agent_name?: string | null;
  tool_name?: string | null;
  message: string;
  latency_ms?: number | null;
  error?: string | null;
}
