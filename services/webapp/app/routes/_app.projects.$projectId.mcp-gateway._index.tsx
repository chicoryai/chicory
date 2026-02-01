import { ServerIcon } from "@heroicons/react/24/outline";

export default function McpGatewayIndexPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full p-8">
      <ServerIcon className="h-16 w-16 text-gray-400 mb-4" />
      <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
        Select a Gateway
      </h2>
      <p className="text-gray-500 dark:text-gray-400 text-center max-w-md">
        Choose a gateway from the list on the left to view its details, manage tools, and access the API endpoint.
      </p>
    </div>
  );
}