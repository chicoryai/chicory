import type { LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';
import type { ActionFunctionArgs } from '@remix-run/node';

// S3 client singleton - works for both AWS S3 (cloud) and MinIO (local)
// When S3_ENDPOINT_URL is set, use custom endpoint with path-style access (MinIO)
// When not set, use standard AWS S3 with auto-loaded credentials (IAM role, env vars, etc.)
const s3Client = new S3Client({
  region: process.env.AWS_REGION || 'us-west-2',
  ...(process.env.S3_ENDPOINT_URL && {
    endpoint: process.env.S3_ENDPOINT_URL,
    forcePathStyle: true, // Required for MinIO/S3-compatible storage
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID || '',
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || '',
    },
  }),
});

import { auth } from "~/auth/auth.server";
import { fetchUserData } from "~/utils/propelauth.server";
import {
  getProjectsByOrgId,
  getProjectById,
  createAgent,
  getAgents,
  getAgent,
  updateAgent,
  deployAgent,
  getAgentTasks,
  getAgentTask,
  getAgentTools,
  getProjectDocumentation,
  getProjectTools,
  createEvaluation,
  getEvaluations,
  getEvaluation,
  deleteEvaluation,
  startEvaluationRun,
  getEvaluationRun,
  addTestCases,
  listEvaluationRuns,
  // Data source functions for MCP integration tools
  getDataSourceTypes,
  getProjectDataSources,
  createProjectDataSource,
  updateProjectDataSource,
  deleteProjectDataSource,
  testDataSourceConnection,
  validateDataSourceCredentials,
  getFolderFiles,
  getFolderFile,
  deleteFolderFile,
} from "~/services/chicory.server";

import {
  createPlayground,
  listPlaygrounds,
  createPlaygroundInvocation as createInvocation
} from "~/services/chicory-playground.server";

// Polling configuration for agent execution
// TODO: Make these configurable via environment variables or request parameters
const POLLING_CONFIG = {
  TASK_POLL_INTERVAL_MS: 5000,    // 5 seconds
  TASK_MAX_ATTEMPTS: 60,          // Total: 300 seconds (5 minutes)
};

// MCP Protocol Types
interface MCPRequest {
  jsonrpc: "2.0";
  id: string | number;
  method: string;
  params?: any;
}

interface MCPResponse {
  jsonrpc: "2.0";
  id: string | number;
  result?: any;
  error?: {
    code: number;
    message: string;
    data?: any;
  };
}

interface MCPTool {
  name: string;
  description: string;
  inputSchema: any;
}

/**
 * Create MCP-compliant response
 */
function createMCPResponse(id: string | number, result: any): MCPResponse {
  return {
    jsonrpc: "2.0",
    id,
    result
  };
}

/**
 * Create MCP-compliant error response
 */
function createMCPError(id: string | number, code: number, message: string, data?: any): MCPResponse {
  return {
    jsonrpc: "2.0",
    id,
    error: {
      code,
      message,
      data
    }
  };
}

/**
 * Validate that a project belongs to the user's organization
 */
async function validateProjectAccess(projectId: string, orgId: string): Promise<{
  valid: boolean;
  error?: string;
}> {
  try {
    const project = await getProjectById(projectId);
    
    if (!project) {
      return {
        valid: false,
        error: "Project not found"
      };
    }
    
    if (project.organization_id !== orgId) {
      return {
        valid: false,
        error: "Project does not belong to your organization"
      };
    }
    
    return { valid: true };
  } catch (error) {
    console.error("Error validating project access:", error);
    return {
      valid: false,
      error: "Failed to validate project access"
    };
  }
}

/**
 * Validate user API key and get user context
 */
async function validateUserApiKey(request: Request): Promise<{
  valid: boolean;
  error?: Response;
  userId?: string;
  orgId?: string;
}> {
  // HTTP headers are case-insensitive per RFC 2616, so we check both common casings
  // The regex replacement also uses case-insensitive flag for "Bearer" prefix
  const authHeader = request.headers.get("Authorization") || request.headers.get("authorization");
  const apiKey = authHeader?.replace(/^Bearer\s+/i, "");
  
  if (!apiKey) {
    return {
      valid: false,
      error: json(createMCPError("unknown", -32002, "Missing API key"))
    };
  }
  
  try {
    // Validate user API key with PropelAuth
    const validationResult = await auth.api.validateApiKey(apiKey);
    
    if (!validationResult?.user) {
      return {
        valid: false,
        error: json(createMCPError("unknown", -32002, "Invalid API key"))
      };
    }
    
    const userId = validationResult.user.userId;
    
    // Fetch user data to get organization info
    const userData = await fetchUserData(userId, true);
    
    if (!userData?.orgIdToOrgInfo) {
      return {
        valid: false,
        error: json(createMCPError("unknown", -32002, "User has no organization"))
      };
    }
    
    // Get user's organization
    // Note: Currently assumes single organization per user. If a user belongs to multiple
    // organizations, this will use the first one. Future enhancement: allow org selection
    // via request parameter or return error if multiple orgs exist.
    const orgIds = Object.keys(userData.orgIdToOrgInfo);
    const orgId = orgIds[0];
    
    if (!orgId) {
      return {
        valid: false,
        error: json(createMCPError("unknown", -32002, "User has no organization"))
      };
    }
    
    return { valid: true, userId, orgId };
    
  } catch (error) {
    console.error("Error validating API key:", error);
    return {
      valid: false,
      error: json(createMCPError("unknown", -32003, "API key validation failed"))
    };
  }
}

/**
 * Handle list_projects tool
 */
