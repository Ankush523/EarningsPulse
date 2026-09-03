"use client";

import { useState } from "react";

import { formatPercent } from "@/lib/format";
import type { PriceScenario } from "@/lib/types";

interface ScenarioTreeProps {
  scenarios: PriceScenario[];
}

const OUTCOME_COLOR: Record<string, string> = {
  beat: "border-success/40 bg-success/5",
  inline: "border-warning/40 bg-warning/5",
  miss: "border-danger/40 bg-danger/5",
};

export function ScenarioTree({ scenarios }: ScenarioTreeProps) {
  const [selected, setSelected] = useState(0);

  if (scenarios.length === 0) {
    return (
      <p className="text-sm text-muted">No scenario tree available.</p>
    );
  }

  const active = scenarios[selected] ?? scenarios[0];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {scenarios.map((scenario, index) => (
          <button
            key={`${scenario.outcome}-${scenario.label}`}
            type="button"
            onClick={() => setSelected(index)}
            className={`rounded-lg border px-3 py-2 text-left transition ${
              selected === index
                ? "border-accent bg-accent/10"
                : "border-card-border bg-background/50 hover:border-accent/40"
            }`}
          >
            <p className="text-xs font-medium capitalize">{scenario.outcome}</p>
            <p className="font-mono text-sm">{formatPercent(scenario.probability)}</p>
          </button>
        ))}
      </div>

      <div
        className={`rounded-xl border p-5 ${OUTCOME_COLOR[active.outcome] ?? "border-card-border"}`}
      >
        <div className="mb-3 flex items-start justify-between gap-4">
          <div>
            <h4 className="font-semibold">{active.label}</h4>
            <p className="mt-1 text-sm text-muted">{active.description}</p>
          </div>
          <div className="text-right">
            <p className="font-mono text-2xl font-bold">
              {formatPercent(active.probability)}
            </p>
            <p className="text-xs capitalize text-muted">
              {active.expected_direction} bias
            </p>
          </div>
        </div>

        {active.historical_reference && (
          <p className="mt-3 rounded-lg bg-background/60 px-3 py-2 text-xs text-muted">
            <span className="font-medium text-foreground">Historical: </span>
            {active.historical_reference}
          </p>
        )}

        {Object.keys(active.key_levels).length > 0 && (
          <div className="mt-4 flex flex-wrap gap-3">
            {Object.entries(active.key_levels).map(([level, value]) => (
              <div
                key={level}
                className="rounded-md border border-card-border bg-background/60 px-3 py-1.5"
              >
                <p className="text-[10px] uppercase text-muted">{level}</p>
                <p className="font-mono text-sm">{value.toFixed(2)}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
