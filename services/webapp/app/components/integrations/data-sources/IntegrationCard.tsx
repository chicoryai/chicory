import React from 'react';
import { DataSourceTypeDefinition } from '~/types/integrations';
import { 
  CircleStackIcon, 
  CloudIcon, 
  DocumentIcon, 
  CogIcon,
  ChartBarIcon,
  BriefcaseIcon,
  CodeBracketIcon
} from '@heroicons/react/24/outline';

interface IntegrationCardProps {
  integration: DataSourceTypeDefinition;
  onSelect: (integration: DataSourceTypeDefinition) => void;
  variant?: 'default' | 'compact';
  className?: string;
}

/**
 * Displays an individual integration option with icon and name in a grid layout
 * Simplified design for 3-column grid display
 */
export default function IntegrationCard({
  integration,
  onSelect,
  variant = 'default',
  className = ""
}: IntegrationCardProps) {
  const getIntegrationIcon = (integrationId: string, category?: string) => {
    // Handle generic_file_upload with different icons based on category
    if (integrationId === 'generic_file_upload') {
      return category === 'code' ? '/icons/code_file_upload.svg' : '/icons/generic_file_upload.svg';
    }
    
    // Map integration IDs to their corresponding icon files
    const iconMap: Record<string, string> = {
      'csv_upload': '/icons/csv_upload.svg',
      'xlsx_upload': '/icons/xlsx_upload.svg',
      'google_drive': '/icons/google_drive.svg',
      'github': '/icons/github.svg',
      'databricks': '/icons/databricks.svg',
      'direct_upload': '/icons/direct_upload.svg',
      'snowflake': '/icons/snowflake.svg',
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
      'webfetch': '/icons/webfetch.svg',
    };

    return iconMap[integrationId] || '/icons/generic-integration.svg';
  };

  const getCategoryIcon = (category?: string) => {
    switch (category) {
      case 'code':
        return CodeBracketIcon;
      case 'document':
        return DocumentIcon;
      case 'databases':
        return CircleStackIcon;
      case 'cloud_storage':
        return CloudIcon;
      case 'files':
        return DocumentIcon;
      case 'apis':
        return CogIcon;
      case 'analytics':
        return ChartBarIcon;
      case 'productivity':
        return BriefcaseIcon;
      default:
        return CogIcon;
    }
  };

  const getDisplayName = (integration: DataSourceTypeDefinition) => {
    // Special case for generic file upload with code category
    if (integration.id === 'generic_file_upload' && integration.category === 'code') {
      return 'Code File Upload';
    }
    return integration.name;
  };

  const iconSrc = getIntegrationIcon(integration.id, integration.category);
  const FallbackIcon = getCategoryIcon(integration.category);

  const handleClick = () => {
    onSelect(integration);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(integration);
    }
  };

  return (
    <button
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={`w-full text-center p-3 rounded-lg hover:bg-whitePurple-50 dark:hover:bg-lime-900/10 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-lime-500 ${className}`}
      aria-label={`Connect ${getDisplayName(integration)}`}
    >
      <div className="flex flex-col items-center space-y-2">
        <div className="flex-shrink-0">
          <div className="w-10 h-10 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center overflow-hidden">
            <img 
              src={iconSrc} 
              alt={`${integration.name} icon`}
              className="w-6 h-6 object-contain"
              onError={(e) => {
                // Fallback to category icon if image fails to load
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
                target.nextElementSibling?.classList.remove('hidden');
              }}
            />
            <FallbackIcon className="w-5 h-5 text-gray-600 dark:text-gray-400 hidden" />
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-900 dark:text-white text-center">
            {getDisplayName(integration)}
          </p>
        </div>
      </div>
    </button>
  );
} 