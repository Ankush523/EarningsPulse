import type { Theme } from "@/lib/theme";

export interface ReactionChartTheme {
  background: string;
  panel: string;
  text: string;
  textSoft: string;
  grid: string;
  border: string;
  crosshair: string;
  crosshairLabel: string;
  up: string;
  down: string;
  upBorder: string;
  downBorder: string;
  volumeUp: string;
  volumeDown: string;
  accent: string;
  median: string;
  ghost: string;
  pivot: string;
  support: string;
  resistance: string;
  entry: string;
  tp: string;
  sl: string;
}

const LIGHT_CHART: ReactionChartTheme = {
  background: "#ffffff",
  panel: "#f4f6fb",
  text: "rgba(29, 29, 31, 0.78)",
  textSoft: "rgba(29, 29, 31, 0.52)",
  grid: "rgba(29, 29, 31, 0.08)",
  border: "rgba(29, 29, 31, 0.12)",
  crosshair: "rgba(29, 29, 31, 0.22)",
  crosshairLabel: "#1d1d1f",
  up: "#089981",
  down: "#f23645",
  upBorder: "#089981",
  downBorder: "#f23645",
  volumeUp: "rgba(8, 153, 129, 0.42)",
  volumeDown: "rgba(242, 54, 69, 0.38)",
  accent: "#0071e3",
  median: "#b25e00",
  ghost: "rgba(29, 29, 31, 0.2)",
  pivot: "#7c4dff",
  support: "#089981",
  resistance: "#f23645",
  entry: "#1d1d1f",
  tp: "#248a3d",
  sl: "#d70015",
};

const DARK_CHART: ReactionChartTheme = {
  background: "#131722",
  panel: "#1a2230",
  text: "rgba(255, 255, 255, 0.78)",
  textSoft: "rgba(255, 255, 255, 0.52)",
  grid: "rgba(42, 46, 57, 0.65)",
  border: "rgba(42, 46, 57, 0.9)",
  crosshair: "rgba(255, 255, 255, 0.22)",
  crosshairLabel: "#2a2e39",
  up: "#26a69a",
  down: "#ef5350",
  upBorder: "#26a69a",
  downBorder: "#ef5350",
  volumeUp: "rgba(38, 166, 154, 0.45)",
  volumeDown: "rgba(239, 83, 80, 0.45)",
  accent: "#2962ff",
  median: "#f5c451",
  ghost: "rgba(255, 255, 255, 0.22)",
  pivot: "#b388ff",
  support: "#26a69a",
  resistance: "#ef5350",
  entry: "#ffffff",
  tp: "#26a69a",
  sl: "#ef5350",
};

export function getReactionChartTheme(theme: Theme): ReactionChartTheme {
  return theme === "dark" ? DARK_CHART : LIGHT_CHART;
}

export function getReferenceLineColors(theme: Theme): Record<string, string> {
  const palette = getReactionChartTheme(theme);
  return {
    pivot: palette.pivot,
    support: palette.support,
    resistance: palette.resistance,
    entry: palette.entry,
    tp: palette.tp,
    sl: palette.sl,
  };
}

export const REFERENCE_LINE_WIDTH: Record<string, 1 | 2 | 3 | 4> = {
  pivot: 1,
  support: 1,
  resistance: 1,
  entry: 2,
  tp: 2,
  sl: 2,
};

export function describeArchetypeShort(archetype: string): string {
  return archetype.replaceAll("_", " ");
}

export function addDaysIso(isoDate: string, offsetDays: number): string {
  const date = new Date(`${isoDate}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

export function formatPrice(value: number): string {
  return value >= 1000 ? value.toFixed(0) : value.toFixed(2);
}
