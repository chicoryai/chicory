import { test, expect } from '@playwright/test';

/**
 * Smoke tests to verify basic application functionality
 */
test.describe('Smoke Tests', () => {
  test('app loads and redirects to login or projects', async ({ page }) => {
    await page.goto('/');

    // Should redirect to either login (if not authenticated) or projects (if authenticated)
    await page.waitForURL(/auth|projects/, { timeout: 30000 });

    const url = page.url();
    expect(url.includes('auth') || url.includes('projects')).toBeTruthy();
  });

  test('authenticated user sees projects page', async ({ page }) => {
    // This test uses stored auth state from global-setup
    await page.goto('/');

    // Wait for redirect
    await page.waitForLoadState('networkidle');

    // Should be on projects page (authenticated via stored state)
    await page.waitForURL(/projects/, { timeout: 30000 });

    // Verify we're on a project-related page by checking URL contains 'projects'
    expect(page.url()).toContain('projects');
  });

  test('navigation elements are present', async ({ page }) => {
    await page.goto('/');
    await page.waitForURL(/projects/, { timeout: 30000 });
    await page.waitForLoadState('networkidle');

    // Check for main navigation elements - at least one should be visible
    const navElements = [
      page.getByText(/agents/i),
      page.getByText(/integrations/i),
      page.locator('[class*="sidebar"]'),
      page.locator('nav'),
    ];

    let foundNav = false;
    for (const element of navElements) {
      try {
        if (await element.first().isVisible({ timeout: 2000 })) {
          foundNav = true;
          break;
        }
      } catch {
        // Continue checking
      }
    }

    expect(foundNav).toBeTruthy();
  });

  test('API backend is reachable', async ({ request }) => {
    const apiUrl = process.env.API_URL || 'http://localhost:8000';

    // Test basic health endpoint
    const response = await request.get(`${apiUrl}/`);

    // Should get a response (200 or similar)
    expect(response.ok()).toBeTruthy();
  });
});
