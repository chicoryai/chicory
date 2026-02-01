import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon } from '@heroicons/react/24/outline';
import type { EvaluationRun, TestCase } from '~/services/chicory.server';
import { StatusBadge } from '~/components/evaluation/StatusBadge';
import { TestResultDisplay } from '~/components/evaluation/results/TestResultDisplay';

interface RunDetailsModalProps {
  run: EvaluationRun;
  isOpen: boolean;
  onClose: () => void;
  testCases: TestCase[];
}

export function RunDetailsModal({ run, isOpen, onClose, testCases }: RunDetailsModalProps) {
  useEffect(() => {
    if (isOpen) {
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = 'unset';
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const modalContent = (
    <>
      {/* Backdrop with glassmorphism */}
      <div 
        className="fixed inset-0 bg-gray-900/60 dark:bg-black/70 backdrop-blur-md z-[9999]"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="fixed inset-4 md:inset-8 lg:inset-12 z-[10000] flex items-center justify-center pointer-events-none">
        <div className="bg-white/95 dark:bg-whitePurple-50/10 backdrop-blur-xl rounded-xl shadow-2xl border border-gray-200/50 dark:border-purple-900/30 max-w-7xl w-full max-h-full overflow-hidden pointer-events-auto">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200/50 dark:border-purple-900/20 bg-gray-50/50 dark:bg-purple-900/10 backdrop-blur-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Evaluation Run Details
                </h2>
                <StatusBadge status={run.status} />
                {run.overall_score !== null && (
                  <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {Math.round(run.overall_score * 100)}%
                  </span>
                )}
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-purple-800/30 transition-colors"
              >
                <XMarkIcon className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 12rem)' }}>
            {/* Run Information */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Started</span>
                <p className="text-sm text-gray-900 dark:text-gray-100">
                  {new Date(run.started_at + 'Z').toLocaleString()}
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Duration</span>
                <p className="text-sm text-gray-900 dark:text-gray-100">
                  {run.completed_at 
                    ? `${Math.round((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000)}s`
                    : 'In progress'
                  }
                </p>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-gray-400 uppercase">Test Cases</span>
                <p className="text-sm text-gray-900 dark:text-gray-100">
                  {run.completed_test_cases}/{run.total_test_cases}
                </p>
              </div>
            </div>

            {/* Progress bar for running evaluations */}
            {run.status === 'running' && (
              <div className="mb-6">
                <div className="h-2 bg-purple-900/20 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-purple-400 to-lime-400 transition-all duration-300"
                    style={{ width: `${(run.completed_test_cases / run.total_test_cases) * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Test Case Results */}
            {run.test_case_results && run.test_case_results.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase mb-4">
                  Test Case Results
                </h3>
                <div className="space-y-6">
                  {run.test_case_results.map((result, idx) => {
                    const isPassed = result.status === 'completed' && result.score >= 0.7;
                    const statusColor = result.status === 'completed' 
                      ? (isPassed ? 'text-green-400' : 'text-red-400')
                      : result.status === 'running_target' ? 'text-amber-400' 
                      : result.status === 'running_grader' ? 'text-amber-400' 
                      : result.status === 'failed' ? 'text-red-400'
                      : 'text-gray-400';
                    
                    // Find the matching test case to get the task
                    const testCase = testCases.find(tc => tc.id === result.test_case_id);
                    return (
                      <div 
                        key={result.test_case_id}
                        className="bg-white/60 dark:bg-gray-800/30 backdrop-blur-sm rounded-lg border border-gray-200/50 dark:border-purple-900/20 p-4"
                      >
                        {/* Status and Score Header */}
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-3">
                            <div className={`w-3 h-3 rounded-full ${
                              result.status === 'completed'
                                ? (isPassed ? 'bg-green-400' : 'bg-red-400')
                                : result.status === 'running_target' ? 'bg-amber-400 animate-pulse'
                                : result.status === 'running_grader' ? 'bg-amber-400 animate-pulse'
                                : result.status === 'failed' ? 'bg-red-400'
                                : 'bg-gray-400'
                            }`} />
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                              Test Case {idx + 1}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            {(result.status === 'running_target' || result.status === 'running_grader') && (
                              <svg className="animate-spin h-4 w-4 text-whitePurple-200 dark:text-lime-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                            )}
                            <span className={`text-sm font-bold ${statusColor}`}>
                              {result.status === 'completed' 
                                ? `${Math.round(result.score * 100)}%`
                                : result.status === 'running_target' ? 'Test Case Running'
                                : result.status === 'failed' ? 'Failed'
                                : result.status === 'running_grader' ? 'Grading'
                                : 'Running'
                              }
                            </span>
                          </div>
                        </div>
                        
                        {/* Test Case Task */}
                        {testCase?.task && (
                          <div className="mb-4 p-3 bg-gray-50/50 dark:bg-purple-900/10 rounded-lg border border-gray-200/30 dark:border-purple-900/20">
                            <span className="text-xs text-gray-500 dark:text-gray-400 uppercase font-semibold">Task</span>
                            <p className="text-sm text-gray-700 dark:text-gray-200 mt-1">
                              {testCase.task}
                            </p>
                          </div>
                        )}
                        
                        {/* Test Result Display */}
                        {(result.target_response || result.grader_response) && (
                          <TestResultDisplay
                            agentResponse={result.target_response || ''}
                            graderResponse={result.grader_response || ''}
                          />
                        )}
                        
                        {/* Error Message */}
                        {result.error_message && (
                          <div className="mt-3 p-3 bg-red-900/20 rounded border border-red-900/30">
                            <p className="text-sm text-red-400">
                              Error: {result.error_message}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Overall Error Message */}
            {run.status === 'failed' && run.error_message && (
              <div className="mt-6 p-4 bg-red-900/20 rounded-lg border border-red-900/30">
                <h4 className="text-sm font-semibold text-red-400 mb-2">Evaluation Failed</h4>
                <p className="text-sm text-red-400">
                  {run.error_message}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );

  // Render modal using React Portal to ensure it appears at the root level
  return createPortal(modalContent, document.body);
}