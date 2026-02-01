import { Link } from "@remix-run/react";
import type { MCPGateway } from "~/services/chicory.server";
import { 
  PencilIcon,
  TrashIcon,
  ArrowTopRightOnSquareIcon
} from "@heroicons/react/24/outline";

interface GatewayCardProps {
  gateway: MCPGateway;
  projectId: string;
  onToggle: (gateway: MCPGateway) => void;
  onEdit: (gateway: MCPGateway) => void;
  onDelete: (gateway: MCPGateway) => void;
}

export function GatewayCard({ 
  gateway, 
  projectId,
  onToggle, 
  onEdit, 
  onDelete 
}: GatewayCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 flex flex-col h-full">
      {/* Header with title and status */}
      <div className="flex justify-between items-start mb-3">
        <h3 className="text-lg font-semibold truncate flex-1 mr-2">{gateway.name}</h3>
        {gateway.enabled ? (
          <span className="px-1.5 py-0.5 text-xs rounded bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 whitespace-nowrap">
            Enabled
          </span>
        ) : (
          <span className="px-1.5 py-0.5 text-xs rounded bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200 whitespace-nowrap">
            Disabled
          </span>
        )}
      </div>
      
      {/* Gateway ID - more compact */}
      <div className="text-xs text-gray-500 dark:text-gray-400 mb-3 font-mono">
        <span className="break-all">{gateway.id.substring(0, 8)}...</span>
      </div>
      
      {/* Actions - stacked for better mobile/grid layout */}
      <div className="mt-auto space-y-2">
        <div className="flex space-x-2">
          <Link
            to={`/mcp-gateway/${gateway.id}`}
            className="p-1.5 text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
            title="View Endpoint"
          >
            <ArrowTopRightOnSquareIcon className="h-4 w-4" />
          </Link>
          
          <button
            onClick={() => onEdit(gateway)}
            className="p-1.5 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Edit Gateway"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
          
          <button
            onClick={() => onDelete(gateway)}
            className="p-1.5 text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            title="Delete Gateway"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}