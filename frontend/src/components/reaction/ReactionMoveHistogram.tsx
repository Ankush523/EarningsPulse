"use client";

import { useTheme } from "@/components/ThemeProvider";
import { formatDate, formatPctMove } from "@/lib/format";
import { getReactionChartTheme } from "@/lib/reactionChartTheme";
import type { HistoricalReaction } from "@/lib/types";

interface ReactionMoveHistogramProps {
  reactions: HistoricalReaction[];
}

export function ReactionMoveHistogram({ reactions }: ReactionMoveHistogramProps) {
  const { theme } = useTheme();
  const palette = getReactionChartTheme(theme);

  if (reactions.length === 0) {
    return null;
  }

  const maxAbs = Math.max(
    ...reactions.map((reaction) => Math.abs(reaction.initial_move_pct)),
    1
  );

  return (
    <div className="reaction-workspace-divider border-t px-4 py-4 sm:px-5">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h4 className="text-[0.85rem] font-medium">First move after each report</h4>
        <span className="font-mono text-[0.75rem] text-chart-shell-soft">% from print</span>
      </div>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(3.5rem,1fr))] gap-2">
        {reactions.map((reaction) => {
          const height = Math.max(8, (Math.abs(reaction.initial_move_pct) / maxAbs) * 72);
          const positive = reaction.initial_move_pct >= 0;
          return (
            <div key={reaction.earnings_date} className="flex flex-col items-center gap-2">
              <div className="reaction-histogram-track flex h-[4.5rem] w-full items-end justify-center rounded-md px-1">
                <div
                  className="w-full max-w-[2rem] rounded-sm"
                  style={{
                    height: `${height}px`,
                    background: positive ? palette.up : palette.down,
                  }}
                  title={formatPctMove(reaction.initial_move_pct)}
                />
              </div>
              <div className="text-center">
                <p className="font-mono text-[0.72rem]">{formatPctMove(reaction.initial_move_pct)}</p>
                <p className="mt-0.5 text-[0.68rem] text-chart-shell-soft">
                  {formatDate(reaction.earnings_date).replace(/, \d{4}$/, "")}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