async function handleListProjects(
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    // Fetch all projects in the organization
    const projects = await getProjectsByOrgId(orgId);
    
    const projectList = projects.map(p => ({
      project_id: p.id,
      name: p.name,
      description: p.description || "",
      organization_id: orgId,
      created_at: p.created_at,
      updated_at: p.updated_at
    }));
    
    const resultText = JSON.stringify({
      projects: projectList,
      count: projectList.length,
      organization_id: orgId
    }, null, 2);
    
    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error listing projects: ${errorMessage}`);
  }
}

/**
 * Handle agent_create tool
 */
async function handleAgentCreate(
  args: any,
  userId: string,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, name, instructions, output_format, description } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required. Use 'chicory_list_projects' to see available projects.");
    }

    if (!name) {
      return createMCPError(requestId, -32602, "name is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const agent = await createAgent(
      project_id,
      name,
      description,
      userId,
      instructions || "You are a helpful assistant.",
      output_format
    );
    
    // Also create a default playground for the agent
    try {
      await createPlayground(project_id, agent.id, {
        name: 'Default Playground',
        description: 'Auto-created default playground'
      });
    } catch (playgroundError) {
      console.warn('Failed to create default playground:', playgroundError);
      // Continue even if playground creation fails
    }

    // Remove api_key from agent response
    const agentWithoutApiKey = 'api_key' in agent ? (() => {
      const { api_key, ...rest } = agent;
      return rest;
    })() : agent;
    const resultText = JSON.stringify({
      message: "Agent created successfully",
      agent: agentWithoutApiKey
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error creating agent: ${errorMessage}`);
  }
}

/**
 * Handle agent_list tool
 */
async function handleAgentList(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id } = args;
    
    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required. Use 'chicory_list_projects' to see available projects.");
    }
    
    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }
    
    const agents = await getAgents(project_id);

    // Remove api_key from agent responses
    const agentsWithoutApiKey = agents.map((agent: any) => {
      if ('api_key' in agent) {
        const { api_key, ...agentWithoutApiKey } = agent;
        return agentWithoutApiKey;
      }
      return agent;
    });
    
    const resultText = JSON.stringify({ agents: agentsWithoutApiKey, count: agentsWithoutApiKey.length }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error listing agents: ${errorMessage}`);
  }
}

/**
 * Handle agent_get tool
 */
async function handleAgentGet(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }
    
    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const agent = await getAgent(project_id, agent_id);
    
    if (!agent) {
      return createMCPError(requestId, -32602, `Agent not found: ${agent_id}`);
    }
    
    // Remove api_key from agent response
    const agentWithoutApiKey = 'api_key' in agent ? (() => {
      const { api_key, ...rest } = agent;
      return rest;
    })() : agent;
    const resultText = JSON.stringify(agentWithoutApiKey, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error getting agent: ${errorMessage}`);
  }
}

/**
 * Handle agent_update tool
 */
async function handleAgentUpdate(
  args: any,
  userId: string,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id, ...updates } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }

    if (!updates.name && !updates.description && !updates.instructions && !updates.output_format) {
      return createMCPError(requestId, -32602, "At least one field to update is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const agent = await updateAgent(
      project_id,
      agent_id,
      updates.name,
      updates.description,
      updates.instructions,
      updates.output_format,
      undefined, // deployed
      undefined, // api_key
      undefined, // state
      undefined, // capabilities
      undefined, // metadata
      userId // updated_by for version tracking
    );
    
    // Remove api_key from agent response
    const agentWithoutApiKey = 'api_key' in agent ? (() => {
      const { api_key, ...rest } = agent;
      return rest;
    })() : agent;
    const resultText = JSON.stringify({
      message: "Agent updated successfully",
      agent: agentWithoutApiKey
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error updating agent: ${errorMessage}`);
  }
}

/**
 * Handle agent_execute tool
 */
async function handleAgentExecute(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { 
      project_id,
      agent_id, 
      task_content, 
      metadata = {},
      wait_for_result = true,
      timeout_seconds = 300
    } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }
    
    if (!task_content) {
      return createMCPError(requestId, -32602, "task_content is required");
    }
    
    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    // Fetch the agent's playground
    const playgroundList = await listPlaygrounds(project_id, agent_id, 1);

    if (playgroundList.playgrounds.length === 0) {
      return createMCPError(requestId, -32602, `No playground found for agent ${agent_id}. Please create a playground first.`);
    }

    const playground_id = playgroundList.playgrounds[0].id;
    console.log('[platform-mcp] Using playground', playground_id, 'for agent', agent_id);

    // Create playground invocation
    const invocationData = await createInvocation(
      project_id,
      agent_id,
      playground_id,
      {
        content: task_content,
        metadata: metadata || {}
      }
    );
    const assistantTaskId = invocationData.assistant_task_id || '';

    if (!wait_for_result) {
      const resultText = JSON.stringify({
        message: "Task submitted successfully",
        invocation_id: invocationData.invocation_id,
        user_task_id: invocationData.user_task_id,
        assistant_task_id: assistantTaskId,
        status: "processing"
      }, null, 2);

      return createMCPResponse(requestId, {
        content: [{ type: "text", text: resultText }]
      });
    }

    // Poll for result
    const maxAttempts = Math.floor((timeout_seconds * 1000) / POLLING_CONFIG.TASK_POLL_INTERVAL_MS);
    let attempts = 0;
    let taskStatus = 'processing';
    let finalTask = null;

    console.log('[platform-mcp] Polling for task completion (max attempts):', maxAttempts);

    while ((taskStatus === 'processing' || taskStatus === 'queued') && attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, POLLING_CONFIG.TASK_POLL_INTERVAL_MS));

      try {
        const taskData = await getAgentTask(project_id, agent_id, assistantTaskId);

        if (taskData) {
          taskStatus = taskData.status || 'processing';
          finalTask = taskData;
          
          console.log('[platform-mcp] Poll attempt', attempts + 1, '/', maxAttempts, 'status:', taskStatus);
        }
      } catch (error) {
        console.error('[platform-mcp] Error polling task:', error);
      }

      attempts++;
    }

    if (taskStatus === 'completed' && finalTask) {
      const content = finalTask.content || "Task completed successfully";
      const resultText = JSON.stringify({
        task_id: assistantTaskId,
        status: "completed",
        content: content,
        completed_at: finalTask.completed_at || new Date().toISOString()
      }, null, 2);
      return createMCPResponse(requestId, {
        content: [{ type: "text", text: resultText }]
      });
    } else if (taskStatus === 'failed') {
      return createMCPError(requestId, -32603, finalTask?.response || "Task execution failed");
    } else {
      const resultText = JSON.stringify({
        message: "Task is still processing after timeout",
        invocation_id: invocationData.invocation_id,
        assistant_task_id: assistantTaskId,
        status: taskStatus,
        note: "Check task status later using the assistant_task_id"
      }, null, 2);

      return createMCPResponse(requestId, {
        content: [{ type: "text", text: resultText }]
      });
    }

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error executing agent: ${errorMessage}`);
  }
}

