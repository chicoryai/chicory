/**
 * DeploymentPanel Component
 * Main container for unified deployment management
 */

import { DeploymentOverview } from "./DeploymentOverview";
import { APIDeploymentCard } from "./APIDeploymentCard";
import { MCPDeploymentCard } from "./MCPDeploymentCard";
import type { Agent, MCPGateway } from "~/services/chicory.server";

interface DeploymentPanelProps {
  agent: Agent;
  projectId: string;
  gateways: MCPGateway[];
  isLoadingGateways: boolean;
  onDeployAPI: () => Promise<void>;
  onUndeployAPI: () => Promise<void>;
  onDeployMCP: (gatewayId: string) => Promise<void>;
  onUndeployMCP: (gatewayId?: string) => Promise<void>;
  onToggleMCPTool?: (gatewayId: string, toolId: string, enabled: boolean) => Promise<void>;
}

export function DeploymentPanel({
  agent,
  projectId,
  gateways,
  isLoadingGateways,
  onDeployAPI,
  onUndeployAPI,
  onDeployMCP,
  onUndeployMCP,
  onToggleMCPTool,
}: DeploymentPanelProps) {
  // Check deployment states
  const isAPIDeployed = agent.deployed && agent.api_key;
  
  // Get enriched gateways directly from metadata (already includes names)
  const connectedGateways = agent.metadata?.mcp_gateways || [];
  
  // Use connected gateways length for deployment status
  const isMCPDeployed = agent.deployed && connectedGateways.length > 0;
  return (
    <div className="space-y-6">
      {/* Deployment Overview */}
      <DeploymentOverview
        isAPIDeployed={isAPIDeployed}
        isMCPDeployed={isMCPDeployed}
        gatewayNames={connectedGateways.map(g => g.name)}
      />

      {/* Deployment Cards */}
      <div className="space-y-4">
        {/* API Deployment Card */}
        <APIDeploymentCard
          agentId={agent.id}
          projectId={projectId}
          isDeployed={isAPIDeployed}
          apiKey={agent.api_key}
          onDeploy={onDeployAPI}
          onUndeploy={onUndeployAPI}
        />

        {/* MCP Gateway Deployment Card */}
        <MCPDeploymentCard
          agentId={agent.id}
          projectId={projectId}
          isDeployed={isMCPDeployed}
          connectedGateways={connectedGateways}
          gateways={gateways}
          isLoadingGateways={isLoadingGateways}
          onDeploy={onDeployMCP}
          onUndeploy={onUndeployMCP}
          onToggleTool={onToggleMCPTool}
        />
      </div>
    </div>
  );
}