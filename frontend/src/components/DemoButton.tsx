"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { generatePlaybook, loadDemoPlaybook } from "@/lib/api";

const DEMO_TICKERS = ["AAPL"];

export function DemoButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDemo = async (ticker: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await loadDemoPlaybook(ticker);
      router.push(`/playbook/${response.job_id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Demo unavailable"
      );
      setLoading(false);
    }
  };

  return (
    <div className="mt-6 text-center">
      <p className="mb-3 text-xs uppercase tracking-wider text-muted">
        Or try instant demo
      </p>
      <div className="flex flex-wrap justify-center gap-2">
        {DEMO_TICKERS.map((ticker) => (
          <button
            key={ticker}
            type="button"
            disabled={loading}
            onClick={() => handleDemo(ticker)}
            className="rounded-lg border border-card-border bg-card px-4 py-2 font-mono text-sm transition hover:border-accent hover:text-accent disabled:opacity-50"
          >
            {loading ? "Loading…" : `Demo ${ticker}`}
          </button>
        ))}
      </div>
      {error && (
        <p className="mt-3 text-xs text-danger">{error}</p>
      )}
    </div>
  );
}

export function RegenerateButton({ ticker }: { ticker: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleRegenerate = async () => {
    setLoading(true);
    try {
      const response = await generatePlaybook(ticker);
      router.push(`/playbook/${response.job_id}`);
    } catch {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      disabled={loading}
      onClick={handleRegenerate}
      className="rounded-lg border border-card-border bg-background px-4 py-2 text-sm transition hover:border-accent disabled:opacity-50"
    >
      {loading ? "Starting…" : `Regenerate ${ticker}`}
    </button>
  );
}
