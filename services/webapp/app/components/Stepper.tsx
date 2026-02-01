import React from "react";

interface StepperProps {
  steps: string[];
  currentStep: number;
  className?: string;
}

export function Stepper({ steps, currentStep, className = "" }: StepperProps) {
  return (
    <div className={`flex items-center w-full ${className}`}>
      {steps.map((step, index) => (
        <React.Fragment key={index}>
          {/* Step circle */}
          <div className="relative flex flex-col items-center">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center
              ${
                index < currentStep
                  ? "bg-purple-500 text-white"
                  : index === currentStep
                  ? "bg-purple-500 text-white ring-4 ring-purple-200 dark:ring-purple-900"
                  : "bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
              }`}
            >
              {index < currentStep ? (
                <span className="material-symbols-outlined text-sm">check</span>
              ) : (
                index + 1
              )}
            </div>
            <div className="mt-2 text-center text-xs font-medium">
              {step}
            </div>
          </div>

          {/* Connector line */}
          {index < steps.length - 1 && (
            <div
              className={`flex-auto border-t-2 ${
                index < currentStep
                  ? "border-purple-500"
                  : "border-gray-200 dark:border-gray-700"
              }`}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
} 