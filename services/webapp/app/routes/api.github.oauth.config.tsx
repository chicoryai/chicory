/**
 * GitHub OAuth Configuration Endpoint
 *
 * Returns the client_id and OAuth URL for the frontend.
 * Does NOT expose client_secret.
 */

import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";

const GITHUB_APP_CLIENT_ID = process.env.GITHUB_APP_CLIENT_ID;
const GITHUB_APP_SLUG_NAME = process.env.GITHUB_APP_SLUG_NAME || 'chicoryai';

export async function loader({ request }: LoaderFunctionArgs) {
  if (!GITHUB_APP_CLIENT_ID) {
    return json(
      {
        configured: false,
        error: 'GitHub App is not configured'
      },
      { status: 500 }
    );
  }

  return json({
    configured: true,
    client_id: GITHUB_APP_CLIENT_ID,
    // Use GitHub App installation URL to allow org-level installation
    authorization_url: `https://github.com/apps/${GITHUB_APP_SLUG_NAME}/installations/new`,
  });
}
