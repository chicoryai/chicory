import React from 'react';
import type { Evaluation, EvaluationRun } from '~/services/chicory.server';
import { ScoreIndicator } from '~/components/evaluation/ScoreIndicator';
import {
  DocumentTextIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';

interface EvaluationOverviewProps {
  evaluation: Evaluation;
  runs: EvaluationRun[];
}

export function EvaluationOverview({ evaluation, runs }: EvaluationOverviewProps) {
  // Calculate statistics
  const completedRuns = runs.filter(r => r.status === 'completed');
  const avgScore = completedRuns.length > 0
    ? completedRuns.reduce((sum, r) => sum + (r.overall_score || 0), 0) / completedRuns.length
    : 0;
  const successRate = completedRuns.length > 0
    ? (completedRuns.filter(r => (r.overall_score || 0) >= 0.7).length / completedRuns.length) * 100
    : 0;
  
  // Calculate additional performance metrics
  const avgDuration = completedRuns.length > 0
    ? completedRuns.reduce((sum, r) => {
        if (r.completed_at && r.started_at) {
          const duration = (new Date(r.completed_at).getTime() - new Date(r.started_at).getTime()) / 1000;
          return sum + duration;
        }
        return sum;
      }, 0) / completedRuns.filter(r => r.completed_at && r.started_at).length
    : 0;
  
  // Performance trend (last 5 runs)
  const recentRuns = completedRuns.slice(0, 5);
  const isImproving = recentRuns.length >= 2 
    ? (recentRuns[0].overall_score || 0) > (recentRuns[recentRuns.length - 1].overall_score || 0)
    : false;
  
  return (
    <div className="space-y-6">
      {/* Details */}
      <div className="relative shadow-sm shadow-whitePurple-100 dark:shadow-none bg-white/25 dark:bg-whitePurple-50/5 backdrop-blur-lg rounded-lg p-6 border border-whitePurple-100/70 dark:border-purple-900/20">
        <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-white/5 dark:from-transparent dark:to-transparent rounded-lg pointer-events-none" />
        <h3 className="relative text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Evaluation Details</h3>
        <dl className="relative grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm text-gray-600 dark:text-gray-400">Created</dt>
            <dd className="text-gray-800 dark:text-gray-300">{new Date(evaluation.created_at).toLocaleDateString()}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-600 dark:text-gray-400">Criteria</dt>
            <dd className="text-gray-800 dark:text-gray-300">{evaluation.criteria || 'Not specified'}</dd>
          </div>
        </dl>
      </div>
      
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="relative shadow-sm shadow-whitePurple-100 dark:shadow-none bg-white/25 dark:bg-whitePurple-50/5 backdrop-blur-lg rounded-lg p-4 border border-whitePurple-100/70 dark:border-purple-900/20">
          <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-white/5 dark:from-transparent dark:to-transparent rounded-lg pointer-events-none" />
          <div className="relative flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Average Score</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">
                {Math.round(avgScore * 100)}%
              </p>
            </div>
            <ScoreIndicator score={avgScore * 100} size="sm" />
          </div>
        </div>
        
        <div className="relative shadow-sm shadow-whitePurple-100 dark:shadow-none bg-white/25 dark:bg-whitePurple-50/5 backdrop-blur-lg rounded-lg p-4 border border-whitePurple-100/70 dark:border-purple-900/20">
          <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-white/5 dark:from-transparent dark:to-transparent rounded-lg pointer-events-none" />
          <div className="relative flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Success Rate</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">
                {Math.round(successRate)}%
              </p>
            </div>
            <CheckCircleIcon className="w-8 h-8 text-green-400" />
          </div>
        </div>
        
        <div className="relative shadow-sm shadow-whitePurple-100 dark:shadow-none bg-white/25 dark:bg-whitePurple-50/5 backdrop-blur-lg rounded-lg p-4 border border-whitePurple-100/70 dark:border-purple-900/20">
          <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-white/5 dark:from-transparent dark:to-transparent rounded-lg pointer-events-none" />
          <div className="relative flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Runs</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">
                {runs.length}
              </p>
            </div>
            <ClockIcon className="w-8 h-8 text-purple-400" />
          </div>
        </div>
      </div>
      
      
      {/* Recent Performance */}
      {completedRuns.length > 0 && (
        <div className="relative shadow-sm shadow-whitePurple-100 dark:shadow-none bg-white/25 dark:bg-whitePurple-50/5 backdrop-blur-lg rounded-lg p-6 border border-whitePurple-100/70 dark:border-purple-900/20">
          <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-white/5 dark:from-transparent dark:to-transparent rounded-lg pointer-events-none" />
          <h3 className="relative text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">Recent Performance</h3>
          <div className="relative space-y-4">
            {completedRuns.slice(0, 5).map((run, index) => {
              const duration = run.completed_at && run.started_at
                ? Math.round((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000)
                : null;
              const passedTests = run.test_case_results?.filter(r => r.score >= 0.7).length || 0;
              const totalTests = run.test_case_results?.length || run.total_test_cases || 0;
              
              // Calculate trend (compare with previous run)
              const previousRun = completedRuns[index + 1];
              const trend = previousRun 
                ? (run.overall_score || 0) - (previousRun.overall_score || 0)
                : 0;
              
              return (
                <div key={run.id} className="flex items-center justify-between py-3 border-b border-gray-200/50 dark:border-purple-900/10 last:border-0">
                  <div className="flex items-center gap-4 flex-1">
                    {/* Status Icon */}
                    {(run.overall_score || 0) >= 0.7 ? (
                      <CheckCircleIcon className="w-5 h-5 text-green-400 flex-shrink-0" />
                    ) : (
                      <XCircleIcon className="w-5 h-5 text-red-400 flex-shrink-0" />
                    )}
                    
                    {/* Run Details */}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          {new Date(run.started_at).toLocaleString()}
                        </span>
                        {/* Trend Indicator */}
                        {trend !== 0 && (
                          <span className={`text-xs font-medium ${trend > 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {trend > 0 ? '↑' : '↓'} {Math.abs(Math.round(trend * 100))}%
                          </span>
                        )}
                      </div>
                      
                      {/* Additional Metrics */}
                      <div className="flex items-center gap-4 mt-1">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {passedTests}/{totalTests} tests passed
                        </span>
                        {duration && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {duration < 60 ? `${duration}s` : `${Math.round(duration / 60)}m ${duration % 60}s`}
                          </span>
                        )}
                        {run.model && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {run.model}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {/* Circular Score Indicator */}
                  <ScoreIndicator 
                    score={(run.overall_score || 0) * 100} 
                    variant="circular" 
                    size="sm" 
                    showLabel={false}
                    className="ml-4"
                  />
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}