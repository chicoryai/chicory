/**
 * JIRA OAuth Configuration Endpoint
 *
 * Returns the client_id and OAuth URL for the frontend.
 * Does NOT expose client_secret.
 */

import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";

const JIRA_CLIENT_ID = process.env.JIRA_CLIENT_ID;

export async function loader({ request }: LoaderFunctionArgs) {
  if (!JIRA_CLIENT_ID) {
    return json(
      {
        configured: false,
        error: 'JIRA OAuth is not configured'
      },
      { status: 500 }
    );
  }
  const scopes = [
    "offline_access",                    // Required for refresh tokens
    "read:jira-user",                   // User information
    "read:jira-work",                   // Issues and projects
    "write:jira-work", 
    "manage:jira-project", 
    "read:project:jira",                // Create/edit issues
    "read:board-scope:jira-software",   // View boards and backlogs
    "read:sprint:jira-software",        // View sprints
    "write:board-scope:jira-software",  // Move issues to/from backlog
    "write:sprint:jira-software",
    "read:comment:jira",      // For getting comments
    "write:comment:jira",     // For adding comments
    "write:attachment:jira",  // For uploading attachments
    "read:field:jira"         // Update sprints
  ];
  return json({
    configured: true,
    client_id: JIRA_CLIENT_ID,
    scopes: scopes.join(" "),
    // Atlassian OAuth 2.0 authorization endpoint
    authorization_url: 'https://auth.atlassian.com/authorize',
  });
}
