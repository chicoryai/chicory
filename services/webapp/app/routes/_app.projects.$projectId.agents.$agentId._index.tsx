/**
 * Default Index Route for Agent
 * Redirects to the playground route which is the default Build view
 */

import { redirect } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";

export async function loader({ params }: LoaderFunctionArgs) {
  const { agentId, projectId } = params;

  if (!agentId || !projectId) {
    throw new Response("Agent ID and Project ID are required", { status: 400 });
  }

  // Redirect to the playground route
  return redirect(`/projects/${projectId}/agents/${agentId}/playground`);
}

// No component needed since we always redirect
export default function AgentIndexRedirect() {
  return null;
}
