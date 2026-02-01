import React, { useState, useMemo } from 'react';
import { DataSourceTypeDefinition, IntegrationCategory } from '~/types/integrations';
import IntegrationCard from '~/components/integrations/data-sources/IntegrationCard';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import DataSourceCreateModal from "~/components/DataSourceCreateModal";
import FolderUploadModal from "~/components/FolderUploadModal";

interface AvailableIntegrationsListProps {
  integrations: DataSourceTypeDefinition[];
  projectId: string;
  onDataSourceCreated?: () => void;
  className?: string;
}

/**
 * Displays available integrations in a categorized, searchable list
 * Groups integrations by category and provides search functionality
 */
export default function AvailableIntegrationsList({
  integrations,
  projectId,
  onDataSourceCreated,
  className = ""
}: AvailableIntegrationsListProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedIntegration, setSelectedIntegration] = useState<DataSourceTypeDefinition | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isFolderUploadModalOpen, setIsFolderUploadModalOpen] = useState(false);

  const filteredIntegrations = integrations.filter(integration => {
    const matchesSearch = integration.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         integration.description?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCategory = selectedCategory === 'all' || 
                           integration.category === selectedCategory;
    
    return matchesSearch && matchesCategory;
  });

  const groupedIntegrations = filteredIntegrations.reduce((acc, integration) => {
    const category = integration.category || 'other';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(integration);
    return acc;
  }, {} as Record<string, DataSourceTypeDefinition[]>);

  // Get available categories
  const availableCategories = Array.from(
    new Set(integrations.map(i => i.category || 'other'))
  ) as IntegrationCategory[];

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'document':
        return 'Documents';
      case 'data':
        return 'Data';
      case 'code':
        return 'Code';
      case 'databases':
        return 'Databases';
      case 'cloud_storage':
        return 'Cloud Storage';
      case 'apis':
        return 'APIs';
      case 'files':
        return 'Files';
      case 'productivity':
        return 'Productivity';
      case 'analytics':
        return 'Analytics';
      case 'tool':
        return 'Tools';
      default:
        return 'Other';
    }
  };

  const handleIntegrationClick = (integration: DataSourceTypeDefinition) => {
    setSelectedIntegration(integration);
    // Use folder upload modal for folder_upload type
    if (integration.id === 'folder_upload') {
      setIsFolderUploadModalOpen(true);
    } else {
      setIsCreateModalOpen(true);
    }
  };

  const handleCloseCreateModal = () => {
    setIsCreateModalOpen(false);
    setSelectedIntegration(null);
  };

  const handleCloseFolderUploadModal = () => {
    setIsFolderUploadModalOpen(false);
    setSelectedIntegration(null);
  };

  const handleDataSourceCreated = () => {
    onDataSourceCreated?.();
    handleCloseCreateModal();
  };

  const handleFolderUploadSuccess = () => {
    onDataSourceCreated?.();
    handleCloseFolderUploadModal();
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Search Bar */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" />
        </div>
        <input
          type="text"
          placeholder="Search integrations..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:border-lime-500 text-sm"
        />
      </div>

      {/* Category Filter */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedCategory('all')}
          className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
            selectedCategory === 'all'
              ? 'bg-whitePurple-100 text-purple-800 dark:bg-purple-800 dark:text-purple-400'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
          }`}
        >
          All
        </button>
        {availableCategories.map(category => (
          <button
            key={category}
            onClick={() => setSelectedCategory(category)}
            className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
              selectedCategory === category
                ? 'bg-whitePurple-100 text-purple-800 dark:bg-purple-800 dark:text-purple-400'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
            }`}
          >
            {getCategoryLabel(category)}
          </button>
        ))}
      </div>

      {/* Results */}
      {filteredIntegrations.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No integrations found matching your criteria.
          </p>
        </div>
      ) : (
        <div className="max-h-96 overflow-y-auto px-4 py-4">
          <div className="grid grid-cols-3 gap-6">
            {filteredIntegrations.map(integration => (
              <IntegrationCard
                key={`${integration.id}-${integration.category}`}
                integration={integration}
                onSelect={() => handleIntegrationClick(integration)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Create Data Source Modal */}
      {selectedIntegration && selectedIntegration.id !== 'folder_upload' && (
        <DataSourceCreateModal
          isOpen={isCreateModalOpen}
          onClose={handleCloseCreateModal}
          onSuccess={handleDataSourceCreated}
          dataSourceType={selectedIntegration}
          projectId={projectId}
        />
      )}

      {/* Folder Upload Modal */}
      <FolderUploadModal
        isOpen={isFolderUploadModalOpen}
        onClose={handleCloseFolderUploadModal}
        projectId={projectId}
        category="document"
        onSuccess={handleFolderUploadSuccess}
      />

      {/* Footer */}
      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {filteredIntegrations.length} integration{filteredIntegrations.length !== 1 ? 's' : ''} available
        </p>
      </div>
    </div>
  );
} 