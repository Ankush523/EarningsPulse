import type { HealthResponse } from "./types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export function getBackendUrl(): string {
  return BACKEND_URL;
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

export async function fetchBackendReadiness(): Promise<HealthResponse | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/ready`, {
      method: "GET",
      cache: "no-store",
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}
