import { useState, useEffect } from "react";
import { useFetcher } from "@remix-run/react";
import { XMarkIcon, SparklesIcon } from "@heroicons/react/24/outline";
import MCPGatewayIcon from "~/components/icons/MCPGatewayIcon";

interface AddMCPToolModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentId: string;
  onSuccess?: () => void;
  actionPath?: string;
}

export default function AddMCPToolModal({ 
  isOpen, 
  onClose, 
  agentId, 
  onSuccess,
  actionPath
}: AddMCPToolModalProps) {
  const fetcher = useFetcher();
  
  const [toolName, setToolName] = useState("");
  const [serverUrl, setServerUrl] = useState("");
  const [authToken, setAuthToken] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  // Check if submission was successful
  useEffect(() => {
    if (fetcher.data?.success) {
      onSuccess?.();
      resetForm();
    } else if (fetcher.data?.error) {
      setErrors({ submit: fetcher.data.error });
    }
  }, [fetcher.data, onSuccess]);
  
  const resetForm = () => {
    setToolName("");
    setServerUrl("");
    setAuthToken("");
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
    
    const config = {
      server_url: serverUrl,
      ...(authToken && { headers: { Authorization: `Bearer ${authToken}` } })
    };

    const normalizedName = toolName.trim();
    const description = normalizedName ? `${normalizedName} MCP tool` : "MCP tool";

    const formData = new FormData();
    formData.append("intent", "addTool");
    formData.append("toolName", normalizedName);
    formData.append("toolDescription", description);
    formData.append("toolProvider", "MCP");
    formData.append("toolType", "mcp");
    formData.append("type", "mcp");
    formData.append("toolConfig", JSON.stringify(config));
    
    fetcher.submit(formData, {
      method: "post",
      action: actionPath ?? '.'
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
        <div className="relative inline-block w-full max-w-2xl align-middle transition-all transform">
          <div className="relative bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-purple-500/20 dark:border-purple-400/20 overflow-hidden">
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
                  <SparklesIcon className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold bg-gradient-to-r from-purple-600 to-purple-500 bg-clip-text text-transparent">
                    Add MCP Tool
                  </h3>
                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    Configure a new Model Context Protocol tool for this agent
                  </p>
                </div>
              </div>
            </div>
          
            <div className="p-6 space-y-6">
              {errors.submit && (
                <div className="p-3 bg-red-50/50 dark:bg-red-900/20 backdrop-blur-sm border border-red-200/50 dark:border-red-800/50 rounded-lg">
                  <p className="text-sm text-red-800 dark:text-red-200">{errors.submit}</p>
                </div>
              )}
              
              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Name */}
                <div className="space-y-2">
                  <label htmlFor="toolName" className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                    Name *
                  </label>
                  <input
                    type="text"
                    id="toolName"
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

                {/* Server Configuration Section */}
                <div className="space-y-4 p-4 rounded-xl bg-gradient-to-br from-purple-50/50 to-purple-100/30 dark:from-purple-900/20 dark:to-purple-800/10 backdrop-blur-sm border border-purple-200/30 dark:border-purple-700/30">
                  <h4 className="text-sm font-semibold text-purple-900 dark:text-purple-200 flex items-center">
                    <MCPGatewayIcon size={16} className="mr-2" /> Server Configuration
                  </h4>
                  
                  {/* URL - Fourth */}
                  <div className="space-y-2">
                    <label htmlFor="serverUrl" className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                      URL *
                    </label>
                    <input
                      type="text"
                      id="serverUrl"
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
                  
                  {/* Token - Fifth */}
                  <div className="space-y-2">
                    <label htmlFor="authToken" className="block text-sm font-medium text-gray-700 dark:text-gray-200">
                      Token
                    </label>
                    <input
                      type="password"
                      id="authToken"
                      value={authToken}
                      onChange={(e) => setAuthToken(e.target.value)}
                      className="w-full px-4 py-2.5 rounded-lg border border-purple-300/50 dark:border-purple-600/50 
                        bg-white/70 dark:bg-gray-800/50 hover:bg-white/90 dark:hover:bg-gray-800/70 
                        focus:bg-white dark:focus:bg-gray-800 backdrop-blur-sm
                        text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                        focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500 transition-all"
                      placeholder="Optional authentication token"
                      disabled={isSubmitting}
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Leave empty if the MCP server doesn't require authentication
                    </p>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex justify-end space-x-3 pt-2">
                  <button
                    type="button"
                    onClick={onClose}
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
                        Adding Tool...
                      </>
                    ) : (
                      'Add Tool'
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
