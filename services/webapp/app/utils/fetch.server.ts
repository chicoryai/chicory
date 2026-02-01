/**
 * Retry utility for fetch operations with exponential backoff
 *
 * This utility helps handle transient network failures and idle-state errors
 * by automatically retrying failed fetch requests with increasing delays.
 */

export interface RetryOptions {
  /**
   * Maximum number of retry attempts (default: 3)
   */
  maxRetries?: number;

  /**
   * Initial delay in milliseconds (default: 1000ms)
   */
  initialDelay?: number;

  /**
   * Maximum delay in milliseconds (default: 10000ms)
   */
  maxDelay?: number;

  /**
   * Multiplier for exponential backoff (default: 2)
   */
  backoffMultiplier?: number;

  /**
   * Predicate function to determine if an error should be retried
   * Default: retry on network errors and 502/503/504 status codes
   */
  shouldRetry?: (error: unknown, response?: Response) => boolean;

  /**
   * Callback invoked before each retry attempt
   */
  onRetry?: (attempt: number, error: unknown, delay: number) => void;
}

const DEFAULT_OPTIONS: Required<RetryOptions> = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 10000,
  backoffMultiplier: 2,
  shouldRetry: (error: unknown, response?: Response) => {
    // Retry on network errors (TypeError: Failed to fetch)
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return true;
    }

    // Retry on specific HTTP status codes
    if (response) {
      const retryableStatuses = [502, 503, 504, 408]; // Bad Gateway, Service Unavailable, Gateway Timeout, Request Timeout
      return retryableStatuses.includes(response.status);
    }

    return false;
  },
  onRetry: (attempt: number, error: unknown, delay: number) => {
    console.log(`[Retry] Attempt ${attempt} failed, retrying in ${delay}ms...`, error);
  },
};

/**
 * Wraps a fetch call with automatic retry logic using exponential backoff
 *
 * @example
 * ```typescript
 * const data = await fetchWithRetry('https://api.example.com/data', {
 *   method: 'GET',
 *   headers: { 'Authorization': 'Bearer token' }
 * });
 * ```
 *
 * @example With custom retry options
 * ```typescript
 * const data = await fetchWithRetry('https://api.example.com/data', {
 *   method: 'POST',
 *   body: JSON.stringify({ data: 'value' })
 * }, {
 *   maxRetries: 5,
 *   initialDelay: 500,
 *   onRetry: (attempt, error, delay) => {
 *     console.log(`Custom retry handler: attempt ${attempt}`);
 *   }
 * });
 * ```
 */
export async function fetchWithRetry(
  url: string | URL | Request,
  init?: RequestInit,
  retryOptions?: RetryOptions
): Promise<Response> {
  const options = { ...DEFAULT_OPTIONS, ...retryOptions };
  let lastError: unknown;
  let lastResponse: Response | undefined;

  for (let attempt = 0; attempt <= options.maxRetries; attempt++) {
    try {
      const response = await fetch(url, init);

      // If response is ok, return it immediately
      if (response.ok) {
        return response;
      }

      // Check if we should retry this response
      lastResponse = response;
      if (attempt < options.maxRetries && options.shouldRetry(null, response)) {
        const delay = calculateDelay(attempt, options);
        options.onRetry(attempt + 1, new Error(`HTTP ${response.status}`), delay);
        await sleep(delay);
        continue;
      }

      // If we shouldn't retry or we've exhausted retries, return the response
      return response;
    } catch (error) {
      lastError = error;

      // If we've exhausted retries, throw the error
      if (attempt >= options.maxRetries) {
        throw error;
      }

      // Check if we should retry this error
      if (options.shouldRetry(error, lastResponse)) {
        const delay = calculateDelay(attempt, options);
        options.onRetry(attempt + 1, error, delay);
        await sleep(delay);
        continue;
      }

      // If we shouldn't retry, throw the error
      throw error;
    }
  }

  // This should never be reached, but TypeScript needs it
  throw lastError || new Error('Fetch failed after retries');
}

/**
 * Calculate delay for exponential backoff
 */
function calculateDelay(attempt: number, options: Required<RetryOptions>): number {
  const delay = options.initialDelay * Math.pow(options.backoffMultiplier, attempt);
  return Math.min(delay, options.maxDelay);
}

/**
 * Sleep utility for delays between retries
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Helper function to check if an error is a network error
 */
export function isNetworkError(error: unknown): boolean {
  return error instanceof TypeError &&
         (error.message.includes('fetch') ||
          error.message.includes('network') ||
          error.message.includes('Failed to fetch'));
}

/**
 * Helper function to check if a response should trigger a retry
 */
export function isRetryableResponse(response: Response): boolean {
  const retryableStatuses = [408, 502, 503, 504];
  return retryableStatuses.includes(response.status);
}
