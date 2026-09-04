/** Display formatting helpers. */

export function formatPercent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatPctMove(value: number, digits = 1): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

/** YYYY-MM-DD is a calendar date; `new Date("YYYY-MM-DD")` is UTC midnight and shifts west of UTC. */
const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;

function parseDisplayDate(value: string): Date {
  const dateOnly = DATE_ONLY.exec(value);
  if (dateOnly) {
    return new Date(
      Number(dateOnly[1]),
      Number(dateOnly[2]) - 1,
      Number(dateOnly[3])
    );
  }
  return new Date(value);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = parseDisplayDate(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatArchetype(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

const ARCHETYPE_LABEL: Record<string, string> = {
  dip_then_rally: "Dip, then rally",
  immediate_rip: "Immediate rip",
  sell_the_news: "Sell the news",
  gap_and_hold: "Gap and hold",
  volatility_pin: "Volatility pin",
  insufficient_data: "Not enough history",
};

export function describeArchetype(value: string): string {
  return ARCHETYPE_LABEL[value] ?? formatArchetype(value);
}

const DIRECTION_LABEL: Record<string, string> = {
  same: "Same way",
  inverse: "Opposite way",
  opposite: "Opposite way",
  up: "Up",
  down: "Down",
  mixed: "Mixed",
  neutral: "Flat",
};

export function describeDirection(value: string): string {
  const key = value.trim().toLowerCase();
  return DIRECTION_LABEL[key] ?? value.charAt(0).toUpperCase() + value.slice(1);
}

export function formatLatency(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

const REPORT_TIME_LABEL: Record<string, string> = {
  amc: "After the close",
  bmo: "Before the open",
  dmh: "During market hours",
};

export function formatReportTime(value: string | null | undefined): string {
  if (!value) return "Time not set";
  return REPORT_TIME_LABEL[value.toLowerCase()] ?? value;
}

export function formatRelationship(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
