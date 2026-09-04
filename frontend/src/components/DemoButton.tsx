"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { generatePlaybook, loadDemoPlaybook } from "@/lib/api";

const DEMO_TICKER = "AAPL";

export function DemoButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await loadDemoPlaybook(DEMO_TICKER);
      router.push(`/playbook/${response.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The demo is unavailable");
      setLoading(false);
    }
  };

  return (
    <p className="mt-2 text-[0.95rem] text-ink-soft">
      No API keys yet?{" "}
      <button
        type="button"
        disabled={loading}
        onClick={handleDemo}
        className="text-ink underline decoration-rule underline-offset-4 hover:decoration-ink disabled:opacity-50"
      >
        {loading ? "Opening the demo" : `Demo ${DEMO_TICKER}`}
      </button>{" "}
      opens a cached playbook instantly.
      {error && <span className="ml-2 text-down">{error}</span>}
    </p>
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
      className="rounded border border-ink px-4 py-2 text-[0.95rem] font-medium text-ink transition hover:bg-ink hover:text-paper disabled:opacity-50"
    >
      {loading ? "Starting" : `Generate ${ticker} again`}
    </button>
  );
}
