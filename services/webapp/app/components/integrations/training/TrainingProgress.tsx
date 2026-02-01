import React from 'react';
import { TrainingJob } from '~/types/integrations';
import {
  CheckCircleIcon,
  ArrowPathIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CpuChipIcon
} from '@heroicons/react/24/outline';

interface TrainingProgressProps {
  job: TrainingJob;
  onRetrain?: (job: TrainingJob) => void;
  className?: string;
}

/**
 * Progress indicator for training jobs
 * Clean design matching the provided mockup with conditional rendering based on status
 */
export default function TrainingProgress({
  job,
  onRetrain,
  className = ""
}: TrainingProgressProps) {
  const formatDate = (dateString: string) => {
    try {
      // Always treat as UTC by appending 'Z' if not already present
      const safeDateString = dateString.endsWith('Z') ? dateString : dateString + 'Z';
      const date = new Date(safeDateString);
      return date.toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
      });
    } catch {
      return 'Unknown';
    }
  };

  // Format current step text: capitalize first letter and replace underscores with spaces
  const formatCurrentStep = (step: string) => {
    if (!step) return '';
    return step
      .replace(/_/g, ' ') // Replace underscores with spaces
      .replace(/^\w/, (c) => c.toUpperCase()); // Capitalize first letter
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
    // Default based on status
    if (job.status === 'completed') {
      return { completed: 5, total: 5, percent: 100 };
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

  const getStatusConfig = () => {
    switch (job.status) {
      case 'completed':
        return {
          title: 'Scan Completed',
          icon: CheckCircleIcon,
          iconColor: 'text-chicoryGreen-900',
          borderColor: 'border-chicoryGreen-900',
          bgColor: 'bg-chicoryGreen-400 dark:bg-gray-800',
          progressColor: 'bg-chicoryGreen-900',
          dateText: `Completed on ${formatDate(job.completed_at || job.created_at)}`,
          showTrainButton: true
        };
      case 'in_progress':
        return {
          title: 'Scanning In Progress',
          icon: CpuChipIcon,
          iconColor: 'text-blue-500',
          borderColor: 'border-blue-500',
          bgColor: 'bg-blue-200 dark:bg-gray-800',
          progressColor: 'bg-blue-500',
          dateText: `Started on ${formatDate(job.created_at)}`,
          showTrainButton: false
        };
      case 'queued':
        return {
          title: 'Scan Pending',
          icon: ClockIcon,
          iconColor: 'text-yellow-500',
          borderColor: 'border-yellow-500',
          bgColor: 'bg-yellow-100 dark:bg-gray-800',
          progressColor: 'bg-yellow-500',
          dateText: `Queued on ${formatDate(job.created_at)}`,
          showTrainButton: false
        };
      case 'failed':
        return {
          title: 'Scan Failed',
          icon: ExclamationTriangleIcon,
          iconColor: 'text-red-500',
          borderColor: 'border-red-500',
          bgColor: 'bg-red-200 dark:bg-gray-800',
          progressColor: 'bg-red-500',
          dateText: `Failed on ${formatDate(job.updated_at || job.created_at)}`,
          showTrainButton: true
        };
      default:
        return {
          title: 'Scan Status',
          icon: ClockIcon,
          iconColor: 'text-gray-500',
          borderColor: 'border-gray-500',
          bgColor: 'bg-gray-200 dark:bg-gray-800',
          progressColor: 'bg-gray-500',
          dateText: `Created on ${formatDate(job.created_at)}`,
          showTrainButton: true
        };
    }
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;

  return (
    <div className={`${statusConfig.bgColor} border-2 ${statusConfig.borderColor} rounded-xl p-6 ${className}`}>
      {/* Title */}
      <h2 className="text-gray-900 dark:text-white text-2xl font-bold mb-4">
        {statusConfig.title}
      </h2>
      
      {/* Status and Date */}
      <div className="flex items-center space-x-3 mb-6">
        <StatusIcon className={`h-6 w-6 ${statusConfig.iconColor}`} />
        <span className="text-gray-900 dark:text-gray-300">
          {statusConfig.dateText}
        </span>
      </div>

      {/* Error Message for Failed Jobs */}
      {job.status === 'failed' && job.error_message && (
        <div className="mb-6 p-3 bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-700 rounded-lg">
          <p className="text-red-800 dark:text-red-200 text-sm">
            <strong>Error:</strong> {job.error_message}
          </p>
        </div>
      )}

      {/* Current Step for In Progress Jobs */}
      {job.status === 'in_progress' && job.progress?.current_step && (
        <div className="mb-4">
          <p className="text-gray-700 dark:text-gray-300 text-sm">
            Current step: <span className="font-medium">{formatCurrentStep(job.progress.current_step)}</span>
          </p>
        </div>
      )}

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="w-full bg-gray-300 dark:bg-gray-700 rounded-full h-3">
          <div 
            className={`${statusConfig.progressColor} h-3 rounded-full transition-all duration-300 ${
              job.status === 'in_progress' ? 'animate-pulse' : ''
            }`}
            style={{ width: `${Math.min(progressPercent, 100)}%` }}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between">
        <span className="text-gray-900 dark:text-gray-400 text-sm">
          {job.status === 'completed' && duration ? (
            <span>Duration: {duration}</span>
          ) : (
            <>
              {completed}/{total} steps
              {job.status === 'in_progress' && percent > 0 && (
                <span className="ml-2">({Math.round(percent)}%)</span>
              )}
            </>
          )}
        </span>
        
        {statusConfig.showTrainButton && (
          <button
            onClick={() => onRetrain?.(job)}
            className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2 rounded-lg font-medium flex items-center space-x-2 transition-colors"
          >
            <ArrowPathIcon className="h-4 w-4" />
            <span>{job.status === 'failed' ? 'Retry' : 'Scan'}</span>
          </button>
        )}
      </div>
    </div>
  );
} 