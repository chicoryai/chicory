import { json, redirect } from "@remix-run/node";
import {
  updateAgent,
  deleteAgent,
  addToolToAgent,
  updateAgentTool,
  deleteAgentTool,
  createMcpGatewayTool,
  updateMcpGatewayTool,
  getAgent,
  getMcpGateways
} from "~/services/chicory.server";

/**
 * Shared action handler for updating agent configuration
 */
export async function handleUpdateAgentConfig(
  projectId: string,
  agentId: string,
  formData: FormData
) {
  const name = formData.get("name") as string;
  const description = formData.get("description") as string;
  const systemPrompt = formData.get("system_prompt") as string;
  const outputFormat = formData.get("output_format") as string;

  try {
    await updateAgent(
      projectId,
      agentId,
      name,
      description,
      systemPrompt,
      outputFormat
    );
    return json({ success: true, type: "config-updated" });
  } catch (error) {
    console.error("Error updating agent:", error);
    return json({ success: false, error: "Failed to update configuration" }, { status: 500 });
  }
}

/**
 * Shared action handler for deleting an agent
 */
export async function handleDeleteAgent(
  projectId: string,
  agentId: string
) {
  try {
    await deleteAgent(projectId, agentId);
    return redirect("/new");
  } catch (error) {
    console.error("Error deleting agent:", error);
    const errorMessage = error instanceof Error ? error.message : "Failed to delete agent";
    if (errorMessage.includes("Internal Server Error")) {
      return json({
        success: false,
        error: "Unable to delete agent. The agent may have associated data that needs to be removed first, or there may be a server issue. Please try again later or contact support."
      }, { status: 500 });
    }
    return json({
      success: false,
      error: errorMessage
    }, { status: 500 });
  }
}

/**
 * Shared action handler for adding a tool to an agent
 */
export async function handleAddTool(
  projectId: string,
  agentId: string,
  formData: FormData
) {
  const toolName = (formData.get("toolName") as string) ?? "";
  const toolDescription = (formData.get("toolDescription") as string) ?? "";
  const toolProvider = (formData.get("toolProvider") as string) || "MCP";
  const toolType = (formData.get("toolType") as string) || "mcp";
  const toolConfig = formData.get("toolConfig") as string;

  if (!toolName.trim() || !toolProvider.trim() || !toolConfig) {
    return json({ success: false, error: "Tool name, provider, and config are required" }, { status: 400 });
  }

  try {
    let config;
    try {
      config = JSON.parse(toolConfig);
    } catch (e) {
      return json({ success: false, error: "Invalid tool configuration JSON" }, { status: 400 });
    }

    const toolData = {
      name: toolName,
      description: toolDescription,
      provider: toolProvider,
      type: toolType,
      config,
      tool_type: "mcp" as const
    };

    const result = await addToolToAgent(projectId, agentId, toolData);

    return json({ success: true, type: "tool-added", tool: result });
  } catch (error) {
    console.error("Error adding tool:", error);
    return json({ success: false, error: "Failed to add tool" }, { status: 500 });
  }
}

/**
 * Shared action handler for updating a tool
 */
export async function handleUpdateTool(
  projectId: string,
  agentId: string,
  formData: FormData
) {
  const toolId = formData.get("toolId") as string;
  const enabled = formData.get("enabled") === "true";
  const config = formData.get("config") as string | null;

  try {
    let parsedConfig = undefined;
    if (config) {
      try {
        parsedConfig = JSON.parse(config);
      } catch (e) {
        return json({ success: false, error: "Invalid configuration JSON" }, { status: 400 });
      }
    }

    await updateAgentTool(
      projectId,
      agentId,
      toolId,
      enabled ? 1 : 0,
      parsedConfig
    );

    return json({ success: true, type: "tool-updated" });
  } catch (error) {
    console.error("Error updating tool:", error);
    return json({ success: false, error: "Failed to update tool" }, { status: 500 });
  }
}

/**
 * Shared action handler for deleting a tool
 */
export async function handleDeleteTool(
  projectId: string,
  agentId: string,
  formData: FormData
) {
  const toolId = formData.get("toolId") as string;

  try {
    await deleteAgentTool(projectId, agentId, toolId);
    return json({ success: true, type: "tool-deleted" });
  } catch (error) {
    console.error("Error deleting tool:", error);
    return json({ success: false, error: "Failed to delete tool" }, { status: 500 });
  }
}

/**
 * Shared action handler for adding an MCP gateway
 */
