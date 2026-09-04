import { test } from "vitest";
import * as hegel from "@hegeldev/hegel";
import * as gs from "@hegeldev/hegel/generators";

import {
  formatArchetype,
  formatDate,
  formatDateTime,
  formatLatency,
  formatPctMove,
  formatPercent,
  formatRelationship,
} from "../src/lib/format";

const settings = {
  database: hegel.Database.disabled,
  testCases: 100,
};

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function assertRoundedDecimal(
  formatted: string,
  expectedValue: number,
  digits: number,
  suffix: string
): void {
  assert(formatted.endsWith(suffix), `missing ${suffix} suffix: ${formatted}`);

  const numericText = formatted.slice(0, -suffix.length);
  const unsignedText = numericText.startsWith("+")
    ? numericText.slice(1)
    : numericText;
  const decimalPlaces = unsignedText.split(".")[1]?.length ?? 0;
  assert(
    decimalPlaces === digits,
    `expected ${digits} decimal places, got ${formatted}`
  );

  const actualValue = Number(numericText);
  const roundingTolerance = 0.5 * 10 ** -digits;
  const floatingPointTolerance =
    Number.EPSILON * Math.max(1, Math.abs(expectedValue)) * 4;
  assert(
    Math.abs(actualValue - expectedValue) <=
      roundingTolerance + floatingPointTolerance,
    `${formatted} is not ${expectedValue} rounded to ${digits} places`
  );
}

test("formatPercent scales finite values and honors the requested precision", () =>
  hegel.test((tc) => {
    const value = tc.draw(
      gs.floats({ minValue: -10_000, maxValue: 10_000 })
    );
    const digits = tc.draw(gs.integers({ minValue: 0, maxValue: 6 }));

    assertRoundedDecimal(formatPercent(value, digits), value * 100, digits, "%");
  }, settings));

test("formatPctMove marks only positive moves with a plus sign", () =>
  hegel.test((tc) => {
    const value = tc.draw(
      gs.floats({ minValue: -100_000, maxValue: 100_000 })
    );
    const digits = tc.draw(gs.integers({ minValue: 0, maxValue: 6 }));
    const formatted = formatPctMove(value, digits);

    assert(
      formatted.startsWith("+") === (value > 0),
      `unexpected sign for ${value}: ${formatted}`
    );
    assertRoundedDecimal(formatted, value, digits, "%");
  }, settings));

test("formatLatency switches units at one second without changing the value", () =>
  hegel.test((tc) => {
    const milliseconds = tc.draw(
      gs.integers({ minValue: -10_000, maxValue: 100_000 })
    );
    const formatted = formatLatency(milliseconds);

    if (milliseconds < 1_000) {
      assert(
        formatted === `${milliseconds}ms`,
        `millisecond value changed: ${milliseconds} became ${formatted}`
      );
      return;
    }

    assertRoundedDecimal(formatted, milliseconds / 1_000, 1, "s");
  }, settings));

test("label formatters replace underscores and capitalize each ASCII word", () =>
  hegel.test((tc) => {
    const value = tc.draw(
      gs.text({ alphabet: "abcdefghijklmnopqrstuvwxyz_", maxSize: 48 })
    );
    const expected = value
      .replaceAll("_", " ")
      .replace(/(^| )([a-z])/g, (_, separator: string, letter: string) =>
        `${separator}${letter.toUpperCase()}`
      );

    assert(
      formatArchetype(value) === expected,
      `archetype mismatch for ${JSON.stringify(value)}`
    );
    assert(
      formatRelationship(value) === expected,
      `relationship mismatch for ${JSON.stringify(value)}`
    );
  }, settings));

test("date formatters preserve non-date input verbatim", () =>
  hegel.test((tc) => {
    const suffix = tc.draw(
      gs.text({ alphabet: "abcdefghijklmnopqrstuvwxyz", maxSize: 32 })
    );
    const invalidDate = `invalid:${suffix}`;

    assert(
      Number.isNaN(new Date(invalidDate).getTime()),
      `test generator produced a valid date: ${invalidDate}`
    );
    assert(formatDate(invalidDate) === invalidDate, "formatDate changed invalid input");
    assert(
      formatDateTime(invalidDate) === invalidDate,
      "formatDateTime changed invalid input"
    );
  }, settings));

test("date formatters match Intl output for valid timestamps", () =>
  hegel.test((tc) => {
    const timestamp = tc.draw(
      gs.integers({
        minValue: Date.UTC(2000, 0, 1),
        maxValue: Date.UTC(2030, 11, 31, 23, 59, 59, 999),
      })
    );
    const date = new Date(timestamp);
    const value = date.toISOString();
    const expectedDate = new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(date);
    const expectedDateTime = new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);

    assert(formatDate(value) === expectedDate, `wrong date for ${value}`);
    assert(
      formatDateTime(value) === expectedDateTime,
      `wrong date and time for ${value}`
    );
  }, settings));

test("formatDate keeps YYYY-MM-DD on the same local calendar day", () =>
  hegel.test((tc) => {
    const year = tc.draw(gs.integers({ minValue: 2000, maxValue: 2030 }));
    const month = tc.draw(gs.integers({ minValue: 1, maxValue: 12 }));
    // Cap at 28 so every month is a valid local calendar date.
    const day = tc.draw(gs.integers({ minValue: 1, maxValue: 28 }));
    const value = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const local = new Date(year, month - 1, day);
    const expected = new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(local);

    assert(
      formatDate(value) === expected,
      `date-only ${value} became ${formatDate(value)}, expected ${expected}`
    );
  }, settings));

test("date formatters use the placeholder for absent values", () =>
  hegel.test((tc) => {
    const absent = tc.draw(gs.sampledFrom([null, undefined, ""] as const));

    assert(formatDate(absent) === "—", "formatDate omitted the placeholder");
    assert(
      formatDateTime(absent) === "—",
      "formatDateTime omitted the placeholder"
    );
  }, settings));

test("formatLatency uses the placeholder for nullish values", () =>
  hegel.test((tc) => {
    const absent = tc.draw(gs.sampledFrom([null, undefined] as const));

    assert(formatLatency(absent) === "—", "formatLatency omitted the placeholder");
  }, settings));
