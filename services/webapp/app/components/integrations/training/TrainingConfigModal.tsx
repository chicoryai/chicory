import React, { useState } from 'react';
import { DataSourceCredential } from '~/types/integrations';
import { TrainingConfig } from './StartTrainingButton';
import { XMarkIcon, CheckIcon } from '@heroicons/react/24/outline';

interface TrainingConfigModalProps {
  dataSources: DataSourceCredential[];
  onStartTraining: (config: TrainingConfig) => void;
  onClose: () => void;
}

/**
 * Modal for configuring training parameters
 * Allows selection of data sources and training settings
 */
export default function TrainingConfigModal({
  dataSources,
  onStartTraining,
  onClose
}: TrainingConfigModalProps) {
  const [modelName, setModelName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedDataSources, setSelectedDataSources] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleDataSourceToggle = (dataSourceId: string) => {
    setSelectedDataSources(prev => 
      prev.includes(dataSourceId)
        ? prev.filter(id => id !== dataSourceId)
        : [...prev, dataSourceId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!modelName.trim() || selectedDataSources.length === 0) {
      return;
    }

    setIsSubmitting(true);
    
    try {
      await onStartTraining({
        modelName: modelName.trim(),
        selectedDataSources,
        description: description.trim() || undefined,
        parameters: {
          // Default training parameters
          epochs: 10,
          batch_size: 32,
          learning_rate: 0.001
        }
      });
    } catch (error) {
      console.error('Failed to start training:', error);
      setIsSubmitting(false);
    }
  };

  const isValid = modelName.trim().length > 0 && selectedDataSources.length > 0;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div 
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          {/* Header */}
          <div className="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Start Training
              </h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Model Name */}
              <div>
                <label htmlFor="modelName" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Model Name *
                </label>
                <input
                  type="text"
                  id="modelName"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  placeholder="Enter a name for your model"
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500"
                  required
                />
              </div>

              {/* Description */}
              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Description
                </label>
                <textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description for this training job"
                  rows={3}
                  className="mt-1 block w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500"
                />
              </div>

              {/* Data Sources Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Select Data Sources * ({selectedDataSources.length} selected)
                </label>
                <div className="space-y-2 max-h-48 overflow-y-auto border border-gray-200 dark:border-gray-600 rounded-md p-3">
                  {dataSources.map((dataSource) => (
                    <label
                      key={dataSource.id}
                      className="flex items-center space-x-3 p-2 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                    >
                      <div className="relative">
                        <input
                          type="checkbox"
                          checked={selectedDataSources.includes(dataSource.id)}
                          onChange={() => handleDataSourceToggle(dataSource.id)}
                          className="sr-only"
                        />
                        <div className={`w-4 h-4 border-2 rounded flex items-center justify-center transition-colors ${
                          selectedDataSources.includes(dataSource.id)
                            ? 'bg-lime-600 border-lime-600'
                            : 'border-gray-300 dark:border-gray-600'
                        }`}>
                          {selectedDataSources.includes(dataSource.id) && (
                            <CheckIcon className="w-3 h-3 text-white" />
                          )}
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {dataSource.name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {dataSource.type} • {dataSource.status}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
                {dataSources.length === 0 && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                    No data sources available. Connect data sources first.
                  </p>
                )}
              </div>
            </form>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="submit"
              onClick={handleSubmit}
              disabled={!isValid || isSubmitting}
              className={`w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 text-base font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 sm:ml-3 sm:w-auto sm:text-sm ${
                isValid && !isSubmitting
                  ? 'bg-lime-600 text-white hover:bg-lime-700 focus:ring-lime-500'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed dark:bg-gray-600 dark:text-gray-400'
              }`}
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Starting...
                </>
              ) : (
                'Start Training'
              )}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-800 text-base font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
} 