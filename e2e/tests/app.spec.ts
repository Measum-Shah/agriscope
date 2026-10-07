import { test, expect } from '@playwright/test';

test('homepage loads and displays application title', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/AgriScope/i);
});
