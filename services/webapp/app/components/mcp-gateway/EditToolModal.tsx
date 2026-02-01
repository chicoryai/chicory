import { useFetcher } from "@remix-run/react";
import { useEffect, useState } from "react";
import type { MCPTool } from "~/services/chicory.server";

interface EditToolModalProps {
  isOpen: boolean;
  onClose: () => void;
  tool: MCPTool | null;
  gatewayId: string;
}

export function EditToolModal({ 
  isOpen, 
  onClose, 
  tool,
  gatewayId 
}: EditToolModalProps) {
  const fetcher = useFetcher();
  const [formData, setFormData] = useState({
    tool_name: '',
    description: '',
    output_format: '',
    input_schema: '',
    additionalProps: ''
  });
  
  // Initialize form data when tool changes
  useEffect(() => {
    if (tool) {
      setFormData({
        tool_name: tool.tool_name || '',
        description: tool.description || '',
        output_format: tool.output_format || '',
        input_schema: tool.input_schema ? JSON.stringify(tool.input_schema, null, 2) : '',
        additionalProps: tool.additionalProps ? JSON.stringify(tool.additionalProps, null, 2) : ''
      });
    }
  }, [tool]);
  
  // Track if we've submitted in this session
  const [hasSubmitted, setHasSubmitted] = useState(false);
  
  // Reset submission tracking when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setHasSubmitted(false);
    }
  }, [isOpen]);
  
  // Close modal on successful submission
  useEffect(() => {
    if (fetcher.state === 'idle' && fetcher.data?.success && hasSubmitted) {
      onClose();
      setHasSubmitted(false);
    }
  }, [fetcher.state, fetcher.data, hasSubmitted, onClose]);
  
  if (!isOpen || !tool) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const updates: any = {};
    
    // Only include changed fields
    if (formData.tool_name !== tool.tool_name) {
      updates.tool_name = formData.tool_name;
    }
    if (formData.description !== tool.description) {
      updates.description = formData.description;
    }
    if (formData.output_format !== tool.output_format) {
      updates.output_format = formData.output_format;
    }
    
    // Parse JSON fields if they're provided
    if (formData.input_schema) {
      try {
        updates.input_schema = JSON.parse(formData.input_schema);
      } catch (e) {
        // If parsing fails, don't include it
      }
    }
    
    if (formData.additionalProps) {
      try {
        updates.additionalProps = JSON.parse(formData.additionalProps);
      } catch (e) {
        // If parsing fails, don't include it
      }
    }
    
    setHasSubmitted(true);
    const formDataToSubmit = new FormData();
    formDataToSubmit.append("_action", "update-tool");
    formDataToSubmit.append("toolId", tool.id);
    formDataToSubmit.append("updates", JSON.stringify(updates));
    fetcher.submit(formDataToSubmit, { method: "post" });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-semibold mb-4">Edit Tool</h2>
        
        {/* Error display */}
        {fetcher.data?.error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400">
              {fetcher.data.error}
            </p>
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Tool Name */}
          <div>
            <label htmlFor="tool_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tool Name
            </label>
            <input
              type="text"
              id="tool_name"
              value={formData.tool_name}
              onChange={(e) => setFormData({ ...formData, tool_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Enter tool name"
            />
          </div>
          
          {/* Description */}
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 min-h-48"
              placeholder="Enter tool description"
            />
          </div>
          
          {/* Action buttons */}
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={fetcher.state !== 'idle'}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={fetcher.state !== 'idle'}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {fetcher.state !== 'idle' ? 'Updating...' : 'Update Tool'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}