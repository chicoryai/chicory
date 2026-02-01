/**
 * MCPToolsSection Component
 * Tool selection and management interface
 */

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PlusIcon, XMarkIcon } from "@heroicons/react/24/outline";
import type { Tool, ToolSelectionProps } from "~/types/panels";

export function MCPToolsSection({
  availableTools,
  selectedTools,
  onToolsChange,
  isLoading = false,
  className = "",
}: ToolSelectionProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [showAddTools, setShowAddTools] = useState(false);

  // Filter available tools
  const unselectedTools = availableTools.filter(
    (tool) => !selectedTools.includes(tool.id)
  );

  const filteredTools = unselectedTools.filter(
    (tool) =>
      tool.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tool.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Add tool
  const handleAddTool = useCallback(
    (toolId: string) => {
      onToolsChange([...selectedTools, toolId]);
      setSearchTerm("");
    },
    [selectedTools, onToolsChange]
  );

  // Remove tool
  const handleRemoveTool = useCallback(
    (toolId: string) => {
      onToolsChange(selectedTools.filter((id) => id !== toolId));
    },
    [selectedTools, onToolsChange]
  );

  // Get tool by ID
  const getToolById = (toolId: string): Tool | undefined => {
    return availableTools.find((tool) => tool.id === toolId);
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Best Practice Tip */}
      <div className="px-3 py-2 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
        <p className="text-xs text-purple-700 dark:text-purple-300">
          <span className="font-medium">Best Practice:</span> Only grant tools that are necessary for your agent's purpose. This improves security and helps the agent focus on relevant actions.
        </p>
      </div>

      {/* Selected Tools */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Selected Tools ({selectedTools.length})
          </h4>
          <button
            onClick={() => setShowAddTools(!showAddTools)}
            className="
              inline-flex items-center gap-1 px-2 py-1
              text-xs font-medium text-purple-600 dark:text-purple-400
              hover:bg-purple-50 dark:hover:bg-purple-900/30
              rounded transition-colors
            "
          >
            <PlusIcon className="w-3 h-3" />
            Add Tool
          </button>
        </div>

        {selectedTools.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 rounded-lg">
            <p className="mb-1">No tools selected yet</p>
            <p className="text-xs">Click "Add Tool" above to get started</p>
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence>
              {selectedTools.map((toolId) => {
                const tool = getToolById(toolId);
                if (!tool) return null;

                return (
                  <motion.div
                    key={tool.id}
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.2 }}
                    className="
                      flex items-start justify-between p-3
                      bg-purple-50 dark:bg-purple-900/20
                      border border-purple-200 dark:border-purple-800
                      rounded-lg
                    "
                  >
                    <div className="flex-1">
                      <h5 className="text-sm font-medium text-gray-900 dark:text-white">
                        {tool.name}
                      </h5>
                      {tool.description && (
                        <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                          {tool.description}
                        </p>
                      )}
                      <div className="flex gap-2 mt-2">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
                          {tool.provider || "MCP"}
                        </span>
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                          {tool.tool_type || "mcp"}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveTool(tool.id)}
                      className="
                        p-1 rounded hover:bg-purple-100 dark:hover:bg-purple-900/50
                        transition-colors
                      "
                      title="Remove tool"
                    >
                      <XMarkIcon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                    </button>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Add Tools Panel */}
      <AnimatePresence>
        {showAddTools && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-gray-200 dark:border-gray-700 pt-4"
          >
            <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Available MCP Tools
            </h4>

            {/* Search */}
            <input
              type="text"
              placeholder="Search tools..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="
                w-full px-3 py-2 mb-3
                border border-gray-300 dark:border-gray-600
                rounded-lg text-sm
                bg-white dark:bg-gray-700
                text-gray-900 dark:text-white
                placeholder-gray-400 dark:placeholder-gray-500
                focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
              "
            />

            {/* Available tools list */}
            <div className="max-h-48 overflow-y-auto space-y-2">
              {filteredTools.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                  {searchTerm ? "No tools found" : "All tools have been added"}
                </p>
              ) : (
                filteredTools.map((tool) => (
                  <motion.div
                    key={tool.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="
                      flex items-center justify-between p-2
                      bg-gray-50 dark:bg-gray-900
                      hover:bg-gray-100 dark:hover:bg-gray-800
                      rounded cursor-pointer
                      transition-colors
                    "
                    onClick={() => handleAddTool(tool.id)}
                  >
                    <div className="flex-1">
                      <h5 className="text-sm font-medium text-gray-900 dark:text-white">
                        {tool.name}
                      </h5>
                      {tool.description && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          {tool.description}
                        </p>
                      )}
                    </div>
                    <PlusIcon className="w-4 h-4 text-gray-400" />
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}