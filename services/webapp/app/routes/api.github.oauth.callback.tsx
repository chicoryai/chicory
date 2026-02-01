/**
 * GitHub OAuth Callback Handler (Server-Side)
 *
 * This route handles the complete OAuth flow on the server side.
 * No need for separate backend API call - we do everything here!
 *
 * Flow:
 * 1. GitHub redirects here with code and state parameters
 * 2. Exchange code for token (using GitHub App client secret)
 * 3. Get user info from GitHub
 * 4. Call backend API to store the data source
 * 5. Redirect user back to integrations page
 */

import type { LoaderFunctionArgs } from "@remix-run/node";
import { redirect } from "@remix-run/node";

// Environment variables (set these in webapp .env)
const GITHUB_APP_CLIENT_ID = process.env.GITHUB_APP_CLIENT_ID;
const GITHUB_APP_CLIENT_SECRET = process.env.GITHUB_APP_CLIENT_SECRET;
const BACKEND_API_URL = process.env.CHICORY_API_URL;

/**
 * Exchange OAuth code for access token
 * This happens on the server side, so client secret is safe
 */
async function exchangeCodeForToken(code: string): Promise<{
  access_token: string;
  token_type: string;
  scope: string;
}> {
  const response = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      client_id: GITHUB_APP_CLIENT_ID,
      client_secret: GITHUB_APP_CLIENT_SECRET,
      code: code,
    }),
  });

  if (!response.ok) {
    throw new Error(`GitHub token exchange failed: ${response.statusText}`);
  }

  const data = await response.json();

  if (data.error) {
    throw new Error(data.error_description || data.error);
  }

  return data;
}

/**
 * Get GitHub user information
 */
async function getGitHubUser(accessToken: string): Promise<{
  login: string;
  email: string | null;
  name: string | null;
  avatar_url: string;
  id: number;
}> {
  const response = await fetch("https://api.github.com/user", {
    headers: {
      Authorization: `token ${accessToken}`,
      Accept: "application/vnd.github+json",
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to get user info: ${response.statusText}`);
  }

  return response.json();
}

export async function loader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url);

  // Extract OAuth response parameters
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const error = url.searchParams.get("error");
  const errorDescription = url.searchParams.get("error_description");

  // Parse state parameter to get project_id
  let projectId: string | null = null;
  if (state) {
    try {
      const stateParams = new URLSearchParams(state);
      projectId = stateParams.get("project_id");
    } catch (e) {
      console.error("Failed to parse state parameter:", e);
    }
  }

  // Default redirect URL
  const defaultRedirect = projectId
    ? `/projects/${projectId}/integrations`
    : "/integrations";

  // Handle OAuth errors (user denied access, etc.)
  if (error) {
    console.error("GitHub OAuth error:", error, errorDescription);
    const errorMessage =
      errorDescription || error || "GitHub authorization failed";
    return redirect(
      `${defaultRedirect}?error=github_oauth_failed&message=${encodeURIComponent(
        errorMessage
      )}`
    );
  }

  // No code means something went wrong
  if (!code) {
    console.error("No OAuth code received");
    return redirect(
      `${defaultRedirect}?error=github_oauth_failed&message=${encodeURIComponent(
        "No authorization code received"
      )}`
    );
  }

  // Check if GitHub App is configured
  if (!GITHUB_APP_CLIENT_ID || !GITHUB_APP_CLIENT_SECRET) {
    console.error("GitHub App not configured");
    return redirect(
      `${defaultRedirect}?error=github_oauth_failed&message=${encodeURIComponent(
        "GitHub App is not configured"
      )}`
    );
  }

  try {
    // Step 1: Exchange code for token (happens on server, client secret is safe!)
    console.log("Exchanging OAuth code for access token...");
    const tokenData = await exchangeCodeForToken(code);

    if (!tokenData.access_token) {
      throw new Error("No access token received from GitHub");
    }

    console.log("Successfully obtained access token");

    // Step 2: Get user information
    console.log("Fetching user information from GitHub...");
    const userInfo = await getGitHubUser(tokenData.access_token);

    console.log("Successfully obtained user info:", userInfo.login);

    // Step 3: Store the data source (if project_id is provided)
    if (projectId) {
      console.log("Creating GitHub data source for project:", projectId);

      const dataSourceResponse = await fetch(
        `${BACKEND_API_URL}/projects/${projectId}/data-sources`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            type: "github",
            name: `GitHub (${userInfo.login})`,
            configuration: {
              access_token: tokenData.access_token,
              username: userInfo.login,
              email: userInfo.email,
              avatar_url: userInfo.avatar_url,
              scope: tokenData.scope,
              auth_method: "oauth",
            },
          }),
        }
      );

      if (!dataSourceResponse.ok) {
        const errorData = await dataSourceResponse.json().catch(() => ({}));
        throw new Error(errorData.message || "Failed to create data source");
      }

      console.log("Successfully created GitHub data source");
    }

    // Step 4: Redirect back with success message
    const successParams = new URLSearchParams({
      success: "github_connected",
      username: userInfo.login || "",
    });

    return redirect(`${defaultRedirect}?${successParams.toString()}`);
  } catch (error) {
    console.error("OAuth callback error:", error);
    const errorMessage =
      error instanceof Error
        ? error.message
        : "Failed to connect GitHub account";
    return redirect(
      `${defaultRedirect}?error=github_oauth_failed&message=${encodeURIComponent(
        errorMessage
      )}`
    );
  }
}
