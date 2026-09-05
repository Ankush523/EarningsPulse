import { AppHeader } from "@/components/AppHeader";
import { DemoButton } from "@/components/DemoButton";
import { EarningsCalendarPreview } from "@/components/EarningsCalendarPreview";
import { ReactionPathHero } from "@/components/ReactionPathHero";
import { SiteFooter } from "@/components/SiteFooter";
import { TickerInput } from "@/components/TickerInput";

const PLAYBOOK_PARTS = [
  {
    title: "Report forecast",
    body: "Beat, inline and miss odds, the two or three metrics that will decide the print, and a bull, base and bear case in plain language.",
  },
  {
    title: "Price reaction scenarios",
    body: "The pattern this stock tends to follow after it reports, with historical reactions charted and the options-implied move set against what actually happened.",
  },
  {
    title: "Peer spillover map",
    body: "Suppliers, customers and direct peers ranked by how tightly they have moved with this name on report day, so you know who else is on the tape.",
  },
  {
    title: "If / then actions",
    body: "Short conditional rules for the first hour after the print, each tied to the historical pattern that supports it.",
  },
  {
    title: "Sources and trace",
    body: "Every filing, article and data call the agents used, plus a full run log you can export alongside the playbook.",
  },
];

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />

      <main className="mx-auto w-full max-w-page flex-1 px-5 pb-10 pt-10 sm:px-6 lg:px-8 lg:pt-14">
        <section className="glass-panel-strong grid gap-y-10 p-6 sm:p-8 lg:grid-cols-[minmax(0,26rem)_1fr] lg:grid-rows-[auto_auto] lg:items-center lg:gap-x-12 lg:p-10">
          <h1 className="text-balance text-[2.5rem] font-semibold leading-[1.05] tracking-tight lg:self-end lg:text-[3.25rem]">
            Know the report.
            <br />
            Read the reaction.
            <br />
            Watch the ripple.
          </h1>
          <div className="lg:col-start-2 lg:row-span-2 lg:row-start-1">
            <ReactionPathHero />
          </div>
          <div className="lg:self-start">
            <p className="max-w-measure text-[1.05rem] leading-relaxed text-ink-soft">
              Type a ticker. Five agents read the filings, the news and the recent prints,
              then write the playbook: beat odds, the price path this stock usually takes,
              who moves with it, and what to do in the first hour.
            </p>
            <div className="mt-8">
              <TickerInput />
              <DemoButton />
            </div>
          </div>
        </section>

        <section className="glass-panel mt-10 p-6 sm:p-8 lg:p-10">
          <h2 className="border-b border-rule pb-4 text-[1.65rem] font-semibold leading-tight tracking-tight">
            What a playbook contains
          </h2>
          <dl className="mt-2 grid gap-x-10 sm:grid-cols-2">
            {PLAYBOOK_PARTS.map((part) => (
              <div key={part.title} className="border-b border-rule-soft py-6">
                <dt className="text-[1.15rem] font-semibold leading-snug">{part.title}</dt>
                <dd className="mt-2 max-w-measure text-[0.98rem] leading-relaxed text-ink-soft">
                  {part.body}
                </dd>
              </div>
            ))}
          </dl>
        </section>

        <EarningsCalendarPreview />
      </main>

      <SiteFooter />
    </div>
  );
}
