/**
 * Playground Index Route
 * Redirects to configure route to show system instructions sidebar by default
 * unless user explicitly closed it
 */

import { redirect } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";

export async function loader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url);

  // Check if user explicitly wants sidebar closed (via ?closed=true param)
  const isClosed = url.searchParams.get('closed') === 'true';

  if (isClosed) {
    // User explicitly closed sidebar, stay on index route
    return null;
  }

  // Default: redirect to configure route to show system instructions sidebar
  return redirect(`${url.pathname}/configure${url.search}`);
}

export default function PlaygroundIndex() {
  // This component renders when user explicitly closes the sidebar
  return null;
}
