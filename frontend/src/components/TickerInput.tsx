"use client";

import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import { generatePlaybook } from "@/lib/api";

const POPULAR_TICKERS = [
  "AAPL",
  "MSFT",
  "NVDA",
  "GOOGL",
  "AMZN",
  "META",
  "TSLA",
  "JPM",
];

interface TickerInputProps {
  suggestions?: string[];
}

function rankTickers(query: string, tickers: string[]): string[] {
  const q = query.trim().toUpperCase();
  if (!q) {
    return tickers.slice(0, 8);
  }

  const starts: string[] = [];
  const contains: string[] = [];

  for (const ticker of tickers) {
    const upper = ticker.toUpperCase();
    if (upper.startsWith(q)) {
      starts.push(ticker);
    } else if (upper.includes(q)) {
      contains.push(ticker);
    }
  }

  return [...starts, ...contains].slice(0, 8);
}

export function TickerInput({ suggestions = POPULAR_TICKERS }: TickerInputProps) {
  const router = useRouter();
  const inputId = useId();
  const listboxId = useId();
  const rootRef = useRef<HTMLDivElement>(null);

  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const allTickers = useMemo(
    () => Array.from(new Set([...suggestions, ...POPULAR_TICKERS])),
    [suggestions]
  );

  const dropdownOptions = useMemo(
    () => rankTickers(ticker, allTickers),
    [ticker, allTickers]
  );

  const closeDropdown = useCallback(() => {
    setOpen(false);
    setActiveIndex(-1);
  }, []);

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        closeDropdown();
      }
    };

    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open, closeDropdown]);

  const selectTicker = (value: string) => {
    setTicker(value.toUpperCase());
    closeDropdown();
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const normalized = ticker.trim().toUpperCase();
    if (!normalized || loading) return;

    closeDropdown();
    setLoading(true);
    setError(null);

    try {
      const response = await generatePlaybook(normalized);
      router.push(`/playbook/${response.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the playbook");
      setLoading(false);
    }
  };

  const handleInputKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (!open && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      event.preventDefault();
      setOpen(true);
      setActiveIndex(0);
      return;
    }

    if (!open) return;

    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        setActiveIndex((prev) =>
          prev < dropdownOptions.length - 1 ? prev + 1 : 0
        );
        break;
      case "ArrowUp":
        event.preventDefault();
        setActiveIndex((prev) =>
          prev > 0 ? prev - 1 : dropdownOptions.length - 1
        );
        break;
      case "Enter":
        if (activeIndex >= 0 && dropdownOptions[activeIndex]) {
          event.preventDefault();
          selectTicker(dropdownOptions[activeIndex]);
        }
        break;
      case "Escape":
        event.preventDefault();
        closeDropdown();
        break;
      case "Tab":
        closeDropdown();
        break;
      default:
        break;
    }
  };

  const showDropdown = open && dropdownOptions.length > 0;

  return (
    <div ref={rootRef} className="max-w-xl">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="relative min-w-0 flex-1">
          <label
            htmlFor={inputId}
            className="mb-2 block text-[0.9rem] font-medium text-ink-soft"
          >
            Stock ticker
          </label>
          <input
            id={inputId}
            type="text"
            role="combobox"
            aria-expanded={showDropdown}
            aria-controls={listboxId}
            aria-autocomplete="list"
            aria-activedescendant={
              activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined
            }
            value={ticker}
            onChange={(e) => {
              setTicker(e.target.value.toUpperCase());
              setOpen(true);
              setActiveIndex(-1);
            }}
            onFocus={() => setOpen(true)}
            placeholder="e.g. NVDA"
            maxLength={10}
            pattern="[A-Za-z.\-]+"
            disabled={loading}
            className="glass-input w-full rounded-xl px-4 py-3.5 font-mono text-lg uppercase text-ink placeholder:normal-case placeholder:text-ink-soft/70 disabled:opacity-60"
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="characters"
            spellCheck={false}
            onKeyDown={handleInputKeyDown}
          />

          {showDropdown && (
            <div
              id={listboxId}
              role="listbox"
              aria-label="Ticker suggestions"
              className="glass-dropdown absolute left-0 right-0 top-full z-[100] mt-2 max-h-64 overflow-y-auto p-1.5"
            >
              {dropdownOptions.map((option, index) => {
                const isActive = index === activeIndex;
                return (
                  <button
                    key={option}
                    id={`${listboxId}-option-${index}`}
                    type="button"
                    role="option"
                    aria-selected={isActive}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => selectTicker(option)}
                    onMouseEnter={() => setActiveIndex(index)}
                    className={`flex w-full cursor-pointer items-center rounded-lg px-3 py-2.5 text-left font-mono text-[1rem] transition ${
                      isActive
                        ? "bg-accent/15 text-ink"
                        : "text-ink hover:bg-[#e8edf8]"
                    }`}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={!ticker.trim() || loading}
          className="btn-primary cursor-pointer rounded-xl px-6 py-3.5 text-[1rem] font-semibold disabled:cursor-not-allowed disabled:opacity-45 sm:mb-0"
        >
          {loading ? "Starting…" : "Generate playbook"}
        </button>
      </form>

      {error && <p className="mt-3 text-[0.95rem] text-down">{error}</p>}

      {!showDropdown && (
        <div className="mt-4">
          <p className="text-[0.85rem] font-medium text-ink-soft">Popular tickers</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {POPULAR_TICKERS.map((symbol) => {
              const selected = ticker === symbol;
              return (
                <button
                  key={symbol}
                  type="button"
                  disabled={loading}
                  onClick={() => selectTicker(symbol)}
                  aria-pressed={selected}
                className={`glass-chip glass-chip-interactive cursor-pointer px-3.5 py-2 font-mono text-[0.9rem] disabled:cursor-not-allowed disabled:opacity-50 ${
                  selected ? "glass-chip-selected" : "text-ink"
                }`}
                >
                  {symbol}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
