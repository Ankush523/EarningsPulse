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

      <main className="mx-auto w-full max-w-5xl flex-1 px-6 pb-8 pt-8">
        <Link
          href="/"
          className="text-[0.95rem] text-ink-soft underline decoration-rule underline-offset-4 transition hover:text-ink hover:decoration-ink"
        >
          Back to home
        </Link>

        <header className="mt-6 border-b border-ink pb-6">
          <h1 className="text-[2.25rem] font-medium leading-[1.1] tracking-tight sm:text-[2.75rem]">
            Earnings calendar
          </h1>
          <p className="mt-3 max-w-measure text-ink-soft">
            Companies reporting in the next {DAYS} days. Pick one to start a
            playbook.
          </p>
        </header>

        {loading ? (
          <ul className="divide-y divide-rule-soft" aria-label="Loading calendar">
            {[0, 1, 2, 3, 4].map((i) => (
              <li key={i} className="flex gap-6 py-4">
                <span className="h-4 w-24 rounded-sm bg-rule-soft" />
                <span className="h-4 w-16 rounded-sm bg-rule-soft" />
                <span className="h-4 w-48 rounded-sm bg-rule-soft" />
              </li>
            ))}
          </ul>
        ) : error ? (
          <p className="max-w-measure py-6 text-down">{error}</p>
        ) : events.length === 0 ? (
          <div className="max-w-measure py-6">
            <p className="text-ink-soft">
              No reports found for the next {DAYS} days. The calendar reads from
              Finnhub, so the API needs a <span className="font-mono text-[0.95rem]">FINNHUB_API_KEY</span> to
              fill it in.
            </p>
            <p className="mt-3 text-ink-soft">
              You can still{" "}
              <Link
                href="/"
                className="text-ink underline decoration-rule underline-offset-4 hover:decoration-ink"
              >
                generate a playbook for any ticker
              </Link>
              .
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left">
              <thead>
                <tr className="border-b border-rule text-[0.95rem] text-ink-soft">
                  <th className="py-3 pr-4 font-normal">Report date</th>
                  <th className="py-3 pr-4 font-normal">Ticker</th>
                  <th className="py-3 pr-4 font-normal">Company</th>
                  <th className="py-3 pr-4 font-normal">When</th>
                  <th className="py-3 pr-4 text-right font-normal">EPS estimate</th>
                  <th className="py-3 text-right font-normal">
                    <span className="sr-only">Generate playbook</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr
                    key={`${event.ticker}-${event.report_date}`}
                    id={event.ticker}
                    className="border-b border-rule-soft"
                  >
                    <td className="py-3.5 pr-4 font-mono text-[0.95rem] text-ink-soft">
                      {formatDate(event.report_date)}
                    </td>
                    <td className="py-3.5 pr-4 font-mono font-medium">{event.ticker}</td>
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
                        className="rounded border border-ink px-3 py-1 text-[0.9rem] font-medium transition hover:bg-ink hover:text-paper disabled:opacity-50"
                      >
                        {generating === event.ticker ? "Starting" : "Generate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      <SiteFooter />
    </div>
  );
}
