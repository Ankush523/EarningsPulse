"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppHeader } from "@/components/AppHeader";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { fetchEarningsCalendar, generatePlaybook } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { EarningsEvent } from "@/lib/types";

export default function CalendarPage() {
  const router = useRouter();
  const [events, setEvents] = useState<EarningsEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    fetchEarningsCalendar(14)
      .then((data) => {
        if (mounted) {
          setEvents(
            [...data.events].sort(
              (a, b) =>
                new Date(a.report_date).getTime() -
                new Date(b.report_date).getTime()
            )
          );
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

  const handleGenerate = async (ticker: string) => {
    setGenerating(ticker);
    try {
      const response = await generatePlaybook(ticker);
      router.push(`/playbook/${response.job_id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to start generation"
      );
      setGenerating(null);
    }
  };

  return (
    <div className="min-h-screen">
      <DisclaimerBanner />
      <AppHeader />

      <main className="mx-auto max-w-6xl px-6 py-12">
        <Link
          href="/"
          className="text-sm text-muted transition hover:text-accent"
        >
          ← Back to home
        </Link>

        <h1 className="mt-4 mb-2 text-3xl font-bold">Earnings Calendar</h1>
        <p className="mb-8 text-muted">Upcoming reports for the next 14 days</p>

        <div className="rounded-xl border border-card-border bg-card overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
            </div>
          ) : error ? (
            <p className="px-6 py-12 text-center text-sm text-danger">{error}</p>
          ) : events.length === 0 ? (
            <p className="px-6 py-12 text-center text-sm text-muted">
              No upcoming earnings found. Check that FINNHUB_API_KEY is configured
              or try again later.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="border-b border-card-border bg-background/50 text-xs uppercase tracking-wider text-muted">
                    <th className="px-6 py-3 font-medium">Ticker</th>
                    <th className="px-6 py-3 font-medium">Company</th>
                    <th className="px-6 py-3 font-medium">Report Date</th>
                    <th className="px-6 py-3 font-medium">Time</th>
                    <th className="px-6 py-3 font-medium">EPS Est.</th>
                    <th className="px-6 py-3 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <tr
                      key={`${event.ticker}-${event.report_date}`}
                      className="border-b border-card-border/50"
                    >
                      <td className="px-6 py-4 font-mono font-semibold">
                        {event.ticker}
                      </td>
                      <td className="px-6 py-4 text-muted">
                        {event.company_name ?? "—"}
                      </td>
                      <td className="px-6 py-4">{formatDate(event.report_date)}</td>
                      <td className="px-6 py-4 font-mono text-xs uppercase text-muted">
                        {event.report_time ?? "—"}
                      </td>
                      <td className="px-6 py-4 font-mono">
                        {event.eps_estimate?.toFixed(2) ?? "—"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          type="button"
                          disabled={generating === event.ticker}
                          onClick={() => handleGenerate(event.ticker)}
                          className="rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white transition hover:bg-accent-hover disabled:opacity-50"
                        >
                          {generating === event.ticker
                            ? "Starting…"
                            : "Generate"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
