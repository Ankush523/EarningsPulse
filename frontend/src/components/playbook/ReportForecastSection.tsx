import { ForecastCase, PlaybookSection } from "@/components/playbook/PlaybookSection";
import type { ConfidenceTier, Playbook } from "@/lib/types";

const IMPORTANCE_LABEL: Record<ConfidenceTier, string> = {
  high: "Decisive",
  medium: "Matters",
  low: "Minor",
};

type ReportForecast = Playbook["report_forecast"];

export function ReportForecastSection({ forecast }: { forecast: ReportForecast }) {
  return (
    <PlaybookSection title="Report forecast" confidence={forecast.confidence}>
      {forecast.key_metrics.length > 0 && (
        <dl className="grid gap-x-10 gap-y-5 lg:grid-cols-2 xl:grid-cols-3">
          {forecast.key_metrics.map((metric) => (
            <div key={metric.name}>
              <dt className="flex flex-wrap items-baseline gap-x-3">
                <span className="text-[1.1rem] font-medium">{metric.name}</span>
                <span className="text-[0.85rem] italic text-ink-soft">
                  {IMPORTANCE_LABEL[metric.importance]}
                </span>
              </dt>
              <dd className="mt-1 text-ink-soft">{metric.description}</dd>
            </div>
          ))}
        </dl>
      )}

      <div className="mt-10 grid gap-6 lg:grid-cols-3 lg:gap-8">
        <ForecastCase title="Bull case" tone="up" text={forecast.bull_case} />
        <ForecastCase title="Base case" tone="ink" text={forecast.base_case} />
        <ForecastCase title="Bear case" tone="down" text={forecast.bear_case} />
      </div>

      <SurpriseLists forecast={forecast} />
    </PlaybookSection>
  );
}

function SurpriseLists({ forecast }: { forecast: ReportForecast }) {
  const hasSurprises =
    forecast.positive_surprises.length > 0 || forecast.negative_surprises.length > 0;

  if (!hasSurprises) {
    return null;
  }

  return (
    <div className="mt-10 grid gap-8 sm:grid-cols-2">
      {forecast.positive_surprises.length > 0 && (
        <div>
          <h3 className="text-[1.1rem] font-medium text-up">Could surprise to the upside</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-soft marker:text-up">
            {forecast.positive_surprises.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {forecast.negative_surprises.length > 0 && (
        <div>
          <h3 className="text-[1.1rem] font-medium text-down">
            Could surprise to the downside
          </h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-soft marker:text-down">
            {forecast.negative_surprises.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
