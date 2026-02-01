import { useEffect, useState, useRef } from "react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { StatusBadge } from "./StatusBadge";
import { Button } from "./Button";
import type { EvaluationRun } from "~/services/chicory.server";

interface EvaluationRunStatusProps {
  run: EvaluationRun;
  onCancel?: () => void;
  streamUrl?: string;
}

export function EvaluationRunStatus({
  run: initialRun,
  onCancel,
  streamUrl
}: EvaluationRunStatusProps) {
  const [run, setRun] = useState(initialRun);
  const [estimatedTime, setEstimatedTime] = useState<number | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const startTimeRef = useRef<number>(Date.now());

  const progress = run.total_test_cases > 0 
    ? (run.completed_test_cases / run.total_test_cases) * 100 
    : 0;

  useEffect(() => {
    setRun(initialRun);
  }, [initialRun]);

  useEffect(() => {
    if (!streamUrl || run.status === 'completed' || run.status === 'failed') {
      return;
    }

    // Set up Server-Sent Events connection
    eventSourceRef.current = new EventSource(streamUrl);

    eventSourceRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'progress') {
          setRun(prev => ({
            ...prev,
            status: data.data.status,
            completed_test_cases: data.data.completed,
            total_test_cases: data.data.total,
            overall_score: data.data.score
          }));

          // Calculate estimated time remaining
          if (data.data.completed > 0 && data.data.completed < data.data.total) {
            const elapsed = Date.now() - startTimeRef.current;
            const rate = data.data.completed / elapsed;
            const remaining = (data.data.total - data.data.completed) / rate;
            setEstimatedTime(Math.round(remaining / 1000));
          }
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error);
      }
    };

    eventSourceRef.current.onerror = (error) => {
      console.error('SSE connection error:', error);
      eventSourceRef.current?.close();
    };

    return () => {
      eventSourceRef.current?.close();
    };
  }, [streamUrl, run.status]);

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getProgressBarColor = () => {
    if (run.status === 'failed') return 'bg-red-500';
    if (run.status === 'completed') {
      if (run.overall_score && run.overall_score >= 80) return 'bg-green-500';
      if (run.overall_score && run.overall_score >= 60) return 'bg-lime-500';
      if (run.overall_score && run.overall_score >= 40) return 'bg-yellow-500';
      return 'bg-orange-500';
    }
    return 'bg-purple-500';
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Evaluation Run Progress
          </h3>
          <StatusBadge 
            status={run.status} 
            animated={run.status === 'running'}
            size="md"
          />
        </div>
        
        {run.status === 'running' && onCancel && (
          <Button
            variant="tertiary"
            size="sm"
            onClick={onCancel}
          >
            <XMarkIcon className="h-4 w-4 mr-1" />
            Cancel
          </Button>
        )}
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
          <span>
            {run.completed_test_cases} / {run.total_test_cases} test cases
          </span>
          {estimatedTime !== null && run.status === 'running' && (
            <span>~{formatTime(estimatedTime)} remaining</span>
          )}
        </div>
        
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ease-out ${getProgressBarColor()}`}
            style={{ width: `${progress}%` }}
          >
            {run.status === 'running' && (
              <div className="h-full bg-white/20 animate-pulse" />
            )}
          </div>
        </div>
        
        <div className="mt-2 text-center">
          <span className="text-2xl font-bold text-gray-900 dark:text-white">
            {Math.round(progress)}%
          </span>
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-3 gap-4 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Completed</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {run.completed_test_cases}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Failed</p>
          <p className="text-lg font-semibold text-red-600 dark:text-red-400">
            {run.failed_test_cases}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Score</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {run.overall_score !== null ? `${Math.round(run.overall_score)}%` : '-'}
          </p>
        </div>
      </div>

      {/* Timestamps */}
      <div className="mt-4 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>Started: {new Date(run.started_at).toLocaleTimeString()}</span>
        {run.completed_at && (
          <span>Completed: {new Date(run.completed_at).toLocaleTimeString()}</span>
        )}
      </div>

      {/* Live Test Results (if streaming) */}
      {run.status === 'running' && run.test_case_results.length > 0 && (
        <div className="mt-4 border-t border-gray-200 dark:border-gray-700 pt-4">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Recent Results
          </h4>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {run.test_case_results.slice(-5).reverse().map((result, idx) => (
              <div 
                key={`${result.test_case_id}-${idx}`}
                className="flex items-center justify-between text-xs p-2 bg-gray-50 dark:bg-gray-900/50 rounded animate-fadeIn"
              >
                <span className="text-gray-600 dark:text-gray-400 truncate flex-1">
                  Test Case {result.test_case_id.slice(0, 8)}...
                </span>
                <div className="flex items-center gap-2 ml-2">
                  <span className={result.passed ? "text-green-600" : "text-red-600"}>
                    {result.passed ? "✓" : "✗"}
                  </span>
                  <span className="text-gray-500">
                    {result.score}%
                  </span>
                  <span className="text-gray-400">
                    {result.execution_time_ms}ms
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}