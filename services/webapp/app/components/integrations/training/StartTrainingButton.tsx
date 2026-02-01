import React from 'react';
import { DataSourceCredential } from '~/types/integrations';
import { BeakerIcon, PlusIcon } from '@heroicons/react/24/outline';

interface StartTrainingButtonProps {
  dataSources: DataSourceCredential[];
  onStartTraining: () => void;
  disabled?: boolean;
  className?: string;
}

/**
 * Button component for starting new training jobs
 * Directly triggers training when clicked
 */
export default function StartTrainingButton({
  dataSources,
  onStartTraining,
  disabled = false,
  className = ""
}: StartTrainingButtonProps) {
  const availableDataSources = dataSources.filter(ds => 
    ds.status === 'active' || ds.status === 'connected' || ds.status === 'ready'
  );

  const hasDataSources = availableDataSources.length > 0;

  return (
    <button
      onClick={onStartTraining}
      disabled={disabled || !hasDataSources}
      className={`
        inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm
        ${disabled || !hasDataSources
          ? 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800 dark:text-gray-600'
          : 'text-white bg-lime-600 hover:bg-lime-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500'
        }
        transition-colors duration-200 ${className}
      `}
      title={!hasDataSources ? 'Connect data sources first' : 'Start training a new model'}
    >
      <BeakerIcon className="h-4 w-4 mr-2" />
      Start Training
      <PlusIcon className="h-4 w-4 ml-2" />
    </button>
  );
} 