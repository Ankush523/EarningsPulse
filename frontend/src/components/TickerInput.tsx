"use client";

import { useState } from "react";

export function TickerInput() {
  const [ticker, setTicker] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const normalized = ticker.trim().toUpperCase();
    if (!normalized) return;
    // Playbook generation will be wired in Phase 4
    alert(
      `Playbook generation for ${normalized} coming in Phase 4. Foundation is ready.`
    );
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto flex max-w-md flex-col gap-3 sm:flex-row"
    >
      <input
        type="text"
        value={ticker}
        onChange={(e) => setTicker(e.target.value.toUpperCase())}
        placeholder="Enter ticker (e.g. AAPL)"
        maxLength={10}
        pattern="[A-Za-z.\-]+"
        className="flex-1 rounded-lg border border-card-border bg-card px-4 py-3 font-mono text-foreground placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        aria-label="Stock ticker symbol"
      />
      <button
        type="submit"
        disabled={!ticker.trim()}
        className="rounded-lg bg-accent px-6 py-3 font-medium text-white transition hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        Generate Playbook
      </button>
    </form>
  );
}
