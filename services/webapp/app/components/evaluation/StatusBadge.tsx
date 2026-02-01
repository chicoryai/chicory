/**
 * StatusBadge Component
 * Displays status with appropriate styling and optional animation
 */

import { clsx } from 'clsx';

export type EvaluationStatus = 'pending' | 'running' | 'completed' | 'failed' | 'passed';

interface StatusBadgeProps {
  status: EvaluationStatus;
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
  className?: string;
}

export function StatusBadge({ 
  status, 
  size = 'md', 
  animated = false,
  className = ''
}: StatusBadgeProps) {
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-full';
  
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base'
  };
  
  const statusClasses = {
    pending: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
    running: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    passed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
  };
  
  const animationClasses = animated && status === 'running' 
    ? 'animate-pulse' 
    : '';
  
  const statusText = {
    pending: 'Pending',
    running: 'Running',
    completed: 'Completed',
    failed: 'Failed',
    passed: 'Passed'
  };
  
  return (
    <span
      className={clsx(
        baseClasses,
        sizeClasses[size],
        statusClasses[status],
        animationClasses,
        className
      )}
      role="status"
      aria-label={`Status: ${statusText[status]}`}
    >
      {status === 'running' && animated && (
        <span className="mr-1">
          <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
            <circle 
              className="opacity-25" 
              cx="12" 
              cy="12" 
              r="10" 
              stroke="currentColor" 
              strokeWidth="4"
              fill="none"
            />
            <path 
              className="opacity-75" 
              fill="currentColor" 
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        </span>
      )}
      {statusText[status]}
    </span>
  );
}