"use client";

import { useState } from "react";

import { ReactionCandleChart } from "@/components/reaction/ReactionCandleChart";
import { ReactionMoveHistogram } from "@/components/reaction/ReactionMoveHistogram";
import { useTheme } from "@/components/ThemeProvider";
import { describeArchetype, formatDate } from "@/lib/format";
import {
  describeArchetypeShort,
  formatPrice,
  getReferenceLineColors,
  getReactionChartTheme,
} from "@/lib/reactionChartTheme";
import type { HistoricalReaction, ReactionChartData } from "@/lib/types";

interface ReactionWorkspaceProps {
  ticker: string;
  chart: ReactionChartData | null | undefined;
  historicalReactions: HistoricalReaction[];
  impliedMovePct?: number | null;
  historicalMovePct?: number | null;
  archetype: string;
}

export function ReactionWorkspace({
  ticker,
  chart,
  historicalReactions,
  impliedMovePct,
  historicalMovePct,
  archetype,
}: ReactionWorkspaceProps) {
  const { theme } = useTheme();
  const palette = getReactionChartTheme(theme);
  const lineColors = getReferenceLineColors(theme);

  const [selectedPathDate, setSelectedPathDate] = useState<string | null>(
    chart?.focus_earnings_date ?? null
  );
  const [showMedian, setShowMedian] = useState(true);
  const [showGhostPaths, setShowGhostPaths] = useState(true);

  const pathOptions = chart?.paths ?? [];

  if (!chart || chart.candles.length === 0) {
    return (
      <section aria-label="Reaction workspace" className="reaction-workspace">
        <div className="reaction-workspace-divider border-b px-4 py-4 sm:px-5">
          <p className="font-mono text-[0.95rem] text-chart-shell-muted">{ticker}</p>
          <h3 className="mt-1 text-[1.15rem] font-semibold">Reaction workspace</h3>
          <p className="mt-2 text-[0.92rem] text-chart-shell-muted">
            Price history around the print is not available for this run yet. The
            summary stats and scenario tabs below still reflect the model output.
          </p>
        </div>
        <ReactionMoveHistogram reactions={historicalReactions} />
      </section>
    );
  }

  const latestClose = chart.candles[chart.candles.length - 1]?.close;
  const moveFromBaseline =
    latestClose != null
      ? ((latestClose - chart.baseline_price) / chart.baseline_price) * 100
      : null;

  return (
    <section aria-label="Reaction workspace" className="reaction-workspace">
      <div className="reaction-workspace-divider border-b px-4 py-4 sm:px-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-[0.95rem] text-chart-shell-muted">{ticker}</p>
            <h3 className="mt-1 text-[1.2rem] font-semibold">
              Price around the {formatDate(chart.focus_earnings_date)} print
            </h3>
            <p className="mt-1 text-[0.9rem] capitalize text-chart-shell-muted">
              {describeArchetypeShort(archetype)} · ±{chart.window_days} trading days
            </p>
          </div>
          <dl className="grid grid-cols-2 gap-x-5 gap-y-2 text-right sm:grid-cols-4">
            <Metric label="Pre-print close" value={`$${formatPrice(chart.baseline_price)}`} />
            <Metric
              label="Window move"
              value={
                moveFromBaseline != null
                  ? `${moveFromBaseline >= 0 ? "+" : ""}${moveFromBaseline.toFixed(1)}%`
                  : "—"
              }
              tone={moveFromBaseline != null && moveFromBaseline >= 0 ? "up" : "down"}
            />
            <Metric
              label="Implied move"
              value={impliedMovePct != null ? `±${impliedMovePct.toFixed(1)}%` : "—"}
            />
            <Metric
              label="Historical avg"
              value={historicalMovePct != null ? `±${historicalMovePct.toFixed(1)}%` : "—"}
            />
          </dl>
        </div>
      </div>

      <div className="reaction-workspace-divider flex flex-wrap items-center gap-2 border-b px-4 py-3 sm:px-5">
        <label className="text-[0.8rem] text-chart-shell-muted">
          Overlay print
          <select
            value={selectedPathDate ?? chart.focus_earnings_date}
            onChange={(event) => setSelectedPathDate(event.target.value)}
            className="reaction-workspace-control ml-2 cursor-pointer rounded-lg px-2.5 py-1.5 font-mono text-[0.82rem]"
          >
            {pathOptions.map((path) => (
              <option key={path.earnings_date} value={path.earnings_date}>
                {formatDate(path.earnings_date)}
                {path.report_outcome ? ` · ${path.report_outcome}` : ""}
              </option>
            ))}
          </select>
        </label>

        <ToggleChip
          pressed={showMedian}
          onClick={() => setShowMedian((value) => !value)}
          label="Median path"
        />
        <ToggleChip
          pressed={showGhostPaths}
          onClick={() => setShowGhostPaths((value) => !value)}
          label="Other prints"
        />

        <span className="ml-auto hidden text-[0.78rem] text-chart-shell-soft sm:inline">
          Pattern: {describeArchetype(archetype)}
        </span>
      </div>

      <ReactionCandleChart
        candles={chart.candles}
        focusEarningsDate={chart.focus_earnings_date}
        focusBaseline={chart.baseline_price}
        referenceLines={chart.reference_lines}
        medianPath={chart.median_path}
        paths={chart.paths}
        selectedPathDate={selectedPathDate}
        showMedian={showMedian}
        showGhostPaths={showGhostPaths}
      />

      {chart.reference_lines.length > 0 && (
        <div className="reaction-workspace-divider flex flex-wrap gap-x-4 gap-y-1 border-t px-4 py-2 sm:px-5">
          {chart.reference_lines.map((line) => (
            <span
              key={`${line.kind}-${line.price}`}
              className="inline-flex items-center gap-1.5 font-mono text-[0.72rem] text-chart-shell-muted"
            >
              <span
                className="inline-block h-0.5 w-4 rounded-full"
                style={{
                  backgroundColor: lineColors[line.kind] ?? palette.accent,
                }}
              />
              {line.label} ${formatPrice(line.price)}
            </span>
          ))}
        </div>
      )}

      <ReactionMoveHistogram reactions={historicalReactions} />

      <p className="reaction-workspace-divider border-t px-4 py-3 text-[0.8rem] text-chart-shell-soft sm:px-5">
        Daily candles and volume from Yahoo Finance. Overlays show pivot, support,
        resistance, entry, take-profit, and stop-loss levels derived from pre-print
        price action and historical reaction stats.
      </p>
    </section>
  );
}

function Metric({
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
      <dt className="text-[0.72rem] uppercase tracking-wide text-chart-shell-soft">{label}</dt>
      <dd className={`mt-0.5 font-mono text-[0.95rem] ${color}`}>{value}</dd>
    </div>
  );
}

function ToggleChip({
  label,
  pressed,
  onClick,
}: {
  label: string;
  pressed: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      data-pressed={pressed ? "true" : "false"}
      onClick={onClick}
      className="reaction-workspace-chip cursor-pointer rounded-full px-3 py-1.5 text-[0.78rem] font-medium"
    >
      {label}
    </button>
  );
}
