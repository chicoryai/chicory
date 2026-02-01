import React, { useState } from 'react';
import { DataSourceTypeDefinition } from '~/types/integrations';
import AvailableIntegrationsList from '~/components/integrations/data-sources/AvailableIntegrationsList';
import { PlusIcon, ChevronDownIcon } from '@heroicons/react/24/outline';

interface AddDataSourceButtonProps {
  availableIntegrations: DataSourceTypeDefinition[];
  projectId: string;
  onDataSourceCreated?: () => void;
  disabled?: boolean;
  className?: string;
}

/**
 * Button component that triggers a popover for selecting integrations
 * Shows available integrations in a categorized list
 */
export default function AddDataSourceButton({
  availableIntegrations,
  projectId,
  onDataSourceCreated,
  disabled = false,
  className = ""
}: AddDataSourceButtonProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleDataSourceCreated = () => {
    setIsOpen(false);
    onDataSourceCreated?.();
  };

  return (
    <div className={`relative ${className}`}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className={`
          inline-flex items-center px-5 py-2.5 border border-transparent text-sm font-semibold rounded-lg shadow-sm
          ${disabled
            ? 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-800 dark:text-gray-600'
            : 'text-white bg-purple-500 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 hover:shadow-md active:scale-95'
          }
          transition-all duration-200
        `}
      >
        <PlusIcon className="h-4 w-4 mr-2" />
        Data Source
        <ChevronDownIcon className={`h-4 w-4 ml-2 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Popover */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Popover Content */}
          <div className="absolute right-0 z-20 mt-3 w-96 bg-white dark:bg-gray-900 rounded-xl shadow-xl ring-1 ring-black ring-opacity-5 focus:outline-none border border-gray-200 dark:border-gray-800">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Add Data Source
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    Choose from available integrations
                  </p>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  <span className="sr-only">Close</span>
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <AvailableIntegrationsList
                integrations={availableIntegrations}
                projectId={projectId}
                onDataSourceCreated={handleDataSourceCreated}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
} 