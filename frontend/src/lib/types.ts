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

export interface ReactionPathPoint {
  offset_days: number;
  date: string;
  pct_from_baseline: number;
  close: number;
}

export interface ReactionEventPath {
  earnings_date: string;
  report_outcome?: ReportOutcome | null;
  baseline_price: number;
  points: ReactionPathPoint[];
}

export interface ReactionReferenceLine {
  label: string;
  price: number;
  kind: string;
}

export interface ReactionChartBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number | null;
}

export interface ReactionChartData {
  ticker: string;
  focus_earnings_date: string;
  baseline_price: number;
  window_days: number;
  candles: ReactionChartBar[];
  paths: ReactionEventPath[];
  median_path: ReactionPathPoint[];
  reference_lines: ReactionReferenceLine[];
}

interface MonteCarloSummary {
  simulations: number;
  p10_final_move_pct: number;
  p50_final_move_pct: number;
  p90_final_move_pct: number;
  p10_max_dip_pct?: number | null;
  p50_max_dip_pct?: number | null;
  p90_max_dip_pct?: number | null;
  dip_before_recovery_prob?: number | null;
  mean_final_move_pct?: number | null;
}

interface ValidationSummary {
  train_events: number;
  test_events: number;
  train_dominant_archetype: ReactionArchetype;
  test_pattern_match_rate: number;
  pattern_drift: number;
  overfitting_risk: string;
  is_reliable: boolean;
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
  sources: Source[];
  monte_carlo?: MonteCarloSummary | null;
  validation?: ValidationSummary | null;
  backtest_years?: number | null;
  fib_levels?: Record<string, number>;
  reaction_chart?: ReactionChartData | null;
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
