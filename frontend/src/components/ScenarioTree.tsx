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
    <div className="space-y-3">
      <div
        role="tablist"
        aria-label="Reaction scenarios"
        className="flex flex-wrap gap-2"
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
              className={`cursor-pointer rounded-xl px-4 py-3 text-left transition sm:min-w-[8rem] ${
                isActive
                  ? "glass-panel-strong"
                  : "border border-transparent bg-surface-hover text-ink-soft hover:brightness-110 hover:text-ink"
              }`}
            >
              <span
                className={`text-[0.95rem] font-medium ${OUTCOME_TEXT[scenario.outcome] ?? ""}`}
              >
                {OUTCOME_LABEL[scenario.outcome] ?? scenario.outcome}
              </span>
              <span className="mt-1 block font-mono text-[1.35rem] leading-none">
                {formatPercent(scenario.probability)}
              </span>
            </button>
          );
        })}
      </div>

      <div role="tabpanel" className="glass-panel p-5 sm:p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2">
          <h3 className="text-[1.35rem] font-semibold leading-snug">{active.label}</h3>
          <span className="text-[0.95rem] text-ink-soft">
            Bias: {describeDirection(active.expected_direction).toLowerCase()}
          </span>
        </div>
        <p className="mt-2 text-ink-soft">{active.description}</p>

        {active.historical_reference && (
          <p className="mt-3 text-[0.95rem]">
            <span className="italic text-ink-soft">History: </span>
            {active.historical_reference}
          </p>
        )}

        {Object.keys(active.key_levels).length > 0 && (
          <dl className="mt-4 flex flex-wrap gap-2">
            {Object.entries(active.key_levels).map(([level, value]) => (
              <div key={level} className="glass-chip rounded-xl px-3 py-2">
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
