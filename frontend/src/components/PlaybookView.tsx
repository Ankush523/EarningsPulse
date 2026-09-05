"use client";

import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { PeerSpilloverTable } from "@/components/PeerSpilloverTable";
import { PlaybookSection } from "@/components/playbook/PlaybookSection";
import { ReactionAnalysisSection } from "@/components/playbook/ReactionAnalysisSection";
import { ReportForecastSection } from "@/components/playbook/ReportForecastSection";
import {
  describeArchetype,
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
  const meta = playbook.metadata;

  return (
    <article className="playbook-view">
      <PlaybookHeader summary={summary} />
      <ExecutiveOddsSection summary={summary} />
      <ReportForecastSection forecast={forecast} />
      <ReactionAnalysisSection reaction={reaction} ticker={summary.ticker} />
      <PlaybookSection title="Peer spillover map" confidence={spillover.confidence}>
        <PeerSpilloverTable peers={spillover.peers} />
      </PlaybookSection>
      <ActionPlaybookSection actions={actions} />
      <SourcesSection sources={playbook.all_sources} />
      <PlaybookFooter meta={meta} />
    </article>
  );
}

function PlaybookHeader({ summary }: { summary: Playbook["executive_summary"] }) {
  const reportLine = buildReportLine(summary);

  return (
    <header className="glass-panel-strong mb-5 p-6 sm:p-8 xl:p-10">
      <p className="font-mono text-[1.05rem] text-ink-soft">{summary.ticker}</p>
      <h1 className="mt-1 text-balance text-[2.25rem] font-semibold leading-[1.1] tracking-tight sm:text-[2.75rem]">
        {summary.company_name ?? summary.ticker} earnings playbook
      </h1>
      <p className="mt-3 flex flex-wrap items-baseline gap-x-5 gap-y-2 text-ink-soft">
        {reportLine && <span>{reportLine}</span>}
        <ConfidenceBadge tier={summary.overall_confidence} />
      </p>
    </header>
  );
}

function buildReportLine(summary: Playbook["executive_summary"]): string | null {
  if (summary.earnings_date) {
    const suffix = summary.is_after_hours ? ", after the close" : "";
    return `Reports ${formatDate(summary.earnings_date)}${suffix}.`;
  }
  if (summary.is_after_hours) {
    return "Reports after the close.";
  }
  return null;
}

function ExecutiveOddsSection({ summary }: { summary: Playbook["executive_summary"] }) {
  return (
    <section className="glass-panel mb-5 p-6 sm:p-8 xl:p-10" aria-labelledby="odds-heading">
      <h2 id="odds-heading" className="sr-only">
        Report odds
      </h2>
      <OddsStrip
        beat={summary.beat_probability}
        inline={summary.inline_probability}
        miss={summary.miss_probability}
      />
      <div className="mt-10 grid gap-10 lg:grid-cols-2 lg:gap-12">
        <div>
          <h3 className="text-[1.15rem] font-semibold">Expected pattern</h3>
          <p className="mt-2 text-[1.35rem] leading-snug">
            {describeArchetype(summary.primary_pattern)}
          </p>
          <p className="mt-2 text-ink-soft">{summary.primary_pattern_description}</p>
        </div>
        <div>
          <h3 className="text-[1.15rem] font-semibold">What decides it</h3>
          <ul className="mt-2 list-disc space-y-1.5 pl-5 marker:text-ink-soft">
            {summary.top_drivers.map((driver) => (
              <li key={driver}>{driver}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function ActionPlaybookSection({ actions }: { actions: Playbook["action_playbook"] }) {
  return (
    <PlaybookSection title="Action playbook">
      {actions.rules.length === 0 ? (
        <p className="text-ink-soft">No conditional rules were produced.</p>
      ) : (
        <ol className="divide-y divide-white/40">
          {actions.rules.map((rule) => (
            <li
              key={`${rule.condition}:${rule.action}:${rule.confidence}`}
              className="grid gap-x-10 gap-y-2 py-5 first:pt-0 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)]"
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
        <p className="mt-8 text-[0.9rem] italic text-ink-soft">
          {actions.disclaimer}
        </p>
      )}
    </PlaybookSection>
  );
}

function SourcesSection({ sources }: { sources: Playbook["all_sources"] }) {
  return (
    <PlaybookSection title="Sources">
      {sources.length === 0 ? (
        <p className="text-ink-soft">No sources were cited for this playbook.</p>
      ) : (
        <ul className="space-y-2.5">
          {sources.map((source) => (
            <li key={source.url} className="flex flex-wrap items-baseline gap-x-3">
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="link-glass font-medium"
              >
                {source.title}
              </a>
              <span className="text-[0.85rem] text-ink-soft">{source.source_type}</span>
            </li>
          ))}
        </ul>
      )}
    </PlaybookSection>
  );
}

function PlaybookFooter({ meta }: { meta: Playbook["metadata"] }) {
  return (
    <footer className="glass-panel mt-5 p-6 text-[0.9rem] text-ink-soft sm:p-8">
      Generated {formatDate(meta.generated_at)}
      {meta.generation_time_ms != null && ` in ${formatLatency(meta.generation_time_ms)}`}
      {" "}by EarningsPulse {meta.model_version}
      {meta.data_sources_used.length > 0 && ` using ${meta.data_sources_used.join(", ")}`}
      . Job <span className="font-mono">{meta.job_id}</span>.
    </footer>
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
      <div className="grid gap-4 sm:grid-cols-3">
        {segments.map((segment) => (
          <div key={segment.label} className="glass-chip min-w-0 rounded-2xl px-5 py-4">
            <p className={`text-[1.05rem] font-medium ${segment.text}`}>{segment.label}</p>
            <p className="font-mono text-[2.5rem] leading-none tracking-tight sm:text-[3rem]">
              {formatPercent(segment.value)}
            </p>
          </div>
        ))}
      </div>
      <div
        className="mt-5 flex h-3 w-full gap-0.5 overflow-hidden rounded-full bg-white/35 p-0.5"
        role="img"
        aria-label={`Beat ${formatPercent(beat)}, inline ${formatPercent(inline)}, miss ${formatPercent(miss)}`}
      >
        {segments.map((segment) => (
          <span
            key={segment.label}
            className={`block h-full rounded-full ${segment.bar}`}
            style={{ width: `${(segment.value / total) * 100}%` }}
          />
        ))}
      </div>
    </div>
  );
}
