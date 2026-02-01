import { ArrowRightIcon } from "@heroicons/react/24/outline";

interface AgentHeaderProps {
  onNavigateToPlayground: () => void;
}

export default function AgentHeader({ onNavigateToPlayground }: AgentHeaderProps) {
  return (
    <div className="px-6 py-4 dark:border-gray-700 flex justify-between items-center">
      <div className="flex-grow">
      </div>
      <div>
        <button
          onClick={onNavigateToPlayground}
          className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-lime-500 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
        >
          <ArrowRightIcon className="h-4 w-4 mr-1" />
          Playground
        </button>
      </div>
    </div>
  );
}
