import { Page, expect } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Login page object for PropelAuth authentication
 */
export class LoginPage extends BasePage {
  // Selectors for PropelAuth login page
  private readonly emailInput = () => this.page.getByLabel(/email/i).or(
    this.page.locator('input[type="email"]')
  ).or(
    this.page.locator('input[name="email"]')
  );

  private readonly passwordInput = () => this.page.getByLabel(/password/i).or(
    this.page.locator('input[type="password"]')
  ).or(
    this.page.locator('input[name="password"]')
  );

  private readonly continueButton = () => this.page.getByRole('button', { name: /continue|next/i });

  private readonly submitButton = () => this.page.getByRole('button', { name: /sign in|log in|submit|continue/i });

  /**
   * Perform login with email and password
   */
  async login(email: string, password: string) {
    // Navigate to app (will redirect to PropelAuth)
    await this.navigateTo('/');

    // Wait for redirect to PropelAuth login page
    try {
      await this.page.waitForURL(/auth/, { timeout: 10000 });
    } catch {
      // May already be logged in
      if (this.getCurrentUrl().includes('projects')) {
        console.log('Already logged in');
        return;
      }
    }

    await this.page.waitForLoadState('networkidle');

    // Fill email
    await this.emailInput().fill(email);

    // Check for two-step flow (email first, then password)
    if (await this.continueButton().isVisible({ timeout: 2000 }).catch(() => false)) {
      await this.continueButton().click();
      await this.page.waitForLoadState('networkidle');
    }

    // Fill password
    await this.passwordInput().fill(password);

    // Submit
    await this.submitButton().click();

    // Wait for successful redirect to app
    await this.page.waitForURL(/projects/, { timeout: 60000 });
  }

  /**
   * Check if user is logged in
   */
  async isLoggedIn(): Promise<boolean> {
    const url = this.getCurrentUrl();

    // If on a projects page, user is logged in
    if (url.includes('projects')) {
      return true;
    }

    // If on auth page, user is not logged in
    if (url.includes('auth') || url.includes('login')) {
      return false;
    }

    // Check for user menu element
    const userMenu = this.page.locator('[data-testid="user-menu"]').or(
      this.page.locator('[class*="user-menu"]')
    ).or(
      this.page.locator('[class*="UserMenu"]')
    );

    try {
      await userMenu.waitFor({ state: 'visible', timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Logout
   */
  async logout() {
    // Find and click user menu
    const userMenu = this.page.locator('[data-testid="user-menu"]').or(
      this.page.locator('[class*="user-menu"]')
    );

    await userMenu.click();

    // Click logout
    await this.page.getByRole('menuitem', { name: /log out|sign out/i }).or(
      this.page.getByText(/log out|sign out/i)
    ).click();

    // Wait for redirect to login
    await this.page.waitForURL(/auth|login/, { timeout: 30000 });
  }
}
