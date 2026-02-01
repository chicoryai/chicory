import { PlusIcon, SparklesIcon } from "@heroicons/react/24/outline";

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionText?: string;
  onAction?: () => void;
}

export default function EmptyState({
  title = "No agents found",
  description = "Create your first agent to get started",
  actionText = "Create Agent",
  onAction,
}: EmptyStateProps) {
  return (
    <div className="text-center p-12 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
        <SparklesIcon className="h-6 w-6 text-blue-600 dark:text-blue-300" />
      </div>
      <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">{title}</h3>
      <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
        {description}
      </p>
      {onAction && (
        <button
          onClick={onAction}
          className="mt-6 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          {actionText}
        </button>
      )}
    </div>
  );
}