export async function handleAddMcpGateway(
  projectId: string,
  agentId: string,
  formData: FormData
) {
  const gatewayId = formData.get("gateway_id") as string;

  if (!gatewayId) {
    return json({
      success: false,
      error: "Gateway ID is required"
    }, { status: 400 });
  }

  try {
    const mcpTool = await createMcpGatewayTool(projectId, gatewayId, agentId);
    const currentAgent = await getAgent(projectId, agentId);
    if (!currentAgent) {
      throw new Error("Agent not found");
    }

    const gateways = await getMcpGateways(projectId);
    const gateway = gateways.find(g => g.id === gatewayId);

    const existingGateways = currentAgent.metadata?.mcp_gateways || [];
    const updatedGateways = [
      ...existingGateways,
      {
        gateway_id: gatewayId,
        tool_id: mcpTool.id,
        name: gateway?.name || 'Unknown Gateway',
        enabled: true
      }
    ];

    const updatedMetadata = {
      ...(currentAgent.metadata || {}),
      mcp_gateways: updatedGateways
    };

    await updateAgent(
      projectId,
      agentId,
      undefined,
      undefined,
      undefined,
      undefined,
      true,
      undefined,
      "enabled",
      undefined,
      updatedMetadata
    );

    return json({
      success: true,
      type: 'mcp-gateway-added',
      tool: mcpTool
    });
  } catch (error) {
    console.error("Error adding MCP gateway:", error);
    return json({
      success: false,
      error: "Failed to add MCP gateway"
    }, { status: 500 });
  }
}

/**
 * Shared action handler for updating an MCP gateway
 */
export async function handleUpdateMcpGateway(
  projectId: string,
  agentId: string,
  formData: FormData
) {
  const toolId = formData.get("tool_id") as string;
  const enabled = formData.get("enabled") === "true";
  const selectedTools = formData.get("selected_tools") as string;

  if (!toolId) {
    return json({
      success: false,
      error: "Tool ID is required"
    }, { status: 400 });
  }

  try {
    let parsedSelectedTools: string[] | undefined;
    if (selectedTools) {
      try {
        parsedSelectedTools = JSON.parse(selectedTools);
      } catch {
        return json({
          success: false,
          error: "Invalid selected tools format"
        }, { status: 400 });
      }
    }

    const result = await updateMcpGatewayTool(
      projectId,
      toolId,
      enabled ? 1 : 0,
      parsedSelectedTools
    );

    // Update agent metadata
    const currentAgent = await getAgent(projectId, agentId);
    if (currentAgent?.metadata?.mcp_gateways) {
      const updatedGateways = currentAgent.metadata.mcp_gateways.map((gw: any) =>
        gw.tool_id === toolId ? { ...gw, enabled } : gw
      );

      const updatedMetadata = {
        ...currentAgent.metadata,
        mcp_gateways: updatedGateways
      };

      await updateAgent(
        projectId,
        agentId,
        undefined,
        undefined,
        undefined,
        undefined,
        undefined,
        undefined,
        undefined,
        undefined,
        updatedMetadata
      );
    }

    return json({
      success: true,
      type: 'mcp-gateway-updated',
      tool: result
    });
  } catch (error) {
    console.error("Error updating MCP gateway:", error);
    return json({
      success: false,
      error: "Failed to update MCP gateway"
    }, { status: 500 });
  }
}

/**
 * Shared action handler for removing an MCP gateway
 */
export async function handleRemoveMcpGateway(
  projectId: string,
  agentId: string,
  formData: FormData
) {
  const toolId = formData.get("tool_id") as string;
  const gatewayId = formData.get("gateway_id") as string;

  if (!toolId || !gatewayId) {
    return json({
      success: false,
      error: "Tool ID and Gateway ID are required"
    }, { status: 400 });
  }

  try {
    await deleteAgentTool(projectId, agentId, toolId);

    // Update agent metadata to remove the gateway
    const currentAgent = await getAgent(projectId, agentId);
    if (currentAgent?.metadata?.mcp_gateways) {
      const updatedGateways = currentAgent.metadata.mcp_gateways.filter(
        (gw: any) => gw.gateway_id !== gatewayId
      );

      const updatedMetadata = {
        ...currentAgent.metadata,
        mcp_gateways: updatedGateways
      };

      await updateAgent(
        projectId,
        agentId,
        undefined,
        undefined,
        undefined,
        undefined,
        undefined,
        undefined,
        undefined,
        undefined,
        updatedMetadata
      );
    }

    return json({
      success: true,
      type: 'mcp-gateway-removed'
    });
  } catch (error) {
    console.error("Error removing MCP gateway:", error);
    return json({
      success: false,
      error: "Failed to remove MCP gateway"
    }, { status: 500 });
  }
}
