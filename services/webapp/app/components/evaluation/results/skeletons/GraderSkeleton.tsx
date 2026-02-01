import React from 'react';

interface SkeletonPulseProps {
  className?: string;
  delay?: number;
  width?: string;
}

export const SkeletonPulse: React.FC<SkeletonPulseProps> = ({ 
  className = '', 
  delay = 0,
  width
}) => (
  <div 
    className={`bg-gray-200 dark:bg-purple-900/20 rounded animate-pulse ${className}`}
    style={{ 
      animationDelay: `${delay}ms`,
      ...(width ? { width } : {})
    }}
  />
);

interface SkeletonBarProps {
  label?: boolean;
  showProgress?: boolean;
  delay?: number;
  progressWidth?: number;
}

export const SkeletonBar: React.FC<SkeletonBarProps> = ({ 
  label = true, 
  showProgress = true,
  delay = 0,
  progressWidth
}) => {
  const width = progressWidth || (40 + Math.random() * 40);
  
  return (
    <div className="flex items-center gap-2" style={{ animationDelay: `${delay}ms` }}>
      {label && <SkeletonPulse className="h-2 w-20" delay={delay} />}
      <div className="flex-1 h-2 bg-gray-200 dark:bg-purple-900/20 rounded-full overflow-hidden">
        {showProgress && (
          <div 
            className="h-full bg-gradient-to-r from-purple-300 to-purple-400 dark:from-purple-600 dark:to-purple-500 animate-shimmer"
            style={{ width: `${width}%` }}
          />
        )}
      </div>
      <SkeletonPulse className="h-2 w-10" delay={delay} />
    </div>
  );
};

export const SkeletonScore: React.FC = () => (
  <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gray-100 dark:bg-purple-900/20 mb-4 animate-pulse">
    <div className="w-14 h-14 rounded-full bg-gray-200 dark:bg-purple-800/30" />
  </div>
);

interface SkeletonTextProps {
  lines?: number;
  baseDelay?: number;
}

export const SkeletonText: React.FC<SkeletonTextProps> = ({ 
  lines = 3,
  baseDelay = 0
}) => (
  <div className="space-y-1.5">
    {Array.from({ length: lines }).map((_, i) => (
      <SkeletonPulse 
        key={i}
        className="h-3"
        delay={baseDelay + (i * 150)}
        width={`${100 - (i * 15)}%`}
      />
    ))}
  </div>
);