"use client";

import { formatDate, formatPctMove } from "@/lib/format";
import type { HistoricalReaction } from "@/lib/types";

interface ReactionChartProps {
  reactions: HistoricalReaction[];
  ticker: string;
}

export function ReactionChart({ reactions, ticker }: ReactionChartProps) {
  if (reactions.length === 0) {
    return (
      <p className="max-w-measure rounded border border-dashed border-rule px-4 py-5 text-[0.95rem] text-ink-soft">
        No prior report-day reactions on file for {ticker}. This chart fills in
        when price history is available for the last several prints.
      </p>
    );
  }

  const width = 640;
  const height = 220;
  const padding = { top: 16, right: 16, bottom: 36, left: 44 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const values = reactions.flatMap((r) =>
    [r.initial_move_pct, r.dip_pct ?? r.initial_move_pct, r.recovery_pct ?? r.initial_move_pct].filter(
      (v): v is number => v != null
    )
  );
  const minY = Math.min(...values, -5) - 2;
  const maxY = Math.max(...values, 5) + 2;
  const rangeY = maxY - minY || 1;

  const xStep = chartW / Math.max(reactions.length - 1, 1);
  const toX = (index: number) => padding.left + index * xStep;
  const toY = (value: number) =>
    padding.top + chartH - ((value - minY) / rangeY) * chartH;

  const zeroY = toY(0);

  const initialPoints = reactions
    .map((r, i) => `${toX(i)},${toY(r.initial_move_pct)}`)
    .join(" ");

  return (
    <div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        role="img"
        aria-label={`Report-day price moves for ${ticker} across the last ${reactions.length} reports`}
      >
        <line
          x1={padding.left}
          y1={zeroY}
          x2={width - padding.right}
          y2={zeroY}
          stroke="var(--rule)"
        />

        {[minY, 0, maxY].map((tick) => (
          <text
            key={tick}
            x={padding.left - 8}
            y={toY(tick) + 4}
            textAnchor="end"
            fill="var(--ink-soft)"
            fontFamily="var(--font-plex-mono)"
            fontSize="10"
          >
            {tick.toFixed(0)}%
          </text>
        ))}

        <polyline
          fill="none"
          stroke="var(--ink)"
          strokeWidth="1.75"
          points={initialPoints}
        />

        {reactions.map((reaction, index) => {
          const cx = toX(index);
          const cy = toY(reaction.initial_move_pct);
          const dipY = reaction.dip_pct != null ? toY(reaction.dip_pct) : null;

          return (
            <g key={`${reaction.earnings_date}-${index}`}>
              {dipY != null && (
                <line
                  x1={cx}
                  y1={cy}
                  x2={cx}
                  y2={dipY}
                  stroke="var(--down)"
                  strokeWidth="1.5"
                  strokeDasharray="3 2"
                />
              )}
              <circle
                cx={cx}
                cy={cy}
                r="3.5"
                fill={reaction.initial_move_pct >= 0 ? "var(--up)" : "var(--down)"}
              />
              <text
                x={cx}
                y={height - 10}
                textAnchor="middle"
                fill="var(--ink-soft)"
                fontFamily="var(--font-plex-mono)"
                fontSize="9.5"
              >
                {formatDate(reaction.earnings_date).replace(/, \d{4}$/, "")}
              </text>
            </g>
          );
        })}
      </svg>

      <p className="mt-2 flex flex-wrap gap-5 text-[0.85rem] text-ink-soft">
        <span className="flex items-center gap-2">
          <span className="inline-block h-px w-5 bg-ink" />
          First move after the print
        </span>
        <span className="flex items-center gap-2">
          <span className="inline-block h-px w-5 border-t border-dashed border-down" />
          Depth of the dip
        </span>
      </p>

      <div className="mt-5 overflow-x-auto">
        <table className="w-full min-w-[480px] text-left text-[0.95rem]">
          <thead>
            <tr className="border-b border-rule text-ink-soft">
              <th className="pb-2 pr-4 font-normal">Report</th>
              <th className="pb-2 pr-4 font-normal">Outcome</th>
              <th className="pb-2 pr-4 text-right font-normal">First move</th>
              <th className="pb-2 pr-4 text-right font-normal">Dip</th>
              <th className="pb-2 text-right font-normal">Recovery</th>
            </tr>
          </thead>
          <tbody>
            {reactions.map((r) => (
              <tr key={r.earnings_date} className="border-b border-rule-soft">
                <td className="py-2 pr-4 font-mono text-[0.9rem]">
                  {formatDate(r.earnings_date)}
                </td>
                <td className="py-2 pr-4 capitalize">{r.report_outcome ?? "Unknown"}</td>
                <td className="py-2 pr-4 text-right font-mono">
                  <Move value={r.initial_move_pct} />
                </td>
                <td className="py-2 pr-4 text-right font-mono">
                  {r.dip_pct != null ? <Move value={r.dip_pct} /> : "—"}
                </td>
                <td className="py-2 text-right font-mono">
                  {r.recovery_pct != null ? <Move value={r.recovery_pct} /> : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Move({ value }: { value: number }) {
  const tone = value > 0 ? "text-up" : value < 0 ? "text-down" : "";
  return <span className={tone}>{formatPctMove(value)}</span>;
}
