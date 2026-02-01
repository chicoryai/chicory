import React from "react";

interface ProgressBarProps {
  steps: string[];
  currentStep: number;
}

export function ProgressBar({ steps, currentStep }: ProgressBarProps) {
  return (
    <div className="w-full py-4">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          
          return (
            <React.Fragment key={index}>
              {/* Step indicator */}
              <div className="flex flex-col items-center">
                <div 
                  className={`
                    flex items-center justify-center w-8 h-8 rounded-full 
                    ${isCompleted ? 'bg-purple-600 text-white' : 
                      isCurrent ? 'bg-purple-100 border-2 border-purple-600 text-purple-600 dark:bg-purple-900/30 dark:border-purple-400 dark:text-purple-400' : 
                      'bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400'}
                  `}
                >
                  {isCompleted ? (
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </div>
                <span className={`
                  mt-2 text-sm font-medium
                  ${isCompleted ? 'text-purple-600 dark:text-purple-400' : 
                    isCurrent ? 'text-purple-600 dark:text-purple-400' : 
                    'text-gray-500 dark:text-gray-400'}
                `}>
                  {step}
                </span>
              </div>
              
              {/* Connector line between steps */}
              {index < steps.length - 1 && (
                <div className="flex-1 mx-4">
                  <div className={`h-1 ${
                    index < currentStep ? 'bg-purple-600 dark:bg-purple-400' : 'bg-gray-200 dark:bg-gray-700'
                  }`}></div>
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
