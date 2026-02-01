import { chromium, FullConfig } from '@playwright/test';
import path from 'path';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: path.resolve(__dirname, '../.env.local') });

/**
 * Global setup function that runs once before all tests.
 * Performs login and saves authentication state to storage/auth.json
 */
async function globalSetup(config: FullConfig) {
  const { baseURL } = config.projects[0].use;

  // Get test credentials from environment
  const email = process.env.TEST_USER_EMAIL;
  const password = process.env.TEST_USER_PASSWORD;

  if (!email || !password) {
    console.log('Warning: TEST_USER_EMAIL and TEST_USER_PASSWORD not set in .env.local');
    console.log('Skipping authentication setup. Tests requiring auth will fail.');
    return;
  }

  console.log('Starting global authentication setup...');
  console.log(`Base URL: ${baseURL}`);

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to the app (will redirect to PropelAuth login)
    console.log('Navigating to app...');
    await page.goto(baseURL || 'http://localhost:3000');

    // Wait for redirect to PropelAuth login page
    // PropelAuth URLs typically contain 'auth' in the domain or path
    await page.waitForURL(/auth/, { timeout: 30000 }).catch(() => {
      // If already logged in, we might be on the projects page
      console.log('Did not redirect to auth page - may already be logged in');
    });

    // Check if we're on an auth page
    const currentUrl = page.url();
    console.log(`Current URL: ${currentUrl}`);

    if (currentUrl.includes('auth') || currentUrl.includes('login')) {
      console.log('On login page, entering credentials...');

      // Wait for the login form to be ready
      await page.waitForLoadState('networkidle');

      // Fill in email
      const emailInput = page.getByLabel(/email/i).or(
        page.locator('input[type="email"]')
      ).or(
        page.locator('input[name="email"]')
      );
      await emailInput.fill(email);

      // Look for a "Continue" or "Next" button (PropelAuth often has a two-step flow)
      const continueButton = page.getByRole('button', { name: /continue|next/i });
      if (await continueButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await continueButton.click();
        await page.waitForLoadState('networkidle');
      }

      // Fill in password
      const passwordInput = page.getByLabel(/password/i).or(
        page.locator('input[type="password"]')
      ).or(
        page.locator('input[name="password"]')
      );
      await passwordInput.fill(password);

      // Submit the form - specifically target "Log in with email" button
      const submitButton = page.getByRole('button', { name: 'Log in with email' });
      await submitButton.click();

      // Wait for successful login (redirect back to app)
      console.log('Waiting for redirect after login...');
      await page.waitForURL(/projects/, { timeout: 60000 });
      console.log('Login successful!');
    } else if (currentUrl.includes('projects')) {
      console.log('Already logged in, on projects page');
    }

    // Save authentication state
    const storagePath = path.resolve(__dirname, '../storage/auth.json');
    await context.storageState({ path: storagePath });
    console.log(`Authentication state saved to ${storagePath}`);

  } catch (error) {
    console.error('Global setup failed:', error);
    // Take a screenshot for debugging
    const screenshotPath = path.resolve(__dirname, '../reports/setup-failure.png');
    await page.screenshot({ path: screenshotPath });
    console.log(`Screenshot saved to ${screenshotPath}`);
    throw error;
  } finally {
    await browser.close();
  }
}

export default globalSetup;
