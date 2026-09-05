"use client";

import { useState } from "react";

import { describeDirection, formatRelationship } from "@/lib/format";
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
      <p className="text-ink-soft">
        No peers with a measurable report-day link were found.
      </p>
    );
  }

  const sortableHeader = (key: SortKey, label: string) => {
    const active = sortKey === key;
    return (
      <th
        className="pb-2.5 pr-4 font-normal"
        aria-sort={active ? (sortAsc ? "ascending" : "descending") : "none"}
      >
        <SortButton
          label={label}
          active={active}
          ascending={sortAsc}
          onClick={() => toggleSort(key)}
        />
      </th>
    );
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-[0.95rem]">
        <thead>
          <tr className="border-b border-white/50 text-ink-soft">
            {sortableHeader("ticker", "Ticker")}
            <th className="pb-2.5 pr-4 font-normal">Company</th>
            {sortableHeader("relationship", "Relationship")}
            {sortableHeader("correlation_score", "Correlation")}
            <th className="pb-2.5 pr-4 font-normal">Direction</th>
            <th className="pb-2.5 font-normal">Why</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((peer) => (
            <tr key={peer.ticker} className="border-b border-white/35 align-top transition hover:bg-white/20">
              <td className="py-3 pr-4">
                <span className="font-mono font-medium">{peer.ticker}</span>
                {peer.watch_flag && (
                  <span className="glass-chip ml-2 px-2 py-0.5 text-[0.75rem] font-medium text-caution">
                    Watch
                  </span>
                )}
              </td>
              <td className="py-3 pr-4 text-ink-soft">{peer.company_name ?? "—"}</td>
              <td className="py-3 pr-4 text-ink-soft">
                {formatRelationship(peer.relationship)}
              </td>
              <td className="py-3 pr-4">
                <CorrelationBar score={peer.correlation_score} />
              </td>
              <td className="py-3 pr-4 text-ink-soft">
                {describeDirection(peer.expected_direction)}
              </td>
              <td className="py-3 text-ink-soft">{peer.rationale}</td>
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
  ascending,
  onClick,
}: {
  label: string;
  active: boolean;
  ascending: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex cursor-pointer items-center gap-1 transition hover:text-ink ${
        active ? "text-ink" : ""
      }`}
    >
      {label}
      <span aria-hidden className="text-[0.7rem]">
        {active ? (ascending ? "▲" : "▼") : ""}
      </span>
    </button>
  );
}

function CorrelationBar({ score }: { score: number }) {
  const pct = Math.min(Math.abs(score), 1) * 100;
  return (
    <span className="flex items-center gap-3">
      <span className="h-1.5 w-24 overflow-hidden rounded-full bg-white/45">
        <span className="block h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
      </span>
      <span className="font-mono text-[0.9rem]">{score.toFixed(2)}</span>
    </span>
  );
}
