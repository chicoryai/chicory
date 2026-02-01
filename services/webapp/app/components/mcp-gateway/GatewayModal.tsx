import { useFetcher } from "@remix-run/react";
import { useEffect, useState } from "react";
import type { MCPGateway } from "~/services/chicory.server";

interface ActionData {
  success?: boolean;
  error?: string;
}

interface GatewayModalProps {
  isOpen: boolean;
  onClose: () => void;
  gateway?: MCPGateway | null;
  mode: 'create' | 'edit';
  projectId?: string;
}

export function GatewayModal({ 
  isOpen, 
  onClose, 
  gateway, 
  mode,
  projectId 
}: GatewayModalProps) {
  const fetcher = useFetcher<ActionData>();
  const [hasSubmittedInSession, setHasSubmittedInSession] = useState(false);
  
  // Reset submission tracking when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setHasSubmittedInSession(false);
    }
  }, [isOpen]);
  
  // Close modal on successful submission from this session only
  useEffect(() => {
    if (fetcher.state === 'idle' && fetcher.data?.success && hasSubmittedInSession) {
      onClose();
      setHasSubmittedInSession(false);
    }
  }, [fetcher.state, fetcher.data, hasSubmittedInSession, onClose]);
  
  if (!isOpen) return null;

  const title = mode === 'create' ? 'Create MCP Gateway' : 'Edit MCP Gateway';
  const submitText = mode === 'create' ? 'Create Gateway' : 'Update Gateway';
  


  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-semibold mb-4">{title}</h2>
        <fetcher.Form 
          method="post"
          onSubmit={() => setHasSubmittedInSession(true)}
        >
          {/* Hidden fields for action type and gateway ID */}
          <input type="hidden" name="_action" value={mode === 'create' ? 'create' : 'update'} />
          {mode === 'edit' && gateway && (
            <input type="hidden" name="gatewayId" value={gateway.id} />
          )}
          
          <div className="mb-4">
            <label htmlFor="gateway-name" className="block text-sm font-medium mb-2">
              Gateway Name
            </label>
            <input
              type="text"
              id="gateway-name"
              name="name"
              defaultValue={gateway?.name || ''}
              required
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700"
              placeholder="My Gateway"
            />
          </div>
          
          <div className="mb-4">
            <label htmlFor="gateway-description" className="block text-sm font-medium mb-2">
              Description (optional)
            </label>
            <textarea
              id="gateway-description"
              name="description"
              defaultValue={gateway?.description || ''}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700"
              placeholder="Describe what this gateway is for..."
            />
          </div>
          
          {mode === 'edit' && (
            <div className="mb-6">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  name="enabled"
                  value="true"
                  defaultChecked={gateway?.enabled}
                  className="mr-2"
                />
                <span className="text-sm font-medium">Gateway Enabled</span>
              </label>
            </div>
          )}
          
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={fetcher.state !== 'idle'}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {fetcher.state !== 'idle' ? 'Saving...' : submitText}
            </button>
          </div>
        </fetcher.Form>
      </div>
    </div>
  );
}