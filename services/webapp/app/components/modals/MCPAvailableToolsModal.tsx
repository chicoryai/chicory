import { useState, useEffect, useRef, useMemo } from "react";
import { XMarkIcon, DocumentTextIcon, MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import MCPGatewayIcon from "~/components/icons/MCPGatewayIcon";

interface AvailableTool {
  name: string;
  description: string;
  parameters?: {
    type: string;
    required?: string[];
    properties?: Record<string, any>;
  };
}

interface MCPAvailableToolsModalProps {
  isOpen: boolean;
  onClose: () => void;
  toolName: string;
  availableTools: AvailableTool[];
}

export default function MCPAvailableToolsModal({ 
  isOpen, 
  onClose, 
  toolName,
  availableTools 
}: MCPAvailableToolsModalProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);
  
  // Filter tools based on search query
  const filteredTools = useMemo(() => {
    if (!searchQuery.trim()) return availableTools;
    
    const query = searchQuery.toLowerCase();
    return availableTools.filter(tool => 
      tool.name.toLowerCase().includes(query) ||
      tool.description?.toLowerCase().includes(query) ||
      (tool.parameters?.properties && 
        Object.keys(tool.parameters.properties).some(param => 
          param.toLowerCase().includes(query)
        )
      )
    );
  }, [availableTools, searchQuery]);
  
  // Focus search input when modal opens
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      setTimeout(() => searchInputRef.current?.focus(), 100);
    }
  }, [isOpen]);
  
  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K to focus search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k' && isOpen) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
      // Escape to close modal
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);
  
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
        <div className="relative inline-block w-full max-w-4xl align-middle transition-all transform">
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
                  <MCPGatewayIcon size={24} />
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-semibold bg-gradient-to-r from-purple-600 to-purple-500 bg-clip-text text-transparent">
                    Available Tools - {toolName}
                  </h3>
                  <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                    {filteredTools.length} of {availableTools.length} tool{availableTools.length !== 1 ? 's' : ''} shown
                  </p>
                </div>
              </div>
            </div>
            
            {/* Search Bar */}
            <div className="px-6 py-3 border-b border-gray-200/50 dark:border-gray-700/50">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" />
                </div>
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-10 py-2 rounded-lg border border-gray-300/50 dark:border-gray-600/50 
                    bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm
                    text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                    focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500 
                    hover:bg-white/70 dark:hover:bg-gray-800/70 transition-all"
                  placeholder="Search tools by name, description, or parameters..."
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  >
                    <XMarkIcon className="h-4 w-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" />
                  </button>
                )}
              </div>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Press ⌘K to focus search
              </p>
            </div>
          
            {/* Tools List */}
            <div className="p-6 max-h-[60vh] overflow-y-auto">
              {availableTools.length === 0 ? (
                <div className="text-center py-8">
                  <div className="mx-auto w-16 h-16 bg-gray-100 dark:bg-gray-800/50 rounded-full flex items-center justify-center mb-4">
                    <MCPGatewayIcon size={32} />
                  </div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white">No tools available</h3>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    This MCP server doesn't expose any tools
                  </p>
                </div>
              ) : filteredTools.length === 0 ? (
                <div className="text-center py-8">
                  <div className="mx-auto w-16 h-16 bg-gray-100 dark:bg-gray-800/50 rounded-full flex items-center justify-center mb-4">
                    <MagnifyingGlassIcon className="h-8 w-8 text-gray-400" />
                  </div>
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white">No tools found</h3>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Try adjusting your search query
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  {filteredTools.map((tool, index) => (
                    <div 
                      key={index}
                      className="group relative overflow-hidden
                        bg-white/60 dark:bg-gray-800/60 backdrop-blur-lg
                        border border-gray-200/50 dark:border-gray-700/50
                        rounded-xl p-4
                        hover:bg-white/80 dark:hover:bg-gray-800/80
                        hover:border-purple-300/50 dark:hover:border-purple-600/50
                        transition-all duration-300"
                    >
                      {/* Gradient overlay on hover */}
                      <div className="absolute inset-0 bg-gradient-to-r from-purple-500/0 via-purple-500/0 to-purple-600/0 
                        group-hover:from-purple-500/5 group-hover:via-purple-500/5 group-hover:to-purple-600/10 
                        transition-all duration-300 pointer-events-none" />
                      
                      <div className="relative space-y-3">
                        {/* Tool Name and Description */}
                        <div className="flex items-start space-x-3">
                          <div className="p-1.5 bg-purple-500/20 rounded-lg group-hover:bg-purple-500/30 transition-colors flex-shrink-0">
                            <DocumentTextIcon className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <h4 className="text-sm font-semibold text-gray-900 dark:text-white group-hover:text-purple-700 dark:group-hover:text-purple-300 transition-colors break-words">
                              {tool.name}
                            </h4>
                            {tool.description && (
                              <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                                {tool.description}
                              </p>
                            )}
                          </div>
                        </div>
                        
                        {/* Parameters */}
                        {tool.parameters && tool.parameters.properties && (
                          <div className="ml-9 space-y-1">
                            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Parameters:</p>
                            <div className="space-y-1">
                              {Object.entries(tool.parameters.properties).map(([paramName, paramDetails]: [string, any]) => (
                                <div key={paramName} className="flex items-start space-x-2">
                                  <span className="text-xs text-purple-600 dark:text-purple-400 font-mono">
                                    {paramName}
                                    {tool.parameters?.required?.includes(paramName) && '*'}
                                  </span>
                                  {paramDetails.description && (
                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                      - {paramDetails.description}
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200/50 dark:border-gray-700/50 bg-gray-50/50 dark:bg-gray-800/30">
              <button
                type="button"
                onClick={onClose}
                className="w-full px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 
                  bg-white/50 dark:bg-gray-700/50 backdrop-blur-sm
                  border border-gray-300/50 dark:border-gray-600/50 rounded-lg 
                  hover:bg-white/70 dark:hover:bg-gray-700/70 
                  focus:outline-none focus:ring-2 focus:ring-purple-500/50 transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