/**
 * Handle context_get tool
 */
async function handleContextGet(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id } = args;
    
    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }
    
    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }
    
    let contextData: any = {};
    
    // Get project.md documentation
    try {
      const projectDoc = await getProjectDocumentation(project_id);
      if (projectDoc) {
        contextData.project_documentation = projectDoc;
      }
    } catch (error) {
      console.warn('Failed to fetch project documentation:', error);
      // Continue even if project.md fetch fails
    }
    
    // Get MCP tools information
    try {
      const projectTools = await getProjectTools(project_id);
      
      if (projectTools.length > 0) {
        contextData.available_tools = {
          project_tools: projectTools,
          description: "MCP tools available at the project level (e.g., Jira, Looker, DBT)"
        };
      }

      // If agent_id is provided, also get agent-specific tools
      if (agent_id) {
        try {
          const agentTools = await getAgentTools(project_id, agent_id);
          
          if (agentTools.length > 0) {
            if (!contextData.available_tools) {
              contextData.available_tools = {};
            }
            contextData.available_tools.agent_tools = agentTools;
            contextData.available_tools.agent_tools_description = `MCP tools specific to agent ${agent_id}`;
          }
        } catch (agentToolsError) {
          console.warn('Failed to fetch agent tools:', agentToolsError);
          // Continue even if agent tools fetch fails
        }
      }
    } catch (error) {
      console.warn('Failed to fetch project tools:', error);
      // Continue even if tools fetch fails
    }
    
    const resultText = JSON.stringify(contextData, null, 2);
    
    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error retrieving project context: ${errorMessage}`);
  }
}

/**
 * Handle evaluation_create tool
 */
async function handleEvaluationCreate(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id, name, description, criteria, test_cases } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }

    if (!name) {
      return createMCPError(requestId, -32602, "name is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    // Convert test cases to CSV format
    let csvContent = '';
    if (test_cases && test_cases.length > 0) {
      csvContent = convertTestCasesToCSV(test_cases);
    }

    // Create FormData with evaluation details
    const formData = new FormData();
    formData.append("name", name);
    if (description) formData.append("description", description);
    if (criteria) formData.append("criteria", criteria);
    
    // Add CSV file if test cases provided
    if (csvContent) {
      const blob = new Blob([csvContent], { type: 'text/csv' });
      formData.append("csv_file", blob, "test_cases.csv");
    }

    const evaluation = await createEvaluation(project_id, agent_id, formData);

    const resultText = JSON.stringify({
      message: "Evaluation created successfully",
      evaluation
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error creating evaluation: ${errorMessage}`);
  }
}

/**
 * Handle evaluation_list tool
 */
async function handleEvaluationList(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id, limit = 10 } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const data = await getEvaluations(project_id, agent_id, { limit });
    const resultText = JSON.stringify(data, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error listing evaluations: ${errorMessage}`);
  }
}

/**
 * Handle evaluation_execute tool
 */
async function handleEvaluationExecute(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id, evaluation_id } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }

    if (!evaluation_id) {
      return createMCPError(requestId, -32602, "evaluation_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const run = await startEvaluationRun(project_id, agent_id, evaluation_id);

    const resultText = JSON.stringify({
      message: "Evaluation run started successfully",
      run
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error executing evaluation: ${errorMessage}`);
  }
}

/**
 * Handle add_test_cases tool
 */
async function handleAddTestCases(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id, evaluation_id, test_cases } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }

    if (!evaluation_id) {
      return createMCPError(requestId, -32602, "evaluation_id is required");
    }

    if (!test_cases || !Array.isArray(test_cases) || test_cases.length === 0) {
      return createMCPError(requestId, -32602, "test_cases array is required and must not be empty");
    }

    if (test_cases.length > 25) {
      return createMCPError(requestId, -32602, `Cannot add more than 25 test cases at once. Provided: ${test_cases.length}`);
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const addedTestCases = await addTestCases(project_id, agent_id, evaluation_id, test_cases);
    const resultText = JSON.stringify({
      message: `Successfully added ${test_cases.length} test case(s)`,
      test_cases: addedTestCases,
      count: addedTestCases.length
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error adding test cases: ${errorMessage}`);
  }
}

/**
 * Handle deploy_agent tool (enables the agent)
 */
async function handleDeployAgent(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const agent = await deployAgent(project_id, agent_id);
    
    const resultText = JSON.stringify({
      message: "Agent deployed successfully",
      agent: {
        id: agent.id,
        name: agent.name,
        state: agent.state,
        deployed: agent.deployed
      }
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error deploying agent: ${errorMessage}`);
  }
}

/**
 * Handle list_agent_tasks tool
 */
