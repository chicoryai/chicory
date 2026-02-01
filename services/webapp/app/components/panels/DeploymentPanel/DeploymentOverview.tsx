/**
 * DeploymentOverview Component
 * Shows deployment status at a glance
 */

import { CheckCircleIcon, XCircleIcon } from "@heroicons/react/24/outline";
import { ServerIcon } from "@heroicons/react/24/solid";
import MCPGatewayIcon from "~/components/icons/MCPGatewayIcon";

interface DeploymentOverviewProps {
  isAPIDeployed: boolean;
  isMCPDeployed: boolean;
  gatewayNames: string[];
}

export function DeploymentOverview({
  isAPIDeployed,
  isMCPDeployed,
  gatewayNames,
}: DeploymentOverviewProps) {
  return (
    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
      <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">Deployment Status</h3>
      
      <div className="grid grid-cols-2 gap-4">
        {/* API Status */}
        <div className="flex items-center space-x-2">
          <ServerIcon className="w-5 h-5 text-gray-400" />
          <span className="text-sm text-gray-700 dark:text-gray-300">API:</span>
          {isAPIDeployed ? (
            <div className="flex items-center space-x-1">
              <CheckCircleIcon className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium text-green-600 dark:text-green-400">Active</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1">
              <XCircleIcon className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-500 dark:text-gray-400">Not deployed</span>
            </div>
          )}
        </div>

        {/* MCP Status */}
        <div className="flex items-center space-x-2">
          <MCPGatewayIcon size={20} className="flex-shrink-0" />
          <span className="text-sm text-gray-700 dark:text-gray-300">MCP:</span>
          {isMCPDeployed ? (
            <div className="flex items-center space-x-1">
              <CheckCircleIcon className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium text-green-600 dark:text-green-400" title={gatewayNames.join(', ')}>
                {gatewayNames.length === 1 
                  ? gatewayNames[0].substring(0, 15) + (gatewayNames[0].length > 15 ? '...' : '')
                  : `${gatewayNames.length} gateways`}
              </span>
            </div>
          ) : (
            <div className="flex items-center space-x-1">
              <XCircleIcon className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-500 dark:text-gray-400">Not deployed</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
