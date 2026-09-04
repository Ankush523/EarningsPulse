"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

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

  const handleSubmit = async (e: FormEvent) => {
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
        err instanceof Error ? err.message : "Could not start the playbook"
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
    <div className="max-w-xl">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
        <input
          type="text"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="Ticker"
          maxLength={10}
          pattern="[A-Za-z.\-]+"
          list="ticker-suggestions"
          disabled={loading}
          className="w-full flex-1 rounded border border-rule bg-panel px-4 py-3 font-mono text-lg uppercase text-ink placeholder:normal-case placeholder:text-ink-soft/70 disabled:opacity-60"
          aria-label="Stock ticker symbol"
          autoComplete="off"
        />
        <datalist id="ticker-suggestions">
          {Array.from(new Set([...suggestions, ...POPULAR_TICKERS])).map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </datalist>
        <button
          type="submit"
          disabled={!ticker.trim() || loading}
          className="rounded bg-ink px-6 py-3 text-[1.05rem] font-medium text-paper transition hover:bg-ink/90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "Starting" : "Generate playbook"}
        </button>
      </form>

      {error && <p className="mt-3 text-[0.95rem] text-down">{error}</p>}

      {ticker && filteredSuggestions.length > 0 ? (
        <p className="mt-4 text-[0.95rem] text-ink-soft">
          Did you mean{" "}
          {filteredSuggestions.slice(0, 5).map((s, i) => (
            <span key={s}>
              {i > 0 && ", "}
              <button
                type="button"
                onClick={() => setTicker(s)}
                className="font-mono text-ink underline decoration-rule underline-offset-4 hover:decoration-ink"
              >
                {s}
              </button>
            </span>
          ))}
        </p>
      ) : (
        <p className="mt-4 text-[0.95rem] text-ink-soft">
          Try{" "}
          {POPULAR_TICKERS.slice(0, 4).map((s, i) => (
            <span key={s}>
              {i > 0 && (i === 3 ? " or " : ", ")}
              <button
                type="button"
                onClick={() => setTicker(s)}
                className="font-mono text-ink underline decoration-rule underline-offset-4 hover:decoration-ink"
              >
                {s}
              </button>
            </span>
          ))}
          .
        </p>
      )}
    </div>
  );
}
