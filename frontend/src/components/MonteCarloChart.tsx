"use client";

import { formatPctMove } from "@/lib/format";
import type { MonteCarloSimulation } from "@/lib/types";

interface MonteCarloChartProps {
  simulation: MonteCarloSimulation;
  ticker: string;
}

export function MonteCarloChart({ simulation, ticker }: MonteCarloChartProps) {
  const { trajectories, baseline_price: baseline } = simulation;

  if (!trajectories || trajectories.length < 2) {
    return (
      <p className="max-w-measure rounded border border-dashed border-rule px-4 py-5 text-[0.95rem] text-ink-soft">
        Monte Carlo simulation data is not available for {ticker}.
      </p>
    );
  }

  const width = 640;
  const height = 240;
  const padding = { top: 20, right: 24, bottom: 40, left: 60 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  // Compute price bounds across all percentiles
  const allPrices = trajectories.flatMap((t) => [t.p5, t.p95]);
  const impliedUpper = baseline * (1 + simulation.expected_move_pct / 100);
  const impliedLower = baseline * (1 - simulation.expected_move_pct / 100);
  allPrices.push(impliedUpper, impliedLower, baseline);

  const minPrice = Math.min(...allPrices) * 0.98;
  const maxPrice = Math.max(...allPrices) * 1.02;
  const priceRange = maxPrice - minPrice || 1;

  const toX = (index: number) =>
    padding.left + (index / (trajectories.length - 1)) * chartW;
  const toY = (price: number) =>
    padding.top + chartH - ((price - minPrice) / priceRange) * chartH;

  const baselineY = toY(baseline);
  const impliedUpperY = toY(impliedUpper);
  const impliedLowerY = toY(impliedLower);

  // Build polygons for 90% corridor (P5 to P95) and 50% corridor (P25 to P75)
  const p95Points = trajectories.map((t, i) => `${toX(i)},${toY(t.p95)}`);
  const p5PointsReversed = [...trajectories]
    .reverse()
    .map((t, i) => `${toX(trajectories.length - 1 - i)},${toY(t.p5)}`);
  const corridor90 = [...p95Points, ...p5PointsReversed].join(" ");

  const p75Points = trajectories.map((t, i) => `${toX(i)},${toY(t.p75)}`);
  const p25PointsReversed = [...trajectories]
    .reverse()
    .map((t, i) => `${toX(trajectories.length - 1 - i)},${toY(t.p25)}`);
  const corridor50 = [...p75Points, ...p25PointsReversed].join(" ");

  const medianPoints = trajectories
    .map((t, i) => `${toX(i)},${toY(t.p50)}`)
    .join(" ");

  // Y-axis tick prices (3 ticks: min, baseline, max)
  const yTicks = [
    { price: minPrice * 1.01, label: `$${(minPrice * 1.01).toFixed(1)}` },
    { price: baseline, label: `$${baseline.toFixed(1)}` },
    { price: maxPrice * 0.99, label: `$${(maxPrice * 0.99).toFixed(1)}` },
  ];

  const terminal = trajectories[trajectories.length - 1];
  const winTone = simulation.prob_positive_return >= 50 ? "text-up" : "text-down";

  return (
    <div className="space-y-6">
      <div className="rounded border border-rule-soft bg-paper-light p-4 sm:p-5">
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule-soft pb-3">
          <div>
            <h4 className="text-[1.05rem] font-medium">
              10,000-path Monte Carlo cone ({simulation.window_days}-session horizon)
            </h4>
            <p className="mt-0.5 text-[0.85rem] text-ink-soft">
              Jump-diffusion model calibrated to options implied move (±
              {simulation.expected_move_pct.toFixed(1)}%) & daily volatility (
              {simulation.realized_daily_volatility_pct.toFixed(1)}%)
            </p>
          </div>
          <span className="font-mono text-[0.85rem] text-ink-soft">
            Baseline: ${baseline.toFixed(2)}
          </span>
        </div>

        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="mt-3 w-full"
          role="img"
          aria-label={`Monte Carlo simulated price fan chart for ${ticker} across ${simulation.window_days} post-earnings sessions`}
        >
          {/* Baseline horizontal line */}
          <line
            x1={padding.left}
            y1={baselineY}
            x2={width - padding.right}
            y2={baselineY}
            stroke="var(--rule)"
            strokeWidth="1.25"
          />

          {/* Options implied move boundaries */}
          <line
            x1={padding.left}
            y1={impliedUpperY}
            x2={width - padding.right}
            y2={impliedUpperY}
            stroke="var(--ink-soft)"
            strokeWidth="1"
            strokeDasharray="3 3"
            opacity={0.6}
          />
          <line
            x1={padding.left}
            y1={impliedLowerY}
            x2={width - padding.right}
            y2={impliedLowerY}
            stroke="var(--ink-soft)"
            strokeWidth="1"
            strokeDasharray="3 3"
            opacity={0.6}
          />

          {/* Y Axis ticks */}
          {yTicks.map((tick) => (
            <text
              key={tick.price}
              x={padding.left - 8}
              y={toY(tick.price) + 4}
              textAnchor="end"
              fill="var(--ink-soft)"
              fontFamily="var(--font-plex-mono)"
              fontSize="10"
            >
              {tick.label}
            </text>
          ))}

          {/* 90% confidence corridor (P5 to P95) */}
          <polygon
            points={corridor90}
            fill="currentColor"
            className="text-ink text-opacity-5"
          />

          {/* 50% interquartile corridor (P25 to P75) */}
          <polygon
            points={corridor50}
            fill="currentColor"
            className="text-ink text-opacity-10"
          />

          {/* Median path */}
          <polyline
            fill="none"
            stroke="var(--ink)"
            strokeWidth="2.25"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={medianPoints}
          />

          {/* Trajectory points & X axis labels */}
          {trajectories.map((traj, idx) => {
            const cx = toX(idx);
            const cy = toY(traj.p50);
            return (
              <g key={traj.day}>
                <circle cx={cx} cy={cy} r="3.5" fill="var(--ink)" />
                <text
                  x={cx}
                  y={height - 12}
                  textAnchor="middle"
                  fill="var(--ink-soft)"
                  fontFamily="var(--font-plex-mono)"
                  fontSize="10"
                >
                  {traj.label}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Legend */}
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3 text-[0.8rem] text-ink-soft">
          <div className="flex flex-wrap items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 bg-ink" />
              Median ($P_{50}$)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-4 rounded-sm bg-ink bg-opacity-10" />
              50% Range ($P_{25}–P_{75}$)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-4 rounded-sm bg-ink bg-opacity-5" />
              90% Corridor ($P_5–P_{95}$)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-px w-4 border-t border-dashed border-ink-soft opacity-60" />
              Options Straddle (±{simulation.expected_move_pct.toFixed(1)}%)
            </span>
          </div>
          <span className="font-mono text-[0.75rem]">
            End Median: ${terminal.p50.toFixed(2)} ({formatPctMove(terminal.p50_return_pct)})
          </span>
        </div>
      </div>

      {/* Probability & Risk Statistics Strip */}
      <dl className="grid grid-cols-2 gap-4 border-t border-rule-soft pt-4 sm:grid-cols-4">
        <div>
          <dt className="text-[0.82rem] text-ink-soft">Win probability</dt>
          <dd className={`font-mono text-[1.25rem] font-medium leading-tight ${winTone}`}>
            {simulation.prob_positive_return.toFixed(1)}%
          </dd>
        </div>
        <div>
          <dt className="text-[0.82rem] text-ink-soft">90% Price corridor</dt>
          <dd className="font-mono text-[1.1rem] leading-tight">
            ${simulation.expected_range.min.toFixed(1)} – ${simulation.expected_range.max.toFixed(1)}
          </dd>
        </div>
        <div>
          <dt className="text-[0.82rem] text-ink-soft">Exceeds implied move</dt>
          <dd className="font-mono text-[1.25rem] leading-tight">
            {simulation.prob_exceeds_implied_move.toFixed(1)}%
          </dd>
        </div>
        <div>
          <dt className="text-[0.82rem] text-ink-soft">95% VaR / CVaR</dt>
          <dd className="font-mono text-[1.1rem] text-down leading-tight">
            {formatPctMove(simulation.var_95_pct)} / {formatPctMove(simulation.cvar_95_pct)}
          </dd>
        </div>
      </dl>

      {/* Synthesis narrative */}
      <p className="rounded bg-paper px-3.5 py-2.5 text-[0.92rem] leading-relaxed text-ink-soft border border-rule-soft">
        <span className="font-medium text-ink">Simulation Takeaway: </span>
        {simulation.summary}
      </p>

      {/* Trajectories Table */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-left text-[0.9rem]">
          <thead>
            <tr className="border-b border-rule text-ink-soft">
              <th className="pb-2 pr-4 font-normal">Session</th>
              <th className="pb-2 pr-4 text-right font-normal">P5 (Bear)</th>
              <th className="pb-2 pr-4 text-right font-normal">P25</th>
              <th className="pb-2 pr-4 text-right font-normal">Median (P50)</th>
              <th className="pb-2 pr-4 text-right font-normal">P75</th>
              <th className="pb-2 pr-4 text-right font-normal">P95 (Bull)</th>
              <th className="pb-2 text-right font-normal">Median move</th>
            </tr>
          </thead>
          <tbody>
            {trajectories.map((t) => (
              <tr key={t.day} className="border-b border-rule-soft font-mono">
                <td className="py-2 pr-4 font-sans text-ink">{t.label}</td>
                <td className="py-2 pr-4 text-right text-ink-soft">${t.p5.toFixed(2)}</td>
                <td className="py-2 pr-4 text-right text-ink-soft">${t.p25.toFixed(2)}</td>
                <td className="py-2 pr-4 text-right font-medium text-ink">
                  ${t.p50.toFixed(2)}
                </td>
                <td className="py-2 pr-4 text-right text-ink-soft">${t.p75.toFixed(2)}</td>
                <td className="py-2 pr-4 text-right text-ink-soft">${t.p95.toFixed(2)}</td>
                <td className="py-2 text-right">
                  <span
                    className={
                      t.p50_return_pct > 0
                        ? "text-up"
                        : t.p50_return_pct < 0
                          ? "text-down"
                          : ""
                    }
                  >
                    {formatPctMove(t.p50_return_pct)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
