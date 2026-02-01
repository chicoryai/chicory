import React from 'react';
import { TrainingJob } from '~/types/integrations';
import { 
  BeakerIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

interface TrainingJobCardProps {
  job: TrainingJob;
  onViewDetails?: (job: TrainingJob) => void;
  onCancel?: (job: TrainingJob) => void;
  onRetry?: (job: TrainingJob) => void;
  className?: string;
}

/**
 * Card component for displaying individual training jobs
 * Shows job status, progress, metrics, and available actions
 */
export default function TrainingJobCard({
  job,
  onViewDetails,
  onCancel,
  onRetry,
  className = ""
}: TrainingJobCardProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
      case 'in_progress':
        return <BeakerIcon className="h-5 w-5 text-blue-500" />;
      case 'pending':
      case 'queued':
        return <ClockIcon className="h-5 w-5 text-yellow-500" />;
      default:
        return <BeakerIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/20';
      case 'failed':
        return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/20';
      case 'in_progress':
        return 'text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/20';
      case 'pending':
      case 'queued':
        return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/20';
      default:
        return 'text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-900/20';
    }
  };

  const formatDate = (dateString: string) => {
    try {
      // Always treat as UTC by appending 'Z' if not already present
      const safeDateString = dateString.endsWith('Z') ? dateString : dateString + 'Z';
      const date = new Date(safeDateString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Unknown';
    }
  };

  const getProgressInfo = () => {
    if (job.progress) {
      const { steps_completed = 0, total_steps = 5, percent_complete = 0 } = job.progress;
      return { 
        completed: steps_completed, 
        total: total_steps,
        percent: percent_complete 
      };
    }
    return { completed: 0, total: 5, percent: 0 };
  };
  
  // Calculate duration for completed jobs
  const calculateDuration = () => {
    if (job.status !== 'completed' || !job.updated_at || !job.created_at) {
      return null;
    }
    
    // Always treat as UTC by appending 'Z' if not already present
    const safeStartDate = job.created_at.endsWith('Z') ? job.created_at : job.created_at + 'Z';
    const safeEndDate = job.updated_at.endsWith('Z') ? job.updated_at : job.updated_at + 'Z';
    const startTime = new Date(safeStartDate).getTime();
    const endTime = new Date(safeEndDate).getTime();
    const durationMs = endTime - startTime;
    
    // Format duration nicely
    const seconds = Math.floor((durationMs / 1000) % 60);
    const minutes = Math.floor((durationMs / (1000 * 60)) % 60);
    const hours = Math.floor(durationMs / (1000 * 60 * 60));
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    } else {
      return `${seconds}s`;
    }
  };
  
  const duration = calculateDuration();

  const { completed, total, percent } = getProgressInfo();
  const progressPercent = percent || (completed / total) * 100;

  return (
    <div className={`bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow duration-200 ${className}`}>
      {/* Header */}
      <div className="flex items-center mb-3">
        <div className="flex items-center mr-auto">
          <div className="flex-shrink-0 mr-1">
            {getStatusIcon(job.status)}
          </div>
          <span className="text-sm font-medium text-gray-900 dark:text-white">
            {job.model_name}
          </span>
          
          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ml-1 ${getStatusColor(job.status)}`}>
            {job.status.replace('_', ' ')}
          </span>
        </div>
        
        {job.status === 'completed' && duration && (
          <span className="text-xs text-gray-500 dark:text-gray-400 ml-4 flex-shrink-0">
            {duration}
          </span>
        )}
      </div>

      {/* Error Message */}
      {job.status === 'failed' && job.error_message && (
        <div className="mb-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
          <p className="text-sm text-red-700 dark:text-red-400">
            <span className="font-medium">Error:</span> {job.error_message}
          </p>
        </div>
      )}

      {/* Metrics */}
      {job.status === 'completed' && job.metrics && (
        <div className="mb-3 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            {Object.entries(job.metrics).map(([key, value]) => (
              <div key={key}>
                <div className="font-medium text-green-700 dark:text-green-400">
                  {typeof value === 'number' ? value.toFixed(3) : String(value)}
                </div>
                <div className="text-green-600 dark:text-green-500 capitalize">
                  {key.replace('_', ' ')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>Started: {formatDate(job.created_at)}</span>
      </div>
    </div>
  );
} 