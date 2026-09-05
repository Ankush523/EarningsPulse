export function SiteFooter() {
  return (
    <footer className="no-print mt-16">
      <div className="glass-nav mx-auto max-w-page rounded-t-glass px-6 py-8 sm:px-8 lg:px-10">
        <div className="flex flex-col gap-3 text-[0.9rem] text-ink-soft sm:flex-row sm:items-baseline sm:justify-between">
          <p role="note" className="max-w-measure">
            Not financial advice. EarningsPulse is decision support: it reads filings, news
            and price history so you can prepare, not so you can trade on autopilot.
          </p>
          <p className="shrink-0">Built for the AI x Finance Hackathon</p>
        </div>
      </div>
    </footer>
  );
}
