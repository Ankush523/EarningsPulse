import { defineConfig, devices } from "@playwright/test";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const frontendUrl = process.env.FRONTEND_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "list",
  timeout: 60_000,
  use: {
    baseURL: frontendUrl,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command:
        "cd ../backend && uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8000",
      url: `${backendUrl}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        CORS_ORIGINS: '["http://localhost:3000","http://127.0.0.1:3000"]',
      },
    },
    {
      command: "bun run dev --port 3000",
      url: frontendUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_BACKEND_URL: backendUrl,
      },
    },
  ],
});
