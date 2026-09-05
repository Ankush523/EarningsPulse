import { ReactionWorkspace } from "@/components/reaction/ReactionWorkspace";
import { ScenarioTree } from "@/components/ScenarioTree";
import { Figure, PlaybookSection } from "@/components/playbook/PlaybookSection";
import { formatPercent } from "@/lib/format";
import type { Playbook } from "@/lib/types";

const FIB_LEVEL_KEYS = ["fib_0.382_pct", "fib_0.500_pct", "fib_0.618_pct"] as const;

type ReactionAnalysis = Playbook["reaction_analysis"];

interface ReactionAnalysisSectionProps {
  reaction: ReactionAnalysis;
  ticker: string;
}

export function ReactionAnalysisSection({ reaction, ticker }: ReactionAnalysisSectionProps) {
  return (
    <PlaybookSection title="Price reaction scenarios" confidence={reaction.confidence}>
      <p className="text-ink-soft">{reaction.archetype_description}</p>

      <div className="mt-6">
        <ReactionWorkspace
          ticker={ticker}
          chart={reaction.reaction_chart}
          historicalReactions={reaction.historical_reactions}
          impliedMovePct={reaction.implied_move_pct}
          historicalMovePct={reaction.historical_move_pct}
          archetype={reaction.archetype}
        />
      </div>

      <div className="mt-8">
        <ScenarioTree scenarios={reaction.scenarios} />
      </div>

      <ReactionStats reaction={reaction} />
      <OptionsVolatilityBlock reaction={reaction} />
      <QuantitativeValidationBlock reaction={reaction} />
    </PlaybookSection>
  );
}

function ReactionStats({ reaction }: { reaction: ReactionAnalysis }) {
  const hasStats =
    reaction.avg_dip_pct != null ||
    reaction.avg_recovery_pct != null ||
    reaction.dip_frequency_on_positive != null;

  if (!hasStats) {
    return null;
  }

  return (
    <dl className="mt-10 grid grid-cols-3 gap-6 border-t border-white/45 pt-6">
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
  );
}

function OptionsVolatilityBlock({ reaction }: { reaction: ReactionAnalysis }) {
  if (reaction.implied_move_pct == null && reaction.historical_move_pct == null) {
    return null;
  }

  return (
    <div className="mt-10 border-t border-rule-soft pt-6">
      <h3 className="text-[1.15rem] font-medium">
        What options expect against what usually happens
      </h3>
      <dl className="mt-4 grid grid-cols-2 gap-6 lg:grid-cols-4">
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
        <p className="mt-4">
          <span className="font-medium">
            {volatilityVerdict(reaction.volatility_assessment)}
          </span>
          {reaction.options_summary && (
            <span className="text-ink-soft"> {reaction.options_summary}</span>
          )}
        </p>
      )}
    </div>
  );
}

function QuantitativeValidationBlock({ reaction }: { reaction: ReactionAnalysis }) {
  const hasQuant =
    reaction.backtest_years != null ||
    reaction.monte_carlo != null ||
    reaction.validation != null;

  if (!hasQuant) {
    return null;
  }

  return (
    <div className="mt-10 border-t border-rule-soft pt-6">
      <h3 className="text-[1.15rem] font-medium">Quantitative validation</h3>
      {reaction.backtest_years != null && (
        <p className="mt-2 text-ink-soft">
          Backtested across {reaction.historical_reactions.length} earnings over{" "}
          {reaction.backtest_years.toFixed(1)} years of price history.
        </p>
      )}
      {reaction.monte_carlo && <MonteCarloFigures monteCarlo={reaction.monte_carlo} />}
      {reaction.validation && (
        <p className="mt-4 text-ink-soft">
          <span className="font-medium text-ink">
            Overfitting check ({reaction.validation.overfitting_risk} risk):
          </span>{" "}
          {reaction.validation.summary}
        </p>
      )}
      <FibLevels fibLevels={reaction.fib_levels} />
    </div>
  );
}

function MonteCarloFigures({
  monteCarlo,
}: {
  monteCarlo: NonNullable<ReactionAnalysis["monte_carlo"]>;
}) {
  return (
    <dl className="mt-4 grid grid-cols-2 gap-6 sm:grid-cols-4">
      <Figure
        label="MC median move"
        value={`${monteCarlo.p50_final_move_pct >= 0 ? "+" : ""}${monteCarlo.p50_final_move_pct.toFixed(1)}%`}
      />
      <Figure
        label="MC 10–90% band"
        value={`${monteCarlo.p10_final_move_pct.toFixed(1)}% to ${monteCarlo.p90_final_move_pct.toFixed(1)}%`}
      />
      {monteCarlo.p50_max_dip_pct != null && (
        <Figure
          label="MC median dip"
          value={`${monteCarlo.p50_max_dip_pct.toFixed(1)}%`}
          tone="down"
        />
      )}
      {monteCarlo.dip_before_recovery_prob != null && (
        <Figure
          label="Dip-then-recovery (sim)"
          value={formatPercent(monteCarlo.dip_before_recovery_prob)}
        />
      )}
    </dl>
  );
}

function FibLevels({ fibLevels }: { fibLevels?: Record<string, number> }) {
  if (!fibLevels || Object.keys(fibLevels).length === 0) {
    return null;
  }

  return (
    <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
      {FIB_LEVEL_KEYS.map((key) => {
        const value = fibLevels[key];
        if (value == null) {
          return null;
        }
        return (
          <Figure
            key={key}
            label={key.replace("_pct", "").replace("fib_", "Fib ")}
            value={`${value >= 0 ? "+" : ""}${value.toFixed(1)}%`}
          />
        );
      })}
    </dl>
  );
}

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
