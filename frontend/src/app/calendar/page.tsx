"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AppHeader } from "@/components/AppHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { fetchEarningsCalendar, generatePlaybook } from "@/lib/api";
import { formatDate, formatReportTime } from "@/lib/format";
import type { EarningsEvent } from "@/lib/types";

const DAYS = 14;

export default function CalendarPage() {
  const router = useRouter();
  const [events, setEvents] = useState<EarningsEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    fetchEarningsCalendar(DAYS)
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

  const handleGenerate = async (ticker: string) => {
    setGenerating(ticker);
    try {
      const response = await generatePlaybook(ticker);
      router.push(`/playbook/${response.job_id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not start the playbook"
      );
      setGenerating(null);
    }
  };

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />

      <main className="mx-auto w-full max-w-page flex-1 px-5 pb-10 pt-8 sm:px-6 lg:px-8">
        <Link href="/" className="link-glass text-[0.95rem] font-medium">
          Back to home
        </Link>

        <header className="glass-panel-strong mt-6 p-6 sm:p-8">
          <h1 className="text-[2.25rem] font-semibold leading-[1.1] tracking-tight sm:text-[2.75rem]">
            Earnings calendar
          </h1>
          <p className="mt-3 max-w-measure text-ink-soft">
            Companies reporting in the next {DAYS} days. Pick one to start a
            playbook.
          </p>
        </header>

        <div className="glass-panel mt-6 p-4 sm:p-6">
          {loading ? (
            <ul className="divide-y divide-white/40" aria-label="Loading calendar">
              {[0, 1, 2, 3, 4].map((i) => (
                <li key={i} className="flex gap-6 py-4">
                  <span className="glass-skeleton h-4 w-24" />
                  <span className="glass-skeleton h-4 w-16" />
                  <span className="glass-skeleton h-4 w-48" />
                </li>
              ))}
            </ul>
          ) : error ? (
            <p className="max-w-measure py-6 text-down">{error}</p>
          ) : events.length === 0 ? (
            <div className="max-w-measure py-6">
              <p className="text-ink-soft">
                No reports found for the next {DAYS} days. The calendar reads from
                Finnhub, so the API needs a{" "}
                <span className="font-mono text-[0.95rem]">FINNHUB_API_KEY</span> to
                fill it in.
              </p>
              <p className="mt-3 text-ink-soft">
                You can still{" "}
                <Link href="/" className="link-glass font-medium text-ink">
                  generate a playbook for any ticker
                </Link>
                .
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left">
                <thead>
                  <tr className="border-b border-white/50 text-[0.95rem] text-ink-soft">
                    <th className="py-3 pr-4 font-medium">Report date</th>
                    <th className="py-3 pr-4 font-medium">Ticker</th>
                    <th className="py-3 pr-4 font-medium">Company</th>
                    <th className="py-3 pr-4 font-medium">When</th>
                    <th className="py-3 pr-4 text-right font-medium">EPS estimate</th>
                    <th className="py-3 text-right font-medium">
                      <span className="sr-only">Generate playbook</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <tr
                      key={`${event.ticker}-${event.report_date}`}
                      id={event.ticker}
                      className="border-b border-white/35 transition hover:bg-white/20"
                    >
                      <td className="py-3.5 pr-4 font-mono text-[0.95rem] text-ink-soft">
                        {formatDate(event.report_date)}
                      </td>
                      <td className="py-3.5 pr-4 font-mono font-semibold">{event.ticker}</td>
                      <td className="py-3.5 pr-4 text-ink-soft">
                        {event.company_name ?? "—"}
                      </td>
                      <td className="py-3.5 pr-4 text-ink-soft">
                        {formatReportTime(event.report_time)}
                      </td>
                      <td className="py-3.5 pr-4 text-right font-mono">
                        {event.eps_estimate?.toFixed(2) ?? "—"}
                      </td>
                      <td className="py-3.5 text-right">
                        <button
                          type="button"
                          disabled={generating === event.ticker}
                          onClick={() => handleGenerate(event.ticker)}
                          className="btn-primary cursor-pointer rounded-lg px-3.5 py-1.5 text-[0.9rem] font-semibold disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {generating === event.ticker ? "Starting…" : "Generate"}
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

      <SiteFooter />
    </div>
  );
}
