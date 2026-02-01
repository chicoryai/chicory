import type { LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { validateApiKeyFromRequest } from "~/utils/propelauth.server";
import { getProjectsByOrgId, getAgent } from "~/services/chicory.server";
import { getAgentTask } from "~/services/chicory.server";

/**
 * ACP-compliant endpoint for getting a run
 * GET /api/v1/projects/:projectId/runs/:runId - Read state of a run
 */
export async function loader({ request, params }: LoaderFunctionArgs) {
  // Extract the run ID from the URL parameters
  const runId = params.runId;
  const projectId = params.projectId;
  if (!runId) {
    return json(
      {
        code: "invalid_input",
        message: "Run ID is required"
      },
      { status: 400 }
    );
  }

  if (!projectId) {
    return json(
      {
        code: "invalid_input",
        message: "Project ID is required"
      },
      { status: 400 }
    );
  }
  try {
    // Step 1: Validate the API key with PropelAuth first
    const validationResult = await validateApiKeyFromRequest(request);

    if (!validationResult || !validationResult.org) {
      return json(
        {
          code: "invalid_input",
          message: "Invalid or missing API key"
        },
        { status: 401 }
      );
    }
    
    // Verify project exists in organization
    const projects = await getProjectsByOrgId(validationResult.org.orgId);
    const projectExists = projects.some(p => p.id === projectId);
    
    if (!projectExists) {
      return json(
        {
          code: "invalid_input",
          message: "Project not found or access denied"
        },
        { status: 404 }
      );
    }
    
    console.log(validationResult);
    const agentId = validationResult.metadata?.agent_id;
    
    // Get the task from the Chicory backend
    const task = await getAgentTask(projectId, agentId, runId);
    console.log(task);

    if (!task) {
      return json(
        {
          code: "not_found",
          message: "Run not found"
        },
        { status: 404 }
      );
    }
    
    // Step 2: Get the agent and check if API key matches
    if (task.agent_id) {
      const agent = await getAgent(projectId, task.agent_id);
      
      // If agent has an API key, verify it matches the request
      if (agent && agent.api_key) {
        const authHeader = request.headers.get("Authorization") || request.headers.get("authorization");
        const requestApiKey = authHeader?.replace(/^Bearer\s+/i, "");
        
        if (!requestApiKey || requestApiKey !== agent.api_key) {
          return json(
            {
              code: "invalid_input",
              message: "API key does not match agent"
            },
            { status: 401 }
          );
        }
      }
    }

    // Map the task to an ACP-compliant run response
    const response = {
      agent_name: task.agent_id, // Using agent_id as agent_name
      run_id: task.id,
      session_id: task.agent_id, // Use session_id from metadata if available
      status: mapTaskStatusToRunStatus(task.status || 'queued'),
      output: task.content ? [
        {
          parts: [
            {
              content_type: "text/plain",
              content: task.content
            }
          ],
          created_at: task.created_at
        }
      ] : [],
      created_at: task.created_at,
      finished_at: task.completed_at || undefined
    };

    return json(response, { status: 200 });
  } catch (error) {
    console.error("Error getting run:", error);
    return json(
      {
        code: "server_error",
        message: "Failed to get run"
      },
      { status: 500 }
    );
  }
}

/**
 * Maps Chicory task status to ACP run status
 */
function mapTaskStatusToRunStatus(taskStatus: string): string {
  switch (taskStatus) {
    case "queued":
      return "created";
    case "processing":
      return "in-progress";
    case "completed":
      return "completed";
    case "failed":
      return "failed";
    default:
      return "created";
  }
}
