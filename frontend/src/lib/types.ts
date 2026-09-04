/** TypeScript types mirroring backend Pydantic models. */

export type ConfidenceTier = "high" | "medium" | "low";

type ReportOutcome = "beat" | "inline" | "miss";

type ReactionArchetype =
  | "dip_then_rally"
  | "immediate_rip"
  | "sell_the_news"
  | "gap_and_hold"
  | "volatility_pin"
  | "insufficient_data";

type PeerRelationship =
  | "direct_peer"
  | "supplier"
  | "customer"
  | "thematic";

type PlaybookStatus = "pending" | "running" | "completed" | "failed";

type TraceEventType =
  | "run_started"
  | "run_completed"
  | "run_failed"
  | "agent_started"
  | "agent_completed"
  | "tool_call_started"
  | "tool_call_completed"
  | "tool_call_failed"
  | "confidence_updated";

interface Source {
  title: string;
  url: string;
  source_type: string;
  accessed_at: string;
}

interface KeyMetric {
  name: string;
  description: string;
  importance: ConfidenceTier;
}

interface ReportForecast {
  key_metrics: KeyMetric[];
  bull_case: string;
  base_case: string;
  bear_case: string;
  positive_surprises: string[];
  negative_surprises: string[];
  confidence: ConfidenceTier;
  sources: Source[];
}

export interface PriceScenario {
  outcome: ReportOutcome;
  label: string;
  description: string;
  probability: number;
  expected_direction: string;
  historical_reference?: string | null;
  key_levels: Record<string, number>;
}

export interface HistoricalReaction {
  earnings_date: string;
  report_outcome?: ReportOutcome | null;
  initial_move_pct: number;
  dip_pct?: number | null;
  recovery_pct?: number | null;
  time_to_bottom_minutes?: number | null;
  pattern: ReactionArchetype;
}

export interface MonteCarloPercentilePoint {
  day: number;
  label: string;
  p5: number;
  p25: number;
  p50: number;
  p75: number;
  p95: number;
  mean: number;
  p5_return_pct: number;
  p25_return_pct: number;
  p50_return_pct: number;
  p75_return_pct: number;
  p95_return_pct: number;
}

export interface MonteCarloSimulation {
  ticker: string;
  num_simulations: number;
  window_days: number;
  baseline_price: number;
  expected_move_pct: number;
  realized_daily_volatility_pct: number;
  prob_positive_return: number;
  prob_exceeds_implied_move: number;
  var_95_pct: number;
  cvar_95_pct: number;
  expected_range: { min: number; max: number };
  expected_return_pct: number;
  trajectories: MonteCarloPercentilePoint[];
  summary: string;
}

interface ReactionAnalysisSummary {
  archetype: ReactionArchetype;
  archetype_description: string;
  scenarios: PriceScenario[];
  historical_reactions: HistoricalReaction[];
  avg_dip_pct?: number | null;
  avg_recovery_pct?: number | null;
  dip_frequency_on_positive?: number | null;
  expected_dip_zone?: Record<string, number> | null;
  implied_move_pct?: number | null;
  historical_move_pct?: number | null;
  volatility_assessment?: string | null;
  options_summary?: string | null;
  confidence: ConfidenceTier;
  monte_carlo?: MonteCarloSimulation | null;
  sources: Source[];
}

export interface PeerSpillover {
  ticker: string;
  company_name?: string | null;
  relationship: PeerRelationship;
  correlation_score: number;
  expected_direction: string;
  rationale: string;
  watch_flag: boolean;
}

interface SpilloverMap {
  reporting_ticker: string;
  peers: PeerSpillover[];
  confidence: ConfidenceTier;
  sources: Source[];
}

interface ActionRule {
  condition: string;
  action: string;
  confidence: ConfidenceTier;
  historical_basis?: string | null;
}

interface ActionPlaybook {
  rules: ActionRule[];
  disclaimer: string;
}

interface ExecutiveSummary {
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

interface PlaybookMetadata {
  job_id: string;
  generated_at: string;
  generation_time_ms?: number | null;
  model_version: string;
  data_sources_used: string[];
}

export interface Playbook {
  metadata: PlaybookMetadata;
  executive_summary: ExecutiveSummary;
  report_forecast: ReportForecast;
  reaction_analysis: ReactionAnalysisSummary;
  spillover_map: SpilloverMap;
  action_playbook: ActionPlaybook;
  all_sources: Source[];
  trace_id?: string | null;
}

export interface PlaybookGenerateResponse {
  job_id: string;
  ticker: string;
  status: string;
  stream_url: string;
}

export interface JobStatus {
  job_id: string;
  ticker: string;
  status: PlaybookStatus;
  playbook: Playbook | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface EarningsEvent {
  ticker: string;
  company_name?: string | null;
  report_date: string;
  report_time?: string | null;
  eps_estimate?: number | null;
  eps_actual?: number | null;
}

export interface EarningsCalendarResponse {
  from_date: string;
  to_date: string;
  events: EarningsEvent[];
}

export interface TraceEvent {
  event_id: string;
  job_id: string;
  event_type: TraceEventType;
  timestamp: string;
  agent_name?: string | null;
  tool_name?: string | null;
  message: string;
  input_summary?: Record<string, unknown> | null;
  output_summary?: Record<string, unknown> | null;
  latency_ms?: number | null;
  error?: string | null;
  retry_attempt?: number | null;
}

export interface TraceLog {
  job_id: string;
  ticker: string;
  events: TraceEvent[];
  started_at: string;
  completed_at?: string | null;
  total_latency_ms?: number | null;
  prism_synced: boolean;
}

export interface SSEEvent {
  type: string;
  job_id?: string;
  ticker?: string;
  timestamp?: string;
  agent_name?: string | null;
  tool_name?: string | null;
  message?: string;
  latency_ms?: number | null;
  error?: string | null;
  trace?: TraceEvent;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment?: string;
  timestamp: string;
}

export interface ApiError {
  detail: string;
  error_code?: string;
}
