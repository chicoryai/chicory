import { Modal } from "~/components/ui/Modal";
import { useFetcher } from "@remix-run/react";
import { useState, useEffect } from "react";
import { 
  ExclamationTriangleIcon,
  DocumentTextIcon, 
  TableCellsIcon, 
  DocumentIcon,
  CodeBracketIcon
} from "@heroicons/react/24/outline";
import type { DataSourceCredential, DataSourceTypeDefinition } from "~/services/chicory.server";

interface ActionData {
  success?: boolean;
  message?: string;
  error?: string;
  dataSourceId?: string;
  _action?: string;
}

interface DataSourceDeleteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  dataSource: DataSourceCredential;
  dataSourceType: DataSourceTypeDefinition;
  projectId: string;
}

export default function DataSourceDeleteModal({
  isOpen,
  onClose,
  onSuccess,
  dataSource,
  dataSourceType,
  projectId,
}: DataSourceDeleteModalProps) {
  const [deleteS3Object, setDeleteS3Object] = useState(true);
  const [notification, setNotification] = useState<{
    type: 'success' | 'error' | null;
    message: string;
  }>({ type: null, message: '' });

  const fetcher = useFetcher<ActionData>();

  // Handle deletion response
  useEffect(() => {
    if (fetcher.data && fetcher.state === "idle" && fetcher.data._action === "deleteDataSource") {
      if (fetcher.data.success) {
        setNotification({
          type: 'success',
          message: fetcher.data.message || "Data source deleted successfully!"
        });
        
        // Close modal and call success callback after showing success message
        setTimeout(() => {
          setNotification({ type: null, message: '' });
          onSuccess?.();
          onClose();
        }, 1500);
      } else {
        setNotification({
          type: 'error',
          message: fetcher.data.error || fetcher.data.message || "Failed to delete data source. Please try again."
        });
        
        // Clear error notification after 5 seconds
        setTimeout(() => {
          setNotification({ type: null, message: '' });
        }, 5000);
      }
    }
  }, [fetcher.data, fetcher.state, onSuccess, onClose]);

  // Clear notification when modal closes
  useEffect(() => {
    if (!isOpen) {
      setNotification({ type: null, message: '' });
      setDeleteS3Object(true); // Reset to default
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Check if this is a file-based data source
  const fileDataSources = ['csv_upload', 'xlsx_upload', 'generic_file_upload'];
  const isFileDataSource = fileDataSources.includes(dataSource.type);

  // Get appropriate icon for data source type and category
  const getDataSourceIcon = () => {
    switch (dataSource.type) {
      case 'csv_upload':
        return TableCellsIcon;
      case 'xlsx_upload':
        return TableCellsIcon;
      case 'generic_file_upload':
        if (dataSourceType.category === 'code') {
          return CodeBracketIcon;
        } else {
          return DocumentTextIcon;
        }
      default:
        return DocumentIcon;
    }
  };

  const handleConfirmDelete = () => {
    const formData = new FormData();
    formData.append("_action", "deleteDataSource");
    formData.append("dataSourceId", dataSource.id);
    formData.append("projectId", projectId);
    formData.append("deleteS3Object", deleteS3Object.toString());
    
    fetcher.submit(formData, { 
      method: "post",
      action: `/projects/${projectId}/integrations`
    });
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      title="Delete Data Source"
    >
      <div className="space-y-6">
        {/* Notification */}
        {notification.type && (
          <div className={`p-4 rounded-lg border ${
            notification.type === 'success' 
              ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800' 
              : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
          }`}>
            <div className="flex items-start">
              <div className="flex-shrink-0">
                {notification.type === 'success' ? (
                  <ExclamationTriangleIcon className="w-5 h-5 text-green-400" />
                ) : (
                  <ExclamationTriangleIcon className="w-5 h-5 text-red-400" />
                )}
              </div>
              <div className="ml-3">
                <p className={`text-sm font-medium ${
                  notification.type === 'success' 
                    ? 'text-green-800 dark:text-green-200' 
                    : 'text-red-800 dark:text-red-200'
                }`}>
                  {notification.message}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Warning Header */}
        <div className="flex items-start space-x-4">
          <div className="flex-shrink-0">
            <div className="w-12 h-12 bg-red-100 dark:bg-red-900 rounded-lg flex items-center justify-center">
              <ExclamationTriangleIcon className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Delete "{dataSource.name}"
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {dataSourceType.name}
            </p>
          </div>
          <div className="flex-shrink-0">
            {isFileDataSource && (
              <div className="w-8 h-8 bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center">
                {(() => {
                  const IconComponent = getDataSourceIcon();
                  return <IconComponent className="w-4 h-4 text-gray-600 dark:text-gray-400" />;
                })()}
              </div>
            )}
          </div>
        </div>

        {/* Warning Message */}
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-400 flex-shrink-0" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                This action cannot be undone
              </h3>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                Deleting this data source will permanently remove it from your project. 
                {isFileDataSource && " The uploaded file will also be removed from storage."}
                {!isFileDataSource && " All connection settings will be lost."}
              </p>
            </div>
          </div>
        </div>

        {/* S3 Object Deletion Option (for file-based data sources) */}
        {isFileDataSource && (
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <div className="flex items-start">
              <input
                type="checkbox"
                id="delete-s3-object"
                checked={deleteS3Object}
                onChange={(e) => setDeleteS3Object(e.target.checked)}
                className="h-4 w-4 text-red-500 focus:ring-red-500 border-gray-300 rounded mt-0.5"
              />
              <div className="ml-3">
                <label htmlFor="delete-s3-object" className="text-sm font-medium text-gray-900 dark:text-white">
                  Delete uploaded file from storage
                </label>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  This will permanently remove the file from cloud storage. Uncheck this if you want to keep the file for other purposes.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            disabled={fetcher.state !== "idle"}
            className="px-4 py-2 text-sm font-medium rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirmDelete}
            disabled={fetcher.state !== "idle"}
            className="px-4 py-2 text-sm font-medium rounded-md bg-red-500 hover:bg-red-600 text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
          >
            {fetcher.state !== "idle" ? "Deleting..." : "Delete Data Source"}
          </button>
        </div>
      </div>
    </Modal>
  );
} 
