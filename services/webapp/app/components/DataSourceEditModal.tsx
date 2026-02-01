import { Modal } from "~/components/ui/Modal";
import { DataSourceForm } from "~/components/forms/DataSourceForm";
import { 
  DocumentTextIcon, 
  TableCellsIcon, 
  DocumentIcon,
  CalendarIcon,
  UserIcon,
  InformationCircleIcon
} from "@heroicons/react/24/outline";
import type { DataSourceCredential, DataSourceTypeDefinition } from "~/services/chicory.server";

interface DataSourceEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  dataSource: DataSourceCredential;
  dataSourceType: DataSourceTypeDefinition;
  projectId: string;
}

export default function DataSourceEditModal({
  isOpen,
  onClose,
  dataSource,
  dataSourceType,
  projectId,
}: DataSourceEditModalProps) {
  if (!isOpen) return null;

  // Check if this is a file-based data source
  const fileDataSources = ['csv_upload', 'xlsx_upload', 'generic_file_upload'];
  const isFileDataSource = fileDataSources.includes(dataSource.type);

  // Extract initial values from the data source configuration
  const initialValues = dataSource.configuration || {};

  // Prepare data source type for the form
  const formDataSource = {
    id: dataSourceType.id,
    name: dataSourceType.name,
    requiredFields: dataSourceType.required_fields
  };

  // Get file icon based on data source type
  const getFileIcon = () => {
    switch (dataSource.type) {
      case 'csv_upload':
        return TableCellsIcon;
      case 'xlsx_upload':
        return TableCellsIcon;
      case 'generic_file_upload':
        return DocumentTextIcon;
      default:
        return DocumentIcon;
    }
  };

  // Get file type label based on data source type and category
  const getFileTypeLabel = () => {
    switch (dataSource.type) {
      case 'csv_upload':
        return 'CSV File';
      case 'xlsx_upload':
        return 'Excel File';
      case 'generic_file_upload':
        if (dataSourceType.category === 'code') {
          return 'Code File';
        } else {
          return 'Document';
        }
      default:
        return 'File';
    }
  };

  // Format file size if available
  const formatFileSize = (bytes: number) => {
    if (!bytes) return 'Unknown size';
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      title={`${dataSource.name}`}
    >
      {isFileDataSource ? (
        <div className="space-y-6">
          {/* File Information Header */}
          <div className="flex items-start space-x-4">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-whiteLime-100 dark:bg-lime-900 rounded-lg flex items-center justify-center">
                {(() => {
                  const IconComponent = getFileIcon();
                  return <IconComponent className="w-6 h-6 text-lime-600 dark:text-lime-400" />;
                })()}
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                {dataSource.name}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {getFileTypeLabel()}
              </p>
            </div>
            <div className="flex-shrink-0">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                dataSource.status === 'configured' 
                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                  : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
              }`}>
                {dataSource.status}
              </span>
            </div>
          </div>

          {/* File Details */}
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3 flex items-center">
              <InformationCircleIcon className="w-4 h-4 mr-2" />
              File Details
            </h4>
            <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {initialValues.filename && (
                <div>
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">Filename</dt>
                  <dd className="text-sm text-gray-900 dark:text-white font-mono bg-white dark:bg-gray-700 px-2 py-1 rounded border">
                    {initialValues.filename}
                  </dd>
                </div>
              )}
              {initialValues.file_size && (
                <div>
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">File Size</dt>
                  <dd className="text-sm text-gray-900 dark:text-white">
                    {formatFileSize(initialValues.file_size)}
                  </dd>
                </div>
              )}
              {initialValues.mime_type && (
                <div>
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">File Type</dt>
                  <dd className="text-sm text-gray-900 dark:text-white font-mono">
                    {initialValues.mime_type}
                  </dd>
                </div>
              )}
              {initialValues.category && (
                <div>
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">Category</dt>
                  <dd className="text-sm text-gray-900 dark:text-white">
                    {initialValues.category}
                  </dd>
                </div>
              )}
            </dl>
          </div>

          {/* Upload Information */}
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
            <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3 flex items-center">
              <CalendarIcon className="w-4 h-4 mr-2" />
              Upload Information
            </h4>
            <dl className="grid grid-cols-1 gap-3">
              <div>
                <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">Uploaded</dt>
                <dd className="text-sm text-gray-900 dark:text-white">
                  {formatDate(dataSource.created_at)}
                </dd>
              </div>
              {dataSource.updated_at !== dataSource.created_at && (
                <div>
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400">Last Modified</dt>
                  <dd className="text-sm text-gray-900 dark:text-white">
                    {formatDate(dataSource.updated_at)}
                  </dd>
                </div>
              )}
            </dl>
          </div>

          {/* Info Message */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex">
              <InformationCircleIcon className="w-5 h-5 text-blue-400 flex-shrink-0" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                  File Data Source
                </h3>
                <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
                  This is a file-based data source. The file has been uploaded and processed. 
                  No connection configuration is required.
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500"
            >
              Close
            </button>
          </div>
        </div>
      ) : (
        <>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Update the connection information for this data source.
          </p>
          
          <DataSourceForm 
            dataSource={formDataSource} 
            projectId={projectId} 
            onSuccess={onClose}
            initialValues={initialValues}
            isEditing={true}
            dataSourceId={dataSource.id}
          />
        </>
      )}
    </Modal>
  );
}
