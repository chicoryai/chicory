import { json, redirect } from "@remix-run/node";
import {
  updateAgent,
  deleteAgent,
  addToolToAgent,
  updateAgentTool,
  deleteAgentTool
} from "~/services/chicory.server";

/**
 * Shared action handler for updating agent configuration
 */
export async function handleUpdateConfig(
  projectId: string,
  agentId: string,
  formData: FormData,
  userId?: string
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
      outputFormat,
      undefined, // deployed
      undefined, // api_key
      undefined, // state
      undefined, // capabilities
      undefined, // metadata
      userId // updated_by for version tracking
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
    if (error instanceof Response) {
      const errorData = await error.json();
      return json({
        success: false,
        error: errorData.detail || "Failed to delete agent"
      }, { status: error.status });
    }
    return json({ success: false, error: "Failed to delete agent" }, { status: 500 });
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
  const toolName = formData.get("toolName") as string;
  const toolDescription = formData.get("toolDescription") as string;
  const type = (formData.get("type") as string) || (formData.get("toolType") as string);
  const toolProvider = (formData.get("toolProvider") as string) || "MCP";
  const rawConfig = formData.get("toolConfig") as string | null;
  const dataSourceId = formData.get("dataSourceId") as string | null;

  if (!toolName || !toolDescription || !type) {
    return json({ success: false, error: "Tool name, description, and type are required" }, { status: 400 });
  }

  try {
    let toolConfig: Record<string, unknown> = {};

    if (type === 'datasource' && dataSourceId) {
      toolConfig = { dataSourceId };
    } else if (rawConfig) {
      try {
        toolConfig = JSON.parse(rawConfig);
      } catch (error) {
        return json({ success: false, error: "Invalid tool configuration JSON" }, { status: 400 });
      }
    }

    await addToolToAgent(projectId, agentId, {
      name: toolName,
      description: toolDescription,
      provider: toolProvider,
      tool_type: type,
      config: toolConfig
    });
    return json({ success: true, intent: "addTool" });
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
  const toolName = formData.get("toolName") as string;
  const toolDescription = formData.get("toolDescription") as string;

  if (!toolId || !toolName || !toolDescription) {
    return json({ success: false, error: "Tool ID, name, and description are required" }, { status: 400 });
  }

  try {
    await updateAgentTool(
      projectId,
      agentId,
      toolId,
      toolName,
      toolDescription
    );
    return json({ success: true, intent: "updateTool" });
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

  if (!toolId) {
    return json({ success: false, error: "Tool ID is required" }, { status: 400 });
  }

  try {
    await deleteAgentTool(projectId, agentId, toolId);
    return json({ success: true, intent: "deleteTool" });
  } catch (error) {
    console.error("Error deleting tool:", error);
    return json({ success: false, error: "Failed to delete tool" }, { status: 500 });
  }
}
