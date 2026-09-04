import type {
  ApiError,
  EarningsCalendarResponse,
  HealthResponse,
  JobStatus,
  PlaybookGenerateResponse,
  TraceLog,
} from "./types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export function getPlaybookStreamUrl(jobId: string): string {
  return `${BACKEND_URL}/api/playbook/stream/${jobId}`;
}

async function parseError(response: Response): Promise<string> {
  try {
    const data: ApiError = await response.json();
    return data.detail || `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      method: "GET",
      cache: "no-store",
    });
    if (!response.ok) return false;
    const data: HealthResponse = await response.json();
    return data.status === "healthy";
  } catch {
    return false;
  }
}

export async function generatePlaybook(
  ticker: string
): Promise<PlaybookGenerateResponse> {
  const response = await fetch(`${BACKEND_URL}/api/playbook/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker: ticker.toUpperCase().trim() }),
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json();
}

export async function fetchPlaybookJob(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${BACKEND_URL}/api/playbook/${jobId}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json();
}

export async function fetchTraceLog(jobId: string): Promise<TraceLog> {
  const response = await fetch(`${BACKEND_URL}/api/trace/${jobId}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json();
}

export async function fetchEarningsCalendar(
  days = 7
): Promise<EarningsCalendarResponse> {
  const response = await fetch(
    `${BACKEND_URL}/api/calendar?days=${days}`,
    { cache: "no-store" }
  );

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return response.json();
}

export function getPlaybookJsonExportUrl(jobId: string): string {
  return `${BACKEND_URL}/api/playbook/${jobId}/export/json`;
}

export function getPlaybookBundleExportUrl(jobId: string): string {
  return `${BACKEND_URL}/api/playbook/${jobId}/export/bundle`;
}

export async function loadDemoPlaybook(
  ticker: string
): Promise<PlaybookGenerateResponse & { demo?: boolean }> {
  const response = await fetch(
    `${BACKEND_URL}/api/playbook/demo/${ticker.toUpperCase()}`,
    { method: "POST" }
  );
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}
