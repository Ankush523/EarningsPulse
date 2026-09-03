import Link from "next/link";

export default function CalendarPage() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-card-border bg-card/50 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent font-mono text-sm font-bold text-white">
              EP
            </div>
            <span className="text-lg font-semibold">EarningsPulse</span>
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-16">
        <h1 className="mb-4 text-3xl font-bold">Earnings Calendar</h1>
        <p className="text-muted">
          Upcoming earnings calendar will be available in Phase 4.
        </p>
        <Link
          href="/"
          className="mt-8 inline-block text-accent hover:underline"
        >
          ← Back to home
        </Link>
      </main>
    </div>
  );
}
