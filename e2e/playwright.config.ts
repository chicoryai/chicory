import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';
import path from 'path';

// Load environment variables from .env.local
dotenv.config({ path: path.resolve(__dirname, '.env.local') });

/**
 * Playwright configuration for Chicory E2E tests
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests',

  // Run tests sequentially for stateful E2E tests
  fullyParallel: false,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Single worker for sequential E2E tests
  workers: process.env.CI ? 1 : 1,

  // Reporters
  reporter: [
    ['html', { outputFolder: 'reports/playwright-report', open: 'never' }],
    ['json', { outputFile: 'reports/results.json' }],
    ['list']
  ],

  // Shared settings for all projects
  use: {
    // Base URL for navigation
    baseURL: process.env.WEBAPP_URL || 'http://localhost:3000',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Capture screenshot on failure
    screenshot: 'only-on-failure',

    // Record video on first retry
    video: 'on-first-retry',

    // Action timeout
    actionTimeout: 30000,

    // Navigation timeout
    navigationTimeout: 30000,
  },

  // Global setup for authentication
  globalSetup: require.resolve('./fixtures/global-setup.ts'),

  // Test timeout (2 minutes per test for long-running operations like training)
  timeout: 120000,

  // Expect timeout
  expect: {
    timeout: 10000,
  },

  // Projects configuration
  projects: [
    // Setup project for authentication
    {
      name: 'setup',
      testMatch: /global\.setup\.ts/,
    },

    // Main test project using Chrome
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Use stored auth state
        storageState: 'storage/auth.json',
      },
      dependencies: ['setup'],
    },
  ],

  // Output directory for test artifacts
  outputDir: 'test-results/',

  // Web server configuration (optional - for local development)
  // Uncomment if you want Playwright to start the webapp automatically
  // webServer: process.env.CI ? undefined : {
  //   command: 'cd ../webapp && npm run dev',
  //   url: 'http://localhost:3000',
  //   reuseExistingServer: true,
  //   timeout: 120000,
  // },
});
