import type { ConfidenceTier } from "@/lib/types";

const STYLES: Record<ConfidenceTier, string> = {
  high: "border-success/40 bg-success/10 text-success",
  medium: "border-warning/40 bg-warning/10 text-warning",
  low: "border-danger/40 bg-danger/10 text-danger",
};

interface ConfidenceBadgeProps {
  tier: ConfidenceTier;
  className?: string;
}

export function ConfidenceBadge({ tier, className = "" }: ConfidenceBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${STYLES[tier]} ${className}`}
    >
      {tier} confidence
    </span>
  );
}
