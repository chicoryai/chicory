/**
 * EvaluationsPanel Component
 * Main panel for agent evaluations management
 */

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PlusIcon, PlayIcon, TrashIcon } from "@heroicons/react/24/outline";
import type { EvaluationsPanelProps } from "~/types/panels";
import { Button } from "~/components/Button";
import { listContainerVariants, listItemVariants } from "~/components/animations/transitions";

export function EvaluationsPanel({
  agent,
  evaluations,
  stats,
  onRunEvaluation,
  onCreateEvaluation,
  onDeleteEvaluation,
  onEditEvaluation,
  currentRun,
  isLoading = false,
  error = null,
  className = "",
}: EvaluationsPanelProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedEvaluation, setSelectedEvaluation] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  // Filter evaluations based on search
  const filteredEvaluations = evaluations.filter((evaluation) =>
    evaluation.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    evaluation.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Handle run evaluation
  const handleRun = useCallback(async (evalId: string) => {
    setIsRunning(true);
    try {
      await onRunEvaluation(evalId);
    } finally {
      setIsRunning(false);
    }
  }, [onRunEvaluation]);

  return (
    <motion.div
      className={`flex flex-col h-full ${className}`}
      variants={listContainerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Stats Dashboard */}
      <motion.div 
        className="p-4 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700"
        variants={listItemVariants}
      >
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white dark:bg-gray-800 p-3 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Total Evaluations</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white">
              {stats.totalEvaluations || 0}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 p-3 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Avg Pass Rate</p>
            <p className="text-xl font-bold text-green-600 dark:text-green-400">
              {stats.avgPassRate ? `${Math.round(stats.avgPassRate)}%` : "N/A"}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 p-3 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Total Runs</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white">
              {stats.totalRuns || 0}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 p-3 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Test Cases</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white">
              {stats.totalTestCases || 0}
            </p>
          </div>
        </div>
      </motion.div>

      {/* Search and Actions */}
      <motion.div className="p-4 space-y-3" variants={listItemVariants}>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Search evaluations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="
              flex-1 px-3 py-2
              border border-gray-300 dark:border-gray-600
              rounded-lg
              bg-white dark:bg-gray-700
              text-gray-900 dark:text-white
              placeholder-gray-400 dark:placeholder-gray-500
              focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
            "
          />
          <Button
            variant="primary"
            onClick={onCreateEvaluation}
            className="flex items-center gap-2"
          >
            <PlusIcon className="w-4 h-4" />
            New
          </Button>
        </div>
      </motion.div>

      {/* Evaluations List */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {error && (
          <motion.div 
            className="p-3 mb-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
            variants={listItemVariants}
          >
            <p className="text-sm text-red-600 dark:text-red-400">{error.message}</p>
          </motion.div>
        )}

        {filteredEvaluations.length === 0 ? (
          <motion.div 
            className="text-center py-12"
            variants={listItemVariants}
          >
            <div className="text-gray-500 dark:text-gray-400">
              {searchTerm ? (
                <p>No evaluations found matching "{searchTerm}"</p>
              ) : (
                <>
                  <p className="text-lg font-medium mb-2">No evaluations yet</p>
                  <p className="text-sm mb-4">Create your first evaluation to test your agent</p>
                  <Button variant="primary" onClick={onCreateEvaluation}>
                    <PlusIcon className="w-4 h-4 mr-2" />
                    Create Evaluation
                  </Button>
                </>
              )}
            </div>
          </motion.div>
        ) : (
          <motion.div className="space-y-3" variants={listContainerVariants}>
            {filteredEvaluations.map((evaluation) => (
              <motion.div
                key={evaluation.id}
                variants={listItemVariants}
                className={`
                  p-4 bg-white dark:bg-gray-800 
                  border border-gray-200 dark:border-gray-700
                  rounded-lg cursor-pointer
                  hover:shadow-md hover:border-purple-300 dark:hover:border-purple-600
                  transition-all duration-200
                  ${selectedEvaluation === evaluation.id ? "ring-2 ring-purple-500" : ""}
                `}
                onClick={() => setSelectedEvaluation(evaluation.id)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-white">
                      {evaluation.name}
                    </h4>
                    {evaluation.description && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        {evaluation.description}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRun(evaluation.id);
                      }}
                      disabled={isRunning}
                      className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      title="Run evaluation"
                    >
                      <PlayIcon className="w-4 h-4 text-green-600 dark:text-green-400" />
                    </button>
                    {onEditEvaluation && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onEditEvaluation(evaluation.id);
                        }}
                        className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                        title="Edit evaluation"
                      >
                        <svg className="w-4 h-4 text-gray-600 dark:text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                    )}
                    {onDeleteEvaluation && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(`Delete evaluation "${evaluation.name}"?`)) {
                            onDeleteEvaluation(evaluation.id);
                          }
                        }}
                        className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                        title="Delete evaluation"
                      >
                        <TrashIcon className="w-4 h-4 text-red-600 dark:text-red-400" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Evaluation metadata */}
                <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                  <span>Created: {new Date(evaluation.created_at).toLocaleDateString()}</span>
                  {evaluation.updated_at && (
                    <span>Updated: {new Date(evaluation.updated_at).toLocaleDateString()}</span>
                  )}
                </div>

                {/* Current run progress */}
                {currentRun && currentRun.evaluation_id === evaluation.id && (
                  <div className="mt-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-blue-600 dark:text-blue-400">Running...</span>
                      <span className="text-xs text-blue-600 dark:text-blue-400">
                        {currentRun.completed_test_cases}/{currentRun.total_test_cases}
                      </span>
                    </div>
                    <div className="w-full bg-blue-100 dark:bg-blue-900 rounded-full h-1.5">
                      <motion.div
                        className="bg-blue-600 dark:bg-blue-400 h-1.5 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${(currentRun.completed_test_cases / currentRun.total_test_cases) * 100}%` }}
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                  </div>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>

      {/* Import/Export Actions */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-800/50">
        <div className="flex gap-2 text-xs">
          <button className="flex-1 py-2 text-gray-600 dark:text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
            Import CSV
          </button>
          <button className="flex-1 py-2 text-gray-600 dark:text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 transition-colors">
            Export Results
          </button>
        </div>
      </div>
    </motion.div>
  );
}