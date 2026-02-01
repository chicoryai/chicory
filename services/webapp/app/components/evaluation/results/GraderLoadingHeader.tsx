import React from 'react';

interface GraderLoadingHeaderProps {
  title?: string;
  loadingText?: string;
}

export const GraderLoadingHeader: React.FC<GraderLoadingHeaderProps> = ({ 
  title = "Grader Evaluation",
  loadingText = "Grading..."
}) => (
  <div className="px-4 py-3 bg-gray-50 dark:bg-purple-900/10 border-b border-gray-200 dark:border-purple-900/20">
    <div className="flex items-center justify-between">
      <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300">
        {title}
      </h5>
      <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
        <div className="w-4 h-4 border-2 border-purple-400/30 border-t-purple-400 rounded-full animate-spin" />
        <span>{loadingText}</span>
      </div>
    </div>
  </div>
);