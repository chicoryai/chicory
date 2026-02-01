/**
 * ScoreIndicator Component
 * Displays evaluation scores in various formats
 */

import { clsx } from 'clsx';

interface ScoreIndicatorProps {
  score: number; // 0-100
  variant?: 'circular' | 'linear' | 'numeric';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export function ScoreIndicator({
  score,
  variant = 'linear',
  size = 'md',
  showLabel = true,
  className = ''
}: ScoreIndicatorProps) {
  const normalizedScore = Math.min(100, Math.max(0, score));
  
  const getColorClass = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400';
    if (score >= 60) return 'text-yellow-600 dark:text-yellow-400';
    if (score >= 40) return 'text-orange-600 dark:text-orange-400';
    return 'text-red-600 dark:text-red-400';
  };
  
  const getBarColorClass = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-yellow-500';
    if (score >= 40) return 'bg-orange-500';
    return 'bg-red-500';
  };
  
  if (variant === 'numeric') {
    const sizeClasses = {
      sm: 'text-sm',
      md: 'text-lg',
      lg: 'text-2xl'
    };
    
    return (
      <div className={clsx('font-semibold', className)}>
        <span className={clsx(sizeClasses[size], getColorClass(normalizedScore))}>
          {Math.round(normalizedScore)}%
        </span>
        {showLabel && (
          <span className="ml-2 text-gray-500 dark:text-gray-400 text-sm">Score</span>
        )}
      </div>
    );
  }
  
  if (variant === 'circular') {
    const sizes = {
      sm: { width: 40, height: 40, strokeWidth: 4, fontSize: 'text-[10px]' },
      md: { width: 60, height: 60, strokeWidth: 5, fontSize: 'text-xs' },
      lg: { width: 80, height: 80, strokeWidth: 6, fontSize: 'text-sm' }
    };
    
    const { width, height, strokeWidth, fontSize } = sizes[size];
    const radius = (Math.min(width, height) - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (normalizedScore / 100) * circumference;
    
    return (
      <div className={clsx('relative inline-flex items-center justify-center', className)}>
        <svg width={width} height={height} className="transform -rotate-90">
          <circle
            cx={width / 2}
            cy={height / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="none"
            className="text-gray-200 dark:text-gray-700"
          />
          <circle
            cx={width / 2}
            cy={height / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={clsx('transition-all duration-500', getColorClass(normalizedScore))}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={clsx('font-semibold', fontSize, getColorClass(normalizedScore))}>
            {Math.round(normalizedScore)}%
          </span>
        </div>
      </div>
    );
  }
  
  // Linear variant (default)
  const heightClasses = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4'
  };
  
  return (
    <div className={clsx('w-full', className)}>
      {showLabel && (
        <div className="flex justify-between mb-1">
          <span className="text-sm text-gray-600 dark:text-gray-400">Score</span>
          <span className={clsx('text-sm font-medium', getColorClass(normalizedScore))}>
            {Math.round(normalizedScore)}%
          </span>
        </div>
      )}
      <div className={clsx('w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden', heightClasses[size])}>
        <div
          className={clsx('h-full transition-all duration-500', getBarColorClass(normalizedScore))}
          style={{ width: `${normalizedScore}%` }}
          role="progressbar"
          aria-valuenow={normalizedScore}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Score: ${normalizedScore} percent`}
        />
      </div>
    </div>
  );
}