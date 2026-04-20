import { test, expect } from '@playwright/test';

test.describe('Auth protection', () => {
  test('redirects /stats to sign-in when unauthenticated', async ({ page }) => {
    await page.goto('/stats');
    await expect(page).toHaveURL(/sign-in/, { timeout: 10000 });
  });

  test('redirects /settings to sign-in when unauthenticated', async ({ page }) => {
    await page.goto('/settings');
    await expect(page).toHaveURL(/sign-in/, { timeout: 10000 });
  });

  test('sign-in page loads Clerk UI', async ({ page }) => {
    await page.goto('/sign-in');
    await expect(page.locator('text=Sign in').or(page.locator('[data-clerk-component]'))).toBeVisible({ timeout: 10000 });
  });
});
