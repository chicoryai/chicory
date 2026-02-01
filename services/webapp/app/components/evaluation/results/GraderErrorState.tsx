import React from 'react';

interface GraderErrorStateProps {
  response?: string;
  errorMessage?: string;
}

export const GraderErrorState: React.FC<GraderErrorStateProps> = ({ 
  response, 
  errorMessage = "Failed to parse grader response"
}) => (
  <div className="bg-white dark:bg-whitePurple-50/5 backdrop-blur-sm rounded-lg border border-gray-200 dark:border-purple-900/20 overflow-hidden h-full flex flex-col">
    <div className="px-4 py-3 bg-gray-50 dark:bg-purple-900/10 border-b border-gray-200 dark:border-purple-900/20">
      <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300">
        Grader Evaluation
      </h5>
    </div>
    
    <div className="p-4">
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3">
        <p className="text-sm text-red-600 dark:text-red-400">
          {errorMessage}
        </p>
        {response && (
          <pre className="mt-2 text-xs text-gray-600 dark:text-gray-400 overflow-x-auto">
            {response.substring(0, 200)}...
          </pre>
        )}
      </div>
    </div>
  </div>
);