import { test as base, expect, Page } from '@playwright/test';
import path from 'path';

/**
 * Extended test fixture with authentication helpers
 */
export const test = base.extend<{
  authenticatedPage: Page;
}>({
  /**
   * Provides a page that's already authenticated.
   * Uses the stored auth state from global-setup.
   */
  authenticatedPage: async ({ page }, use) => {
    // The page should already have auth state loaded from playwright.config.ts
    // Just verify we're authenticated
    await page.goto('/');

    // Wait for either auth redirect or app load
    await page.waitForLoadState('networkidle');

    // Check if we got redirected to login
    const currentUrl = page.url();
    if (currentUrl.includes('auth') || currentUrl.includes('login')) {
      throw new Error('Not authenticated - auth state may have expired. Run global setup again.');
    }

    await use(page);
  },
});

export { expect };

/**
 * Helper to check if the current page is authenticated
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  // Check for common auth indicators
  const userMenu = page.locator('[data-testid="user-menu"]').or(
    page.locator('[class*="user-menu"]')
  ).or(
    page.locator('[class*="UserMenu"]')
  );

  try {
    await userMenu.waitFor({ state: 'visible', timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * Helper to get the current user's info from the page
 */
export async function getCurrentUser(page: Page): Promise<{ email?: string } | null> {
  try {
    // Look for user info in the page
    const userMenu = page.locator('[data-testid="user-menu"]').or(
      page.locator('[class*="user-menu"]')
    );

    if (await userMenu.isVisible()) {
      // Try to get email from user menu or settings
      await userMenu.click();
      const emailElement = page.locator('[data-testid="user-email"]').or(
        page.getByText(/@.*\./i)
      );

      if (await emailElement.isVisible()) {
        const email = await emailElement.textContent();
        return { email: email || undefined };
      }
    }

    return null;
  } catch {
    return null;
  }
}
