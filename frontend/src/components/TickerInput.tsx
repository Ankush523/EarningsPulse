"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { generatePlaybook } from "@/lib/api";

const POPULAR_TICKERS = [
  "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM",
];

interface TickerInputProps {
  suggestions?: string[];
}

export function TickerInput({ suggestions = POPULAR_TICKERS }: TickerInputProps) {
  const router = useRouter();
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const normalized = ticker.trim().toUpperCase();
    if (!normalized || loading) return;

    setLoading(true);
    setError(null);

    try {
      const response = await generatePlaybook(normalized);
      router.push(`/playbook/${response.job_id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to start playbook generation"
      );
      setLoading(false);
    }
  };

  const filteredSuggestions = suggestions.filter(
    (s) =>
      s.toUpperCase().includes(ticker.toUpperCase()) &&
      s.toUpperCase() !== ticker.toUpperCase()
  );

  return (
    <div className="mx-auto max-w-md">
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-3 sm:flex-row"
      >
        <div className="relative flex-1">
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="Enter ticker (e.g. AAPL)"
            maxLength={10}
            pattern="[A-Za-z.\-]+"
            list="ticker-suggestions"
            disabled={loading}
            className="w-full rounded-lg border border-card-border bg-card px-4 py-3 font-mono text-foreground placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-60"
            aria-label="Stock ticker symbol"
          />
          <datalist id="ticker-suggestions">
            {Array.from(new Set([...suggestions, ...POPULAR_TICKERS])).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </datalist>
        </div>
        <button
          type="submit"
          disabled={!ticker.trim() || loading}
          className="rounded-lg bg-accent px-6 py-3 font-medium text-white transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Starting…" : "Generate Playbook"}
        </button>
      </form>

      {error && (
        <p className="mt-3 text-center text-sm text-danger">{error}</p>
      )}

      {ticker && filteredSuggestions.length > 0 && (
        <div className="mt-2 flex flex-wrap justify-center gap-2">
          {filteredSuggestions.slice(0, 5).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setTicker(s)}
              className="rounded-md border border-card-border px-2 py-1 font-mono text-xs text-muted transition hover:border-accent hover:text-foreground"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <p className="mt-4 text-center text-xs text-muted">
        Or pick from{" "}
        {POPULAR_TICKERS.slice(0, 4).map((s, i) => (
          <span key={s}>
            {i > 0 && ", "}
            <button
              type="button"
              onClick={() => setTicker(s)}
              className="font-mono text-accent hover:underline"
            >
              {s}
            </button>
          </span>
        ))}
      </p>
    </div>
  );
}
