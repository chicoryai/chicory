import React from 'react';

/**
 * No-op RevalidateSession component for local auth.
 * PropelAuth uses this to refresh sessions on the client, but local auth
 * uses cookie-based sessions that don't need client-side refresh.
 */
export function RevalidateSession(): React.ReactElement | null {
  return null;
}
