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
    <section className="glass-panel mb-5 grid gap-x-12 gap-y-5 p-6 sm:p-8 xl:grid-cols-[13rem_minmax(0,1fr)] xl:p-10">
      <div className="xl:sticky xl:top-24 xl:self-start">
        <h2 className="text-[1.2rem] font-semibold leading-snug">{title}</h2>
        {confidence && (
          <p className="mt-2">
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
    <div className="glass-chip rounded-2xl px-4 py-3">
      <dt className="text-[0.85rem] text-ink-soft">{label}</dt>
      <dd className={`mt-1 font-mono text-[1.5rem] leading-none ${color}`}>{value}</dd>
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
  const border = { up: "border-up/40", ink: "border-white/50", down: "border-down/40" };
  const color = { up: "text-up", ink: "text-ink", down: "text-down" };
  const wash = { up: "bg-up-wash", ink: "bg-white/35", down: "bg-down-wash" };
  return (
    <div className={`rounded-2xl border-t-2 ${border[tone]} ${wash[tone]} p-4 backdrop-blur-sm`}>
      <h3 className={`text-[1.05rem] font-semibold ${color[tone]}`}>{title}</h3>
      <p className="mt-2 text-[0.98rem] leading-relaxed text-ink-soft">{text}</p>
    </div>
  );
}
