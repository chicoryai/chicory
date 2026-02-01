import { useState } from "react";
import { Form, useFetcher } from "@remix-run/react";
import { PlayIcon, TrashIcon, PencilIcon, ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/24/outline";
import { StatusBadge } from "./StatusBadge";
import { ScoreIndicator } from "./ScoreIndicator";
import { Button } from "./Button";
import type { Evaluation, EvaluationRun } from "~/services/chicory.server";

interface EvaluationCardProps {
  evaluation: Evaluation;
  latestRun?: EvaluationRun;
  onRun?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

export function EvaluationCard({
  evaluation,
  latestRun,
  onRun,
  onEdit,
  onDelete
}: EvaluationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const fetcher = useFetcher();
  const isRunning = fetcher.state === "submitting" && fetcher.formData?.get("intent") === "run";

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleRun = () => {
    if (onRun) {
      onRun();
    } else {
      fetcher.submit(
        { intent: "run", evaluation_id: evaluation.id },
        { method: "post" }
      );
    }
  };

  const handleDelete = () => {
    if (onDelete) {
      onDelete();
    } else {
      if (confirm(`Are you sure you want to delete the evaluation "${evaluation.name}"?`)) {
        fetcher.submit(
          { intent: "delete", evaluation_id: evaluation.id },
          { method: "post" }
        );
      }
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden transition-all duration-200 hover:shadow-md">
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
              {evaluation.name}
            </h3>
            {evaluation.description && (
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {evaluation.description}
              </p>
            )}
          </div>
          
          {latestRun && (
            <div className="ml-4 flex items-center gap-3">
              <StatusBadge 
                status={latestRun.status} 
                animated={latestRun.status === 'running'} 
              />
              {latestRun.overall_score !== null && (
                <ScoreIndicator
                  score={latestRun.overall_score}
                  variant="circular"
                  size="sm"
                />
              )}
            </div>
          )}
        </div>

        {latestRun && (
          <div className="grid grid-cols-3 gap-4 mb-4 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Test Cases</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {latestRun.completed_test_cases} / {latestRun.total_test_cases}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Failed</p>
              <p className="text-sm font-medium text-red-600 dark:text-red-400">
                {latestRun.failed_test_cases}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Pass Rate</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {latestRun.total_test_cases > 0 
                  ? Math.round(((latestRun.total_test_cases - latestRun.failed_test_cases) / latestRun.total_test_cases) * 100)
                  : 0}%
              </p>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={handleRun}
              disabled={isRunning || latestRun?.status === 'running'}
            >
              <PlayIcon className="h-4 w-4 mr-1" />
              {isRunning || latestRun?.status === 'running' ? 'Running...' : 'Run'}
            </Button>
            
            {onEdit && (
              <Button
                variant="tertiary"
                size="sm"
                onClick={onEdit}
              >
                <PencilIcon className="h-4 w-4" />
              </Button>
            )}
            
            <Button
              variant="tertiary"
              size="sm"
              onClick={handleDelete}
            >
              <TrashIcon className="h-4 w-4" />
            </Button>
          </div>

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
          >
            {isExpanded ? (
              <ChevronUpIcon className="h-5 w-5" />
            ) : (
              <ChevronDownIcon className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 px-6 py-4 bg-gray-50 dark:bg-gray-900/50">
          <div className="space-y-3">
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Evaluation Criteria
              </h4>
              <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                {evaluation.criteria}
              </p>
            </div>
            
            <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
              <span>Created: {formatDate(evaluation.created_at)}</span>
              {latestRun?.completed_at && (
                <span>Last run: {formatDate(latestRun.completed_at)}</span>
              )}
            </div>

            {latestRun && latestRun.test_case_results.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Recent Results
                </h4>
                <div className="space-y-1">
                  {latestRun.test_case_results.slice(0, 3).map((result, idx) => (
                    <div 
                      key={result.test_case_id}
                      className="flex items-center justify-between text-xs p-2 bg-white dark:bg-gray-800 rounded"
                    >
                      <span className="text-gray-600 dark:text-gray-400">
                        Test Case #{idx + 1}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className={result.passed ? "text-green-600" : "text-red-600"}>
                          {result.passed ? "✓ Passed" : "✗ Failed"}
                        </span>
                        <span className="text-gray-500">
                          {result.execution_time_ms}ms
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}