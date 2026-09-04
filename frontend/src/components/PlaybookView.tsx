"use client";

import type { ReactNode } from "react";

import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { PeerSpilloverTable } from "@/components/PeerSpilloverTable";
import { ReactionChart } from "@/components/ReactionChart";
import { ScenarioTree } from "@/components/ScenarioTree";
import {
  describeArchetype,
  formatDate,
  formatLatency,
  formatPercent,
} from "@/lib/format";
import type { ConfidenceTier, Playbook } from "@/lib/types";

interface PlaybookViewProps {
  playbook: Playbook;
}

export function PlaybookView({ playbook }: PlaybookViewProps) {
  const { executive_summary: summary, report_forecast: forecast } = playbook;
  const reaction = playbook.reaction_analysis;
  const spillover = playbook.spillover_map;
  const actions = playbook.action_playbook;
  const meta = playbook.metadata;

  const reportLine = summary.earnings_date
    ? `Reports ${formatDate(summary.earnings_date)}${
        summary.is_after_hours ? ", after the close" : ""
      }.`
    : summary.is_after_hours
      ? "Reports after the close."
      : null;

  return (
    <article className="playbook-view">
      <header className="border-b border-ink pb-8">
        <p className="font-mono text-[1.05rem] text-ink-soft">{summary.ticker}</p>
        <h1 className="mt-1 text-balance text-[2.25rem] font-medium leading-[1.1] tracking-tight sm:text-[2.75rem]">
          {summary.company_name ?? summary.ticker} earnings playbook
        </h1>
        <p className="mt-3 flex flex-wrap items-baseline gap-x-5 gap-y-1 text-ink-soft">
          {reportLine && <span>{reportLine}</span>}
          <ConfidenceBadge tier={summary.overall_confidence} />
        </p>
      </header>

      <section className="py-10" aria-labelledby="odds-heading">
        <h2 id="odds-heading" className="sr-only">
          Report odds
        </h2>
        <OddsStrip
          beat={summary.beat_probability}
          inline={summary.inline_probability}
          miss={summary.miss_probability}
        />

        <div className="mt-10 grid gap-10 md:grid-cols-2">
          <div>
            <h3 className="text-[1.15rem] font-medium">Expected pattern</h3>
            <p className="mt-2 text-[1.35rem] leading-snug">
              {describeArchetype(summary.primary_pattern)}
            </p>
            <p className="mt-2 max-w-measure text-ink-soft">
              {summary.primary_pattern_description}
            </p>
          </div>
          <div>
            <h3 className="text-[1.15rem] font-medium">What decides it</h3>
            <ul className="mt-2 list-disc space-y-1.5 pl-5 marker:text-ink-soft">
              {summary.top_drivers.map((driver) => (
                <li key={driver}>{driver}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <DocSection title="Report forecast" confidence={forecast.confidence}>
        {forecast.key_metrics.length > 0 && (
          <dl className="grid gap-x-10 gap-y-5 sm:grid-cols-2">
            {forecast.key_metrics.map((metric) => (
              <div key={metric.name}>
                <dt className="flex flex-wrap items-baseline gap-x-3">
                  <span className="text-[1.1rem] font-medium">{metric.name}</span>
                  <span className="text-[0.85rem] italic text-ink-soft">
                    {IMPORTANCE_LABEL[metric.importance]}
                  </span>
                </dt>
                <dd className="mt-1 text-ink-soft">{metric.description}</dd>
              </div>
            ))}
          </dl>
        )}

        <div className="mt-10 grid gap-8 md:grid-cols-3">
          <Case title="Bull case" tone="up" text={forecast.bull_case} />
          <Case title="Base case" tone="ink" text={forecast.base_case} />
          <Case title="Bear case" tone="down" text={forecast.bear_case} />
        </div>

        {(forecast.positive_surprises.length > 0 ||
          forecast.negative_surprises.length > 0) && (
          <div className="mt-10 grid gap-8 sm:grid-cols-2">
            {forecast.positive_surprises.length > 0 && (
              <div>
                <h3 className="text-[1.1rem] font-medium text-up">
                  Could surprise to the upside
                </h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-soft marker:text-up">
                  {forecast.positive_surprises.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {forecast.negative_surprises.length > 0 && (
              <div>
                <h3 className="text-[1.1rem] font-medium text-down">
                  Could surprise to the downside
                </h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-soft marker:text-down">
                  {forecast.negative_surprises.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </DocSection>

      <DocSection title="Price reaction scenarios" confidence={reaction.confidence}>
        <p className="max-w-measure text-ink-soft">{reaction.archetype_description}</p>

        <div className="mt-6">
          <ScenarioTree scenarios={reaction.scenarios} />
        </div>

        {(reaction.avg_dip_pct != null ||
          reaction.avg_recovery_pct != null ||
          reaction.dip_frequency_on_positive != null) && (
          <dl className="mt-10 grid grid-cols-3 gap-6 border-t border-rule-soft pt-6">
            {reaction.avg_dip_pct != null && (
              <Figure
                label="Average dip"
                value={`${reaction.avg_dip_pct.toFixed(1)}%`}
                tone="down"
              />
            )}
            {reaction.avg_recovery_pct != null && (
              <Figure
                label="Average recovery"
                value={`+${reaction.avg_recovery_pct.toFixed(1)}%`}
                tone="up"
              />
            )}
            {reaction.dip_frequency_on_positive != null && (
              <Figure
                label="Beats that dipped first"
                value={formatPercent(reaction.dip_frequency_on_positive)}
              />
            )}
          </dl>
        )}

        {(reaction.implied_move_pct != null || reaction.historical_move_pct != null) && (
          <div className="mt-10 border-t border-rule-soft pt-6">
            <h3 className="text-[1.15rem] font-medium">
              What options expect against what usually happens
            </h3>
            <dl className="mt-4 grid grid-cols-2 gap-6 sm:max-w-md">
              {reaction.implied_move_pct != null && (
                <Figure
                  label="Options-implied move"
                  value={`±${reaction.implied_move_pct.toFixed(1)}%`}
                />
              )}
              {reaction.historical_move_pct != null && (
                <Figure
                  label="Typical realized move"
                  value={`±${reaction.historical_move_pct.toFixed(1)}%`}
                />
              )}
            </dl>
            {reaction.volatility_assessment && (
              <p className="mt-4 max-w-measure">
                <span className="font-medium">
                  {volatilityVerdict(reaction.volatility_assessment)}
                </span>
                {reaction.options_summary && (
                  <span className="text-ink-soft"> {reaction.options_summary}</span>
                )}
              </p>
            )}
          </div>
        )}

        {(reaction.backtest_years != null ||
          reaction.monte_carlo != null ||
          reaction.validation != null) && (
          <div className="mt-10 border-t border-rule-soft pt-6">
            <h3 className="text-[1.15rem] font-medium">Quantitative validation</h3>
            {reaction.backtest_years != null && (
              <p className="mt-2 text-ink-soft">
                Backtested across {reaction.historical_reactions.length} earnings over{" "}
                {reaction.backtest_years.toFixed(1)} years of price history.
              </p>
            )}
            {reaction.monte_carlo && (
              <dl className="mt-4 grid grid-cols-2 gap-6 sm:grid-cols-4">
                <Figure
                  label="MC median move"
                  value={`${reaction.monte_carlo.p50_final_move_pct >= 0 ? "+" : ""}${reaction.monte_carlo.p50_final_move_pct.toFixed(1)}%`}
                />
                <Figure
                  label="MC 10–90% band"
                  value={`${reaction.monte_carlo.p10_final_move_pct.toFixed(1)}% to ${reaction.monte_carlo.p90_final_move_pct.toFixed(1)}%`}
                />
                {reaction.monte_carlo.p50_max_dip_pct != null && (
                  <Figure
                    label="MC median dip"
                    value={`${reaction.monte_carlo.p50_max_dip_pct.toFixed(1)}%`}
                    tone="down"
                  />
                )}
                {reaction.monte_carlo.dip_before_recovery_prob != null && (
                  <Figure
                    label="Dip-then-recovery (sim)"
                    value={formatPercent(reaction.monte_carlo.dip_before_recovery_prob)}
                  />
                )}
              </dl>
            )}
            {reaction.validation && (
              <p className="mt-4 max-w-measure text-ink-soft">
                <span className="font-medium text-ink">
                  Overfitting check ({reaction.validation.overfitting_risk} risk):
                </span>{" "}
                {reaction.validation.summary}
              </p>
            )}
            {reaction.fib_levels && Object.keys(reaction.fib_levels).length > 0 && (
              <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
                {(["fib_0.382_pct", "fib_0.500_pct", "fib_0.618_pct"] as const).map((key) =>
                  reaction.fib_levels?.[key] != null ? (
                    <Figure
                      key={key}
                      label={key.replace("_pct", "").replace("fib_", "Fib ")}
                      value={`${reaction.fib_levels[key] >= 0 ? "+" : ""}${reaction.fib_levels[key].toFixed(1)}%`}
                    />
                  ) : null,
                )}
              </dl>
            )}
          </div>
        )}

        <div className="mt-10 border-t border-rule-soft pt-6">
          <h3 className="text-[1.15rem] font-medium">How the last reports traded</h3>
          <div className="mt-4">
            <ReactionChart
              reactions={reaction.historical_reactions}
              ticker={summary.ticker}
            />
          </div>
        </div>
      </DocSection>

      <DocSection title="Peer spillover map" confidence={spillover.confidence}>
        <PeerSpilloverTable peers={spillover.peers} />
      </DocSection>

      <DocSection title="Action playbook">
        {actions.rules.length === 0 ? (
          <p className="text-ink-soft">No conditional rules were produced.</p>
        ) : (
          <ol className="divide-y divide-rule-soft">
            {actions.rules.map((rule) => (
              <li
                key={`${rule.condition}:${rule.action}:${rule.confidence}`}
                className="grid gap-x-8 gap-y-2 py-5 first:pt-0 sm:grid-cols-[1fr_1.4fr]"
              >
                <p>
                  <span className="italic text-ink-soft">If </span>
                  <span className="font-medium">{rule.condition}</span>
                </p>
                <div>
                  <p>
                    <span className="italic text-ink-soft">then </span>
                    {rule.action}
                  </p>
                  <p className="mt-2 flex flex-wrap items-baseline gap-x-4 text-[0.9rem] text-ink-soft">
                    <ConfidenceBadge tier={rule.confidence} />
                    {rule.historical_basis && <span>{rule.historical_basis}</span>}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        )}
        {actions.disclaimer && (
          <p className="mt-8 max-w-measure text-[0.9rem] italic text-ink-soft">
            {actions.disclaimer}
          </p>
        )}
      </DocSection>

      <DocSection title="Sources">
        {playbook.all_sources.length === 0 ? (
          <p className="text-ink-soft">No sources were cited for this playbook.</p>
        ) : (
          <ul className="space-y-2.5">
            {playbook.all_sources.map((source) => (
              <li key={source.url} className="flex flex-wrap items-baseline gap-x-3">
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline decoration-rule underline-offset-4 hover:decoration-ink"
                >
                  {source.title}
                </a>
                <span className="text-[0.85rem] text-ink-soft">
                  {source.source_type}
                </span>
              </li>
            ))}
          </ul>
        )}
      </DocSection>

      <footer className="border-t border-rule pt-6 text-[0.9rem] text-ink-soft">
        Generated {formatDate(meta.generated_at)}
        {meta.generation_time_ms != null && ` in ${formatLatency(meta.generation_time_ms)}`}
        {" "}by EarningsPulse {meta.model_version}
        {meta.data_sources_used.length > 0 &&
          ` using ${meta.data_sources_used.join(", ")}`}
        . Job <span className="font-mono">{meta.job_id}</span>.
      </footer>
    </article>
  );
}

const IMPORTANCE_LABEL: Record<ConfidenceTier, string> = {
  high: "Decisive",
  medium: "Matters",
  low: "Minor",
};

function volatilityVerdict(assessment: string): string {
  switch (assessment.toUpperCase()) {
    case "OVERPRICED":
      return "Options look expensive relative to history.";
    case "UNDERPRICED":
      return "Options look cheap relative to history.";
    case "FAIR":
    case "FAIRLY_PRICED":
      return "Options are priced about in line with history.";
    default:
      return assessment;
  }
}

function DocSection({
  title,
  confidence,
  children,
}: {
  title: string;
  confidence?: ConfidenceTier;
  children: ReactNode;
}) {
  return (
    <section className="grid gap-x-10 gap-y-4 border-t border-rule py-10 lg:grid-cols-[11rem_1fr]">
      <div className="lg:sticky lg:top-6 lg:self-start">
        <h2 className="text-[1.25rem] font-medium leading-snug">{title}</h2>
        {confidence && (
          <p className="mt-1.5">
            <ConfidenceBadge tier={confidence} />
          </p>
        )}
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

function OddsStrip({
  beat,
  inline,
  miss,
}: {
  beat: number;
  inline: number;
  miss: number;
}) {
  const total = beat + inline + miss || 1;
  const segments = [
    { label: "Beat", value: beat, bar: "bg-up", text: "text-up" },
    { label: "Inline", value: inline, bar: "bg-rule", text: "text-ink-soft" },
    { label: "Miss", value: miss, bar: "bg-down", text: "text-down" },
  ];

  return (
    <div>
      <div className="grid grid-cols-3 gap-4">
        {segments.map((segment) => (
          <div key={segment.label}>
            <p className={`text-[1.05rem] ${segment.text}`}>{segment.label}</p>
            <p className="font-mono text-[2.5rem] leading-none tracking-tight sm:text-[3rem]">
              {formatPercent(segment.value)}
            </p>
          </div>
        ))}
      </div>
      <div
        className="mt-5 flex h-2.5 w-full gap-0.5 overflow-hidden rounded-sm"
        role="img"
        aria-label={`Beat ${formatPercent(beat)}, inline ${formatPercent(inline)}, miss ${formatPercent(miss)}`}
      >
        {segments.map((segment) => (
          <span
            key={segment.label}
            className={`block h-full ${segment.bar}`}
            style={{ width: `${(segment.value / total) * 100}%` }}
          />
        ))}
      </div>
    </div>
  );
}

function Case({
  title,
  tone,
  text,
}: {
  title: string;
  tone: "up" | "ink" | "down";
  text: string;
}) {
  const border = { up: "border-up", ink: "border-ink", down: "border-down" };
  const color = { up: "text-up", ink: "", down: "text-down" };
  return (
    <div className={`border-t-2 pt-3 ${border[tone]}`}>
      <h3 className={`text-[1.1rem] font-medium ${color[tone]}`}>{title}</h3>
      <p className="mt-1.5 text-ink-soft">{text}</p>
    </div>
  );
}

function Figure({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "up" | "down";
}) {
  const color = tone === "up" ? "text-up" : tone === "down" ? "text-down" : "";
  return (
    <div>
      <dt className="text-[0.9rem] text-ink-soft">{label}</dt>
      <dd className={`mt-0.5 font-mono text-[1.6rem] leading-none ${color}`}>{value}</dd>
    </div>
  );
}
