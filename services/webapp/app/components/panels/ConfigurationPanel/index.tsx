/**
 * ConfigurationPanel Component
 * Main panel for agent configuration settings
 */

import { useState, useCallback, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import type { ConfigurationPanelProps, AgentConfig } from "~/types/panels";
import { CollapsibleSection } from "~/components/ui/Collapsible";
import { BasicConfiguration } from "./BasicConfiguration";
import { SystemInstructions } from "./SystemInstructions";
import { Button } from "~/components/Button";
import { listContainerVariants, listItemVariants } from "~/components/animations/transitions";
import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";

export function ConfigurationPanel({
  agent,
  tools,
  onSave,
  onReset,
  onDelete,
  isLoading = false,
  error = null,
  className = "",
}: ConfigurationPanelProps) {
  const computedConfig = useMemo<AgentConfig>(() => ({
    name: agent.name || "",
    description: agent.description || "",
    systemInstructions: agent.instructions || "",
    outputFormat: agent.output_format || "",
    tools: [], // Tools will be loaded separately
    isDirty: false,
  }), [agent.description, agent.instructions, agent.name, agent.output_format]);

  // Initialize configuration state from agent
  const [config, setConfig] = useState<AgentConfig>(computedConfig);

  // Track if configuration has changed
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Sync configuration when the active agent changes
  useEffect(() => {
    setConfig(computedConfig);
    setIsDirty(false);
  }, [computedConfig]);

  // Check if configuration has changed
  useEffect(() => {
    const hasChanges = 
      config.name !== agent.name ||
      config.description !== agent.description ||
      config.systemInstructions !== agent.instructions ||
      config.outputFormat !== agent.output_format;
    // Note: tools comparison is omitted as they're managed separately
    
    setIsDirty(hasChanges);
  }, [config, agent]);

  // Handle configuration updates
  const updateConfig = useCallback((updates: Partial<AgentConfig>) => {
    setConfig(prev => ({
      ...prev,
      ...updates,
      isDirty: true,
    }));
    setSaveError(null);
  }, []);

  // Handle save
  const handleSave = useCallback(async () => {
    if (!isDirty) return;
    
    setIsSaving(true);
    setSaveError(null);
    
    try {
      await onSave(config);
      setIsDirty(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save configuration");
    } finally {
      setIsSaving(false);
    }
  }, [config, isDirty, onSave]);

  // Handle reset
  const handleReset = useCallback(() => {
    setConfig(computedConfig);
    setIsDirty(false);
    setSaveError(null);
    onReset();
  }, [computedConfig, onReset]);
  
  // Handle delete
  const handleDelete = useCallback(async () => {
    if (!onDelete) return;
    
    setIsDeleting(true);
    try {
      await onDelete();
      // Navigation will be handled by the parent
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to delete agent");
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  }, [onDelete]);
  
  return (
    <motion.div
      className={`flex flex-col h-full ${className}`}
      variants={listContainerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Configuration Sections */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <motion.div variants={listItemVariants}>
          <CollapsibleSection
            title="Basic Configuration"
            defaultOpen={true}
            icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            }
          >
            <BasicConfiguration
              name={config.name}
              description={config.description}
              outputFormat={config.outputFormat}
              onNameChange={(name) => updateConfig({ name })}
              onDescriptionChange={(description) => updateConfig({ description })}
              onOutputFormatChange={(outputFormat) => updateConfig({ outputFormat })}
            />
          </CollapsibleSection>
        </motion.div>

        <motion.div variants={listItemVariants}>
          <CollapsibleSection
            title="System Instructions"
            defaultOpen={true}
            icon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            }
          >
            <SystemInstructions
              value={config.systemInstructions}
              onChange={(systemInstructions) => updateConfig({ systemInstructions })}
            />
          </CollapsibleSection>
        </motion.div>
        
        {/* Danger Zone */}
        {onDelete && (
          <motion.div variants={listItemVariants}>
            <CollapsibleSection
              title="Danger Zone"
              defaultOpen={false}
              icon={
                <ExclamationTriangleIcon className="w-4 h-4 text-red-500" />
              }
            >
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <h4 className="text-sm font-medium text-red-800 dark:text-red-200 mb-2">
                  Delete Agent
                </h4>
                <p className="text-sm text-red-600 dark:text-red-400 mb-4">
                  Once you delete an agent, there is no going back. Please be certain.
                </p>
                <Button
                  variant="danger"
                  onClick={() => setShowDeleteModal(true)}
                  className="bg-red-600 hover:bg-red-700 text-white"
                >
                  Delete Agent
                </Button>
              </div>
            </CollapsibleSection>
          </motion.div>
        )}
      </div>

      {/* Action Bar */}
      <div className="p-4 bg-transparent dark:bg-gray-900/50">
        {/* Error message */}
        {(error || saveError) && (
          <div className="mb-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400">
              {error?.message || saveError}
            </p>
          </div>
        )}

        {/* Dirty state indicator */}
        {isDirty && (
          <div className="mb-3 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-xs text-yellow-600 dark:text-yellow-400">
              You have unsaved changes
            </p>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3">
          <Button
            variant="secondary"
            onClick={handleReset}
            disabled={!isDirty || isSaving}
            className="flex-1"
          >
            Reset
          </Button>
          <Button
            variant="primary"
            onClick={handleSave}
            disabled={!isDirty || isSaving || isLoading}
            className="flex-1"
          >
            {isSaving ? (
              <span className="flex items-center gap-2">
                <motion.div
                  className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                />
                Saving...
              </span>
            ) : (
              "Save Changes"
            )}
          </Button>
        </div>
      </div>
      
      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div 
              className="fixed inset-0 transition-opacity" 
              aria-hidden="true"
              onClick={() => !isDeleting && setShowDeleteModal(false)}
            >
              <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
            </div>
            
            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full sm:p-6">
              <div className="sm:flex sm:items-start">
                <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100 dark:bg-red-900 sm:mx-0 sm:h-10 sm:w-10">
                  <ExclamationTriangleIcon className="h-6 w-6 text-red-600 dark:text-red-400" aria-hidden="true" />
                </div>
                <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                  <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white">
                    Delete Agent
                  </h3>
                  <div className="mt-2">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Are you sure you want to delete <strong>{agent.name}</strong>? All of the agent's data will be permanently removed. This action cannot be undone.
                    </p>
                  </div>
                </div>
              </div>
              <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={handleDelete}
                  disabled={isDeleting}
                >
                  {isDeleting ? (
                    <span className="flex items-center gap-2">
                      <motion.div
                        className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                      />
                      Deleting...
                    </span>
                  ) : (
                    "Delete"
                  )}
                </button>
                <button
                  type="button"
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-700 text-base font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 sm:mt-0 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={() => setShowDeleteModal(false)}
                  disabled={isDeleting}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
