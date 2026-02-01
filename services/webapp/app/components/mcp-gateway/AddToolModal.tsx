import { useFetcher } from "@remix-run/react";
import { useEffect, useState } from "react";
import type { Agent } from "~/services/chicory.server";
import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";

interface AddToolModalProps {
  isOpen: boolean;
  onClose: () => void;
  agents: Agent[];
  gatewayId: string;
}

export function AddToolModal({ 
  isOpen, 
  onClose, 
  agents,
  gatewayId 
}: AddToolModalProps) {
  const fetcher = useFetcher();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  
  // Filter agents based on search term
  const filteredAgents = agents.filter(agent => 
    agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (agent.description && agent.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );
  
  // Close modal on successful submission
  useEffect(() => {
    if (fetcher.state === 'idle' && fetcher.data?.success) {
      onClose();
      setSelectedAgentId(null);
      setSearchTerm("");
    }
  }, [fetcher.state, fetcher.data, onClose]);
  
  if (!isOpen) return null;

  const handleAddTool = () => {
    if (!selectedAgentId) return;
    
    const formData = new FormData();
    formData.append("_action", "add-tool");
    formData.append("agentId", selectedAgentId);
    formData.append("gatewayId", gatewayId);
    fetcher.submit(formData, { method: "post" });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[80vh] flex flex-col">
        <h2 className="text-xl font-semibold mb-4">Add Agent as Tool</h2>
        
        {/* Search input */}
        <div className="relative mb-4">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search agents..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        
        {/* Error display */}
        {fetcher.data?.error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400">
              {fetcher.data.error}
            </p>
          </div>
        )}
        
        {/* Agents list */}
        <div className="flex-1 overflow-y-auto mb-4 space-y-2">
          {filteredAgents.length === 0 ? (
            <p className="text-center text-gray-500 dark:text-gray-400 py-8">
              {searchTerm ? 'No agents found matching your search' : 'No agents available'}
            </p>
          ) : (
            filteredAgents.map((agent) => (
              <div
                key={agent.id}
                onClick={() => setSelectedAgentId(agent.id)}
                className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                  selectedAgentId === agent.id
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="font-medium text-sm">{agent.name}</h3>
                    {agent.description && (
                      <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                        {agent.description}
                      </p>
                    )}
                    <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500 dark:text-gray-500">
                      <span>ID: {agent.id.substring(0, 8)}...</span>
                      {agent.output_format && (
                        <span>Output: {agent.output_format}</span>
                      )}
                      <span className={`px-2 py-0.5 rounded ${
                        agent.deployed 
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
                      }`}>
                        {agent.deployed ? 'Deployed' : 'Not Deployed'}
                      </span>
                    </div>
                  </div>
                  {selectedAgentId === agent.id && (
                    <div className="ml-2">
                      <svg className="h-5 w-5 text-indigo-600 dark:text-indigo-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
        
        {/* Action buttons */}
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            disabled={fetcher.state !== 'idle'}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleAddTool}
            disabled={!selectedAgentId || fetcher.state !== 'idle'}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {fetcher.state !== 'idle' ? 'Adding...' : 'Add Tool'}
          </button>
        </div>
      </div>
    </div>
  );
}