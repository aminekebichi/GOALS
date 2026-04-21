import { test, expect } from "@playwright/test";

test.describe("Match Calendar (public)", () => {
  test("homepage loads and shows GOALS branding", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("text=GOALS")).toBeVisible();
    await expect(page.locator("text=Match Calendar")).toBeVisible();
  });

  test("shows match cards or empty state", async ({ page }) => {
    await page.goto("/");
    const matchCards = page.getByTestId("match-card");
    const emptyState = page.locator("text=No matches available");
    await expect(matchCards.or(emptyState).first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("shows Sign In button for unauthenticated users", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("button", { name: "Sign In" })).toBeVisible();
  });
});
