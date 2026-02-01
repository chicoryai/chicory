/**
 * JIRA OAuth Callback Handler (Server-Side)
 *
 * This route handles the complete OAuth flow on the server side.
 * No need for separate backend API call - we do everything here!
 *
 * Flow:
 * 1. Atlassian redirects here with code and state parameters
 * 2. Exchange code for access token (using JIRA client secret)
 * 3. Get accessible resources (Jira Cloud sites)
 * 4. Get user info from Jira
 * 5. Call backend API to store the data source
 * 6. Redirect user back to integrations page
 */

import type { LoaderFunctionArgs } from "@remix-run/node";
import { redirect } from "@remix-run/node";

// Environment variables (set these in webapp .env)
const JIRA_CLIENT_ID = process.env.JIRA_CLIENT_ID;
const JIRA_CLIENT_SECRET = process.env.JIRA_CLIENT_SECRET;
const JIRA_OAUTH_REDIRECT_URI = process.env.JIRA_OAUTH_REDIRECT_URI;
const BACKEND_API_URL = process.env.CHICORY_API_URL;

/**
 * Exchange OAuth code for access token
 * This happens on the server side, so client secret is safe
 */
async function exchangeCodeForToken(code: string): Promise<{
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  scope: string;
}> {
  const response = await fetch("https://auth.atlassian.com/oauth/token", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      grant_type: "authorization_code",
      client_id: JIRA_CLIENT_ID,
      client_secret: JIRA_CLIENT_SECRET,
      code: code,
      redirect_uri: JIRA_OAUTH_REDIRECT_URI,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Atlassian token exchange failed: ${response.statusText} - ${errorText}`);
  }

  const data = await response.json();

  if (data.error) {
    throw new Error(data.error_description || data.error);
  }

  return data;
}

/**
 * Get accessible Jira resources (Cloud sites)
 */
async function getAccessibleResources(accessToken: string): Promise<
  Array<{
    id: string;
    name: string;
    url: string;
    scopes: string[];
    avatarUrl: string;
  }>
> {
  const response = await fetch(
    "https://api.atlassian.com/oauth/token/accessible-resources",
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        Accept: "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to get accessible resources: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get Jira user information
 */
async function getJiraUser(
  accessToken: string,
  cloudId: string
): Promise<{
  accountId: string;
  emailAddress: string;
  displayName: string;
  avatarUrls: {
    "48x48": string;
    "24x24": string;
    "16x16": string;
    "32x32": string;
  };
  locale: string;
  timeZone: string;
}> {
  const response = await fetch(
    `https://api.atlassian.com/ex/jira/${cloudId}/rest/api/3/myself`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        Accept: "application/json",
      },
    }
  );

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
    console.error("JIRA OAuth error:", error, errorDescription);
    const errorMessage =
      errorDescription || error || "JIRA authorization failed";
    return redirect(
      `${defaultRedirect}?error=jira_oauth_failed&message=${encodeURIComponent(
        errorMessage
      )}`
    );
  }

  // No code means something went wrong
  if (!code) {
    console.error("No OAuth code received");
    return redirect(
      `${defaultRedirect}?error=jira_oauth_failed&message=${encodeURIComponent(
        "No authorization code received"
      )}`
    );
  }

  // Check if JIRA OAuth is configured
  if (!JIRA_CLIENT_ID || !JIRA_CLIENT_SECRET || !JIRA_OAUTH_REDIRECT_URI) {
    console.error("JIRA OAuth not configured");
    return redirect(
      `${defaultRedirect}?error=jira_oauth_failed&message=${encodeURIComponent(
        "JIRA OAuth is not configured"
      )}`
    );
  }

  try {
    // Step 1: Exchange code for token (happens on server, client secret is safe!)
    console.log("Exchanging OAuth code for access token...");
    const tokenData = await exchangeCodeForToken(code);

    if (!tokenData.access_token) {
      throw new Error("No access token received from Atlassian");
    }

    console.log("Successfully obtained access token");

    // Step 2: Get accessible resources (Jira Cloud sites)
    console.log("Fetching accessible Jira resources...");
    const resources = await getAccessibleResources(tokenData.access_token);

    if (!resources || resources.length === 0) {
      throw new Error("No accessible Jira sites found");
    }

    // Use the first accessible resource (in production, you might want to let user choose)
    const jiraSite = resources[0];
    console.log("Using Jira site:", jiraSite.name, jiraSite.url);

    // Step 3: Get user information
    console.log("Fetching user information from Jira...");
    const userInfo = await getJiraUser(tokenData.access_token, jiraSite.id);

    console.log("Successfully obtained user info:", userInfo.displayName);

    // Step 4: Store the data source (if project_id is provided)
    if (projectId) {
      console.log("Creating Jira data source for project:", projectId);

      const dataSourceResponse = await fetch(
        `${BACKEND_API_URL}/projects/${projectId}/data-sources`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            type: "jira",
            name: `Jira`,
            configuration: {
              access_token: tokenData.access_token,
              refresh_token: tokenData.refresh_token,
              cloud_id: jiraSite.id,
              site_name: jiraSite.name,
              site_url: jiraSite.url,
              account_id: userInfo.accountId,
              email: userInfo.emailAddress,
              display_name: userInfo.displayName,
              avatar_url: userInfo.avatarUrls["48x48"],
              scope: tokenData.scope,
              expires_in: tokenData.expires_in,
              auth_method: "oauth",
            },
          }),
        }
      );

      if (!dataSourceResponse.ok) {
        const errorData = await dataSourceResponse.json().catch(() => ({}));
        throw new Error(errorData.message || "Failed to create data source");
      }

      console.log("Successfully created Jira data source");
    }

    // Step 5: Redirect back with success message
    const successParams = new URLSearchParams({
      success: "jira_connected",
      site_name: jiraSite.name || "",
      display_name: userInfo.displayName || "",
    });

    return redirect(`${defaultRedirect}?${successParams.toString()}`);
  } catch (error) {
    console.error("OAuth callback error:", error);
    const errorMessage =
      error instanceof Error
        ? error.message
        : "Failed to connect Jira account";
    return redirect(
      `${defaultRedirect}?error=jira_oauth_failed&message=${encodeURIComponent(
        errorMessage
      )}`
    );
  }
}
