/**
 * Utility functions for formatting and text manipulation
 */

/**
 * Truncate a string in the middle with ellipsis
 * Useful for long file paths or IDs
 *
 * @example
 * truncateMiddle('/app/data/a621ea97-aed0-4f1c-8b20-5ecaeb3d022c/raw/data', 30)
 * // => '/app/data/.../raw/data'
 */
export function truncateMiddle(str: string, maxLength: number): string {
  if (str.length <= maxLength) {
    return str;
  }

  const ellipsis = '...';
  const charsToShow = maxLength - ellipsis.length;
  const frontChars = Math.ceil(charsToShow / 2);
  const backChars = Math.floor(charsToShow / 2);

  return str.slice(0, frontChars) + ellipsis + str.slice(str.length - backChars);
}

/**
 * Truncate a file path intelligently by keeping important parts
 *
 * @example
 * truncatePath('/app/data/long-id/providers/snowflake/tables/TABLE_NAME/file.json')
 * // => '/app/.../snowflake/tables/TABLE_NAME/file.json'
 */
export function truncatePath(path: string, maxSegments: number = 5): string {
  const segments = path.split('/');

  if (segments.length <= maxSegments) {
    return path;
  }

  // Keep first segment, last few segments, and add ellipsis
  const keepStart = 2;
  const keepEnd = maxSegments - keepStart - 1;

  const startParts = segments.slice(0, keepStart);
  const endParts = segments.slice(-keepEnd);

  return [...startParts, '...', ...endParts].join('/');
}

/**
 * Format JSON with syntax highlighting classes (basic)
 * Returns formatted JSON string
 */
export function formatJson(obj: any): string {
  try {
    return JSON.stringify(obj, null, 2);
  } catch (error) {
    return String(obj);
  }
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch (error) {
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      document.execCommand('copy');
    } catch (err) {
      console.error('Failed to copy text:', err);
    }

    document.body.removeChild(textArea);
  }
}

/**
 * Format a timestamp to a readable format
 */
export function formatTimestamp(timestamp: string | Date): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;

  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3
  });
}

/**
 * Get a summary/preview of long text
 */
export function getTextSummary(text: string, maxLength: number = 200): {
  summary: string;
  isTruncated: boolean;
} {
  if (text.length <= maxLength) {
    return {
      summary: text,
      isTruncated: false
    };
  }

  // Try to truncate at a sentence boundary
  const truncated = text.slice(0, maxLength);
  const lastPeriod = truncated.lastIndexOf('.');
  const lastSpace = truncated.lastIndexOf(' ');

  const cutoff = lastPeriod > maxLength * 0.7
    ? lastPeriod + 1
    : lastSpace > 0
      ? lastSpace
      : maxLength;

  return {
    summary: text.slice(0, cutoff).trim() + '...',
    isTruncated: true
  };
}

/**
 * Extract file name from a path
 */
export function getFileName(path: string): string {
  return path.split('/').pop() || path;
}

/**
 * Detect if content is JSON and format it
 */
export function smartFormatContent(content: string): string {
  try {
    const parsed = JSON.parse(content);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return content;
  }
}
