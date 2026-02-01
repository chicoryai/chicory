import React, { useState, useEffect } from 'react';
import { useFetcher } from '@remix-run/react';
import { DataSourceCredential } from '~/types/integrations';
import {
  PencilIcon,
  TrashIcon,
  CheckCircleIcon,
  XCircleIcon,
  FolderOpenIcon
} from '@heroicons/react/24/outline';
import { TbPlugConnected } from "react-icons/tb";

interface DataSourceActionsProps {
  dataSource: DataSourceCredential;
  projectId: string;
  onEdit?: (dataSource: DataSourceCredential) => void;
  onDelete?: (dataSource: DataSourceCredential) => void;
  onTest?: (dataSource: DataSourceCredential) => void;
  onViewFiles?: (dataSource: DataSourceCredential) => void;
}

/**
 * Action buttons for data source management
 * Provides edit, delete, and test connection functionality
 */
export default function DataSourceActions({
  dataSource,
  projectId,
  onEdit,
  onDelete,
  onTest,
  onViewFiles
}: DataSourceActionsProps) {
  const isFolderUpload = dataSource.type === 'folder_upload';
  const [isDeleting, setIsDeleting] = useState(false);
  const [testStatus, setTestStatus] = useState<{
    status: 'idle' | 'testing' | 'success' | 'error';
    message?: string;
  }>({ status: 'idle' });
  
  const fetcher = useFetcher<{
    success?: boolean;
    message?: string;
    dataSourceId?: string;
    error?: string;
  }>();

  // Handle test connection response
  useEffect(() => {
    if (fetcher.data && fetcher.state === 'idle') {
      // Check if this response is for our data source
      if (fetcher.data.dataSourceId === dataSource.id) {
        if (fetcher.data.success) {
          setTestStatus({
            status: 'success',
            message: fetcher.data.message || 'Connection successful!'
          });
        } else {
          setTestStatus({
            status: 'error',
            message: fetcher.data.error || fetcher.data.message || 'Connection failed'
          });
        }
        
        // Clear the notification after 3 seconds
        setTimeout(() => {
          setTestStatus({ status: 'idle' });
        }, 3000);
      }
    }
  }, [fetcher.data, fetcher.state, dataSource.id]);

  // Update testing status based on fetcher state
  useEffect(() => {
    if (fetcher.state === 'submitting' && fetcher.formData?.get('_action') === 'testConnection') {
      setTestStatus({ status: 'testing' });
    }
  }, [fetcher.state, fetcher.formData]);

  const handleEdit = () => {
    onEdit?.(dataSource);
  };

  const handleDelete = () => {
    setIsDeleting(true);
    // You might want to show a confirmation modal here
    onDelete?.(dataSource);
  };

  const handleViewFiles = () => {
    onViewFiles?.(dataSource);
  };

  const handleTest = () => {
    // Use fetcher to submit test connection request to the integrations route
    const formData = new FormData();
    formData.append('_action', 'testConnection');
    formData.append('dataSourceId', dataSource.id);
    formData.append('projectId', projectId);
    
    fetcher.submit(formData, { 
      method: 'post',
      action: `/projects/${projectId}/integrations`
    });
    
    // Also call the optional onTest callback
    onTest?.(dataSource);
  };

  // Show notification if there's a test result
  if (testStatus.status !== 'idle') {
    return (
      <div className="flex items-center space-x-2">
        {/* View Files Button for folder uploads */}
        {isFolderUpload && onViewFiles && (
          <button
            onClick={handleViewFiles}
            className="p-2 text-gray-400 hover:text-purple-500 dark:hover:text-purple-400 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
            title="View files"
          >
            <FolderOpenIcon className="h-4 w-4" />
          </button>
        )}

        {/* Test Connection Button with Status */}
        {onTest && !isFolderUpload && (
          <button
            onClick={handleTest}
            disabled={fetcher.state === 'submitting'}
            className={`p-2 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 ${
              testStatus.status === 'testing'
                ? 'text-blue-600 dark:text-blue-400'
                : testStatus.status === 'success'
                ? 'text-green-600 dark:text-green-400'
                : testStatus.status === 'error'
                ? 'text-red-600 dark:text-red-400'
                : 'text-gray-400 hover:text-purple-500 dark:hover:text-purple-400'
            }`}
            title={
              testStatus.status === 'testing'
                ? 'Testing connection...'
                : testStatus.status === 'success'
                ? testStatus.message || 'Connection successful!'
                : testStatus.status === 'error'
                ? testStatus.message || 'Connection failed'
                : 'Test connection'
            }
          >
            {testStatus.status === 'testing' ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : testStatus.status === 'success' ? (
              <CheckCircleIcon className="h-4 w-4" />
            ) : testStatus.status === 'error' ? (
              <XCircleIcon className="h-4 w-4" />
            ) : (
              <TbPlugConnected className="h-4 w-4" />
            )}
          </button>
        )}

        {/* Edit Settings Button */}
        {onEdit && (
          <button
            onClick={handleEdit}
            className="p-2 text-gray-400 hover:text-lime-600 dark:hover:text-lime-400 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
            title="Edit settings"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
        )}

        {/* Delete Button */}
        {onDelete && (
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
            title="Delete data source"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        )}
      </div>
    );
  }

  // Helper function to clean up error messages
  function getCleanErrorMessage(message?: string): string {
    if (!message) return 'Connection failed';
    
    // Clean up common technical error messages
    if (message.includes('No credentials found')) {
      return 'Configuration incomplete';
    }
    
    if (message.includes('DataSourceType.')) {
      return 'Configuration error';
    }
    
    if (message.includes('data source configuration')) {
      return 'Invalid configuration';
    }
    
    if (message.includes('Failed to')) {
      return 'Connection failed';
    }
    
    if (message.includes('timeout') || message.includes('Timeout')) {
      return 'Connection timeout';
    }
    
    if (message.includes('unauthorized') || message.includes('Unauthorized')) {
      return 'Authentication failed';
    }
    
    if (message.includes('not found') || message.includes('Not found')) {
      return 'Resource not found';
    }
    
    // If message is too long, truncate it
    if (message.length > 50) {
      return message.substring(0, 47) + '...';
    }
    
    return message;
  }

  return (
    <div className="flex items-center space-x-2">
      {/* View Files Button for folder uploads */}
      {isFolderUpload && onViewFiles && (
        <button
          onClick={handleViewFiles}
          className="p-2 text-gray-400 hover:text-purple-500 dark:hover:text-purple-400 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
          title="View files"
        >
          <FolderOpenIcon className="h-4 w-4" />
        </button>
      )}

      {/* Test Connection Button */}
      {onTest && !isFolderUpload && (
        <button
          onClick={handleTest}
          disabled={fetcher.state === 'submitting'}
          className="p-2 text-gray-400 hover:text-purple-500 dark:hover:text-purple-400 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
          title="Test connection"
        >
          <TbPlugConnected className="h-4 w-4" />
        </button>
      )}

      {/* Edit Settings Button */}
      {onEdit && (
        <button
          onClick={handleEdit}
          className="p-2 text-gray-400 hover:text-lime-600 dark:hover:text-lime-400 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
          title="Edit settings"
        >
          <PencilIcon className="h-4 w-4" />
        </button>
      )}

      {/* Delete Button */}
      {onDelete && (
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
          title="Delete data source"
        >
          <TrashIcon className="h-4 w-4" />
        </button>
      )}
    </div>
  );
} 
