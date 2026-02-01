import { useState, useEffect } from "react";
import { useFetcher } from "@remix-run/react";
import { 
  XMarkIcon, 
  PencilIcon, 
  TrashIcon, 
  ServerStackIcon, 
  KeyIcon, 
  CodeBracketIcon,
  CheckCircleIcon 
} from "@heroicons/react/24/outline";
import type { Tool } from "~/types/panels";
import MCPGatewayIcon from "~/components/icons/MCPGatewayIcon";

interface MCPToolDetailsModalProps {
  isOpen: boolean;
  tool: Tool;
  onClose: () => void;
  agentId: string;
  projectId?: string;
  onDelete?: () => void;
  onUpdate?: () => void;
}

export default function MCPToolDetailsModal({ 
  isOpen, 
  tool,
  onClose, 
  agentId,
  projectId,
  onDelete,
  onUpdate
}: MCPToolDetailsModalProps) {
  const fetcher = useFetcher();
  const [isEditMode, setIsEditMode] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  
  // Edit form states
  const [editName, setEditName] = useState(tool.name);
  const [editDescription, setEditDescription] = useState(tool.description || "");
  const [editProvider, setEditProvider] = useState(tool.provider || "MCP");
  const [editServerUrl, setEditServerUrl] = useState("");
  const [editAuthToken, setEditAuthToken] = useState("");
  const [editConfig, setEditConfig] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  // Parse tool config to get server details
  const getServerDetails = () => {
    try {
      const config = typeof tool.config === 'string' ? JSON.parse(tool.config) : tool.config;
      return {
        serverUrl: config.server_url || '',
        authToken: config.auth_token || '',
        availableTools: config.available_tools || []
      };
    } catch (e) {
      return { serverUrl: '', authToken: '', availableTools: [] };
    }
  };
  
  const { serverUrl, authToken, availableTools } = getServerDetails();
  
  // Initialize edit states when entering edit mode
  useEffect(() => {
    if (isEditMode) {
      setEditName(tool.name);
      setEditDescription(tool.description || "");
      setEditProvider(tool.provider || "MCP");
      setEditServerUrl(serverUrl);
      setEditAuthToken(authToken);
      
      const config = typeof tool.config === 'string' ? tool.config : JSON.stringify(tool.config, null, 2);
      setEditConfig(config);
    }
  }, [isEditMode, tool, serverUrl, authToken]);
  
  // Update config when URL or token changes in edit mode
  useEffect(() => {
    if (isEditMode && (editServerUrl || editAuthToken)) {
      const config = {
        server_url: editServerUrl,
        ...(editAuthToken && { auth_token: editAuthToken }),
        ...(availableTools.length > 0 && { available_tools: availableTools })
      };
      setEditConfig(JSON.stringify(config, null, 2));
    }
  }, [editServerUrl, editAuthToken, isEditMode, availableTools]);
  
  // Check if operation was successful
  useEffect(() => {
    const data = fetcher.data as any;
    if (data?.success) {
      if (data?.intent === "deleteTool") {
        onDelete?.();
      } else if (data?.intent === "updateTool") {
        setIsEditMode(false);
        onUpdate?.();
      }
    } else if (data?.error) {
      setErrors({ submit: data.error });
    }
  }, [fetcher.data, onDelete, onUpdate]);
  
  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    if (!editName.trim()) {
      newErrors.name = "Tool name is required";
    }
    
    if (!editServerUrl.trim()) {
      newErrors.serverUrl = "Server URL is required";
    } else {
      try {
        new URL(editServerUrl);
      } catch {
        newErrors.serverUrl = "Please enter a valid URL";
      }
    }
    
    if (!editConfig.trim()) {
      newErrors.config = "Configuration is required";
    } else {
      try {
        JSON.parse(editConfig);
      } catch {
        newErrors.config = "Invalid JSON configuration";
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    const formData = new FormData();
    formData.append("intent", "updateTool");
    formData.append("toolId", tool.id);
    formData.append("toolName", editName);
    formData.append("toolDescription", editDescription);
    formData.append("toolProvider", editProvider);
    formData.append("toolConfig", editConfig);
    
    const target = projectId ? `/projects/${projectId}/agents/${agentId}` : `/agents/${agentId}`;
    fetcher.submit(formData, { 
      method: "post",
      action: target
    });
  };
  
  const handleDelete = () => {
    const formData = new FormData();
    formData.append("intent", "deleteTool");
    formData.append("toolId", tool.id);
    
    const target = projectId ? `/projects/${projectId}/agents/${agentId}` : `/agents/${agentId}`;
    fetcher.submit(formData, { 
      method: "post",
      action: target
    });
  };
  
  const isSubmitting = fetcher.state !== "idle";
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen p-4">
        {/* Glassmorphism backdrop */}
        <div 
          className="fixed inset-0 bg-gradient-to-br from-purple-900/20 via-gray-900/50 to-purple-900/20 backdrop-blur-sm transition-opacity" 
          aria-hidden="true"
          onClick={onClose}
        />
        
        {/* Glassmorphism modal with purple theme */}
        <div className="relative inline-block w-full max-w-3xl align-middle transition-all transform">
          <div className="relative bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-purple-500/20 dark:border-purple-400/20 overflow-hidden max-h-[90vh] overflow-y-auto">
            {/* Purple gradient glow effect */}
            <div className="absolute inset-0 bg-gradient-to-br from-purple-500/10 via-transparent to-purple-600/10 pointer-events-none" />
            
            {/* Header with gradient */}
            <div className="relative px-6 pt-6 pb-4 bg-gradient-to-r from-purple-600/10 to-purple-500/10 border-b border-purple-500/20">
              <button
                type="button"
                className="absolute top-4 right-4 p-2 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-all focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                onClick={onClose}
              >
                <span className="sr-only">Close</span>
                <XMarkIcon className="h-5 w-5" />
              </button>
              
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-purple-500/20 rounded-lg backdrop-blur-sm">
                  <MCPGatewayIcon size={24} />
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold bg-gradient-to-r from-purple-600 to-purple-500 bg-clip-text text-transparent">
                    {isEditMode ? 'Edit MCP Tool' : showDeleteConfirm ? 'Delete MCP Tool' : 'MCP Tool Details'}
                  </h3>
                  {!isEditMode && !showDeleteConfirm && (
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                      View and manage your MCP tool configuration
                    </p>
                  )}
                </div>
                {!isEditMode && !showDeleteConfirm && (
                  <div className="flex space-x-2">
                    <button
                      onClick={() => setIsEditMode(true)}
                      className="p-2 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 backdrop-blur-sm text-purple-600 dark:text-purple-400 transition-all"
                      disabled={isSubmitting}
                    >
                      <PencilIcon className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => setShowDeleteConfirm(true)}
                      className="p-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 backdrop-blur-sm text-red-600 dark:text-red-400 transition-all"
                      disabled={isSubmitting}
                    >
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  </div>
                )}
              </div>
            </div>
            
            <div className="relative p-6">
              {showDeleteConfirm ? (
                // Delete Confirmation View
                <div className="text-center py-8">
                  <div className="mx-auto w-20 h-20 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mb-4">
                    <TrashIcon className="h-10 w-10 text-red-500" />
                  </div>
                  <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    Are you sure you want to delete "{tool.name}"?
                  </h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">
                    This action cannot be undone. The tool will be permanently removed from this agent.
                  </p>
                  <div className="flex justify-center space-x-3">
                    <button
                      onClick={() => setShowDeleteConfirm(false)}
                      className="px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 
                        bg-white/50 dark:bg-gray-700/50 backdrop-blur-sm
                        border border-gray-300/50 dark:border-gray-600/50 rounded-lg 
                        hover:bg-white/70 dark:hover:bg-gray-700/70 
                        focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition-all"
                      disabled={isSubmitting}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleDelete}
                      className="px-5 py-2.5 text-sm font-medium text-white 
                        bg-gradient-to-r from-red-600 to-red-500 
                        hover:from-red-700 hover:to-red-600
                        border border-transparent rounded-lg shadow-lg shadow-red-500/25
                        focus:outline-none focus:ring-2 focus:ring-red-500/50 
                        disabled:opacity-50 disabled:cursor-not-allowed 
                        flex items-center transition-all transform hover:scale-105"
                      disabled={isSubmitting}
                    >
                      {isSubmitting ? (
                        <>
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Deleting...
                        </>
                      ) : (
                        'Delete Tool'
                      )}
                    </button>
                  </div>
                </div>
              ) : isEditMode ? (
                // Edit Mode View
                <div className="space-y-6">
                  {errors.submit && (
                    <div className="p-3 bg-red-50/50 dark:bg-red-900/20 backdrop-blur-sm border border-red-200/50 dark:border-red-800/50 rounded-lg">
                      <p className="text-sm text-red-800 dark:text-red-200">{errors.submit}</p>
                    </div>
                  )}
                  
                  <form onSubmit={handleUpdate} className="space-y-5">
                    {/* Tool Name */}
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                        Tool Name *
                      </label>
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className={`w-full px-4 py-2.5 rounded-lg border backdrop-blur-sm transition-all
                          ${errors.name 
                            ? 'border-red-300 dark:border-red-600 bg-red-50/50 dark:bg-red-900/10' 
                            : 'border-gray-300/50 dark:border-gray-600/50 bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-800/70 focus:bg-white dark:focus:bg-gray-800'
                          }
                          text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                          focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500`}
                        disabled={isSubmitting}
                      />
                      {errors.name && (
                        <p className="text-xs text-red-600 dark:text-red-400">{errors.name}</p>
                      )}
                    </div>
                    
                    {/* Description */}
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                        Description
                      </label>
                      <textarea
                        value={editDescription}
                        onChange={(e) => setEditDescription(e.target.value)}
                        rows={3}
                        className="w-full px-4 py-2.5 rounded-lg border border-gray-300/50 dark:border-gray-600/50 
                          bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-800/70 
                          focus:bg-white dark:focus:bg-gray-800 backdrop-blur-sm
                          text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                          focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500 transition-all resize-none"
                        placeholder="Brief description of what this tool does"
                        disabled={isSubmitting}
                      />
                    </div>
                    
                    {/* Provider */}
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                        Provider
                      </label>
                      <input
                        type="text"
                        value={editProvider}
                        onChange={(e) => setEditProvider(e.target.value)}
                        className="w-full px-4 py-2.5 rounded-lg border border-gray-300/50 dark:border-gray-600/50 
                          bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-800/70 
                          focus:bg-white dark:focus:bg-gray-800 backdrop-blur-sm
                          text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                          focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500 transition-all"
                        placeholder="MCP"
                        disabled={isSubmitting}
                      />
                    </div>
                    
                    {/* Server Configuration */}
                    <div className="space-y-4 p-4 rounded-xl bg-gradient-to-br from-purple-50/50 to-purple-100/30 dark:from-purple-900/20 dark:to-purple-800/10 backdrop-blur-sm border border-purple-200/30 dark:border-purple-700/30">
                      <h4 className="text-sm font-semibold text-purple-900 dark:text-purple-200 flex items-center">
                        <MCPGatewayIcon size={16} className="mr-2" /> Server Configuration
                      </h4>
                      
                      {/* URL */}
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                          URL *
                        </label>
                        <input
                          type="text"
                          value={editServerUrl}
                          onChange={(e) => setEditServerUrl(e.target.value)}
                          className={`w-full px-4 py-2.5 rounded-lg border backdrop-blur-sm transition-all
                            ${errors.serverUrl 
                              ? 'border-red-300 dark:border-red-600 bg-red-50/50 dark:bg-red-900/10' 
                              : 'border-purple-300/50 dark:border-purple-600/50 bg-white/70 dark:bg-gray-800/50 hover:bg-white/90 dark:hover:bg-gray-800/70 focus:bg-white dark:focus:bg-gray-800'
                            }
                            text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                            focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500`}
                          placeholder="http://localhost:3000"
                          disabled={isSubmitting}
                        />
                        {errors.serverUrl && (
                          <p className="text-xs text-red-600 dark:text-red-400">{errors.serverUrl}</p>
                        )}
                      </div>
                      
                      {/* Token */}
                      <div className="space-y-2">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                          Token
                        </label>
                        <input
                          type="password"
                          value={editAuthToken}
                          onChange={(e) => setEditAuthToken(e.target.value)}
                          className="w-full px-4 py-2.5 rounded-lg border border-purple-300/50 dark:border-purple-600/50 
                            bg-white/70 dark:bg-gray-800/50 hover:bg-white/90 dark:hover:bg-gray-800/70 
                            focus:bg-white dark:focus:bg-gray-800 backdrop-blur-sm
                            text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                            focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500 transition-all"
                          placeholder="Optional authentication token"
                          disabled={isSubmitting}
                        />
                      </div>
                    </div>
                    
                    {/* Configuration JSON */}
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                        Configuration (JSON)
                      </label>
                      <div className="relative">
                        <textarea
                          value={editConfig}
                          onChange={(e) => setEditConfig(e.target.value)}
                          rows={6}
                          className={`w-full px-4 py-3 rounded-lg border backdrop-blur-sm transition-all font-mono text-xs
                            ${errors.config 
                              ? 'border-red-300 dark:border-red-600 bg-red-50/50 dark:bg-red-900/10' 
                              : 'border-gray-300/50 dark:border-gray-600/50 bg-gray-900/90 dark:bg-gray-900/80'
                            }
                            text-green-400 placeholder-gray-500 dark:placeholder-gray-600
                            focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500`}
                          disabled={isSubmitting}
                        />
                        <div className="absolute top-2 right-2 px-2 py-1 bg-gray-800/50 backdrop-blur-sm rounded text-xs text-gray-400">
                          JSON
                        </div>
                      </div>
                      {errors.config && (
                        <p className="text-xs text-red-600 dark:text-red-400">{errors.config}</p>
                      )}
                    </div>
                    
                    {/* Action Buttons */}
                    <div className="flex justify-end space-x-3 pt-2">
                      <button
                        type="button"
                        onClick={() => setIsEditMode(false)}
                        className="px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 
                          bg-white/50 dark:bg-gray-700/50 backdrop-blur-sm
                          border border-gray-300/50 dark:border-gray-600/50 rounded-lg 
                          hover:bg-white/70 dark:hover:bg-gray-700/70 
                          focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition-all"
                        disabled={isSubmitting}
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="px-5 py-2.5 text-sm font-medium text-white 
                          bg-gradient-to-r from-purple-600 to-purple-500 
                          hover:from-purple-700 hover:to-purple-600
                          border border-transparent rounded-lg shadow-lg shadow-purple-500/25
                          focus:outline-none focus:ring-2 focus:ring-purple-500/50 
                          disabled:opacity-50 disabled:cursor-not-allowed 
                          flex items-center transition-all transform hover:scale-105"
                        disabled={isSubmitting}
                      >
                        {isSubmitting ? (
                          <>
                            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Updating...
                          </>
                        ) : (
                          'Update Tool'
                        )}
                      </button>
                    </div>
                  </form>
                </div>
              ) : (
                // View Mode
                <div className="space-y-6">
                  {/* Tool Information Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Tool Name */}
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Tool Name
                      </label>
                      <div className="p-3 rounded-lg bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border border-gray-300/50 dark:border-gray-600/50">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">{tool.name}</p>
                      </div>
                    </div>
                    
                    {/* Provider */}
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Provider
                      </label>
                      <div className="p-3 rounded-lg bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border border-gray-300/50 dark:border-gray-600/50">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">{tool.provider || 'MCP'}</p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Description */}
                  {tool.description && (
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Description
                      </label>
                      <div className="p-3 rounded-lg bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border border-gray-300/50 dark:border-gray-600/50">
                        <p className="text-sm text-gray-700 dark:text-gray-300">{tool.description}</p>
                      </div>
                    </div>
                  )}
                  
                  {/* Server Configuration */}
                  <div className="space-y-4 p-4 rounded-xl bg-gradient-to-br from-purple-50/50 to-purple-100/30 dark:from-purple-900/20 dark:to-purple-800/10 backdrop-blur-sm border border-purple-200/30 dark:border-purple-700/30">
                    <h4 className="text-sm font-semibold text-purple-900 dark:text-purple-200 flex items-center">
                      <ServerStackIcon className="h-4 w-4 mr-2" />
                      Server Configuration
                    </h4>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* URL */}
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400 flex items-center">
                          <CodeBracketIcon className="h-3 w-3 mr-1" />
                          URL
                        </label>
                        <div className="p-2.5 rounded-lg bg-white/70 dark:bg-gray-800/50 backdrop-blur-sm">
                          <p className="text-sm font-mono text-purple-600 dark:text-purple-400 break-all">{serverUrl || 'Not configured'}</p>
                        </div>
                      </div>
                      
                      {/* Token Status */}
                      <div className="space-y-2">
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400 flex items-center">
                          <KeyIcon className="h-3 w-3 mr-1" />
                          Authentication
                        </label>
                        <div className="p-2.5 rounded-lg bg-white/70 dark:bg-gray-800/50 backdrop-blur-sm">
                          <p className="text-sm text-gray-700 dark:text-gray-300 flex items-center">
                            {authToken ? (
                              <>
                                <CheckCircleIcon className="h-4 w-4 mr-1 text-green-500" />
                                Token configured
                              </>
                            ) : (
                              'No authentication'
                            )}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Configuration JSON */}
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Configuration JSON
                    </label>
                    <div className="relative">
                      <pre className="p-4 rounded-lg bg-gray-900/90 dark:bg-gray-900/80 backdrop-blur-sm border border-gray-300/50 dark:border-gray-600/50 overflow-x-auto">
                        <code className="text-xs font-mono text-green-400">
                          {typeof tool.config === 'string' ? tool.config : JSON.stringify(tool.config, null, 2)}
                        </code>
                      </pre>
                      <div className="absolute top-2 right-2 px-2 py-1 bg-gray-800/50 backdrop-blur-sm rounded text-xs text-gray-400">
                        JSON
                      </div>
                    </div>
                  </div>
                  
                  {/* Available Tools */}
                  {availableTools.length > 0 && (
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Available Tools ({availableTools.length})
                      </label>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                        {availableTools.map((toolName: string, index: number) => (
                          <div 
                            key={index} 
                            className="px-3 py-2 rounded-lg bg-purple-50/50 dark:bg-purple-900/20 backdrop-blur-sm border border-purple-200/50 dark:border-purple-700/50"
                          >
                            <p className="text-xs font-medium text-purple-700 dark:text-purple-300">{toolName}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
