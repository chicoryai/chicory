import type { ActionFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { validateApiKeyFromRequest } from "~/utils/propelauth.server";
import { getUserOrgDetails } from "~/auth/auth.server";
import { createAgentTask, getAgent } from "~/services/chicory.server";
import { getProjectsByOrgId } from "~/services/chicory.server";
import { v4 as uuidv4 } from "uuid";
/**
 * ACP-compliant endpoint for creating a run
 * POST /api/v1/projects/:projectId/runs - Creates a new run for an agent
 */
export async function action({ request, params }: ActionFunctionArgs) {
  // Only allow POST requests
  if (request.method !== "POST") {
    return json(
      {
        code: "invalid_input",
        message: "Method not allowed"
      },
      { status: 405 }
    );
  }

  const projectId = params.projectId;

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

    // Parse request body
    const body = await request.json();

    // Validate required fields according to ACP spec
    if (!body.agent_name || !body.input || !Array.isArray(body.input)) {
      return json(
        {
          code: "invalid_input",
          message: "agent_name and input array are required"
        },
        { status: 400 }
      );
    }

    // Generate a run ID
    const runId = uuidv4();

    // Extract session ID if provided, or generate a new one
    const sessionId = body.session_id || uuidv4();

    // Get the first message content from the input
    const firstMessage = body.input[0];
    if (!firstMessage || !firstMessage.parts || !firstMessage.parts.length) {
      return json(
        {
          code: "invalid_input",
          message: "Input must contain at least one message with parts"
        },
        { status: 400 }
      );
    }

    // Extract the content from the first part of the first message
    const content = firstMessage.parts[0].content;
    const metadata = {request_source: "api"};
    
    // Step 2: Get the agent and check if API key matches
    const agent = await getAgent(projectId, body.agent_name);
    if (!agent) {
      return json(
        {
          code: "invalid_input",
          message: "Agent not found"
        },
        { status: 404 }
      );
    }
    
    // If agent has an API key, verify it matches the request
    if (agent.api_key) {
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
    
    // Create a task in the Chicory backend
    const result = await createAgentTask(projectId, body.agent_name, content, metadata);
    console.log("Task created successfully:", result);

    // Prepare the response according to ACP spec
    const response = {
      agent_name: body.agent_name,
      run_id: result.related_task_id,
      session_id: body.agent_name,
      status: "created",
      output: [],
      created_at: new Date().toISOString()
    };

    // Return appropriate status code based on the requested mode
    const mode = body.mode || "sync";
    if (mode === "async" || mode === "stream") {
      return json(response, { status: 202 });
    }

    return json(response, { status: 200 });
  } catch (error) {
    console.error("Error creating run:", error);
    return json(
      {
        code: "server_error",
        message: "Failed to create run"
      },
      { status: 500 }
    );
  }
}
