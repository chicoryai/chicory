import { Page, Locator, expect } from '@playwright/test';

/**
 * Base page object with common methods for all pages
 */
export class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Navigate to a specific path
   */
  async navigateTo(path: string) {
    await this.page.goto(path);
  }

  /**
   * Wait for page to finish loading
   */
  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Wait for toast/notification message
   */
  async waitForToast(messagePattern: string | RegExp, options?: { timeout?: number }) {
    const timeout = options?.timeout || 10000;
    const toast = this.page.getByRole('alert').or(
      this.page.locator('[class*="toast"]')
    ).or(
      this.page.locator('[class*="notification"]')
    ).or(
      this.page.locator('[class*="alert"]')
    );

    if (typeof messagePattern === 'string') {
      await expect(toast).toContainText(messagePattern, { timeout });
    } else {
      await expect(toast).toHaveText(messagePattern, { timeout });
    }
  }

  /**
   * Wait for success toast
   */
  async waitForSuccessToast(timeout = 10000) {
    await this.waitForToast(/success/i, { timeout });
  }

  /**
   * Wait for error toast
   */
  async waitForErrorToast(timeout = 10000) {
    await this.waitForToast(/error|failed/i, { timeout });
  }

  /**
   * Close any open modal
   */
  async closeModal() {
    await this.page.keyboard.press('Escape');
  }

  /**
   * Get current URL
   */
  getCurrentUrl(): string {
    return this.page.url();
  }

  /**
   * Wait for navigation to a URL pattern
   */
  async waitForNavigation(urlPattern: string | RegExp, timeout = 30000) {
    await this.page.waitForURL(urlPattern, { timeout });
  }

  /**
   * Check if element is visible
   */
  async isVisible(selector: string, timeout = 5000): Promise<boolean> {
    try {
      await this.page.locator(selector).waitFor({ state: 'visible', timeout });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get text content of element
   */
  async getText(locator: Locator): Promise<string | null> {
    return await locator.textContent();
  }

  /**
   * Click with retry
   */
  async clickWithRetry(locator: Locator, retries = 3) {
    for (let i = 0; i < retries; i++) {
      try {
        await locator.click();
        return;
      } catch (error) {
        if (i === retries - 1) throw error;
        await this.page.waitForTimeout(500);
      }
    }
  }

  /**
   * Extract project ID from URL
   */
  extractProjectIdFromUrl(): string | null {
    const url = this.getCurrentUrl();
    const match = url.match(/projects\/([^/]+)/);
    return match ? match[1] : null;
  }

  /**
   * Extract agent ID from URL
   */
  extractAgentIdFromUrl(): string | null {
    const url = this.getCurrentUrl();
    const match = url.match(/agents\/([^/]+)/);
    return match ? match[1] : null;
  }
}
