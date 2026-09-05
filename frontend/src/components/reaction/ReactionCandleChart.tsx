"use client";

import {
  CandlestickSeries,
  ColorType,
  createChart,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import { useTheme } from "@/components/ThemeProvider";
import {
  addDaysIso,
  getReactionChartTheme,
  getReferenceLineColors,
  REFERENCE_LINE_WIDTH,
  type ReactionChartTheme,
} from "@/lib/reactionChartTheme";
import { readStoredTheme } from "@/lib/theme";
import type {
  ReactionChartBar,
  ReactionEventPath,
  ReactionPathPoint,
  ReactionReferenceLine,
} from "@/lib/types";

interface ReactionCandleChartProps {
  candles: ReactionChartBar[];
  focusEarningsDate: string;
  focusBaseline: number;
  referenceLines: ReactionReferenceLine[];
  medianPath: ReactionPathPoint[];
  paths: ReactionEventPath[];
  selectedPathDate: string | null;
  showMedian: boolean;
  showGhostPaths: boolean;
}

function rebasedLinePoints(
  points: ReactionPathPoint[],
  focusEarningsDate: string,
  focusBaseline: number
): { time: Time; value: number }[] {
  return points.map((point) => ({
    time: addDaysIso(focusEarningsDate, point.offset_days) as Time,
    value: focusBaseline * (1 + point.pct_from_baseline / 100),
  }));
}

function lineStyleForKind(kind: string): LineStyle {
  if (kind === "entry") return LineStyle.Solid;
  if (kind === "pivot") return LineStyle.Dotted;
  return LineStyle.Dashed;
}

function applyChartTheme(chart: IChartApi, palette: ReactionChartTheme): void {
  chart.applyOptions({
    layout: {
      background: { type: ColorType.Solid, color: palette.background },
      textColor: palette.text,
    },
    grid: {
      vertLines: { color: palette.grid },
      horzLines: { color: palette.grid },
    },
    rightPriceScale: {
      borderColor: palette.border,
    },
    timeScale: {
      borderColor: palette.border,
    },
    crosshair: {
      vertLine: {
        color: palette.crosshair,
        labelBackgroundColor: palette.crosshairLabel,
      },
      horzLine: {
        color: palette.crosshair,
        labelBackgroundColor: palette.crosshairLabel,
      },
    },
  });
}

export function ReactionCandleChart({
  candles,
  focusEarningsDate,
  focusBaseline,
  referenceLines,
  medianPath,
  paths,
  selectedPathDate,
  showMedian,
  showGhostPaths,
}: ReactionCandleChartProps) {
  const { theme } = useTheme();
  const palette = getReactionChartTheme(theme);
  const lineColors = getReferenceLineColors(theme);

  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const overlaySeriesRef = useRef<ISeriesApi<"Line">[]>([]);
  const priceLineRefs = useRef<ReturnType<ISeriesApi<"Candlestick">["createPriceLine"]>[]>([]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const initialPalette = getReactionChartTheme(readStoredTheme());

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: initialPalette.background },
        textColor: initialPalette.text,
        fontFamily: "var(--font-plex-mono), ui-monospace, monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: initialPalette.grid },
        horzLines: { color: initialPalette.grid },
      },
      rightPriceScale: {
        borderColor: initialPalette.border,
        scaleMargins: { top: 0.08, bottom: 0.22 },
      },
      timeScale: {
        borderColor: initialPalette.border,
        fixLeftEdge: false,
        fixRightEdge: false,
        barSpacing: 9,
        minBarSpacing: 4,
        rightOffset: 4,
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: initialPalette.crosshair,
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: initialPalette.crosshairLabel,
        },
        horzLine: {
          color: initialPalette.crosshair,
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: initialPalette.crosshairLabel,
        },
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: initialPalette.up,
      downColor: initialPalette.down,
      borderUpColor: initialPalette.upBorder,
      borderDownColor: initialPalette.downBorder,
      wickUpColor: initialPalette.up,
      wickDownColor: initialPalette.down,
      borderVisible: true,
      wickVisible: true,
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
      borderVisible: false,
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    return () => {
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      overlaySeriesRef.current = [];
      priceLineRefs.current = [];
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    const candleSeries = candleSeriesRef.current;
    if (!chart || !candleSeries) return;

    applyChartTheme(chart, palette);
    candleSeries.applyOptions({
      upColor: palette.up,
      downColor: palette.down,
      borderUpColor: palette.upBorder,
      borderDownColor: palette.downBorder,
      wickUpColor: palette.up,
      wickDownColor: palette.down,
    });
  }, [palette]);

  useEffect(() => {
    const chart = chartRef.current;
    const candleSeries = candleSeriesRef.current;
    const volumeSeries = volumeSeriesRef.current;
    if (!chart || !candleSeries || !volumeSeries) return;

    candleSeries.setData(
      candles.map((bar) => ({
        time: bar.date as Time,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      }))
    );

    volumeSeries.setData(
      candles.map((bar) => {
        const isUp = bar.close >= bar.open;
        return {
          time: bar.date as Time,
          value: bar.volume ?? 0,
          color: isUp ? palette.volumeUp : palette.volumeDown,
        };
      })
    );

    for (const priceLine of priceLineRefs.current) {
      candleSeries.removePriceLine(priceLine);
    }
    priceLineRefs.current = [];

    for (const line of referenceLines) {
      const created = candleSeries.createPriceLine({
        price: line.price,
        color: lineColors[line.kind] ?? palette.accent,
        lineWidth: REFERENCE_LINE_WIDTH[line.kind] ?? 1,
        lineStyle: lineStyleForKind(line.kind),
        axisLabelVisible: true,
        title: line.label,
      });
      priceLineRefs.current.push(created);
    }

    for (const series of overlaySeriesRef.current) {
      chart.removeSeries(series);
    }
    overlaySeriesRef.current = [];

    if (showGhostPaths) {
      for (const path of paths) {
        if (path.earnings_date === selectedPathDate) continue;
        const ghostSeries = chart.addSeries(LineSeries, {
          color: palette.ghost,
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        ghostSeries.setData(
          rebasedLinePoints(path.points, focusEarningsDate, focusBaseline)
        );
        overlaySeriesRef.current.push(ghostSeries);
      }
    }

    if (selectedPathDate) {
      const selected = paths.find((path) => path.earnings_date === selectedPathDate);
      if (selected) {
        const selectedSeries = chart.addSeries(LineSeries, {
          color: palette.accent,
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        selectedSeries.setData(
          rebasedLinePoints(selected.points, focusEarningsDate, focusBaseline)
        );
        overlaySeriesRef.current.push(selectedSeries);
      }
    }

    if (showMedian && medianPath.length > 0) {
      const medianSeries = chart.addSeries(LineSeries, {
        color: palette.median,
        lineWidth: 2,
        lineStyle: LineStyle.Dotted,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      medianSeries.setData(
        rebasedLinePoints(medianPath, focusEarningsDate, focusBaseline)
      );
      overlaySeriesRef.current.push(medianSeries);
    }

    chart.timeScale().fitContent();
  }, [
    candles,
    focusBaseline,
    focusEarningsDate,
    lineColors,
    medianPath,
    palette,
    paths,
    referenceLines,
    selectedPathDate,
    showGhostPaths,
    showMedian,
  ]);

  return (
    <div
      ref={containerRef}
      className="h-[26rem] w-full min-h-[20rem] bg-chart-shell sm:h-[28rem]"
      role="img"
      aria-label="Daily price candles with pivot, support, resistance, entry, take profit, and stop loss levels"
    />
  );
}
