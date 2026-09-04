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
    <section className="mt-24">
      <div className="mb-6 flex flex-wrap items-baseline justify-between gap-4 border-b border-ink pb-3">
        <h2 className="text-[1.75rem] font-medium leading-tight tracking-tight">
          Reporting in the next seven days
        </h2>
        <Link
          href="/calendar"
          className="text-[0.95rem] text-ink-soft underline decoration-rule underline-offset-4 transition hover:text-ink hover:decoration-ink"
        >
          Full calendar
        </Link>
      </div>

      {loading ? (
        <ul className="divide-y divide-rule-soft" aria-label="Loading calendar">
          {[0, 1, 2].map((i) => (
            <li key={i} className="flex gap-6 py-4">
              <span className="h-4 w-24 rounded-sm bg-rule-soft" />
              <span className="h-4 w-16 rounded-sm bg-rule-soft" />
              <span className="h-4 w-40 rounded-sm bg-rule-soft" />
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
        <ul className="divide-y divide-rule-soft">
          {events.map((event) => (
            <li
              key={`${event.ticker}-${event.report_date}`}
              className="grid grid-cols-[7.5rem_5rem_1fr] items-baseline gap-4 py-3.5 sm:grid-cols-[8rem_6rem_1fr_8rem]"
            >
              <span className="font-mono text-[0.9rem] text-ink-soft">
                {formatDate(event.report_date)}
              </span>
              <Link
                href={`/calendar#${event.ticker}`}
                className="font-mono font-medium underline decoration-rule underline-offset-4 hover:decoration-ink"
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
