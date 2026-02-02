import { json } from "@remix-run/node";
import {
  updateAgent,
  createMcpGatewayTool,
  getMcpGateways,
  getAgent
} from "~/services/chicory.server";
import { createApiKey } from "~/utils/propelauth.server";
import { getAuth, isCloudAuth } from "~/auth/auth.server";

function normalizeGatewayMetadata(rawGateways: unknown): any[] {
  if (!rawGateways) {
    return [];
  }

  if (Array.isArray(rawGateways)) {
    return rawGateways;
  }

  if (typeof rawGateways === "string") {
    return [{ gateway_id: rawGateways }];
  }

  if (typeof rawGateways === "object") {
    const entries: any[] = [];
    for (const [key, value] of Object.entries(rawGateways as Record<string, unknown>)) {
      if (typeof value === "string") {
        entries.push({ gateway_id: value });
      } else if (value && typeof value === "object") {
        entries.push({ gateway_id: (value as any).gateway_id ?? key, ...value });
      } else {
        entries.push({ gateway_id: key });
      }
    }
    return entries;
  }

  return [];
}

/**
 * Shared action handler for deploying an agent
 */
export async function handleDeployAgent(
  projectId: string,
  agentId: string,
  formData: FormData,
  userDetails: any
) {
  const deploymentType = formData.get("deploymentType") as string;
  const gatewayId = formData.get("gatewayId") as string;

  try {
    if (deploymentType === 'mcp-tool') {
      if (!gatewayId) {
        throw new Error("Gateway ID is required for MCP tool deployment");
      }

      const mcpTool = await createMcpGatewayTool(projectId, gatewayId, agentId);
      const currentAgent = await getAgent(projectId, agentId);
      if (!currentAgent) {
        throw new Error("Agent not found");
      }

      const gateways = await getMcpGateways(projectId);
      const gateway = gateways.find(g => String(g.id) === String(gatewayId));

      const existingGateways = normalizeGatewayMetadata(currentAgent.metadata?.mcp_gateways);
      const gatewayIdString = String(gatewayId);
      const withoutGateway = existingGateways.filter((entry) => {
        const existingId = entry?.gateway_id ?? entry?.id;
        return String(existingId) !== gatewayIdString;
      });

      const updatedGateways = [
        ...withoutGateway,
        {
          gateway_id: gatewayIdString,
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
        intent: "deploy",
        deploymentStatus: "success",
        deploymentType: 'mcp-tool',
        gatewayId: gatewayIdString,
        toolId: mcpTool.id,
        isDeployed: true
      });
    } else {
      // Generate API key for agent deployment
      let generatedApiKey: string;

      if (isCloudAuth()) {
        // PropelAuth mode - requires org
        const orgId = userDetails && 'orgId' in userDetails ? userDetails.orgId : null;
        if (!orgId) {
          throw new Error("Organization ID is required for deployment");
        }
        const apiKeyResult = await createApiKey(orgId as string, agentId, 'agent');
        generatedApiKey = apiKeyResult.apiKeyToken;
      } else {
        // Local auth mode - create key directly with agent as resource
        const auth = await getAuth();
        const userId = userDetails?.userId;
        const apiKeyResult = await auth.createApiKey({
          userId,
          resourceType: 'agent',
          resourceId: agentId,
          metadata: {
            name: `Agent API Key`,
            created_for: 'deployment',
          }
        });
        generatedApiKey = apiKeyResult.apiKeyToken;
      }

      await updateAgent(
        projectId,
        agentId,
        undefined,
        undefined,
        undefined,
        undefined,
        true,
        generatedApiKey,
        "enabled"
      );

      return json({
        success: true,
        intent: "deploy",
        deploymentStatus: "success",
        deploymentType: 'api',
        apiKey: generatedApiKey,
        isDeployed: true
      });
    }
  } catch (error) {
    console.error("Error deploying agent:", error);
    return json({
      success: false,
      intent: "deploy",
      deploymentStatus: "error",
      error: error instanceof Error ? error.message : "Failed to deploy agent"
    }, { status: 500 });
  }
}

/**
 * Shared action handler for undeploying an agent
 */
export async function handleUndeployAgent(
  projectId: string,
  agentId: string,
  formData: FormData
) {
  const deploymentType = formData.get("deploymentType") as string;
  const gatewayId = formData.get("gatewayId") as string;

  try {
    const currentAgent = await getAgent(projectId, agentId);
    if (!currentAgent) {
      throw new Error("Agent not found");
    }

    if (deploymentType === 'mcp-tool') {
      const existingGateways = normalizeGatewayMetadata(currentAgent.metadata?.mcp_gateways);
      let updatedGateways = existingGateways;

      if (gatewayId) {
        const gatewayIdString = String(gatewayId);
        updatedGateways = existingGateways.filter(
          (gateway: any) => String(gateway.gateway_id ?? gateway.id) !== gatewayIdString
        );
      } else {
        updatedGateways = [];
      }

      const updatedMetadata = {
        ...(currentAgent.metadata || {}),
        mcp_gateways: updatedGateways
      };

      const stillDeployed = !!currentAgent.api_key || updatedGateways.length > 0;

      await updateAgent(
        projectId,
        agentId,
        undefined,
        undefined,
        undefined,
        undefined,
        stillDeployed,
        undefined,
        stillDeployed ? "enabled" : "disabled",
        undefined,
        updatedMetadata
      );
    } else {
      const gateways = normalizeGatewayMetadata(currentAgent.metadata?.mcp_gateways);
      const stillDeployed = gateways.length > 0;

      await updateAgent(
        projectId,
        agentId,
        undefined,
        undefined,
        undefined,
        undefined,
        stillDeployed,
        "",
        stillDeployed ? "enabled" : "disabled",
        undefined,
        currentAgent.metadata
      );
    }

    return json({
      success: true,
      intent: "undeploy",
      deploymentType
    });
  } catch (error) {
    console.error("Error undeploying agent:", error);
    return json({
      success: false,
      intent: "undeploy",
      error: error instanceof Error ? error.message : "Failed to undeploy agent"
    }, { status: 500 });
  }
}

/**
 * Shared action handler for updating agent status
 */
export async function handleUpdateAgentStatus(
  projectId: string,
  agentId: string,
  formData: FormData
) {
  const state = formData.get("state") as string;

  if (!state || (state !== "enabled" && state !== "disabled")) {
    return json({ success: false, error: "Valid state is required" }, { status: 400 });
  }

  try {
    await updateAgent(
      projectId,
      agentId,
      undefined,
      undefined,
      undefined,
      undefined,
      undefined,
      undefined,
      state
    );

    return json({ success: true, type: 'state-updated', state });
  } catch (error) {
    console.error("Error updating agent state:", error);
    return json({ success: false, error: 'Failed to update agent state' }, { status: 500 });
  }
}
