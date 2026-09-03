"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchEarningsCalendar } from "@/lib/api";
import { formatDate } from "@/lib/format";
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
            err instanceof Error ? err.message : "Failed to load calendar"
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
    <section className="mt-20">
      <div className="mb-6 flex items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">Upcoming Earnings</h2>
          <p className="mt-1 text-sm text-muted">Next 7 days</p>
        </div>
        <Link
          href="/calendar"
          className="text-sm text-accent transition hover:underline"
        >
          View full calendar →
        </Link>
      </div>

      <div className="rounded-xl border border-card-border bg-card">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
          </div>
        ) : error ? (
          <p className="px-6 py-8 text-center text-sm text-muted">{error}</p>
        ) : events.length === 0 ? (
          <p className="px-6 py-8 text-center text-sm text-muted">
            No earnings events found for the next 7 days.
          </p>
        ) : (
          <ul className="divide-y divide-card-border">
            {events.map((event) => (
              <li
                key={`${event.ticker}-${event.report_date}`}
                className="flex items-center justify-between gap-4 px-6 py-4"
              >
                <div>
                  <p className="font-mono font-semibold">{event.ticker}</p>
                  {event.company_name && (
                    <p className="text-sm text-muted">{event.company_name}</p>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-sm">{formatDate(event.report_date)}</p>
                  {event.report_time && (
                    <p className="font-mono text-xs uppercase text-muted">
                      {event.report_time}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
