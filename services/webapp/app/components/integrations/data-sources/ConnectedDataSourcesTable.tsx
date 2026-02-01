import React, { useState, useMemo } from 'react';
import { DataSourceCredential, DataSourceTypeDefinition } from '~/types/integrations';
import { DataSourceTableRow } from './index';
import EmptyState from '../layout/EmptyState';
import { CircleStackIcon } from '@heroicons/react/24/outline';

interface ConnectedDataSourcesTableProps {
  dataSources: DataSourceCredential[];
  dataSourceTypes: DataSourceTypeDefinition[];
  projectId: string;
  onEdit?: (dataSource: DataSourceCredential) => void;
  onDelete?: (dataSource: DataSourceCredential) => void;
  onTest?: (dataSource: DataSourceCredential) => void;
  onViewFiles?: (dataSource: DataSourceCredential) => void;
  isLoading?: boolean;
  className?: string;
}

/**
 * Table component for displaying connected data sources
 * Shows data source information with actions for edit, delete, and test
 */
export default function ConnectedDataSourcesTable({
  dataSources,
  dataSourceTypes,
  projectId,
  onEdit,
  onDelete,
  onTest,
  onViewFiles,
  isLoading = false,
  className = ""
}: ConnectedDataSourcesTableProps) {
  const [activeFilter, setActiveFilter] = useState<string>('all');

  // Create a map of type to category for quick lookup
  const typeToCategory = useMemo(() => {
    return dataSourceTypes.reduce((acc, dsType) => {
      acc[dsType.id] = dsType.category || 'other';
      return acc;
    }, {} as Record<string, string>);
  }, [dataSourceTypes]);

  // Get unique categories and their counts
  const categories = useMemo(() => {
    const categoryMap = dataSources.reduce((acc, ds) => {
      const category = typeToCategory[ds.type] || 'other';
      acc[category] = (acc[category] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(categoryMap).map(([category, count]) => ({
      category,
      count,
      label: getCategoryLabel(category)
    }));
  }, [dataSources, typeToCategory]);

  // Filter data sources based on active filter
  const filteredDataSources = useMemo(() => {
    if (activeFilter === 'all') return dataSources;
    return dataSources.filter(ds => {
      const category = typeToCategory[ds.type] || 'other';
      return category === activeFilter;
    });
  }, [dataSources, activeFilter, typeToCategory]);

  function getCategoryLabel(category: string): string {
    const labels: Record<string, string> = {
      'databases': 'Databases',
      'cloud_storage': 'Cloud Storage',
      'apis': 'APIs',
      'files': 'Files',
      'productivity': 'Productivity',
      'analytics': 'Analytics',
      'other': 'Other'
    };
    return labels[category] || category.charAt(0).toUpperCase() + category.slice(1);
  }

  if (isLoading) {
    return (
      <div className={`animate-pulse space-y-3 ${className}`}>
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-20 bg-gray-100 dark:bg-gray-800 rounded-lg"></div>
        ))}
      </div>
    );
  }

  if (dataSources.length === 0) {
    return (
      <div className={`py-12 ${className}`}>
        <EmptyState
          icon={CircleStackIcon}
          title="No data sources connected"
          description="Connect your first data source to start training your model with your data."
        />
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header with Count and Filter Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {filteredDataSources.length} of {dataSources.length} connected
            </span>
          </div>
        </div>

        {/* Filter Tabs */}
        {categories.length > 1 && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveFilter('all')}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                activeFilter === 'all'
                  ? 'bg-whitePurple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400 shadow-sm'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
              }`}
            >
              All ({dataSources.length})
            </button>
            {categories.map(({ category, count, label }) => (
              <button
                key={category}
                onClick={() => setActiveFilter(category)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 ${
                  activeFilter === category
                    ? 'bg-whitePurple-100 text-whitePurple-800 dark:bg-purple-900/30 dark:text-purple-400 shadow-sm'
                    : 'bg-gray-50 text-gray-600 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
                }`}
              >
                {label} ({count})
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Table Header */}
      <div className="hidden md:grid md:grid-cols-10 gap-4 px-6 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="col-span-4">Data Source</div>
        <div className="col-span-2">Status</div>
        <div className="col-span-2">Last Updated</div>
        <div className="col-span-2">Actions</div>
      </div>

      {/* Table Body */}
      <div className="space-y-3">
        {filteredDataSources.map((dataSource) => (
          <DataSourceTableRow
            key={dataSource.id}
            dataSource={dataSource}
            projectId={projectId}
            onEdit={onEdit}
            onDelete={onDelete}
            onTest={onTest}
            onViewFiles={onViewFiles}
          />
        ))}
      </div>

      {/* Empty State for Filtered Results */}
      {filteredDataSources.length === 0 && activeFilter !== 'all' && (
        <div className="text-center py-12">
          <div className="w-12 h-12 mx-auto mb-4 bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center">
            <CircleStackIcon className="w-6 h-6 text-gray-400" />
          </div>
          <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
            No {getCategoryLabel(activeFilter).toLowerCase()} found
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No {getCategoryLabel(activeFilter).toLowerCase()} data sources are currently connected.
          </p>
        </div>
      )}
    </div>
  );
} 