async function handleListAgentTasks(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id, limit = 50, skip = 0 } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const taskList = await getAgentTasks(project_id, agent_id, limit, 'desc', undefined, skip);
    
    // Remove sensitive metadata fields (S3 audit trail) while preserving other metadata
    const tasksWithoutSensitiveData = (taskList.tasks || []).map(task => {
      if (task.metadata && 'audit_trail' in task.metadata) {
        const { audit_trail, ...safeMetadata } = task.metadata;
        return { ...task, metadata: safeMetadata };
      }
      return task;
    });
    
    const resultText = JSON.stringify({
      tasks: tasksWithoutSensitiveData,
      count: tasksWithoutSensitiveData.length
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error listing agent tasks: ${errorMessage}`);
  }
}

/**
 * Handle get_agent_task tool
 * Always includes execution trail when available
 */
async function handleGetAgentTask(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id, task_id } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }

    if (!task_id) {
      return createMCPError(requestId, -32602, "task_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const task = await getAgentTask(project_id, agent_id, task_id);
    
    if (!task) {
      return createMCPError(requestId, -32602, `Task not found: ${task_id}`);
    }
    
    // Fetch the execution trail if available
    let executionTrail = null;
    let trailFetchStatus: 'success' | 'failed' | 'not_available' = 'not_available';
    
    if (task.metadata?.audit_trail) {
      try {
        const auditTrailUrl = task.metadata.audit_trail;
        
        if (auditTrailUrl.startsWith('s3://')) {
          const url = auditTrailUrl.replace('s3://', '');
          const [bucket, ...keyParts] = url.split('/');
          const key = keyParts.join('/');
          
          if (bucket && key) {
            const command = new GetObjectCommand({ Bucket: bucket, Key: key });
            const response = await s3Client.send(command);
            
            // Security: Limit size to 10MB to prevent memory issues
            const contentLength = response.ContentLength || 0;
            if (contentLength > 10 * 1024 * 1024) {
              console.error(`Execution trail too large: ${contentLength} bytes`);
              trailFetchStatus = 'failed';
            } else {
              const bodyString = await response.Body?.transformToString();

              if (bodyString) {
                const parsed = JSON.parse(bodyString);
                // Type validation: ensure it's an array
                if (Array.isArray(parsed)) {
                  executionTrail = parsed;
                  trailFetchStatus = 'success';
                } else {
                  console.warn('Invalid execution trail format: expected array');
                  trailFetchStatus = 'failed';
                }
              }
            }
          }
        }
      } catch (trailError) {
        // If trail fetch fails, just continue without it
        console.error('Failed to fetch execution trail:', trailError);
        trailFetchStatus = 'failed';
      }
    }
    
    // Remove metadata from response
    const { metadata, ...taskWithoutMetadata } = task;
    
    const result = {
      ...taskWithoutMetadata,
      execution_trail: executionTrail,
      trail_items_count: executionTrail?.length || 0,
      trail_fetch_status: trailFetchStatus
    };
    
    const resultText = JSON.stringify(result, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error getting agent task: ${errorMessage}`);
  }
}

/**
 * Handle get_evaluation tool
 */
async function handleGetEvaluation(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id, evaluation_id } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }

    if (!evaluation_id) {
      return createMCPError(requestId, -32602, "evaluation_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const evaluation = await getEvaluation(project_id, agent_id, evaluation_id);
    
    if (!evaluation) {
      return createMCPError(requestId, -32602, `Evaluation not found: ${evaluation_id}`);
    }
    
    const resultText = JSON.stringify(evaluation, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error getting evaluation: ${errorMessage}`);
  }
}

/**
 * Handle delete_evaluation tool
 */
async function handleDeleteEvaluation(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id, evaluation_id } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }

    if (!evaluation_id) {
      return createMCPError(requestId, -32602, "evaluation_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    await deleteEvaluation(project_id, agent_id, evaluation_id);

    const resultText = JSON.stringify({
      message: "Evaluation deleted successfully",
      evaluation_id
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error deleting evaluation: ${errorMessage}`);
  }
}

/**
 * Handle list_evaluation_runs tool
 */
