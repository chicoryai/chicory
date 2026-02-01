import { Page, expect } from '@playwright/test';

/**
 * Wait for a streaming response to complete
 */
export async function waitForStreamingResponse(
  page: Page,
  options: {
    timeout?: number;
    pollInterval?: number;
  } = {}
) {
  const { timeout = 60000, pollInterval = 500 } = options;

  // Common streaming indicators
  const streamingSelectors = [
    '[data-streaming="true"]',
    '[class*="streaming"]',
    '[class*="loading"]',
    '.animate-pulse',
  ];

  const streamingSelector = streamingSelectors.join(', ');

  // Wait for streaming to start (may already be done for fast responses)
  try {
    await page.waitForSelector(streamingSelector, { timeout: 5000 });
  } catch {
    // Streaming may have completed very quickly or not started yet
  }

  // Wait for streaming to complete
  await expect(page.locator(streamingSelector).first()).toBeHidden({ timeout });
}

/**
 * Wait for network to be idle
 */
export async function waitForNetworkIdle(page: Page, timeout = 10000) {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Wait for an SSE connection to be established
 */
export async function waitForSSEConnection(page: Page, urlPattern: RegExp | string) {
  await page.waitForRequest(request => {
    if (typeof urlPattern === 'string') {
      return request.url().includes(urlPattern);
    }
    return urlPattern.test(request.url());
  });
}

/**
 * Generic polling utility
 */
export async function pollUntil<T>(
  fn: () => Promise<T>,
  predicate: (result: T) => boolean,
  options: { timeout?: number; interval?: number } = {}
): Promise<T> {
  const { timeout = 30000, interval = 1000 } = options;
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    const result = await fn();
    if (predicate(result)) {
      return result;
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }

  throw new Error('Polling timed out');
}

/**
 * Wait for element count to change
 */
export async function waitForElementCountChange(
  page: Page,
  selector: string,
  expectedChange: 'increase' | 'decrease' | number,
  timeout = 30000
) {
  const initialCount = await page.locator(selector).count();

  await expect(async () => {
    const currentCount = await page.locator(selector).count();

    if (typeof expectedChange === 'number') {
      expect(currentCount).toBe(initialCount + expectedChange);
    } else if (expectedChange === 'increase') {
      expect(currentCount).toBeGreaterThan(initialCount);
    } else {
      expect(currentCount).toBeLessThan(initialCount);
    }
  }).toPass({ timeout });
}

/**
 * Wait for toast notification and dismiss it
 */
export async function waitForAndDismissToast(
  page: Page,
  messagePattern: string | RegExp,
  timeout = 10000
) {
  const toast = page.getByRole('alert').or(
    page.locator('[class*="toast"]')
  ).or(
    page.locator('[class*="notification"]')
  );

  // Wait for toast to appear
  if (typeof messagePattern === 'string') {
    await expect(toast).toContainText(messagePattern, { timeout });
  } else {
    await expect(toast).toHaveText(messagePattern, { timeout });
  }

  // Try to dismiss it
  try {
    const closeButton = toast.locator('button[aria-label*="close"]').or(
      toast.locator('[class*="close"]')
    );
    if (await closeButton.isVisible({ timeout: 1000 })) {
      await closeButton.click();
    }
  } catch {
    // Toast may auto-dismiss
  }
}

/**
 * Wait for navigation and page load
 */
export async function waitForNavigationAndLoad(
  page: Page,
  urlPattern: string | RegExp,
  timeout = 30000
) {
  await page.waitForURL(urlPattern, { timeout });
  await page.waitForLoadState('networkidle', { timeout: 10000 });
}

/**
 * Retry an action with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: {
    maxRetries?: number;
    initialDelay?: number;
    maxDelay?: number;
    multiplier?: number;
  } = {}
): Promise<T> {
  const {
    maxRetries = 3,
    initialDelay = 1000,
    maxDelay = 10000,
    multiplier = 2,
  } = options;

  let lastError: Error | undefined;
  let delay = initialDelay;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      if (attempt < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, delay));
        delay = Math.min(delay * multiplier, maxDelay);
      }
    }
  }

  throw lastError;
}
