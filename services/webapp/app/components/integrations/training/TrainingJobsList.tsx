import React from 'react';
import { TrainingJob } from '~/types/integrations';
import TrainingJobCard from './TrainingJobCard';
import EmptyState from '../layout/EmptyState';
import { BeakerIcon } from '@heroicons/react/24/outline';

interface TrainingJobsListProps {
  trainingJobs: TrainingJob[];
  onViewDetails?: (job: TrainingJob) => void;
  onCancel?: (job: TrainingJob) => void;
  onRetry?: (job: TrainingJob) => void;
  isLoading?: boolean;
  className?: string;
}

/**
 * List component for displaying training jobs
 * Shows training status, progress, and provides actions for job management
 */
export default function TrainingJobsList({
  trainingJobs,
  onViewDetails,
  onCancel,
  onRetry,
  isLoading = false,
  className = ""
}: TrainingJobsListProps) {
  if (isLoading) {
    return (
      <div className={`space-y-4 ${className}`}>
        {[...Array(3)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                  <div>
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32 mb-2"></div>
                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
                  </div>
                </div>
                <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
              </div>
              <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (trainingJobs.length === 0) {
    return (
      <div className={`${className}`}>
        {/* Preview of what training jobs will look like */}
        <div className="space-y-3 relative overflow-hidden">
          {/* Overlay to make it clear these are previews */}
          <div className="absolute inset-0 bg-whitePurple-50/60 dark:bg-gray-900/60 backdrop-blur-[1px] z-10"></div>
          
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 relative">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-600 rounded-lg flex items-center justify-center">
                    <BeakerIcon className="w-5 h-5 text-gray-500" />
                  </div>
                  <div className="space-y-1">
                    <div className="h-4 bg-gradient-to-r from-gray-200 to-gray-300 dark:from-gray-600 dark:to-gray-500 rounded w-36"></div>
                    <div className="h-3 bg-gradient-to-r from-gray-200 to-gray-300 dark:from-gray-600 dark:to-gray-500 rounded w-24"></div>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className={`h-6 px-3 rounded-full flex items-center ${
                    i === 0 ? 'bg-blue-100 dark:bg-blue-900/30' : 
                    i === 1 ? 'bg-green-100 dark:bg-green-900/30' : 
                    'bg-red-100 dark:bg-red-900/30'
                  }`}>
                    <div className={`h-3 rounded w-16 ${
                      i === 0 ? 'bg-blue-200 dark:bg-blue-700' : 
                      i === 1 ? 'bg-green-200 dark:bg-green-700' : 
                      'bg-red-200 dark:bg-red-700'
                    }`}></div>
                  </div>
                  <div className="h-3 bg-gray-200 dark:bg-gray-600 rounded w-14"></div>
                </div>
              </div>
              
              {/* Progress bar */}
              <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2 mb-3">
                <div className={`h-2 rounded-full transition-all duration-1000 ${
                  i === 0 ? 'bg-gradient-to-r from-blue-400 to-blue-500 w-3/4' : 
                  i === 1 ? 'bg-gradient-to-r from-green-400 to-green-500 w-full' : 
                  'bg-gradient-to-r from-red-400 to-red-500 w-2/5'
                }`}></div>
              </div>
              
              {/* Footer */}
              <div className="flex justify-between items-center text-xs">
                <div className="h-3 bg-gray-200 dark:bg-gray-600 rounded w-28"></div>
                <div className="h-3 bg-gray-200 dark:bg-gray-600 rounded w-20"></div>
              </div>
            </div>
                      ))}
            
            {/* Simple overlay indicator */}
            <div className="absolute inset-0 flex items-center justify-center z-20 pointer-events-none">
              <div className="bg-white/90 dark:bg-gray-800/90 px-4 py-2 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  No training jobs yet
                </p>
              </div>
            </div>
 
          </div>
      </div>
    );
  }

  // Sort jobs by creation date (newest first)
  const sortedJobs = [...trainingJobs].sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  // Group jobs by status
  const groupedJobs = sortedJobs.reduce((acc, job) => {
    const status = job.status;
    if (!acc[status]) {
      acc[status] = [];
    }
    acc[status].push(job);
    return acc;
  }, {} as Record<string, TrainingJob[]>);

  const getStatusOrder = (status: string) => {
    switch (status) {
      case 'in_progress': return 0;
      case 'pending': return 1;
      case 'completed': return 2;
      case 'failed': return 3;
      default: return 4;
    }
  };

  const sortedStatuses = Object.keys(groupedJobs).sort((a, b) => 
    getStatusOrder(a) - getStatusOrder(b)
  );

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'in_progress': return 'In Progress';
      case 'pending': return 'Pending';
      case 'completed': return 'Completed';
      case 'failed': return 'Failed';
      default: return status;
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Summary Stats - moved to top */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {trainingJobs.length}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">Total Jobs</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {trainingJobs.filter(j => j.status === 'in_progress').length}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">Running</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {trainingJobs.filter(j => j.status === 'completed').length}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">Completed</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-red-600 dark:text-red-400">
            {trainingJobs.filter(j => j.status === 'failed').length}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">Failed</div>
        </div>
      </div>

      {/* Job Listings */}
      {sortedStatuses.map(status => (
        <div key={status}>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              {getStatusLabel(status)}
            </h3>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {groupedJobs[status].length} job{groupedJobs[status].length !== 1 ? 's' : ''}
            </span>
          </div>
          
          <div className="space-y-3">
            {groupedJobs[status].map(job => (
              <TrainingJobCard
                key={job.id}
                job={job}
                onViewDetails={onViewDetails}
                onCancel={onCancel}
                onRetry={onRetry}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
} 