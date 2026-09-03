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
      <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-card-border text-sm text-muted">
        No historical reaction data available
      </div>
    );
  }

  const width = 640;
  const height = 220;
  const padding = { top: 20, right: 20, bottom: 40, left: 48 };
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
    <div className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full min-w-[320px]"
        role="img"
        aria-label={`Historical earnings reactions for ${ticker}`}
      >
        <line
          x1={padding.left}
          y1={zeroY}
          x2={width - padding.right}
          y2={zeroY}
          stroke="var(--card-border)"
          strokeDasharray="4 4"
        />

        {[minY, 0, maxY].map((tick) => (
          <g key={tick}>
            <line
              x1={padding.left - 4}
              y1={toY(tick)}
              x2={padding.left}
              y2={toY(tick)}
              stroke="var(--muted)"
            />
            <text
              x={padding.left - 8}
              y={toY(tick) + 4}
              textAnchor="end"
              className="fill-muted text-[10px]"
            >
              {tick.toFixed(0)}%
            </text>
          </g>
        ))}

        <polyline
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
          points={initialPoints}
        />

        {reactions.map((reaction, index) => {
          const cx = toX(index);
          const cy = toY(reaction.initial_move_pct);
          const dipY =
            reaction.dip_pct != null ? toY(reaction.dip_pct) : null;

          return (
            <g key={`${reaction.earnings_date}-${index}`}>
              {dipY != null && (
                <line
                  x1={cx}
                  y1={cy}
                  x2={cx}
                  y2={dipY}
                  stroke="var(--danger)"
                  strokeWidth="1.5"
                  strokeDasharray="3 2"
                />
              )}
              <circle cx={cx} cy={cy} r="4" fill="var(--accent)" />
              <text
                x={cx}
                y={height - 12}
                textAnchor="middle"
                className="fill-muted text-[9px]"
              >
                {formatDate(reaction.earnings_date).replace(/, \d{4}$/, "")}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 bg-accent" />
          Initial move
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 border-t border-dashed border-danger" />
          Dip depth
        </span>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[480px] text-left text-xs">
          <thead>
            <tr className="border-b border-card-border text-muted">
              <th className="pb-2 pr-4 font-medium">Date</th>
              <th className="pb-2 pr-4 font-medium">Outcome</th>
              <th className="pb-2 pr-4 font-medium">Initial</th>
              <th className="pb-2 pr-4 font-medium">Dip</th>
              <th className="pb-2 font-medium">Recovery</th>
            </tr>
          </thead>
          <tbody>
            {reactions.map((r) => (
              <tr
                key={r.earnings_date}
                className="border-b border-card-border/50"
              >
                <td className="py-2 pr-4 font-mono">{formatDate(r.earnings_date)}</td>
                <td className="py-2 pr-4 capitalize">{r.report_outcome ?? "—"}</td>
                <td className="py-2 pr-4 font-mono">{formatPctMove(r.initial_move_pct)}</td>
                <td className="py-2 pr-4 font-mono">
                  {r.dip_pct != null ? formatPctMove(r.dip_pct) : "—"}
                </td>
                <td className="py-2 font-mono">
                  {r.recovery_pct != null ? formatPctMove(r.recovery_pct) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
