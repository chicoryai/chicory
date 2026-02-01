import { TrashIcon } from "@heroicons/react/24/outline";

interface DangerZoneProps {
  onDeleteAgent: () => void;
}

export default function DangerZone({ onDeleteAgent }: DangerZoneProps) {
  return (
    <div className="mt-8 border border-red-300 dark:border-red-700 rounded-lg bg-red-50 dark:bg-red-900/20 p-6">
      <h3 className="text-lg font-medium text-red-800 dark:text-red-400 mb-4">Danger Zone</h3>
      <p className="text-red-700 dark:text-red-300 mb-4">
        Deleting this agent will permanently remove it and all associated tasks. This action cannot be undone.
      </p>
      <button
        onClick={onDeleteAgent}
        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
      >
        <TrashIcon className="h-4 w-4 mr-2" />
        Delete Agent
      </button>
    </div>
  );
}
