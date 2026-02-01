import { ServerIcon } from "@heroicons/react/24/outline";

interface EmptyStateProps {
  onCreateClick: () => void;
}

export function EmptyState({ onCreateClick }: EmptyStateProps) {
  return (
    <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <ServerIcon className="h-12 w-12 mx-auto text-gray-400 mb-4" />
      <p className="text-gray-600 dark:text-gray-400 mb-4">
        No MCP gateways configured yet
      </p>
      <button
        onClick={onCreateClick}
        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
      >
        Create Your First Gateway
      </button>
    </div>
  );
}