async function handleListEvaluationRuns(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id, evaluation_id, limit = 10 } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }

    if (!evaluation_id) {
      return createMCPError(requestId, -32602, "evaluation_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const data = await listEvaluationRuns(project_id, agent_id, evaluation_id, limit);
    
    const resultText = JSON.stringify({
      runs: data.runs || [],
      total: data.total || 0,
      has_more: data.has_more || false
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error listing evaluation runs: ${errorMessage}`);
  }
}

/**
 * Handle get_evaluation_result tool
 */
async function handleGetEvaluationResult(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, agent_id, evaluation_id, run_id } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!agent_id) {
      return createMCPError(requestId, -32602, "agent_id is required");
    }

    if (!evaluation_id) {
      return createMCPError(requestId, -32602, "evaluation_id is required");
    }

    if (!run_id) {
      return createMCPError(requestId, -32602, "run_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const run = await getEvaluationRun(project_id, agent_id, evaluation_id, run_id);
    
    if (!run) {
      return createMCPError(requestId, -32602, `Evaluation run not found: ${run_id}`);
    }
    const resultText = JSON.stringify({
      run,
      summary: {
        status: run.status,
        total_test_cases: run.total_test_cases || 0,
        completed_test_cases: run.completed_test_cases || 0,
        failed_test_cases: run.failed_test_cases || 0,
        overall_score: run.overall_score || 0,
        started_at: run.started_at,
        completed_at: run.completed_at
      }
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error getting evaluation run result: ${errorMessage}`);
  }
}

// ============================================================================
// Data Source / Integration Management Handlers
// ============================================================================

/**
 * Handle listing data source types
 */
async function handleListDataSourceTypes(
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const types = await getDataSourceTypes();

    const resultText = JSON.stringify({
      message: "Available data source types",
      data_source_types: types
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error listing data source types: ${errorMessage}`);
  }
}

/**
 * Handle listing data sources in a project
 */
async function handleListDataSources(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const dataSources = await getProjectDataSources(project_id);

    // Mask sensitive fields in configuration
    const maskedDataSources = dataSources.map(ds => ({
      ...ds,
      configuration: maskSensitiveFields(ds.configuration)
    }));

    const resultText = JSON.stringify({
      project_id,
      data_sources: maskedDataSources,
      count: dataSources.length
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error listing data sources: ${errorMessage}`);
  }
}

/**
 * Handle getting a specific data source
 */
async function handleGetDataSource(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, data_source_id } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!data_source_id) {
      return createMCPError(requestId, -32602, "data_source_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const dataSources = await getProjectDataSources(project_id);
    const dataSource = dataSources.find(ds => ds.id === data_source_id);

    if (!dataSource) {
      return createMCPError(requestId, -32602, `Data source not found: ${data_source_id}`);
    }

    const resultText = JSON.stringify({
      data_source: {
        ...dataSource,
        configuration: maskSensitiveFields(dataSource.configuration)
      }
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error getting data source: ${errorMessage}`);
  }
}

/**
 * Handle creating a new data source
 */
async function handleCreateDataSource(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, type, name, configuration, validate_on_create = true } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!type) {
      return createMCPError(requestId, -32602, "type is required");
    }

    if (!name) {
      return createMCPError(requestId, -32602, "name is required");
    }

    if (!configuration) {
      return createMCPError(requestId, -32602, "configuration is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    // Optionally validate credentials first
    if (validate_on_create) {
      const validationResult = await validateDataSourceCredentials(type, configuration);
      if (!validationResult.success) {
        return createMCPError(requestId, -32602, `Credential validation failed: ${validationResult.message}`);
      }
    }

    // Create the data source
    const dataSource = await createProjectDataSource(project_id, type, name, configuration);

    const resultText = JSON.stringify({
      message: "Data source created successfully",
      data_source: {
        ...dataSource,
        configuration: maskSensitiveFields(dataSource.configuration)
      }
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error creating data source: ${errorMessage}`);
  }
}

/**
 * Handle updating a data source
 */
async function handleUpdateDataSource(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, data_source_id, name, configuration } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!data_source_id) {
      return createMCPError(requestId, -32602, "data_source_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const dataSource = await updateProjectDataSource(project_id, data_source_id, name, configuration);

    const resultText = JSON.stringify({
      message: "Data source updated successfully",
      data_source: {
        ...dataSource,
        configuration: maskSensitiveFields(dataSource.configuration)
      }
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error updating data source: ${errorMessage}`);
  }
}

/**
 * Handle deleting a data source
 */
async function handleDeleteDataSource(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, data_source_id } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!data_source_id) {
      return createMCPError(requestId, -32602, "data_source_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    await deleteProjectDataSource(project_id, data_source_id);

    const resultText = JSON.stringify({
      message: "Data source deleted successfully",
      data_source_id
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error deleting data source: ${errorMessage}`);
  }
}

/**
 * Handle validating data source credentials
 */
async function handleValidateCredentials(
  args: any,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { type, configuration } = args;

    if (!type) {
      return createMCPError(requestId, -32602, "type is required");
    }

    if (!configuration) {
      return createMCPError(requestId, -32602, "configuration is required");
    }

    const result = await validateDataSourceCredentials(type, configuration);

    const resultText = JSON.stringify({
      validation_result: result
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error validating credentials: ${errorMessage}`);
  }
}

/**
 * Handle testing connection to an existing data source
 */
async function handleTestConnection(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, data_source_id } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!data_source_id) {
      return createMCPError(requestId, -32602, "data_source_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const result = await testDataSourceConnection(project_id, data_source_id);

    const resultText = JSON.stringify({
      connection_test: result
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error testing connection: ${errorMessage}`);
  }
}

// ============================================================================
// Folder/File Management Handlers
// ============================================================================

/**
 * Handle listing files in a folder upload
 */
async function handleListFolderFiles(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, data_source_id, path, include_tree = true } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!data_source_id) {
      return createMCPError(requestId, -32602, "data_source_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const files = await getFolderFiles(project_id, data_source_id, path, include_tree);

    const resultText = JSON.stringify(files, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error listing folder files: ${errorMessage}`);
  }
}

/**
 * Handle getting a specific file from a folder upload
 */
async function handleGetFolderFile(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, data_source_id, file_id, download: includeDownloadUrl = true } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!data_source_id) {
      return createMCPError(requestId, -32602, "data_source_id is required");
    }

    if (!file_id) {
      return createMCPError(requestId, -32602, "file_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const file = await getFolderFile(project_id, data_source_id, file_id, includeDownloadUrl);

    const resultText = JSON.stringify(file, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error getting folder file: ${errorMessage}`);
  }
}

/**
 * Handle deleting a file from a folder upload
 */
