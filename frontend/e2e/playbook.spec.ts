import { expect, test } from "@playwright/test";

test.describe("Home page", () => {
  test("loads hero and ticker input", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /Know the report/i })
    ).toBeVisible();
    await expect(
      page.getByRole("combobox", { name: /stock ticker/i })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /generate playbook/i })
    ).toBeVisible();
  });

  test("shows disclaimer banner", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/not financial advice/i)).toBeVisible();
  });
});

test.describe("Demo playbook flow", () => {
  test("loads instant demo and renders playbook sections", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /demo aapl/i }).click();

    await expect(page).toHaveURL(/\/playbook\/demo_aapl/);
    await expect(
      page.getByRole("heading", { name: /Apple Inc\. Earnings Playbook/i })
    ).toBeVisible({ timeout: 15_000 });

    await expect(page.getByRole("heading", { name: "Report Forecast" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Price Reaction Scenarios" })
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Peer Spillover Map" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Action Playbook" })).toBeVisible();
    await expect(
      page.getByRole("region", { name: /reaction workspace/i }).getByText("AAPL")
    ).toBeVisible();
  });

  test("export toolbar is visible on completed demo", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /demo aapl/i }).click();
    await expect(page).toHaveURL(/\/playbook\/demo_aapl/);

    await expect(page.getByText("Export playbook")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("button", { name: /^JSON$/i })).toBeVisible();
    await expect(
      page.getByRole("button", { name: /print \/ pdf/i })
    ).toBeVisible();
  });
});

test.describe("Calendar page", () => {
  test("loads calendar view", async ({ page }) => {
    await page.goto("/calendar");
    await expect(
      page.getByRole("heading", { name: /earnings calendar/i })
    ).toBeVisible();
  });
});
