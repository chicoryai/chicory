import { json } from "@remix-run/node";
import { createPlaygroundInvocation } from "~/services/chicory-playground.server";
import { updateMcpGatewayTool } from "~/services/chicory.server";

/**
 * Shared action handler for creating a playground invocation
 */
export async function handleCreateInvocation(
  projectId: string,
  agentId: string,
  formData: FormData
) {
  const task = formData.get("task") as string;
  const playgroundId = formData.get("playgroundId") as string;

  if (!task || typeof task !== "string" || !task.trim()) {
    throw new Response("Task is required", { status: 400 });
  }

  if (!playgroundId) {
    throw new Response("Playground ID is required", { status: 400 });
  }

  try {
    const invocation = await createPlaygroundInvocation(projectId, agentId, playgroundId, {
      content: task.trim()
    });

    return json({
      success: true,
      invocationId: invocation.invocation_id,
      userTaskId: (invocation as any).user_task_id,
      assistantTaskId: (invocation as any).assistant_task_id,
      agentId
    });
  } catch (error) {
    console.error("Error creating playground invocation:", error);
    return json({ success: false, error: "Failed to create invocation" }, { status: 500 });
  }
}

/**
 * Shared action handler for running an evaluation
 */
export async function handleRunEvaluation(
  projectId: string,
  agentId: string,
  formData: FormData
) {
  const evaluationId = formData.get("evaluation_id") as string;

  if (!evaluationId) {
    return json({ success: false, error: "Evaluation ID is required" }, { status: 400 });
  }

  try {
    const response = await fetch(
      `${process.env.CHICORY_API_URL}/projects/${projectId}/agents/${agentId}/evaluations/${evaluationId}/run`,
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${process.env.CHICORY_API_KEY}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error("Failed to start evaluation run");
    }

    const runData = await response.json();
    return json({ success: true, type: "evaluation-started", runId: runData.id });
  } catch (error) {
    console.error("Error running evaluation:", error);
    return json({ success: false, error: "Failed to start evaluation" }, { status: 500 });
  }
}

/**
 * Shared action handler for toggling MCP tool
 */
export async function handleToggleMcpTool(
  projectId: string,
  agentId: string,
  formData: FormData
) {
  const toolId = formData.get("toolId") as string;
  const enabled = formData.get("enabled") === "true";
  const gatewayId = formData.get("gatewayId") as string;

  if (!toolId) {
    return json({ success: false, error: "Tool ID is required" }, { status: 400 });
  }

  if (!gatewayId) {
    return json({ success: false, error: "Gateway ID is required" }, { status: 400 });
  }

  try {
    await updateMcpGatewayTool(
      projectId,
      gatewayId,
      toolId,
      {
        enabled
      }
    );

    return json({
      success: true,
      intent: "toggle-mcp-tool",
      toolId,
      gatewayId,
      enabled
    });
  } catch (error) {
    console.error("Error toggling MCP tool:", error);
    return json({
      success: false,
      error: error instanceof Error ? error.message : "Failed to toggle MCP tool"
    }, { status: 500 });
  }
}
