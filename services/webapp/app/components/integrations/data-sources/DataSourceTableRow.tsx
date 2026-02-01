import React from 'react';
import { DataSourceCredential } from '~/types/integrations';
import { DataSourceActions } from './index';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  FolderIcon
} from '@heroicons/react/24/outline';

interface DataSourceTableRowProps {
  dataSource: DataSourceCredential;
  projectId: string;
  onEdit?: (dataSource: DataSourceCredential) => void;
  onDelete?: (dataSource: DataSourceCredential) => void;
  onTest?: (dataSource: DataSourceCredential) => void;
  onViewFiles?: (dataSource: DataSourceCredential) => void;
}

/**
 * Individual data source row component
 * Displays data source information with status and actions
 */
export default function DataSourceTableRow({
  dataSource,
  projectId,
  onEdit,
  onDelete,
  onTest,
  onViewFiles
}: DataSourceTableRowProps) {
  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
      case 'connected':
      case 'ready':
        return <CheckCircleIcon className="h-4 w-4 text-green-500" />;
      case 'error':
      case 'failed':
      case 'disconnected':
        return <ExclamationTriangleIcon className="h-4 w-4 text-red-500" />;
      case 'pending':
      case 'connecting':
        return <ClockIcon className="h-4 w-4 text-yellow-500" />;
      default:
        return <CheckCircleIcon className="h-4 w-4 text-green-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'active':
      case 'connected':
      case 'ready':
        return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/20';
      case 'error':
      case 'failed':
      case 'disconnected':
        return 'text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/20';
      case 'pending':
      case 'connecting':
        return 'text-yellow-600 bg-yellow-100 dark:text-yellow-400 dark:bg-yellow-900/20';
      default:
        return 'text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/20';
    }
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return 'Unknown';
    }
  };

  const getDisplayName = (dataSource: DataSourceCredential) => {
    if (dataSource.type === 'snowflake') {
      return 'Snowflake Connection';
    }
    return dataSource.name;
  };

  const getDataSourceIcon = (type: string) => {
    // Handle generic_file_upload with different icons based on category
    if (type === 'generic_file_upload') {
      const category = dataSource.configuration?.category;
      const iconPath = category === 'code' ? '/icons/code_file_upload.svg' : '/icons/generic_file_upload.svg';
      
      return (
        <div className="h-10 w-10 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center p-2">
          <img 
            src={iconPath} 
            alt={`${type} icon`}
            className="h-6 w-6"
          />
        </div>
      );
    }
    
    const iconMap: Record<string, string> = {
      'google_drive': '/icons/google_drive.svg',
      'github': '/icons/github.svg',
      'databricks': '/icons/databricks.svg',
      'snowflake': '/icons/snowflake.svg',
      'csv_upload': '/icons/csv_upload.svg',
      'xlsx_upload': '/icons/xlsx_upload.svg',
      'direct_upload': '/icons/direct_upload.svg',
      'bigquery': '/icons/bigquery.svg',
      'glue': '/icons/glue.svg',
      'datazone': '/icons/datazone.svg',
      's3': '/icons/s3.png',
      'redash': '/icons/redash.svg',
      'redshift': '/icons/redshift.svg',
      'looker': '/icons/looker.svg',
      'dbt': '/icons/dbt.svg',
      'datahub': '/icons/datahub.svg',
      'airflow': '/icons/airflow.svg',
      'anthropic': '/icons/anthropic.png',
      'jira': '/icons/jira.svg',
      'azure_blob_storage': '/icons/azure_blob_storage.svg',
      'azure_data_factory': '/icons/azure_data_factory.svg',
      'folder_upload': '/icons/folder_upload.svg'
    };

    const iconPath = iconMap[type] || '/icons/generic-integration.svg';
    
    return (
      <div className="h-10 w-10 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center p-2">
        <img 
          src={iconPath} 
          alt={`${type} icon`}
          className="h-6 w-6"
        />
      </div>
    );
  };

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow duration-200">
      {/* Mobile Layout */}
      <div className="md:hidden space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            {getDataSourceIcon(dataSource.type)}
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                {getDisplayName(dataSource)}
              </h3>
            </div>
          </div>
          <DataSourceActions
            dataSource={dataSource}
            projectId={projectId}
            onEdit={onEdit}
            onDelete={onDelete}
            onTest={onTest}
            onViewFiles={onViewFiles}
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {getStatusIcon(dataSource.status)}
            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(dataSource.status)}`}>
              {dataSource.status || 'connected'}
            </span>
          </div>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {formatDate(dataSource.updated_at)}
          </span>
        </div>
      </div>

      {/* Desktop Layout */}
      <div className="hidden md:grid md:grid-cols-10 gap-4 items-center">
        {/* Data Source Info */}
        <div className="col-span-4 flex items-center space-x-3">
          {getDataSourceIcon(dataSource.type)}
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {getDisplayName(dataSource)}
            </h3>
          </div>
        </div>

        {/* Status */}
        <div className="col-span-2">
          <div className="flex items-center space-x-2">
            {getStatusIcon(dataSource.status)}
            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(dataSource.status)}`}>
              {dataSource.status || 'connected'}
            </span>
          </div>
        </div>

        {/* Last Updated */}
        <div className="col-span-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {formatDate(dataSource.updated_at)}
          </span>
        </div>

        {/* Actions */}
        <div className="col-span-2">
          <DataSourceActions
            dataSource={dataSource}
            projectId={projectId}
            onEdit={onEdit}
            onDelete={onDelete}
            onTest={onTest}
            onViewFiles={onViewFiles}
          />
        </div>
      </div>
    </div>
  );
} 