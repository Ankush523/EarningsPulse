"use client";

import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { PeerSpilloverTable } from "@/components/PeerSpilloverTable";
import { ReactionChart } from "@/components/ReactionChart";
import { ScenarioTree } from "@/components/ScenarioTree";
import {
  formatArchetype,
  formatDate,
  formatLatency,
  formatPercent,
} from "@/lib/format";
import type { Playbook } from "@/lib/types";

interface PlaybookViewProps {
  playbook: Playbook;
}

export function PlaybookView({ playbook }: PlaybookViewProps) {
  const { executive_summary: summary, report_forecast: forecast } = playbook;
  const reaction = playbook.reaction_analysis;
  const spillover = playbook.spillover_map;
  const actions = playbook.action_playbook;

  return (
    <div className="playbook-view space-y-8">
      {/* Section A — Executive Summary */}
      <section className="rounded-xl border border-card-border bg-card p-6">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-sm text-accent">{summary.ticker}</p>
            <h2 className="text-2xl font-bold">
              {summary.company_name ?? summary.ticker} Earnings Playbook
            </h2>
            {summary.earnings_date && (
              <p className="mt-1 text-sm text-muted">
                Report date: {formatDate(summary.earnings_date)}
                {summary.is_after_hours && " · After hours"}
              </p>
            )}
          </div>
          <ConfidenceBadge tier={summary.overall_confidence} />
        </div>

        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <ProbabilityCard label="Beat" value={summary.beat_probability} tone="success" />
          <ProbabilityCard label="Inline" value={summary.inline_probability} tone="warning" />
          <ProbabilityCard label="Miss" value={summary.miss_probability} tone="danger" />
        </div>

        <div className="mb-4 rounded-lg border border-accent/20 bg-accent/5 p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-accent">
            Primary Pattern
          </p>
          <p className="mt-1 font-semibold">
            {formatArchetype(summary.primary_pattern)}
          </p>
          <p className="mt-1 text-sm text-muted">
            {summary.primary_pattern_description}
          </p>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted">
            Top Drivers
          </p>
          <ul className="space-y-1.5">
            {summary.top_drivers.map((driver) => (
              <li key={driver} className="flex gap-2 text-sm">
                <span className="text-accent">→</span>
                {driver}
              </li>
            ))}
          </ul>
        </div>

        {playbook.metadata.generation_time_ms != null && (
          <p className="mt-4 font-mono text-xs text-muted">
            Generated in {formatLatency(playbook.metadata.generation_time_ms)}
          </p>
        )}
      </section>

      {/* Section B — Report Forecast */}
      <section className="rounded-xl border border-card-border bg-card p-6">
        <SectionHeader
          title="Report Forecast"
          badge={<ConfidenceBadge tier={forecast.confidence} />}
        />

        {forecast.key_metrics.length > 0 && (
          <div className="mb-6 grid gap-3 sm:grid-cols-2">
            {forecast.key_metrics.map((metric) => (
              <div
                key={metric.name}
                className="rounded-lg border border-card-border bg-background/50 p-4"
              >
                <div className="mb-1 flex items-center justify-between">
                  <p className="font-medium">{metric.name}</p>
                  <ConfidenceBadge tier={metric.importance} />
                </div>
                <p className="text-sm text-muted">{metric.description}</p>
              </div>
            ))}
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-3">
          <CaseCard title="Bull Case" content={forecast.bull_case} tone="success" />
          <CaseCard title="Base Case" content={forecast.base_case} tone="accent" />
          <CaseCard title="Bear Case" content={forecast.bear_case} tone="danger" />
        </div>

        {(forecast.positive_surprises.length > 0 ||
          forecast.negative_surprises.length > 0) && (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {forecast.positive_surprises.length > 0 && (
              <SurpriseList
                title="Positive Surprises"
                items={forecast.positive_surprises}
                tone="success"
              />
            )}
            {forecast.negative_surprises.length > 0 && (
              <SurpriseList
                title="Negative Surprises"
                items={forecast.negative_surprises}
                tone="danger"
              />
            )}
          </div>
        )}
      </section>

      {/* Section C — Reaction Analysis */}
      <section className="rounded-xl border border-card-border bg-card p-6">
        <SectionHeader
          title="Price Reaction Scenarios"
          badge={<ConfidenceBadge tier={reaction.confidence} />}
        />
        <p className="mb-4 text-sm text-muted">{reaction.archetype_description}</p>

        <ScenarioTree scenarios={reaction.scenarios} />

        <div className="mt-8">
          <h4 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted">
            Historical Reactions
          </h4>
          <ReactionChart
            reactions={reaction.historical_reactions}
            ticker={summary.ticker}
          />
        </div>

        {(reaction.avg_dip_pct != null || reaction.dip_frequency_on_positive != null) && (
          <div className="mt-6 flex flex-wrap gap-4 text-sm">
            {reaction.avg_dip_pct != null && (
              <StatPill label="Avg dip" value={`${reaction.avg_dip_pct.toFixed(1)}%`} />
            )}
            {reaction.avg_recovery_pct != null && (
              <StatPill
                label="Avg recovery"
                value={`${reaction.avg_recovery_pct.toFixed(1)}%`}
              />
            )}
            {reaction.dip_frequency_on_positive != null && (
              <StatPill
                label="Dip on beat"
                value={formatPercent(reaction.dip_frequency_on_positive)}
              />
            )}
          </div>
        )}

        {(reaction.implied_move_pct != null || reaction.historical_move_pct != null) && (
          <div className="mt-6 rounded-lg border border-card-border bg-background/60 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted">
                Options Implied Move vs. Realized Move
              </span>
              {reaction.volatility_assessment && (
                <span
                  className={`rounded px-2 py-0.5 text-xs font-semibold ${
                    reaction.volatility_assessment === "OVERPRICED"
                      ? "border border-amber-500/30 bg-amber-500/20 text-amber-400"
                      : reaction.volatility_assessment === "UNDERPRICED"
                      ? "border border-emerald-500/30 bg-emerald-500/20 text-emerald-400"
                      : "border border-blue-500/30 bg-blue-500/20 text-blue-400"
                  }`}
                >
                  {reaction.volatility_assessment}
                </span>
              )}
            </div>
            <div className="mt-3 flex flex-wrap gap-4 text-sm">
              {reaction.implied_move_pct != null && (
                <StatPill
                  label="Options Implied Move"
                  value={`±${reaction.implied_move_pct.toFixed(1)}%`}
                />
              )}
              {reaction.historical_move_pct != null && (
                <StatPill
                  label="Historical Realized Move"
                  value={`±${reaction.historical_move_pct.toFixed(1)}%`}
                />
              )}
            </div>
            {reaction.options_summary && (
              <p className="mt-2 text-xs text-muted">{reaction.options_summary}</p>
            )}
          </div>
        )}
      </section>

      {/* Section D — Peer Spillover */}
      <section className="rounded-xl border border-card-border bg-card p-6">
        <SectionHeader
          title="Peer Spillover Map"
          badge={<ConfidenceBadge tier={spillover.confidence} />}
        />
        <PeerSpilloverTable peers={spillover.peers} />
      </section>

      {/* Section E — Action Playbook */}
      <section className="rounded-xl border border-card-border bg-card p-6">
        <SectionHeader title="Action Playbook" />
        <ol className="space-y-4">
          {actions.rules.map((rule, index) => (
            <li
              key={`${rule.condition}-${index}`}
              className="rounded-lg border border-card-border bg-background/50 p-4"
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="text-xs font-medium uppercase tracking-wider text-accent">
                  If
                </p>
                <ConfidenceBadge tier={rule.confidence} />
              </div>
              <p className="mb-3 text-sm font-medium">{rule.condition}</p>
              <p className="text-xs font-medium uppercase tracking-wider text-muted">
                Then
              </p>
              <p className="mt-1 text-sm">{rule.action}</p>
              {rule.historical_basis && (
                <p className="mt-2 text-xs text-muted">{rule.historical_basis}</p>
              )}
            </li>
          ))}
        </ol>
      </section>

      {/* Section F — Sources */}
      <section className="rounded-xl border border-card-border bg-card p-6">
        <SectionHeader title="Sources" />
        {playbook.all_sources.length === 0 ? (
          <p className="text-sm text-muted">No sources cited.</p>
        ) : (
          <ul className="space-y-2">
            {playbook.all_sources.map((source) => (
              <li key={source.url}>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-accent hover:underline"
                >
                  {source.title}
                </a>
                <span className="ml-2 font-mono text-[10px] text-muted">
                  {source.source_type}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function SectionHeader({
  title,
  badge,
}: {
  title: string;
  badge?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
      <h3 className="text-lg font-semibold">{title}</h3>
      {badge}
    </div>
  );
}

function ProbabilityCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "success" | "warning" | "danger";
}) {
  const colors = {
    success: "text-success",
    warning: "text-warning",
    danger: "text-danger",
  };
  return (
    <div className="rounded-lg border border-card-border bg-background/50 p-4 text-center">
      <p className="text-xs uppercase tracking-wider text-muted">{label}</p>
      <p className={`mt-1 font-mono text-3xl font-bold ${colors[tone]}`}>
        {formatPercent(value)}
      </p>
    </div>
  );
}

function CaseCard({
  title,
  content,
  tone,
}: {
  title: string;
  content: string;
  tone: "success" | "accent" | "danger";
}) {
  const border = {
    success: "border-success/30",
    accent: "border-accent/30",
    danger: "border-danger/30",
  };
  return (
    <div className={`rounded-lg border ${border[tone]} bg-background/50 p-4`}>
      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted">
        {title}
      </p>
      <p className="text-sm leading-relaxed">{content}</p>
    </div>
  );
}

function SurpriseList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "success" | "danger";
}) {
  const color = tone === "success" ? "text-success" : "text-danger";
  return (
    <div>
      <p className={`mb-2 text-xs font-medium uppercase tracking-wider ${color}`}>
        {title}
      </p>
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item} className="text-sm text-muted">
            · {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-full border border-card-border bg-background/50 px-3 py-1.5">
      <span className="text-muted">{label}: </span>
      <span className="font-mono font-medium">{value}</span>
    </div>
  );
}
