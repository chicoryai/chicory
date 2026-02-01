import React from 'react';
import { EmptyStateProps } from '~/types/integrations';
import { PlusIcon, BeakerIcon, ArrowRightIcon } from '@heroicons/react/24/outline';

/**
 * Empty state component for displaying when no data is available
 * Provides consistent empty state UI with optional action button
 */
export default function EmptyState({
  icon: Icon = PlusIcon,
  title,
  description,
  action,
  className = "",
  variant = "default"
}: EmptyStateProps & { variant?: "default" | "training" }) {
  if (variant === "training") {
    return (
      <div className={`text-center py-8 border bg-gray-50 border-gray-200 dark:border-gray-700 rounded-lg ${className}`}>
        {/* Enhanced icon design for training */}
        <div className="flex justify-center mb-4">
          <div className="bg-gradient-to-br from-lime-100 to-lime-200 dark:from-lime-900/30 dark:to-lime-800/30 rounded-full p-3 shadow-md">
            <Icon className="h-10 w-10 text-lime-600 dark:text-lime-400" />
          </div>
        </div>
        
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
          {title}
        </h3>
        
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
          {description}
        </p>
        
        {action && (
          <button
            onClick={action.onClick}
            className="group inline-flex items-center px-6 py-2.5 border border-transparent text-sm font-medium rounded-lg shadow-sm text-white bg-purple-500 hover:from-purple-700 hover:to-purple-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-all duration-200 hover:shadow-md"
          >
            <BeakerIcon className="w-4 h-4 mr-2 group-hover:animate-pulse" />
            {action.label}
            <ArrowRightIcon className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={`text-center py-12 ${className}`}>
      <div className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500 mb-4">
        <Icon className="h-12 w-12" />
      </div>
      
      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
        {title}
      </h3>
      
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-6 max-w-sm mx-auto">
        {description}
      </p>
      
      {action && (
        <button
          onClick={action.onClick}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-lime-600 hover:bg-lime-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 transition-colors duration-200"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          {action.label}
        </button>
      )}
    </div>
  );
} 