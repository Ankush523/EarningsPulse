export function SiteFooter() {
  return (
    <footer className="no-print mt-24 border-t border-rule">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-8 text-[0.9rem] text-ink-soft sm:flex-row sm:items-baseline sm:justify-between">
        <p role="note" className="max-w-measure">
          Not financial advice. EarningsPulse is decision support: it reads
          filings, news and price history so you can prepare, not so you can
          trade on autopilot.
        </p>
        <p className="shrink-0">Built for the AI x Finance Hackathon</p>
      </div>
    </footer>
  );
}
