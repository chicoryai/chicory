import React, { useState } from 'react';
import { TrainingJob } from '~/types/integrations';
import { 
  EllipsisVerticalIcon,
  EyeIcon,
  XMarkIcon,
  ArrowPathIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';

interface TrainingJobActionsProps {
  job: TrainingJob;
  onViewDetails?: (job: TrainingJob) => void;
  onCancel?: (job: TrainingJob) => void;
  onRetry?: (job: TrainingJob) => void;
}

/**
 * Action buttons for training job management
 * Provides view details, cancel, and retry functionality
 */
export default function TrainingJobActions({
  job,
  onViewDetails,
  onCancel,
  onRetry
}: TrainingJobActionsProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleViewDetails = () => {
    setIsMenuOpen(false);
    onViewDetails?.(job);
  };

  const handleCancel = async () => {
    setIsMenuOpen(false);
    setIsProcessing(true);
    try {
      await onCancel?.(job);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRetry = async () => {
    setIsMenuOpen(false);
    setIsProcessing(true);
    try {
      await onRetry?.(job);
    } finally {
      setIsProcessing(false);
    }
  };

  const canCancel = job.status === 'pending' || job.status === 'in_progress';
  const canRetry = job.status === 'failed';

  return (
    <div className="relative">
      {/* Quick Actions (visible on hover) */}
      <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {onViewDetails && (
          <button
            onClick={handleViewDetails}
            className="p-1 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            title="View details"
          >
            <EyeIcon className="h-4 w-4" />
          </button>
        )}
        
        {canCancel && onCancel && (
          <button
            onClick={handleCancel}
            disabled={isProcessing}
            className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors disabled:opacity-50"
            title="Cancel training"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        )}
        
        {canRetry && onRetry && (
          <button
            onClick={handleRetry}
            disabled={isProcessing}
            className="p-1 text-gray-400 hover:text-lime-600 dark:hover:text-lime-400 transition-colors disabled:opacity-50"
            title="Retry training"
          >
            <ArrowPathIcon className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Dropdown Menu */}
      <div className="relative">
        <button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
          aria-label="More actions"
        >
          <EllipsisVerticalIcon className="h-4 w-4" />
        </button>

        {isMenuOpen && (
          <>
            {/* Backdrop */}
            <div 
              className="fixed inset-0 z-10" 
              onClick={() => setIsMenuOpen(false)}
            />
            
            {/* Menu */}
            <div className="absolute right-0 z-20 mt-1 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
              <div className="py-1">
                {onViewDetails && (
                  <button
                    onClick={handleViewDetails}
                    className="flex w-full items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    <DocumentTextIcon className="h-4 w-4 mr-3 text-blue-500" />
                    View Details
                  </button>
                )}
                
                {canCancel && onCancel && (
                  <>
                    <div className="border-t border-gray-200 dark:border-gray-600 my-1" />
                    <button
                      onClick={handleCancel}
                      disabled={isProcessing}
                      className="flex w-full items-center px-4 py-2 text-sm text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
                    >
                      {isProcessing ? (
                        <>
                          <div className="h-4 w-4 mr-3 animate-spin rounded-full border-2 border-red-500 border-t-transparent" />
                          Canceling...
                        </>
                      ) : (
                        <>
                          <XMarkIcon className="h-4 w-4 mr-3" />
                          Cancel Training
                        </>
                      )}
                    </button>
                  </>
                )}
                
                {canRetry && onRetry && (
                  <>
                    <div className="border-t border-gray-200 dark:border-gray-600 my-1" />
                    <button
                      onClick={handleRetry}
                      disabled={isProcessing}
                      className="flex w-full items-center px-4 py-2 text-sm text-lime-700 dark:text-lime-400 hover:bg-lime-50 dark:hover:bg-lime-900/20 transition-colors disabled:opacity-50"
                    >
                      {isProcessing ? (
                        <>
                          <div className="h-4 w-4 mr-3 animate-spin rounded-full border-2 border-lime-500 border-t-transparent" />
                          Retrying...
                        </>
                      ) : (
                        <>
                          <ArrowPathIcon className="h-4 w-4 mr-3" />
                          Retry Training
                        </>
                      )}
                    </button>
                  </>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
} 