"use client";

import { useState } from "react";

import { formatRelationship } from "@/lib/format";
import type { PeerSpillover } from "@/lib/types";

interface PeerSpilloverTableProps {
  peers: PeerSpillover[];
}

type SortKey = "correlation_score" | "ticker" | "relationship";

export function PeerSpilloverTable({ peers }: PeerSpilloverTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("correlation_score");
  const [sortAsc, setSortAsc] = useState(false);

  const sorted = [...peers].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    if (typeof aVal === "number" && typeof bVal === "number") {
      return sortAsc ? aVal - bVal : bVal - aVal;
    }
    return sortAsc
      ? String(aVal).localeCompare(String(bVal))
      : String(bVal).localeCompare(String(aVal));
  });

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc((prev) => !prev);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  if (peers.length === 0) {
    return (
      <p className="text-sm text-muted">No peer spillover data available.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-card-border text-xs text-muted">
            <th className="pb-3 pr-4">
              <SortButton label="Ticker" active={sortKey === "ticker"} onClick={() => toggleSort("ticker")} />
            </th>
            <th className="pb-3 pr-4">Company</th>
            <th className="pb-3 pr-4">
              <SortButton
                label="Relationship"
                active={sortKey === "relationship"}
                onClick={() => toggleSort("relationship")}
              />
            </th>
            <th className="pb-3 pr-4">
              <SortButton
                label="Correlation"
                active={sortKey === "correlation_score"}
                onClick={() => toggleSort("correlation_score")}
              />
            </th>
            <th className="pb-3 pr-4">Direction</th>
            <th className="pb-3">Rationale</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((peer) => (
            <tr
              key={peer.ticker}
              className="border-b border-card-border/50 align-top"
            >
              <td className="py-3 pr-4">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-semibold">{peer.ticker}</span>
                  {peer.watch_flag && (
                    <span className="rounded bg-accent/20 px-1.5 py-0.5 text-[10px] text-accent">
                      WATCH
                    </span>
                  )}
                </div>
              </td>
              <td className="py-3 pr-4 text-muted">
                {peer.company_name ?? "—"}
              </td>
              <td className="py-3 pr-4 capitalize text-muted">
                {formatRelationship(peer.relationship)}
              </td>
              <td className="py-3 pr-4">
                <CorrelationBar score={peer.correlation_score} />
              </td>
              <td className="py-3 pr-4 capitalize text-muted">
                {peer.expected_direction}
              </td>
              <td className="py-3 text-muted">{peer.rationale}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SortButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`font-medium uppercase tracking-wider transition hover:text-foreground ${active ? "text-accent" : ""}`}
    >
      {label}
    </button>
  );
}

function CorrelationBar({ score }: { score: number }) {
  const pct = Math.abs(score) * 100;
  const color =
    score >= 0.5 ? "bg-success" : score >= 0.3 ? "bg-warning" : "bg-muted";

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded-full bg-background">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-mono text-xs">{score.toFixed(2)}</span>
    </div>
  );
}
