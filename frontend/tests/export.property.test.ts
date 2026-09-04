import { afterEach, beforeEach, test, vi } from "vitest";
import * as hegel from "@hegeldev/hegel";
import * as gs from "@hegeldev/hegel/generators";

import { buildClientSideBundle } from "../src/lib/export";
import type { Playbook, TraceLog } from "../src/lib/types";

const exportedAt = "2026-09-03T12:34:56.789Z";
const settings = {
  database: hegel.Database.disabled,
  testCases: 100,
};
const identifier = gs.text({
  alphabet: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_ ",
  maxSize: 40,
});

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date(exportedAt));
});

afterEach(() => {
  vi.useRealTimers();
});

test("buildClientSideBundle preserves identifiers and object identity", () =>
  hegel.test((tc) => {
    const jobId = tc.draw(identifier);
    const ticker = tc.draw(identifier);
    const playbookMarker = tc.draw(
      gs.integers({ minValue: -1_000_000, maxValue: 1_000_000 })
    );
    const traceMarker = tc.draw(
      gs.integers({ minValue: -1_000_000, maxValue: 1_000_000 })
    );
    const playbook = { marker: playbookMarker } as unknown as Playbook;
    const trace = { marker: traceMarker } as unknown as TraceLog;

    const bundle = buildClientSideBundle(jobId, ticker, playbook, trace);

    assert(bundle.exported_at === exportedAt, "bundle used the wrong export time");
    assert(bundle.job_id === jobId, "bundle changed the job ID");
    assert(bundle.ticker === ticker, "bundle changed the ticker");
    assert(bundle.playbook === playbook, "bundle copied or replaced the playbook");
    assert(bundle.trace === trace, "bundle copied or replaced the trace");
    assert(
      Object.keys(bundle).sort().join(",") ===
        "exported_at,job_id,playbook,ticker,trace",
      `bundle keys changed: ${Object.keys(bundle).join(",")}`
    );
  }, settings));

test("buildClientSideBundle normalizes an absent trace to null", () =>
  hegel.test((tc) => {
    const jobId = tc.draw(identifier);
    const ticker = tc.draw(identifier);
    const trace = tc.draw(gs.sampledFrom([null, undefined] as const));
    const playbook = {
      marker: tc.draw(gs.booleans()),
    } as unknown as Playbook;

    const bundle = buildClientSideBundle(jobId, ticker, playbook, trace);

    assert(bundle.trace === null, "absent trace was not normalized to null");
    assert(bundle.playbook === playbook, "bundle copied or replaced the playbook");
    assert(bundle.job_id === jobId, "bundle changed the job ID");
    assert(bundle.ticker === ticker, "bundle changed the ticker");
    assert(bundle.exported_at === exportedAt, "bundle used the wrong export time");
  }, settings));
