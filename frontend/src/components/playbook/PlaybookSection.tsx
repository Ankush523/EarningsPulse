import type { ReactNode } from "react";

import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import type { ConfidenceTier } from "@/lib/types";

export function PlaybookSection({
  title,
  confidence,
  children,
}: {
  title: string;
  confidence?: ConfidenceTier;
  children: ReactNode;
}) {
  return (
    <section className="grid gap-x-10 gap-y-4 border-t border-rule py-10 lg:grid-cols-[11rem_1fr]">
      <div className="lg:sticky lg:top-6 lg:self-start">
        <h2 className="text-[1.25rem] font-medium leading-snug">{title}</h2>
        {confidence && (
          <p className="mt-1.5">
            <ConfidenceBadge tier={confidence} />
          </p>
        )}
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

export function Figure({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "up" | "down";
}) {
  const color = tone === "up" ? "text-up" : tone === "down" ? "text-down" : "";
  return (
    <div>
      <dt className="text-[0.9rem] text-ink-soft">{label}</dt>
      <dd className={`mt-0.5 font-mono text-[1.6rem] leading-none ${color}`}>{value}</dd>
    </div>
  );
}

export function ForecastCase({
  title,
  tone,
  text,
}: {
  title: string;
  tone: "up" | "ink" | "down";
  text: string;
}) {
  const border = { up: "border-up", ink: "border-ink", down: "border-down" };
  const color = { up: "text-up", ink: "", down: "text-down" };
  return (
    <div className={`border-t-2 pt-3 ${border[tone]}`}>
      <h3 className={`text-[1.1rem] font-medium ${color[tone]}`}>{title}</h3>
      <p className="mt-1.5 text-ink-soft">{text}</p>
    </div>
  );
}
