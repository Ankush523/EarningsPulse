import type { ConfidenceTier } from "@/lib/types";

const DOT: Record<ConfidenceTier, string> = {
  high: "bg-up",
  medium: "bg-caution",
  low: "bg-down",
};

const LABEL: Record<ConfidenceTier, string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
};

interface ConfidenceBadgeProps {
  tier: ConfidenceTier;
  className?: string;
}

export function ConfidenceBadge({ tier, className = "" }: ConfidenceBadgeProps) {
  return (
    <span
      className={`glass-chip inline-flex items-center gap-2 px-3 py-1 text-[0.85rem] text-ink-soft ${className}`}
    >
      <span className={`h-2 w-2 rounded-full ${DOT[tier]}`} aria-hidden />
      {LABEL[tier]}
    </span>
  );
}
