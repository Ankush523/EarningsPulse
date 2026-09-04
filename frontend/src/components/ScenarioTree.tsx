"use client";

import { useState } from "react";

import { describeDirection, formatPercent } from "@/lib/format";
import type { PriceScenario } from "@/lib/types";

interface ScenarioTreeProps {
  scenarios: PriceScenario[];
}

const OUTCOME_TEXT: Record<string, string> = {
  beat: "text-up",
  inline: "text-ink-soft",
  miss: "text-down",
};

const OUTCOME_LABEL: Record<string, string> = {
  beat: "Beat",
  inline: "Inline",
  miss: "Miss",
};

export function ScenarioTree({ scenarios }: ScenarioTreeProps) {
  const [selected, setSelected] = useState(0);

  if (scenarios.length === 0) {
    return (
      <p className="text-ink-soft">
        No scenario tree was produced for this report.
      </p>
    );
  }

  const active = scenarios[selected] ?? scenarios[0];

  return (
    <div>
      <div
        role="tablist"
        aria-label="Reaction scenarios"
        className="flex border-b border-rule"
      >
        {scenarios.map((scenario, index) => {
          const isActive = selected === index;
          return (
            <button
              key={`${scenario.outcome}-${scenario.label}`}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setSelected(index)}
              className={`-mb-px flex flex-1 flex-col items-start gap-0.5 border-b-2 px-1 pb-3 pt-1 text-left transition sm:flex-none sm:pr-8 ${
                isActive
                  ? "border-ink"
                  : "border-transparent text-ink-soft hover:text-ink"
              }`}
            >
              <span className={`text-[0.95rem] ${OUTCOME_TEXT[scenario.outcome] ?? ""}`}>
                {OUTCOME_LABEL[scenario.outcome] ?? scenario.outcome}
              </span>
              <span className="font-mono text-[1.35rem] leading-none">
                {formatPercent(scenario.probability)}
              </span>
            </button>
          );
        })}
      </div>

      <div role="tabpanel" className="pt-5">
        <div className="flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2">
          <h3 className="text-[1.35rem] font-medium leading-snug">{active.label}</h3>
          <span className="text-[0.95rem] text-ink-soft">
            Bias: {describeDirection(active.expected_direction).toLowerCase()}
          </span>
        </div>
        <p className="mt-2 max-w-measure text-ink-soft">{active.description}</p>

        {active.historical_reference && (
          <p className="mt-3 max-w-measure text-[0.95rem]">
            <span className="italic text-ink-soft">History: </span>
            {active.historical_reference}
          </p>
        )}

        {Object.keys(active.key_levels).length > 0 && (
          <dl className="mt-4 flex flex-wrap gap-x-8 gap-y-2">
            {Object.entries(active.key_levels).map(([level, value]) => (
              <div key={level}>
                <dt className="text-[0.85rem] text-ink-soft">{level}</dt>
                <dd className="font-mono text-[1.05rem]">{value.toFixed(2)}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </div>
  );
}
