/**
 * MCPDeploymentCard Component
 * Manages MCP Gateway deployment for the agent
 */

import { useState, useCallback } from "react";
import { 
  LinkIcon,
  XMarkIcon
} from "@heroicons/react/24/outline";
import type { MCPGateway } from "~/services/chicory.server";
import GatewaySelector from "~/components/agents/GatewaySelector";
import { ToggleSwitch } from "~/components/ui/ToggleSwitch";
import MCPGatewayIcon from "~/components/icons/MCPGatewayIcon";

// Type for enriched gateway data from metadata
interface EnrichedGateway {
  gateway_id: string;
  tool_id?: string;
  name: string;
  enabled?: boolean;
  description?: string;
}

interface MCPDeploymentCardProps {
  agentId: string;
  projectId: string;
  isDeployed: boolean;
  connectedGateways: EnrichedGateway[]; // Enriched gateway data from metadata
  gateways: MCPGateway[];
  isLoadingGateways: boolean;
  onDeploy: (gatewayId: string) => Promise<void>;
  onUndeploy: (gatewayId?: string) => Promise<void>;
  onToggleTool?: (gatewayId: string, toolId: string, enabled: boolean) => Promise<void>;
}

export function MCPDeploymentCard({
  agentId,
  projectId,
  isDeployed,
  connectedGateways,
  gateways,
  isLoadingGateways,
  onDeploy,
  onUndeploy,
  onToggleTool,
}: MCPDeploymentCardProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [selectedGatewayId, setSelectedGatewayId] = useState<string>("");
  const [togglingTools, setTogglingTools] = useState<Set<string>>(new Set());

  const handleDeploy = useCallback(async () => {
    if (!selectedGatewayId) return;
    
    setIsLoading(true);
    try {
      await onDeploy(selectedGatewayId);
      setSelectedGatewayId(""); // Reset selection after successful deployment
    } finally {
      setIsLoading(false);
    }
  }, [selectedGatewayId, onDeploy]);

  const handleRemoveGateway = useCallback(async (gatewayId: string) => {
    setIsLoading(true);
    try {
      await onUndeploy(gatewayId);
    } finally {
      setIsLoading(false);
    }
  }, [onUndeploy]);

  const handleToggleTool = useCallback(async (gateway: EnrichedGateway, enabled: boolean) => {
    if (!onToggleTool) {
      return;
    }
    
    if (!gateway.tool_id) {
      alert('Unable to toggle: Tool ID is missing. This agent may need to be redeployed.');
      return;
    }
    
    const toolKey = `${gateway.gateway_id}-${gateway.tool_id}`;
    setTogglingTools(prev => new Set(prev).add(toolKey));
    
    try {
      await onToggleTool(gateway.gateway_id, gateway.tool_id, enabled);
    } catch (error) {
      console.error('Error in handleToggleTool:', error);
    } finally {
      setTogglingTools(prev => {
        const next = new Set(prev);
        next.delete(toolKey);
        return next;
      });
    }
  }, [onToggleTool]);

  // Get available gateways (not yet connected)
  // Connected gateways have gateway_id field from metadata
  const availableGateways = gateways.filter(
    g => !connectedGateways.some(cg => cg.gateway_id === g.id)
  );

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Card Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <MCPGatewayIcon size={20} className="flex-shrink-0" />
            <h3 className="font-medium text-gray-900 dark:text-white">MCP Gateway Deployment</h3>
            {isDeployed && (
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded-full">
                Connected
              </span>
            )}
          </div>
          
          {/* Show count if multiple gateways */}
          {isDeployed && connectedGateways.length > 1 && (
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {connectedGateways.length} gateways
            </span>
          )}
        </div>
      </div>

      {/* Card Content */}
      <div className="p-4">
        {isDeployed && connectedGateways.length > 0 ? (
          <div className="space-y-4">
            {/* Connected Gateways List */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Assigned Gateways ({connectedGateways.length})
              </label>
              <div className="space-y-2">
                {connectedGateways.map((gateway) => {
                  const toolKey = `${gateway.gateway_id}-${gateway.tool_id}`;
                  const isToggling = togglingTools.has(toolKey);
                  
                  return (
                    <div
                      key={gateway.gateway_id}
                      className="flex items-center justify-between bg-gray-50 dark:bg-gray-800 px-3 py-2.5 rounded-md border border-gray-200 dark:border-gray-700"
                    >
                      <div className="flex items-center space-x-2">
                        <LinkIcon className="w-4 h-4 text-gray-400" />
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {gateway.name}
                        </span>
                        {gateway.enabled ? (
                          <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                            Active
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 text-xs font-medium bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-400 rounded">
                            Disabled
                          </span>
                        )}
                      </div>
                      <div className="flex items-center space-x-2">
                        {onToggleTool && gateway.tool_id ? (
                          <ToggleSwitch
                            checked={gateway.enabled || false}
                            onChange={(enabled) => handleToggleTool(gateway, enabled)}
                            disabled={isLoading}
                            loading={isToggling}
                            size="sm"
                          />
                        ) : (
                          !gateway.tool_id && (
                            <span className="text-xs text-yellow-600 dark:text-yellow-400">
                              Redeploy needed
                            </span>
                          )
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Add to Another Gateway - Hidden when agent already has a gateway (single gateway restriction) */}
            {availableGateways.length > 0 && connectedGateways.length === 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Add to Another Gateway
                </label>
                <div className="flex space-x-2">
                  <GatewaySelector
                    projectId={projectId}
                    selectedGatewayId={selectedGatewayId}
                    onSelectGateway={setSelectedGatewayId}
                    gateways={availableGateways}
                  />
                  <button
                    onClick={handleDeploy}
                    disabled={!selectedGatewayId || isLoading}
                    className="px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Add
                  </button>
                </div>
              </div>
            )}

            {/* Info Text */}
            <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
              <p>This agent is available as a tool in the connected MCP gateways.</p>
              <p>Other agents can use this agent's capabilities through these gateways.</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Gateway Selection */}
            <div>
              {isLoadingGateways ? (
                <div className="animate-pulse">
                  <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
                </div>
              ) : availableGateways.length > 0 ? (
                <GatewaySelector
                  projectId={projectId}
                  selectedGatewayId={selectedGatewayId}
                  onSelectGateway={setSelectedGatewayId}
                  gateways={availableGateways}
                />
              ) : (
                <div className="text-sm text-gray-500 dark:text-gray-400 py-2">
                  No gateways available. Create a gateway first to deploy this agent as an MCP tool.
                </div>
              )}
            </div>

            {/* Deploy Button */}
            {availableGateways.length > 0 && (
              <button
                onClick={handleDeploy}
                disabled={!selectedGatewayId || isLoading}
                className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? "Deploying..." : "Deploy to Gateway"}
              </button>
            )}

            {/* Info Text */}
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Deploy this agent as an MCP tool to make it available for other agents to use through a gateway.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
