import type { LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { validateApiKeyFromRequest } from "~/utils/propelauth.server";
import { 
  getProjectsByOrgId,
  getMcpGateway, 
  getMcpGatewayTools,
  createMcpToolInvocation,
  getMcpInvocationStatus,
  getAgentTask
} from "~/services/chicory.server";

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

// Polling configuration to stay under HTTP gateway timeout (120 seconds)
const POLLING_CONFIG = {
  // For getting assistant_task_id from invocation
  INVOCATION_POLL_INTERVAL_MS: 3000,        // 3 seconds
  INVOCATION_MAX_ATTEMPTS: 6,                // Total: 18 seconds

  // For polling task completion status
  TASK_POLL_INTERVAL_MS: 50000,              // 50 seconds
  TASK_MAX_ATTEMPTS: 20,                     // Total: 1000 seconds

  // Total max time: ~78 seconds (safely under 120s gateway timeout)
}

/**
 * Validate API key and gateway ownership
 */
async function validateGatewayOwnership(request: Request, projectId: string, gatewayId: string): Promise<{
  valid: boolean;
  error?: Response;
}> {
  const validationResult = await validateApiKeyFromRequest(request);
  
  if (!validationResult?.org) {
    return {
      valid: false,
      error: json(createMCPError("unknown", -32002, "Invalid or missing API key"))
    };
  }
  
  // Verify project exists in organization
  const projects = await getProjectsByOrgId(validationResult.org.orgId);
  const projectExists = projects.some(p => p.id === projectId);
  
  if (!projectExists) {
    return {
      valid: false,
      error: json(createMCPError("unknown", -32002, "Project not found or access denied"))
    };
  }
  
  // Verify the gateway exists and get its details
  const gateway = await getMcpGateway(projectId, gatewayId);
  if (!gateway) {
    return {
      valid: false,
      error: json(createMCPError("unknown", -32002, "Gateway not found"))
    };
  }
  
  // Extract the API key from the Authorization header
  const authHeader = request.headers.get("Authorization") || request.headers.get("authorization");
  const requestApiKey = authHeader?.replace(/^Bearer\s+/i, "");
  
  // Check if gateway has an API key configured
  if (gateway.api_key) {
    // If gateway has API key, verify it matches the request
    if (!requestApiKey || requestApiKey !== gateway.api_key) {
      return {
        valid: false,
        error: json(createMCPError("unknown", -32003, "API key does not match gateway"))
      };
    }
  }
  
  return { valid: true };
}

/**
 * Handle tools/list method
 */
async function handleToolsList(gatewayId: string, projectId: string, mcpRequest: MCPRequest): Promise<MCPResponse> {
  try {
    const gateway = await getMcpGateway(projectId, gatewayId);
    if (!gateway) {
      return createMCPError(mcpRequest.id, -32002, "Gateway not found");
    }
    
    if (!gateway.enabled) {
      return createMCPError(mcpRequest.id, -32002, "Gateway is disabled");
    }

    // Get enabled tools
    const allTools = await getMcpGatewayTools(projectId, gatewayId);
    const enabledTools = allTools.filter(tool => tool.enabled);

    // Transform to MCP Tool format
    const mcpTools: MCPTool[] = enabledTools.map(tool => ({
      name: tool.tool_name,
      description: tool.description,
      inputSchema: tool.input_schema
    }));

    return createMCPResponse(mcpRequest.id, { tools: mcpTools });
  } catch (error) {
    console.error("Error listing tools:", error);
    return createMCPError(mcpRequest.id, -32603, "Internal error");
  }
}

/**
 * Handle tools/call method
 */
async function handleToolCall(
  gatewayId: string, 
  projectId: string, 
  mcpRequest: MCPRequest
): Promise<MCPResponse> {
  try {
    const { name: toolName, arguments: toolArgs } = mcpRequest.params;

    // Validate gateway and tool
    const gateway = await getMcpGateway(projectId, gatewayId);
    if (!gateway?.enabled) {
      return createMCPError(mcpRequest.id, -32002, "Gateway not found or disabled");
    }

    const allTools = await getMcpGatewayTools(projectId, gatewayId);
    const tool = allTools.find(t => t.tool_name === toolName && t.enabled);
    
    if (!tool) {
      return createMCPError(mcpRequest.id, -32002, "Tool not found or disabled");
    }

    // Execute tool
    const result = await executeToolWithStreaming(
      projectId, 
      gatewayId, 
      toolName, 
      toolArgs
    );

    // Extract the result string and return in MCP content format
    const resultText = result?.result || JSON.stringify(result);
    
    return createMCPResponse(mcpRequest.id, {
      content: [
        {
          type: "text",
          text: resultText
        }
      ]
    });

  } catch (error) {
    console.error("Error calling tool:", error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    return createMCPError(mcpRequest.id, -32603, `Tool execution error: ${errorMessage}`);
  }
}

/**
 * Execute tool
 */
async function executeToolWithStreaming(
  projectId: string,
  gatewayId: string,
  toolName: string,
  args: any
): Promise<any> {
  console.log('[executeToolWithStreaming] Starting execution for tool:', toolName, {
    projectId,
    gatewayId,
    args
  });

  try {
    // Get the tool to find its ID
    console.log('[executeToolWithStreaming] Fetching tools for gateway:', gatewayId);
    const allTools = await getMcpGatewayTools(projectId, gatewayId);
    console.log('[executeToolWithStreaming] Found tools in gateway:', allTools.length);

    const tool = allTools.find(t => t.tool_name === toolName);

    if (!tool) {
      console.error('[executeToolWithStreaming] Tool not found:', toolName, {
        availableTools: allTools.map(t => t.tool_name)
      });
      throw new Error('Tool not found: ' + toolName);
    }

    console.log('[executeToolWithStreaming] Found tool:', toolName, {
      toolId: tool.id,
      agentId: tool.agent_id
    });

    // Create tool invocation
    console.log('[executeToolWithStreaming] Creating tool invocation', {
      toolId: tool.id,
      args
    });
    const invocation = await createMcpToolInvocation(
      projectId,
      gatewayId,
      tool.id,
      args
    );
    console.log('[executeToolWithStreaming] Tool invocation created', {
      invocationId: invocation.invocation_id,
      assistantTaskId: invocation.assistant_task_id
    });


    // Get assistant_task_id from invocation and poll on the task
    let assistantTaskId = invocation.assistant_task_id;

    // If we don't have assistant_task_id yet, poll invocation briefly to get it
    if (!assistantTaskId) {
      console.log('[executeToolWithStreaming] No assistant_task_id yet, starting invocation polling');
      let invocationAttempts = 0;
      let invocationStatus = invocation;

      while (!assistantTaskId && invocationAttempts < POLLING_CONFIG.INVOCATION_MAX_ATTEMPTS) {
        console.log('[executeToolWithStreaming] Polling for assistant_task_id, attempt', invocationAttempts + 1, '/', POLLING_CONFIG.INVOCATION_MAX_ATTEMPTS);
        await new Promise(resolve => setTimeout(resolve, POLLING_CONFIG.INVOCATION_POLL_INTERVAL_MS));

        invocationStatus = await getMcpInvocationStatus(
          projectId,
          gatewayId,
          tool.id,
          invocation.invocation_id
        );

        assistantTaskId = invocationStatus.assistant_task_id;
        invocationAttempts++;

        if (assistantTaskId) {
          console.log('[executeToolWithStreaming] Received assistant_task_id after attempts:', assistantTaskId, invocationAttempts);
        }
      }
    }

    if (!assistantTaskId) {
      console.error('[executeToolWithStreaming] Failed to get assistant_task_id after maximum attempts', {
        invocationId: invocation.invocation_id,
        maxAttempts: POLLING_CONFIG.INVOCATION_MAX_ATTEMPTS
      });
      throw new Error("Could not get assistant_task_id from invocation");
    }

    console.log('[executeToolWithStreaming] Starting task polling with assistant_task_id:', assistantTaskId);

    // Now poll on the task directly - limited polling to stay under gateway timeout
    let attempts = 0;
    let taskStatus: string = 'processing';
    let finalTask = null;

    console.log('[executeToolWithStreaming] Beginning task status polling (max attempts):', POLLING_CONFIG.TASK_MAX_ATTEMPTS, 'total seconds:', POLLING_CONFIG.TASK_MAX_ATTEMPTS * POLLING_CONFIG.TASK_POLL_INTERVAL_MS / 1000);

    while ((taskStatus === 'processing' || taskStatus === 'queued') && attempts < POLLING_CONFIG.TASK_MAX_ATTEMPTS) {
      await new Promise(resolve => setTimeout(resolve, POLLING_CONFIG.TASK_POLL_INTERVAL_MS));

      try {
        console.log('[executeToolWithStreaming] Polling task status, attempt', attempts + 1, '/', POLLING_CONFIG.TASK_MAX_ATTEMPTS, 'current status:', taskStatus);
        const assistantTask = await getAgentTask(
          projectId,
          tool.agent_id,
          assistantTaskId
        );

        if (assistantTask) {
          const previousStatus = taskStatus;
          taskStatus = assistantTask.status || 'processing';
          finalTask = assistantTask;

          if (previousStatus !== taskStatus) {
            console.log('[executeToolWithStreaming] Task status changed:', previousStatus, '->', taskStatus);
          }
        } else {
          console.warn('[executeToolWithStreaming] getAgentTask returned null/undefined for task', assistantTaskId);
        }
      } catch (error) {
        console.error('[executeToolWithStreaming] Error polling task status (attempt', attempts + 1, '):', error);
        // Continue polling on error
      }

      attempts++;
    }

    console.log('[executeToolWithStreaming] Task polling completed', {
      finalStatus: taskStatus,
      totalAttempts: attempts,
      maxAttempts: POLLING_CONFIG.TASK_MAX_ATTEMPTS,
      taskId: assistantTaskId
    });

    // Return the result based on task status
    if (taskStatus === 'completed' && finalTask) {
      console.log('[executeToolWithStreaming] Task completed successfully', {
        taskId: assistantTaskId,
        hasContent: !!finalTask.content
      });
      let actualOutput = finalTask.content || "Tool executed successfully";

      // Try to parse content as JSON, otherwise use as string
      try {
        const parsedContent = JSON.parse(actualOutput);
        actualOutput = parsedContent;
        console.log('[executeToolWithStreaming] Successfully parsed task output as JSON');
      } catch {
        console.log('[executeToolWithStreaming] Task output is not JSON, using as string');
        // Keep as string if not valid JSON
      }

      const result = {
        result: typeof actualOutput === 'string' ? actualOutput : JSON.stringify(actualOutput)
      };

      console.log('[executeToolWithStreaming] Returning completed result');
      return result;
    } else if (taskStatus === 'failed') {
      console.error('[executeToolWithStreaming] Task failed', {
        taskId: assistantTaskId,
        response: finalTask?.response
      });
      const result = {
        result: finalTask?.response || "Tool execution failed"
      };

      return result;
    } else {
      // Still processing - return task info so client can retry or check status
      console.warn('[executeToolWithStreaming] Task still processing after polling timeout', {
        taskId: assistantTaskId,
        status: taskStatus,
        attempts,
        maxAttempts: POLLING_CONFIG.TASK_MAX_ATTEMPTS
      });
      const result = {
        result: `Task is still processing (status: "${taskStatus}"). This is a long-running operation. The task continues to execute in the background.\n\nTask ID: ${assistantTaskId}\nInvocation ID: ${invocation.invocation_id}\nCurrent Status: ${taskStatus}`,
        isComplete: false,
        taskId: assistantTaskId,
        invocationId: invocation.invocation_id,
        status: taskStatus
      };

      return result;
    }

  } catch (error) {
    console.error('[executeToolWithStreaming] Error executing tool:', toolName, {
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
      projectId,
      gatewayId
    });

    const result = {
      result: `Tool execution error: ${error instanceof Error ? error.message : String(error)}`
    };


    return result;
  }
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
 * GET /mcp/{projectId}/{gatewayId} - MCP Server endpoint
 * Returns server info and available tools
 */
export async function loader({ request, params }: LoaderFunctionArgs) {
  try {
    const { gatewayId, projectId } = params;
    
    if (!gatewayId || !projectId) {
      return json({ error: "Both Project ID and Gateway ID are required" }, { status: 400 });
    }

    // Validate API key and gateway ownership
    const { valid, error } = await validateGatewayOwnership(request, projectId, gatewayId);
    if (!valid) {
      return error || json({ error: "Access denied" }, { status: 403 });
    }

    // Validate gateway
    const gateway = await getMcpGateway(projectId, gatewayId);
    if (!gateway) {
      return json({ error: "Gateway not found" }, { status: 404 });
    }
    
    if (!gateway.enabled) {
      return json({ error: "Gateway is disabled" }, { status: 403 });
    }

    // Get tools directly
    const allTools = await getMcpGatewayTools(projectId, gatewayId);
    const enabledTools = allTools.filter(tool => tool.enabled);

    // Transform to MCP Tool format
    const mcpTools: MCPTool[] = enabledTools.map(tool => ({
      name: tool.tool_name,
      description: tool.description,
      inputSchema: tool.input_schema
    }));

    // Return MCP server info and tools
    return json({
      server: {
        name: `chicory-gateway-${gatewayId}`,
        version: "1.0.0",
        capabilities: {
          tools: {}
        }
      },
      tools: mcpTools,
      gateway: {
        id: gateway.id,
        name: gateway.name,
        enabled: gateway.enabled
      }
    });

  } catch (error) {
    console.error("Error in MCP server:", error);
    return json({ error: "Internal server error" }, { status: 500 });
  }
}

/**
 * POST /mcp/{projectId}/{gatewayId} - MCP Protocol handler
 * Handles JSON-RPC 2.0 requests directly
 */
export async function action({ request, params }: LoaderFunctionArgs) {
  try {
    const { gatewayId, projectId } = params;
    
    if (!gatewayId || !projectId) {
      return json({ 
        jsonrpc: "2.0", 
        id: null, 
        error: { code: -32600, message: "Both Project ID and Gateway ID are required" } 
      });
    }

    // Validate API key and gateway ownership
    const { valid, error } = await validateGatewayOwnership(request, projectId, gatewayId);
    if (!valid) {
      return error || json({ 
        jsonrpc: "2.0", 
        id: null, 
        error: { code: -32002, message: "Access denied" } 
      });
    }

    // Parse MCP request
    const mcpRequest: MCPRequest = await request.json();

    // Handle MCP methods directly
    switch (mcpRequest.method) {
      case "initialize":
        return json({
          jsonrpc: "2.0",
          id: mcpRequest.id,
          result: {
            protocolVersion: "2024-11-05",
            capabilities: {
              tools: {}
            },
            serverInfo: {
              name: `chicory-gateway-${gatewayId}`,
              version: "1.0.0"
            }
          }
        });

      case "tools/list":
        const response = await handleToolsList(gatewayId, projectId, mcpRequest);
        return json(response);
      
      case "tools/call":
        const callResponse = await handleToolCall(gatewayId, projectId, mcpRequest);
        return json(callResponse);
      
      default:
        return json(createMCPError(mcpRequest.id, -32601, "Method not found"));
    }

  } catch (error) {
    console.error("Error in MCP protocol handler:", error);
    return json({ 
      jsonrpc: "2.0", 
      id: null, 
      error: { code: -32603, message: "Internal error" } 
    });
  }
}
