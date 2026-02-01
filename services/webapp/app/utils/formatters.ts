/**
 * Format timestamp in user's local timezone with Google Docs-style naming
 * Examples: "November 10, 2:30 PM", "November 9, 3:45 PM"
 */
export function formatVersionName(timestamp: string): string {
  // Backend sends UTC timestamp without 'Z' suffix, so add it for proper parsing
  const utcTimestamp = timestamp.endsWith('Z') ? timestamp : `${timestamp}Z`;
  const date = new Date(utcTimestamp);
  
  // Format in local timezone - always show day and time
  const monthDay = date.toLocaleDateString('en-US', { month: 'long', day: 'numeric' });
  const time = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  
  // Always include time - "November 10, 2:30 PM"
  return `${monthDay}, ${time}`;
}
