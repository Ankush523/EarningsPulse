"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchEarningsCalendar } from "@/lib/api";
import { formatDate, formatReportTime } from "@/lib/format";
import type { EarningsEvent } from "@/lib/types";

export function EarningsCalendarPreview() {
  const [events, setEvents] = useState<EarningsEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    fetchEarningsCalendar(7)
      .then((data) => {
        if (mounted) {
          setEvents(data.events.slice(0, 6));
          setError(null);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(
            err instanceof Error ? err.message : "Could not load the calendar"
          );
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <section className="glass-panel mt-10 p-6 sm:p-8 lg:p-10">
      <div className="mb-6 flex flex-wrap items-baseline justify-between gap-4 border-b border-white/50 pb-4">
        <h2 className="text-[1.65rem] font-semibold leading-tight tracking-tight">
          Reporting in the next seven days
        </h2>
        <Link href="/calendar" className="link-glass text-[0.95rem] font-medium">
          Full calendar
        </Link>
      </div>

      {loading ? (
        <ul className="divide-y divide-white/40" aria-label="Loading calendar">
          {[0, 1, 2].map((i) => (
            <li key={i} className="flex gap-6 py-4">
              <span className="glass-skeleton h-4 w-24" />
              <span className="glass-skeleton h-4 w-16" />
              <span className="glass-skeleton h-4 w-40" />
            </li>
          ))}
        </ul>
      ) : error ? (
        <p className="max-w-measure py-4 text-ink-soft">
          The calendar did not load ({error}). The API may be offline; you can
          still generate a playbook for any ticker above.
        </p>
      ) : events.length === 0 ? (
        <p className="max-w-measure py-4 text-ink-soft">
          No reports found for the next seven days. The calendar reads from
          Finnhub, so the API needs a key to fill it in. You can still generate
          a playbook for any ticker above.
        </p>
      ) : (
        <ul className="divide-y divide-white/40">
          {events.map((event) => (
            <li
              key={`${event.ticker}-${event.report_date}`}
              className="grid grid-cols-[7.5rem_5rem_1fr] items-baseline gap-4 py-3.5 transition hover:bg-white/25 sm:grid-cols-[8rem_6rem_1fr_8rem] sm:rounded-xl sm:px-2"
            >
              <span className="font-mono text-[0.9rem] text-ink-soft">
                {formatDate(event.report_date)}
              </span>
              <Link
                href={`/calendar#${event.ticker}`}
                className="font-mono font-semibold text-accent underline decoration-accent/30 underline-offset-4 hover:decoration-accent"
              >
                {event.ticker}
              </Link>
              <span className="truncate text-ink-soft">
                {event.company_name ?? ""}
              </span>
              <span className="hidden text-right text-[0.95rem] text-ink-soft sm:block">
                {formatReportTime(event.report_time)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
