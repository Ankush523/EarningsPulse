import Link from "next/link";
import { BackendStatus } from "@/components/BackendStatus";
import { TickerInput } from "@/components/TickerInput";

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-card-border bg-card/50 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent font-mono text-sm font-bold text-white">
              EP
            </div>
            <span className="text-lg font-semibold tracking-tight">
              EarningsPulse
            </span>
          </div>
          <nav className="flex items-center gap-6 text-sm text-muted">
            <Link href="/calendar" className="transition hover:text-foreground">
              Calendar
            </Link>
            <BackendStatus />
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-16">
        <section className="mb-16 text-center">
          <p className="mb-4 font-mono text-sm uppercase tracking-widest text-accent">
            AI x Finance Hackathon
          </p>
          <h1 className="mb-6 text-balance text-4xl font-bold tracking-tight md:text-6xl">
            Know the report.
            <br />
            Read the reaction.
            <br />
            <span className="text-accent">Watch the ripple.</span>
          </h1>
          <p className="mx-auto mb-10 max-w-2xl text-lg text-muted">
            EarningsPulse is an AI agent that researches upcoming after-hours
            earnings, forecasts report sentiment, models price reaction scenarios,
            and maps peer spillover — before the market moves.
          </p>
          <TickerInput />
        </section>

        <section className="grid gap-6 md:grid-cols-3">
          {[
            {
              step: "01",
              title: "Research",
              description:
                "Agent gathers last quarter data, news, filings, and analyst context via live web research.",
            },
            {
              step: "02",
              title: "Forecast",
              description:
                "Beat/miss probabilities, key metrics, and historical reaction patterns including dip-then-rally.",
            },
            {
              step: "03",
              title: "Playbook",
              description:
                "Structured scenario tree with peer spillover map and actionable if/then guidance.",
            },
          ].map((item) => (
            <div
              key={item.step}
              className="rounded-xl border border-card-border bg-card p-6"
            >
              <p className="mb-3 font-mono text-sm text-accent">{item.step}</p>
              <h3 className="mb-2 text-lg font-semibold">{item.title}</h3>
              <p className="text-sm leading-relaxed text-muted">
                {item.description}
              </p>
            </div>
          ))}
        </section>

        <p className="mt-16 text-center text-xs text-muted">
          Not financial advice. For informational and decision-support purposes
          only.
        </p>
      </main>
    </div>
  );
}
