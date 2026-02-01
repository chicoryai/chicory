/**
 * Date formatting utilities for consistent date handling across the application
 */

/**
 * Format a UTC date string to local timezone with configurable options
 * @param dateString - UTC date string
 * @param options - Optional Intl.DateTimeFormatOptions
 * @returns Formatted date string in local timezone
 */
export function formatLocalDateTime(
  dateString: string,
  options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }
): string {
  const utcDate = new Date(dateString + 'Z');
  return new Intl.DateTimeFormat('en-US', options).format(utcDate);
}

/**
 * Calculate duration between two dates
 * @param startDate - Start date string
 * @param endDate - Optional end date string, defaults to current time
 * @returns Formatted duration string
 */
export function calculateDuration(startDate: string, endDate?: string): string {
  const start = new Date(startDate + 'Z');
  const end = endDate ? new Date(endDate + 'Z') : new Date();
  const durationMs = end.getTime() - start.getTime();
  
  const minutes = Math.floor(durationMs / 60000);
  const seconds = Math.floor((durationMs % 60000) / 1000);
  
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

/**
 * Format a UTC date string to local date only (no time)
 * @param dateString - UTC date string
 * @returns Formatted date string in local timezone
 */
export function formatLocalDate(dateString: string): string {
  return formatLocalDateTime(dateString, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format a UTC date string to local time only (no date)
 * @param dateString - UTC date string
 * @returns Formatted time string in local timezone
 */
export function formatLocalTime(dateString: string): string {
  return formatLocalDateTime(dateString, {
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  });
}

/**
 * Format a UTC date string to relative time (e.g., "5 min ago", "1hr 10 min ago", "3 days ago")
 * @param dateString - UTC date string
 * @returns Formatted relative time string
 */
export function formatRelativeTime(dateString: string): string {
  const startDate = new Date(dateString + 'Z');
  const now = new Date();
  const diffMs = now.getTime() - startDate.getTime();
  
  // Convert to various time units
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  // Format based on the appropriate time unit
  if (diffDays > 0) {
    return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
  } else if (diffHours > 0) {
    const remainingMins = diffMins % 60;
    if (remainingMins > 0) {
      return `${diffHours}hr ${remainingMins} min ago`;
    }
    return `${diffHours}hr ago`;
  } else if (diffMins > 0) {
    return `${diffMins} min ago`;
  } else {
    return 'just now';
  }
} 