async function handleDeleteFolderFile(
  args: any,
  orgId: string,
  requestId: string | number
): Promise<MCPResponse> {
  try {
    const { project_id, data_source_id, file_id } = args;

    if (!project_id) {
      return createMCPError(requestId, -32602, "project_id is required");
    }

    if (!data_source_id) {
      return createMCPError(requestId, -32602, "data_source_id is required");
    }

    if (!file_id) {
      return createMCPError(requestId, -32602, "file_id is required");
    }

    // Validate project access
    const projectAccess = await validateProjectAccess(project_id, orgId);
    if (!projectAccess.valid) {
      return createMCPError(requestId, -32602, projectAccess.error || "Access denied to project");
    }

    const result = await deleteFolderFile(project_id, data_source_id, file_id);

    const resultText = JSON.stringify({
      message: result.message,
      file_id
    }, null, 2);

    return createMCPResponse(requestId, {
      content: [{ type: "text", text: resultText }]
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(requestId, -32603, `Error deleting folder file: ${errorMessage}`);
  }
}

/**
 * Helper function to mask sensitive fields in configuration objects
 */
function maskSensitiveFields(configuration: Record<string, any>): Record<string, any> {
  const sensitiveFields = [
    'password', 'private_key', 'api_key', 'access_token', 'client_secret',
    'secret_key', 'auth_token', 'bearer_token', 'credentials', 'private_key_id'
  ];

  const masked = { ...configuration };
  for (const field of sensitiveFields) {
    if (masked[field]) {
      masked[field] = '********';
    }
  }
  return masked;
}

/**
 * Helper function to convert test cases array to CSV format
 * Implements RFC 4180 compliant CSV escaping
 */
function convertTestCasesToCSV(testCases: Array<{ task: string; expected_output: string; evaluation_guideline?: string }>): string {
  /**
   * Escape a CSV cell according to RFC 4180
   * - Wrap in quotes if contains: comma, quote, newline, or carriage return
   * - Escape internal quotes by doubling them
   */
  const escapeCell = (cell: string): string => {
    // Check if cell needs quoting (contains special characters)
    if (cell.includes(',') || cell.includes('"') || cell.includes('\n') || cell.includes('\r')) {
      // Escape quotes by doubling them, then wrap in quotes
      return `"${cell.replace(/"/g, '""')}"`;
    }
    return cell;
  };
  
  const headers = ['task', 'expected_output', 'evaluation_guideline'];
  const headerLine = headers.map(escapeCell).join(',');
  
  const dataLines = testCases.map(tc => {
    const row = [
      tc.task || '',
      tc.expected_output || '',
      tc.evaluation_guideline || ''
    ];
    return row.map(escapeCell).join(',');
  });
  
  // Use CRLF line endings per RFC 4180
  return [headerLine, ...dataLines].join('\r\n');
}

/**
 * GET /mcp/platform - Platform MCP server info
 */
export async function loader({ request }: LoaderFunctionArgs) {
  const { valid, error } = await validateUserApiKey(request);
  if (!valid) {
    return error || json({ error: "Access denied" }, { status: 403 });
  }

  return json({
    server: {
      name: "chicory-platform-mcp",
      version: "1.0.0",
      capabilities: { tools: {} }
    },
    description: "Chicory Platform MCP Server - Manage projects and agents"
  });
}

/**
 * POST /mcp/platform - MCP protocol handler
 */
export async function action({ request }: LoaderFunctionArgs) {
  const { valid, error, orgId, userId } = await validateUserApiKey(request);
  if (!valid) {
    return error || json({ 
      jsonrpc: "2.0", 
      id: null, 
      error: { code: -32002, message: "Access denied" } 
    });
  }

  const mcpRequest: MCPRequest = await request.json();

  switch (mcpRequest.method) {
    case "initialize":
      return json({
        jsonrpc: "2.0",
        id: mcpRequest.id,
        result: {
          protocolVersion: "2024-11-05",
          capabilities: { tools: {} },
          serverInfo: {
            name: "chicory-platform-mcp",
            version: "1.0.0"
          }
        }
      });

    case "tools/list":
      // Return all available tools (platform + project-scoped)
      return json(createMCPResponse(mcpRequest.id, {
        tools: [
          {
            name: "chicory_list_projects",
            description: "List all projects in your organization. Use this first to discover available project IDs.",
            inputSchema: { type: "object", properties: {}, required: [] }
          },
          {
            name: "chicory_create_agent",
            description: "Create a new agent with instructions (prompt) and output format in a specific project.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required - use chicory_list_projects to discover)" },
                name: { type: "string", description: "Agent name (required)" },
                instructions: { type: "string", description: "Agent instructions/system prompt" },
                output_format: { type: "string", description: "Expected output format (e.g., 'json', 'markdown', 'text')" },
                description: { type: "string", description: "Agent description" }
              },
              required: ["project_id", "name"]
            }
          },
          {
            name: "chicory_list_agents",
            description: "List all agents in a project. Returns full agent details (excluding api_key).",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" }
              },
              required: ["project_id"]
            }
          },
          {
            name: "chicory_get_agent",
            description: "Get details of a specific agent by ID.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "The ID of the agent to retrieve (required)" }
              },
              required: ["project_id", "agent_id"]
            }
          },
          {
            name: "chicory_update_agent",
            description: "Update an agent's configuration including instructions (prompt) and output format.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "The ID of the agent to update (required)" },
                instructions: { type: "string", description: "The agent's instructions/system prompt" },
                output_format: { type: "string", description: "Expected output format (e.g., 'json', 'markdown', 'text')" },
                name: { type: "string", description: "Agent name" },
                description: { type: "string", description: "Agent description" }
              },
              required: ["project_id", "agent_id"]
            }
          },
          {
            name: "chicory_execute_agent",
            description: "Execute an agent with a task via playground invocation. Automatically uses the agent's playground. Can optionally wait for the result.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "The ID of the agent to execute (required)" },
                task_content: { type: "string", description: "The task or prompt to execute (required)" },
                metadata: { type: "object", description: "Optional metadata for the invocation" },
                wait_for_result: { type: "boolean", description: "Whether to wait for task completion (default: true)", default: true },
                timeout_seconds: { type: "integer", description: "Maximum seconds to wait for result (default: 300)", default: 300, minimum: 1, maximum: 600 }
              },
              required: ["project_id", "agent_id", "task_content"]
            }
          },
          {
            name: "chicory_get_context",
            description: "Get comprehensive project context and available MCP tools (from data sources like Jira, Looker, DBT, etc.). Optionally include agent-specific tools.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "Optional: Agent ID to include agent-specific tools in addition to project-wide tools" }
              },
              required: ["project_id"]
            }
          },
          {
            name: "chicory_deploy_agent",
            description: "Deploy (enable) an agent to make it active and ready to use.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "Agent ID (required)" }
              },
              required: ["project_id", "agent_id"]
            }
          },
          {
            name: "chicory_list_agent_tasks",
            description: "List all tasks executed by an agent to monitor execution history.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "Agent ID (required)" },
                limit: { type: "integer", description: "Maximum number of tasks to return (default: 50)", default: 50 },
                skip: { type: "integer", description: "Number of tasks to skip for pagination (default: 0)", default: 0 }
              },
              required: ["project_id", "agent_id"]
            }
          },
          {
            name: "chicory_get_agent_task",
            description: "Get detailed information about a specific agent task including status, response, and errors. Optionally include the execution trail (step-by-step logs of tool calls, thinking, and results).",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "Agent ID (required)" },
                task_id: { type: "string", description: "Task ID (required)" },
                include_trail: { type: "boolean", description: "Include execution trail with step-by-step logs (default: false)", default: false }
              },
              required: ["project_id", "agent_id", "task_id"]
            }
          },
          {
            name: "chicory_create_evaluation",
            description: "Create a new evaluation for an agent with test cases.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "Agent ID (required)" },
                name: { type: "string", description: "Evaluation name (required)" },
                description: { type: "string", description: "Evaluation description" },
                criteria: { type: "string", description: "Evaluation criteria" },
                test_cases: {
                  type: "array",
                  description: "Array of test cases",
                  items: {
                    type: "object",
                    properties: {
                      task: { type: "string", description: "Task/input for the test case" },
                      expected_output: { type: "string", description: "Expected output" },
                      evaluation_guideline: { type: "string", description: "Guideline for evaluating this test case" }
                    },
                    required: ["task", "expected_output"]
                  }
                }
              },
              required: ["project_id", "agent_id", "name"]
            }
          },
          {
            name: "chicory_list_evaluations",
            description: "List all evaluations for an agent.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "Agent ID (required)" },
                limit: { type: "integer", description: "Maximum number of evaluations to return (default: 10)", default: 10 }
              },
              required: ["project_id", "agent_id"]
            }
          },
          {
            name: "chicory_execute_evaluation",
            description: "Execute an evaluation run for an agent. This will run all test cases and grade the results.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "Agent ID (required)" },
                evaluation_id: { type: "string", description: "Evaluation ID (required)" }
              },
              required: ["project_id", "agent_id", "evaluation_id"]
            }
          },
          {
            name: "chicory_get_evaluation_result",
            description: "Get the results of a completed evaluation run, including scores and test case results.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "Agent ID (required)" },
                evaluation_id: { type: "string", description: "Evaluation ID (required)" },
                run_id: { type: "string", description: "Evaluation run ID (required)" }
              },
              required: ["project_id", "agent_id", "evaluation_id", "run_id"]
            }
          },
          {
            name: "chicory_add_evaluation_test_cases",
            description: "Add one or more test cases to an existing evaluation.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "Agent ID (required)" },
                evaluation_id: { type: "string", description: "Evaluation ID (required)" },
                test_cases: {
                  type: "array",
                  description: "Array of test cases to add",
                  items: {
                    type: "object",
                    properties: {
                      task: { type: "string", description: "Task/input for the test case" },
                      expected_output: { type: "string", description: "Expected output" },
                      evaluation_guideline: { type: "string", description: "Guideline for evaluating this test case" },
                      metadata: { type: "object", description: "Optional metadata" }
                    },
                    required: ["task", "expected_output"]
                  }
                }
              },
              required: ["project_id", "agent_id", "evaluation_id", "test_cases"]
            }
          },
          {
            name: "chicory_get_evaluation",
            description: "Get detailed information about a specific evaluation including test cases and metadata.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "Agent ID (required)" },
                evaluation_id: { type: "string", description: "Evaluation ID (required)" }
              },
              required: ["project_id", "agent_id", "evaluation_id"]
            }
          },
          {
            name: "chicory_delete_evaluation",
            description: "Delete an evaluation and all its associated data.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "Agent ID (required)" },
                evaluation_id: { type: "string", description: "Evaluation ID (required)" }
              },
              required: ["project_id", "agent_id", "evaluation_id"]
            }
          },
          {
            name: "chicory_list_evaluation_runs",
            description: "List all runs for a specific evaluation to track evaluation history.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                agent_id: { type: "string", description: "Agent ID (required)" },
                evaluation_id: { type: "string", description: "Evaluation ID (required)" },
                limit: { type: "integer", description: "Maximum number of runs to return (default: 10)", default: 10 }
              },
              required: ["project_id", "agent_id", "evaluation_id"]
            }
          },
          // Data Source / Integration Management Tools
          {
            name: "chicory_list_data_source_types",
            description: "List all available data source/integration types with their required credential fields. Use this to discover what integrations are supported.",
            inputSchema: {
              type: "object",
              properties: {},
              required: []
            }
          },
          {
            name: "chicory_list_data_sources",
            description: "List all connected data sources/integrations in a project.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" }
              },
              required: ["project_id"]
            }
          },
          {
            name: "chicory_get_data_source",
            description: "Get details of a specific data source/integration by ID.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                data_source_id: { type: "string", description: "Data source ID (required)" }
              },
              required: ["project_id", "data_source_id"]
            }
          },
          {
            name: "chicory_create_data_source",
            description: "Create a new data source/integration with credentials. Supports all integration types including BigQuery, Snowflake, GitHub, S3, etc. Use chicory_list_data_source_types to see required fields for each type.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                type: { type: "string", description: "Data source type (e.g., 'bigquery', 'snowflake', 'github', 'databricks', 's3') (required)" },
                name: { type: "string", description: "Display name for the data source (required)" },
                configuration: { type: "object", description: "Configuration object with credentials - structure depends on type. Use chicory_list_data_source_types to see required fields." },
                validate_on_create: { type: "boolean", description: "Whether to validate credentials before creating (default: true)", default: true }
              },
              required: ["project_id", "type", "name", "configuration"]
            }
          },
          {
            name: "chicory_update_data_source",
            description: "Update an existing data source/integration configuration.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                data_source_id: { type: "string", description: "Data source ID (required)" },
                name: { type: "string", description: "New display name" },
                configuration: { type: "object", description: "Updated configuration object" }
              },
              required: ["project_id", "data_source_id"]
            }
          },
          {
            name: "chicory_delete_data_source",
            description: "Delete a data source/integration from a project.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                data_source_id: { type: "string", description: "Data source ID (required)" }
              },
              required: ["project_id", "data_source_id"]
            }
          },
          {
            name: "chicory_validate_credentials",
            description: "Validate data source credentials before creating a connection. Returns validation status and any error messages.",
            inputSchema: {
              type: "object",
              properties: {
                type: { type: "string", description: "Data source type (required)" },
                configuration: { type: "object", description: "Configuration/credentials to validate (required)" }
              },
              required: ["type", "configuration"]
            }
          },
          {
            name: "chicory_test_connection",
            description: "Test the connection to an existing data source to verify it is working.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                data_source_id: { type: "string", description: "Data source ID (required)" }
              },
              required: ["project_id", "data_source_id"]
            }
          },
          // Folder/File Management Tools
          {
            name: "chicory_list_folder_files",
            description: "List files in a folder upload data source. Returns file hierarchy with paths, sizes, and types.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                data_source_id: { type: "string", description: "Data source ID of a folder upload (required)" },
                path: { type: "string", description: "Optional path filter to list files in a specific directory" },
                include_tree: { type: "boolean", description: "Include tree structure for file browser (default: true)", default: true }
              },
              required: ["project_id", "data_source_id"]
            }
          },
          {
            name: "chicory_get_folder_file",
            description: "Get details and download URL for a specific file in a folder upload.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                data_source_id: { type: "string", description: "Data source ID (required)" },
                file_id: { type: "string", description: "File ID (required)" },
                download: { type: "boolean", description: "Generate download URL (default: true)", default: true }
              },
              required: ["project_id", "data_source_id", "file_id"]
            }
          },
          {
            name: "chicory_delete_folder_file",
            description: "Delete a specific file from a folder upload data source.",
            inputSchema: {
              type: "object",
              properties: {
                project_id: { type: "string", description: "Project ID (required)" },
                data_source_id: { type: "string", description: "Data source ID (required)" },
                file_id: { type: "string", description: "File ID (required)" }
              },
              required: ["project_id", "data_source_id", "file_id"]
            }
          }
        ]
      }));
    
    case "tools/call":
      const { name: toolName, arguments: toolArgs } = mcpRequest.params;
      
      console.log('[platform-mcp] Tool call:', toolName, toolArgs);
      
      switch (toolName) {
        case "chicory_list_projects":
          return json(await handleListProjects(orgId!, mcpRequest.id));
        
        case "chicory_create_agent":
          return json(await handleAgentCreate(toolArgs, userId!, orgId!, mcpRequest.id));
        
        case "chicory_list_agents":
          return json(await handleAgentList(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_get_agent":
          return json(await handleAgentGet(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_update_agent":
          return json(await handleAgentUpdate(toolArgs, userId!, orgId!, mcpRequest.id));
        
        case "chicory_execute_agent":
          return json(await handleAgentExecute(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_get_context":
          return json(await handleContextGet(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_deploy_agent":
          return json(await handleDeployAgent(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_list_agent_tasks":
          return json(await handleListAgentTasks(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_get_agent_task":
          return json(await handleGetAgentTask(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_create_evaluation":
          return json(await handleEvaluationCreate(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_list_evaluations":
          return json(await handleEvaluationList(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_execute_evaluation":
          return json(await handleEvaluationExecute(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_get_evaluation_result":
          return json(await handleGetEvaluationResult(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_add_evaluation_test_cases":
          return json(await handleAddTestCases(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_get_evaluation":
          return json(await handleGetEvaluation(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_delete_evaluation":
          return json(await handleDeleteEvaluation(toolArgs, orgId!, mcpRequest.id));
        
        case "chicory_list_evaluation_runs":
          return json(await handleListEvaluationRuns(toolArgs, orgId!, mcpRequest.id));

        // Data Source / Integration Management Tools
        case "chicory_list_data_source_types":
          return json(await handleListDataSourceTypes(mcpRequest.id));

        case "chicory_list_data_sources":
          return json(await handleListDataSources(toolArgs, orgId!, mcpRequest.id));

        case "chicory_get_data_source":
          return json(await handleGetDataSource(toolArgs, orgId!, mcpRequest.id));

        case "chicory_create_data_source":
          return json(await handleCreateDataSource(toolArgs, orgId!, mcpRequest.id));

        case "chicory_update_data_source":
          return json(await handleUpdateDataSource(toolArgs, orgId!, mcpRequest.id));

        case "chicory_delete_data_source":
          return json(await handleDeleteDataSource(toolArgs, orgId!, mcpRequest.id));

        case "chicory_validate_credentials":
          return json(await handleValidateCredentials(toolArgs, mcpRequest.id));

        case "chicory_test_connection":
          return json(await handleTestConnection(toolArgs, orgId!, mcpRequest.id));

        // Folder/File Management Tools
        case "chicory_list_folder_files":
          return json(await handleListFolderFiles(toolArgs, orgId!, mcpRequest.id));

        case "chicory_get_folder_file":
          return json(await handleGetFolderFile(toolArgs, orgId!, mcpRequest.id));

        case "chicory_delete_folder_file":
          return json(await handleDeleteFolderFile(toolArgs, orgId!, mcpRequest.id));

        default:
          return json(createMCPError(mcpRequest.id, -32601, `Tool not found: ${toolName}`));
      }
    
    default:
      return json(createMCPError(mcpRequest.id, -32601, "Method not found"));
  }
}
