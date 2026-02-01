import { useFetcher } from "@remix-run/react";
import { useEffect } from "react";
import type { MCPGateway } from "~/services/chicory.server";

interface DeleteConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  gateway: MCPGateway | null;
}

interface ActionData {
  success?: boolean;
  error?: string;
}

export function DeleteConfirmationModal({ 
  isOpen, 
  onClose, 
  gateway 
}: DeleteConfirmationModalProps) {
  const fetcher = useFetcher<ActionData>();
  
  // Close modal on successful deletion
  // The server redirect will handle navigation
  useEffect(() => {
    if (fetcher.state === 'idle' && fetcher.data) {
      if (fetcher.data.success) {
        onClose();
      }
      // If there's an error, keep the modal open to show the error
    }
  }, [fetcher.state, fetcher.data, onClose]);
  
  if (!isOpen || !gateway) return null;

  const handleDelete = () => {
    const formData = new FormData();
    formData.append("_action", "delete");
    formData.append("gatewayId", gateway.id);
    fetcher.submit(formData, { method: "post" });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-semibold mb-4">Delete Gateway</h2>
        
        {fetcher.data?.error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400">
              {fetcher.data.error}
            </p>
          </div>
        )}
        
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          {fetcher.state === 'submitting' || fetcher.state === 'loading' ? (
            <>Deleting gateway "{gateway.name}"...</>
          ) : (
            <>
              Are you sure you want to delete the gateway "{gateway.name}"? 
              This action cannot be undone.
            </>
          )}
        </p>
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            disabled={fetcher.state !== 'idle'}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleDelete}
            disabled={fetcher.state !== 'idle'}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {fetcher.state !== 'idle' ? 'Deleting...' : 'Delete Gateway'}
          </button>
        </div>
      </div>
    </div>
  );
}