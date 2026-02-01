import { useState, useEffect } from "react";
import { useFetcher } from "@remix-run/react";
import { 
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ChevronRightIcon,
  ServerStackIcon,
  KeyIcon,
  CheckCircleIcon,
  CommandLineIcon
} from "@heroicons/react/24/outline";
import type { Tool } from "~/types/panels";
import MCPAvailableToolsModal from "~/components/modals/MCPAvailableToolsModal";
import MCPGatewayIcon from "~/components/icons/MCPGatewayIcon";

interface MCPToolsPanelProps {
  tools: Tool[];
  agentId: string;
  projectId?: string;
}

type ViewMode = 'list' | 'add' | 'view' | 'edit';

export function MCPToolsPanel({ tools, agentId }: MCPToolsPanelProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showAvailableToolsModal, setShowAvailableToolsModal] = useState(false);
  const [selectedToolForModal, setSelectedToolForModal] = useState<Tool | null>(null);
  
  // Helper functions for default tools
  const isDefaultTool = (tool: Tool) => tool.name === "default_tools";
  const getDisplayName = (tool: Tool) => isDefaultTool(tool) ? "Default Tools" : tool.name;
  
  // Form states for add/edit
  const [toolName, setToolName] = useState("");
  const [toolDescription, setToolDescription] = useState("");
  const [serverUrl, setServerUrl] = useState("");
  const [authToken, setAuthToken] = useState("");
  const [existingToken, setExistingToken] = useState(""); // Store original token when editing
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  const fetcher = useFetcher();
  const isSubmitting = fetcher.state !== "idle";
  
  const parseToolConfig = (tool: Tool | null) => {
    if (!tool) return null;
    try {
      return typeof tool.config === 'string' ? JSON.parse(tool.config) : tool.config;
    } catch {
      return null;
    }
  };
  
  // Parse tool config to get server details
  const getServerDetails = (tool: Tool | null) => {
    const config = parseToolConfig(tool);
    if (!config) {
      return { serverUrl: '', authToken: '', config: null };
    }
    
    let authToken = '';
    if (config.headers?.Authorization) {
      authToken = config.headers.Authorization.replace(/^Bearer\s+/i, '');
    }
    
    return {
      serverUrl: config.server_url || '',
      authToken,
      config
    };
  };
  
  // Check if submission was successful
  useEffect(() => {
    const data = fetcher.data as any;
    if (data?.success) {
      if (data?.intent === 'addTool' || data?.intent === 'updateTool') {
        setViewMode('list');
        resetForm();
      } else if (data?.intent === 'deleteTool') {
        setViewMode('list');
        setSelectedTool(null);
        setShowDeleteConfirm(false);
      }
    } else if (data?.error) {
      setErrors({ submit: data.error });
    }
  }, [fetcher.data]);
  
  // Initialize form when editing
  useEffect(() => {
    if (viewMode === 'edit' && selectedTool) {
      const { serverUrl: url, authToken: token } = getServerDetails(selectedTool);
      setToolName(selectedTool.name);
      setToolDescription(selectedTool.description || "");
      setServerUrl(url);
      setAuthToken(""); // Don't populate the actual token for security
      setExistingToken(token); // Store the existing token
      setErrors({});
    }
  }, [viewMode, selectedTool]);
  
  const resetForm = () => {
    setToolName("");
    setToolDescription("");
    setServerUrl("");
    setAuthToken("");
    setExistingToken("");
    setErrors({});
  };
  
  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    if (!toolName.trim()) {
      newErrors.name = "Tool name is required";
    }
    
    if (!serverUrl.trim()) {
      newErrors.serverUrl = "Server URL is required";
    } else {
      try {
        new URL(serverUrl);
      } catch {
        newErrors.serverUrl = "Please enter a valid URL";
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    // Use existing token if no new token provided during edit
    const tokenToUse = viewMode === 'edit' && !authToken ? existingToken : authToken;
    
    const config = {
      server_url: serverUrl,
      ...(tokenToUse && { headers: { Authorization: `Bearer ${tokenToUse}` } })
    };
    
    const formData = new FormData();
    formData.append("intent", viewMode === 'add' ? "addTool" : "updateTool");
    if (viewMode === 'edit' && selectedTool) {
      formData.append("toolId", selectedTool.id);
    }
    formData.append("toolName", toolName);
    formData.append("toolDescription", toolDescription);
    formData.append("toolProvider", "MCP");
    formData.append("toolConfig", JSON.stringify(config));
    
    fetcher.submit(formData, { 
      method: "post"
    });
  };
  
  const handleDelete = () => {
    if (!selectedTool) return;
    
    const formData = new FormData();
    formData.append("intent", "deleteTool");
    formData.append("toolId", selectedTool.id);
    
    fetcher.submit(formData, { 
      method: "post"
    });
  };
  
  const handleAddClick = () => {
    resetForm();
    setViewMode('add');
  };
  
  const handleToolClick = (tool: Tool) => {
    // Don't allow viewing/editing default tools
    if (isDefaultTool(tool)) {
      return;
    }
    setSelectedTool(tool);
    setViewMode('view');
  };
  
  const handleEditClick = () => {
    setViewMode('edit');
  };
  
  const handleBackToList = () => {
    setViewMode('list');
    setSelectedTool(null);
    resetForm();
  };
  
  return (
    <div className="h-full flex flex-col">
      {/* Back button for non-list views */}
      {viewMode !== 'list' && (
        <div className="px-4 py-3 border-b border-gray-200/50 dark:border-gray-700/50">
          <button
            onClick={handleBackToList}
            className="inline-flex items-center text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <ChevronRightIcon className="h-4 w-4 mr-1 rotate-180" />
            Back to Tools
          </button>
        </div>
      )}
      
      
      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-4">
        {viewMode === 'list' ? (
          // List View
          <div className="space-y-4">
            {/* Add Tool Button at the top */}
            <button
              onClick={handleAddClick}
              className="w-full py-3 px-4 rounded-xl
                bg-gradient-to-r from-purple-600/10 to-purple-500/10
                border-2 border-dashed border-purple-400/30 dark:border-purple-600/30
                hover:from-purple-600/20 hover:to-purple-500/20
                hover:border-purple-500/50 dark:hover:border-purple-500/50
                transition-all duration-200 group"
              disabled={isSubmitting}
            >
              <div className="flex items-center justify-center space-x-2">
                <div className="p-1.5 bg-purple-500/20 rounded-lg group-hover:bg-purple-500/30 transition-colors">
                  <PlusIcon className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                </div>
                <span className="text-sm font-medium text-purple-700 dark:text-purple-300">
                  Add MCP Tool
                </span>
              </div>
            </button>
            
            {/* Tools List */}
            {tools.length === 0 ? (
              <div className="text-center py-8">
                <div className="mx-auto w-16 h-16 bg-gray-100 dark:bg-gray-800/50 rounded-full flex items-center justify-center mb-4">
                  <MCPGatewayIcon size={32} />
                </div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">No tools configured</h3>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Click the button above to add your first MCP tool
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {tools.map((tool) => {
                  const { serverUrl } = getServerDetails(tool);
                  const isDefault = isDefaultTool(tool);
                  return (
                    <div 
                      key={tool.id} 
                      className={`group relative overflow-hidden
                        bg-white/60 dark:bg-gray-800/60 backdrop-blur-lg
                        border border-gray-200/50 dark:border-gray-700/50
                        rounded-xl
                        ${!isDefault ? 'hover:bg-white/80 dark:hover:bg-gray-800/80 hover:border-purple-300/50 dark:hover:border-purple-600/50 hover:shadow-lg hover:shadow-purple-500/10 cursor-pointer' : ''}
                        transition-all duration-300`}
                      onClick={() => !isDefault && handleToolClick(tool)}
                    >
                      {/* Gradient overlay on hover - only for non-default tools */}
                      {!isDefault && (
                        <div className="absolute inset-0 bg-gradient-to-r from-purple-500/0 via-purple-500/0 to-purple-600/0 
                          group-hover:from-purple-500/5 group-hover:via-purple-500/5 group-hover:to-purple-600/10 
                          transition-all duration-300 pointer-events-none" />
                      )}
                      
                      <div className="relative p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1 space-y-3">
                            {/* Tool Name and Icon */}
                            <div className="flex items-start space-x-3">
                              <div className="p-2 bg-gradient-to-br from-purple-500/20 to-purple-600/20 rounded-lg backdrop-blur-sm
                                group-hover:from-purple-500/30 group-hover:to-purple-600/30 transition-colors">
                                <MCPGatewayIcon size={20} />
                              </div>
                              <div className="flex-1">
                                <h4 className="text-base font-semibold text-gray-900 dark:text-white group-hover:text-purple-700 dark:group-hover:text-purple-300 transition-colors">
                                  {getDisplayName(tool)}
                                </h4>
                                {tool.description && (
                                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                                    {tool.description}
                                  </p>
                                )}
                              </div>
                            </div>
                            
                            {/* Server URL and Available Tools */}
                            <div className="flex items-center justify-between">
                              {serverUrl && (
                                <div className="flex items-center space-x-1.5">
                                  <ServerStackIcon className="h-3.5 w-3.5 text-gray-400" />
                                  <span className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[200px]">
                                    {serverUrl}
                                  </span>
                                </div>
                              )}
                              
                              {/* View Available Tools Button */}
                              {(() => {
                                const parsedConfig = parseToolConfig(tool);
                                const availableTools = parsedConfig?.available_tools;
                                if (!Array.isArray(availableTools) || availableTools.length === 0) {
                                  return null;
                                }
                                return (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setSelectedToolForModal(tool);
                                      setShowAvailableToolsModal(true);
                                    }}
                                    className="inline-flex items-center space-x-1 px-2 py-1 text-xs font-medium 
                                      text-purple-700 dark:text-purple-300 
                                      bg-purple-100/50 dark:bg-purple-900/30 
                                      hover:bg-purple-200/50 dark:hover:bg-purple-800/40
                                      rounded-lg transition-all"
                                  >
                                    <CommandLineIcon className="h-3 w-3" />
                                    <span>{availableTools.length} tools</span>
                                  </button>
                                );
                              })()}
                            </div>
                          </div>
                          
                          {/* Arrow Icon - only show for non-default tools */}
                          {!isDefault && (
                            <div className="ml-3 p-2 rounded-lg bg-gray-100/50 dark:bg-gray-700/50 
                              group-hover:bg-purple-100/50 dark:group-hover:bg-purple-900/30 transition-all">
                              <ChevronRightIcon className="h-4 w-4 text-gray-400 group-hover:text-purple-500 transition-colors" />
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : viewMode === 'add' || viewMode === 'edit' ? (
          // Add/Edit Form
          <form onSubmit={handleSubmit} className="space-y-5">
            {errors.submit && (
              <div className="p-3 bg-red-50/50 dark:bg-red-900/20 backdrop-blur-sm border border-red-200/50 dark:border-red-800/50 rounded-lg">
                <p className="text-sm text-red-800 dark:text-red-200">{errors.submit}</p>
              </div>
            )}
            
            {/* Tool Name */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                Tool Name *
              </label>
              <input
                type="text"
                value={toolName}
                onChange={(e) => setToolName(e.target.value)}
                className={`w-full px-4 py-2.5 rounded-lg border backdrop-blur-sm transition-all
                  ${errors.name 
                    ? 'border-red-300 dark:border-red-600 bg-red-50/50 dark:bg-red-900/10' 
                    : 'border-gray-300/50 dark:border-gray-600/50 bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-800/70 focus:bg-white dark:focus:bg-gray-800'
                  }
                  text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                  focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500`}
                placeholder="e.g., HuggingFace, Slack, GitHub"
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
                value={toolDescription}
                onChange={(e) => setToolDescription(e.target.value)}
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
            
            {/* Server Configuration */}
            <div className="space-y-4 p-4 rounded-xl bg-gradient-to-br from-purple-50/50 to-purple-100/30 dark:from-purple-900/20 dark:to-purple-800/10 backdrop-blur-sm border border-purple-200/30 dark:border-purple-700/30">
              <h4 className="text-sm font-semibold text-purple-900 dark:text-purple-200 flex items-center">
                <ServerStackIcon className="h-4 w-4 mr-2" />
                Server Configuration
              </h4>
              
              {/* URL */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                  URL *
                </label>
                <input
                  type="text"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
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
                  Token {viewMode === 'edit' && existingToken && (
                    <span className="text-xs text-purple-600 dark:text-purple-400 ml-2">
                      (Token configured - leave empty to keep existing)
                    </span>
                  )}
                </label>
                <input
                  type="password"
                  value={authToken}
                  onChange={(e) => setAuthToken(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-lg border border-purple-300/50 dark:border-purple-600/50 
                    bg-white/70 dark:bg-gray-800/50 hover:bg-white/90 dark:hover:bg-gray-800/70 
                    focus:bg-white dark:focus:bg-gray-800 backdrop-blur-sm
                    text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                    focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500 transition-all"
                  placeholder={viewMode === 'edit' && existingToken 
                    ? "Enter new token or leave empty to keep existing" 
                    : "Optional authentication token"}
                  disabled={isSubmitting}
                />
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {viewMode === 'edit' && existingToken 
                    ? "Current token is hidden for security. Enter a new token to replace it, or leave empty to keep the existing token."
                    : "Leave empty if the MCP server doesn't require authentication"}
                </p>
              </div>
            </div>
            
            {/* Action Buttons */}
            <div className="flex justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={handleBackToList}
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
                    {viewMode === 'add' ? 'Adding...' : 'Updating...'}
                  </>
                ) : (
                  viewMode === 'add' ? 'Add Tool' : 'Update Tool'
                )}
              </button>
            </div>
          </form>
        ) : viewMode === 'view' && selectedTool ? (
          // View Details
          <div className="space-y-6">
            {showDeleteConfirm ? (
              // Delete Confirmation
              <div className="text-center py-8">
                <div className="mx-auto w-20 h-20 bg-red-100 dark:bg-red-900/20 rounded-full flex items-center justify-center mb-4">
                  <TrashIcon className="h-10 w-10 text-red-500" />
                </div>
                <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  Are you sure you want to delete "{selectedTool.name}"?
                </h4>
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-8">
                  This action cannot be undone.
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
            ) : (
              // Tool Details View
              <>
                {/* Action Buttons */}
                <div className="flex justify-end space-x-2">
                  <button
                    onClick={handleEditClick}
                    className="p-2 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 backdrop-blur-sm text-purple-600 dark:text-purple-400 transition-all"
                    disabled={isSubmitting}
                  >
                    <PencilIcon className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(true)}
                    className="p-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 backdrop-blur-sm text-red-600 dark:text-red-400 transition-all"
                    disabled={isSubmitting}
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
                
                {/* Tool Information */}
                <div className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Name
                    </label>
                    <div className="p-3 rounded-lg bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border border-gray-300/50 dark:border-gray-600/50">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{selectedTool.name}</p>
                    </div>
                  </div>
                  
                  {selectedTool.description && (
                    <div className="space-y-2">
                      <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Description
                      </label>
                      <div className="p-3 rounded-lg bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border border-gray-300/50 dark:border-gray-600/50">
                        <p className="text-sm text-gray-700 dark:text-gray-300">{selectedTool.description}</p>
                      </div>
                    </div>
                  )}
                  
                  
                  {/* Server Configuration */}
                  <div className="space-y-4 p-4 rounded-xl bg-gradient-to-br from-purple-50/50 to-purple-100/30 dark:from-purple-900/20 dark:to-purple-800/10 backdrop-blur-sm border border-purple-200/30 dark:border-purple-700/30">
                    <h4 className="text-sm font-semibold text-purple-900 dark:text-purple-200 flex items-center">
                      <ServerStackIcon className="h-4 w-4 mr-2" />
                      Server Configuration
                    </h4>
                    
                    <div className="space-y-3">
                      <div className="space-y-1">
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400">URL</label>
                        <div className="p-2.5 rounded-lg bg-white/70 dark:bg-gray-800/50 backdrop-blur-sm">
                          <p className="text-sm font-mono text-purple-600 dark:text-purple-400 break-all">
                            {getServerDetails(selectedTool).serverUrl || 'Not configured'}
                          </p>
                        </div>
                      </div>
                      
                      <div className="space-y-1">
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400 flex items-center">
                          <KeyIcon className="h-3 w-3 mr-1" />
                          Authentication
                        </label>
                        <div className="p-2.5 rounded-lg bg-white/70 dark:bg-gray-800/50 backdrop-blur-sm">
                          <p className="text-sm text-gray-700 dark:text-gray-300 flex items-center">
                            {getServerDetails(selectedTool).authToken ? (
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
                </div>
              </>
            )}
          </div>
        ) : null}
      </div>
      
      {/* Available Tools Modal */}
      {showAvailableToolsModal && selectedToolForModal && (
        <MCPAvailableToolsModal
          isOpen={showAvailableToolsModal}
          onClose={() => {
            setShowAvailableToolsModal(false);
            setSelectedToolForModal(null);
          }}
          toolName={getDisplayName(selectedToolForModal)}
          availableTools={(() => {
            const parsedConfig = parseToolConfig(selectedToolForModal);
            return Array.isArray(parsedConfig?.available_tools) ? parsedConfig.available_tools : [];
          })()}
        />
      )}
    </div>
  );
}
