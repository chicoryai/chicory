import { ReactNode } from "react";

type Status = 'pending' | 'running' | 'completed' | 'failed' | 'passed' | 'queued' | 'in_progress';
type BadgeSize = 'sm' | 'md' | 'lg';

interface StatusBadgeProps {
  status: Status;
  animated?: boolean;
  size?: BadgeSize;
  children?: ReactNode;
}

export function StatusBadge({ 
  status, 
  animated = false, 
  size = 'md', 
  children 
}: StatusBadgeProps) {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base'
  };

  const statusConfig = {
    pending: {
      bg: 'bg-yellow-100 dark:bg-yellow-900/30',
      text: 'text-yellow-800 dark:text-yellow-300',
      border: 'border-yellow-300 dark:border-yellow-700',
      dot: 'bg-yellow-400',
      label: 'Pending'
    },
    queued: {
      bg: 'bg-blue-100 dark:bg-blue-900/30',
      text: 'text-blue-800 dark:text-blue-300',
      border: 'border-blue-300 dark:border-blue-700',
      dot: 'bg-blue-400',
      label: 'Queued'
    },
    running: {
      bg: 'bg-purple-100 dark:bg-purple-900/30',
      text: 'text-purple-800 dark:text-purple-300',
      border: 'border-purple-300 dark:border-purple-700',
      dot: 'bg-purple-400',
      label: 'Running'
    },
    in_progress: {
      bg: 'bg-purple-100 dark:bg-purple-900/30',
      text: 'text-purple-800 dark:text-purple-300',
      border: 'border-purple-300 dark:border-purple-700',
      dot: 'bg-purple-400',
      label: 'In Progress'
    },
    completed: {
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-800 dark:text-green-300',
      border: 'border-green-300 dark:border-green-700',
      dot: 'bg-green-400',
      label: 'Completed'
    },
    passed: {
      bg: 'bg-lime-100 dark:bg-lime-900/30',
      text: 'text-lime-800 dark:text-lime-300',
      border: 'border-lime-300 dark:border-lime-700',
      dot: 'bg-lime-400',
      label: 'Passed'
    },
    failed: {
      bg: 'bg-red-100 dark:bg-red-900/30',
      text: 'text-red-800 dark:text-red-300',
      border: 'border-red-300 dark:border-red-700',
      dot: 'bg-red-400',
      label: 'Failed'
    }
  };

  const config = statusConfig[status];
  const isAnimated = animated && (status === 'running' || status === 'in_progress');

  return (
    <span 
      className={`
        inline-flex items-center gap-1.5 rounded-full font-medium border
        ${config.bg} ${config.text} ${config.border} ${sizeClasses[size]}
      `}
    >
      <span className="relative flex h-2 w-2">
        {isAnimated && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${config.dot} opacity-75`} />
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${config.dot}`} />
      </span>
      {children || config.label}
    </span>
  );
}