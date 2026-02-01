import { useState } from 'react';
import type { EvaluationRun, TestCase } from '~/services/chicory.server';
import { StatusBadge } from '~/components/evaluation/StatusBadge';
import { RunDetailsModal } from '~/components/evaluation/modals/RunDetailsModal';

interface RunHistoryTimelineProps {
  runs: EvaluationRun[];
  testCases: TestCase[];
}

export function RunHistoryTimeline({ runs , testCases}: RunHistoryTimelineProps) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  
  // Derive the current run data from the ID to ensure live updates
  const selectedRun = selectedRunId 
    ? runs.find(run => run.id === selectedRunId) || null
    : null;
  if (runs.length === 0) {
    return (
      <div className="bg-white dark:bg-whitePurple-50/5 backdrop-blur-sm rounded-lg border border-gray-200 dark:border-purple-900/20 p-12 text-center">
        <p className="text-gray-600 dark:text-gray-400">No evaluation runs yet</p>
        <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">Run an evaluation to see history</p>
      </div>
    );
  }
  
  // Sort runs by date to show newest first (most recent at the top)
  const sortedRuns = [...runs].sort((a, b) => {
    const dateA = new Date(a.created_at || a.started_at).getTime();
    const dateB = new Date(b.created_at || b.started_at).getTime();
    return dateB - dateA; // Descending order (newest first)
  });
  

  return (
    <div className="relative">
      {/* Vertical timeline line - gradient from top (newest) to bottom (oldest) */}
      <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-t from-transparent via-purple-400/50 to-purple-400" />
      
      {sortedRuns.map((run) => {
        // Skip rendering runs with invalid data
        if (!run.status || !run.id) return null;
        
        return (
          <div key={run.id} className="relative flex items-start mb-6">
            {/* Timeline node */}
            <div className={`
              absolute left-6 w-4 h-4 rounded-full border-2
              ${run.status === 'completed' ? 'bg-green-400 border-green-400' :
                run.status === 'failed' ? 'bg-red-400 border-red-400' :
                run.status === 'running' ? 'bg-amber-400 border-amber-400 animate-pulse' :
                run.status === 'pending' ? 'bg-amber-400 border-amber-400 animate-pulse' :
                'bg-gray-400 border-gray-400'}
            `}>
              {(run.status === 'running' || run.status === 'pending') && (
                <div className="absolute inset-0 rounded-full bg-amber-400 animate-ping" />
              )}
            </div>
          
          {/* Content card */}
          <div className="ml-14 flex-1">
            <div className="bg-white dark:bg-whitePurple-50/5 backdrop-blur-sm rounded-lg p-4 border border-whitePurple-100 dark:border-purple-900/20 hover:border-purple-300 dark:hover:border-purple-400/30 shadow-md shadow-whitePurple-100/70 dark:shadow-none transition-colors">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <StatusBadge status={run.status} />
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    {new Date(run.started_at + 'Z').toLocaleString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {run.overall_score ? `${Math.round(run.overall_score * 100)}%` : '-'}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                   {run.total_test_cases === 1 ? '1 case' : `${run.total_test_cases} cases`}
                  </p>
                </div>
              </div>
              
              {/* Progress bar for running evaluations */}
              {run.status === 'running' && (
                <div className="mt-3">
                  <div className="h-2 bg-purple-900/20 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-purple-400 to-lime-400 transition-all duration-300"
                      style={{ width: `${(run.completed_test_cases / run.total_test_cases) * 100}%` }}
                    />
                  </div>
                </div>
              )}
              
              {/* View Details Button */}
              <button
                onClick={() => setSelectedRunId(run.id)}
                className="mt-3 text-sm text-purple-400 hover:text-purple-300 transition-colors"
              >
                View Details →
              </button>
            </div>
          </div>
        </div>
        );
      })}
      
      {/* Details Modal */}
      {selectedRun && (
        <RunDetailsModal
          run={selectedRun}
          testCases={testCases}
          isOpen={!!selectedRun}
          onClose={() => setSelectedRunId(null)}
        />
      )}
    </div>
  );
}