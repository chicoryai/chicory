import { Fragment, useState, useEffect } from 'react';
import { Dialog, Transition, Tab, Disclosure } from '@headlessui/react';
import { 
  XMarkIcon, 
  MagnifyingGlassIcon,
  ChevronUpIcon,
  DocumentIcon,
  CodeBracketIcon,
  ServerIcon,
  CogIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline';
import type { DataSourceTypeDefinition, DataSourceCredential } from '~/services/chicory.server';

// Define the integration type that extends DataSourceTypeDefinition
interface IntegrationType extends DataSourceTypeDefinition {
  connected?: boolean;
  configuredSources?: DataSourceCredential[];
  description?: string;
}

interface IntegrationsModalProps {
  isOpen: boolean;
  onClose: () => void;
  integrations: IntegrationType[];
  projectDataSources: DataSourceCredential[];
  projectId: string;
  onSelectIntegration: (integration: IntegrationType) => void;
}

import CsvUploadModal from "~/components/CsvUploadModal";
import ExcelUploadModal from "~/components/ExcelUploadModal";
import GenericFileUploadModal from "~/components/GenericFileUploadModal";
import DataSourceModal from "~/components/DataSourceModal";

export default function IntegrationsModal({
  isOpen,
  onClose,
  integrations,
  projectDataSources,
  projectId,
  onSelectIntegration
}: IntegrationsModalProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredIntegrations, setFilteredIntegrations] = useState<IntegrationType[]>(integrations);
  const [showCsvUploadModal, setShowCsvUploadModal] = useState(false);
  const [showExcelUploadModal, setShowExcelUploadModal] = useState(false);
  const [showGenericUploadModal, setShowGenericUploadModal] = useState<{category: 'document' | 'code'} | null>(null);
  const [selectedIntegration, setSelectedIntegration] = useState<IntegrationType | null>(null);
  const [showDataSourceModal, setShowDataSourceModal] = useState(false);
  const [selectedDataSourceForModal, setSelectedDataSourceForModal] = useState<IntegrationType | null>(null);

  // Group integrations by category
  const groupedIntegrations = filteredIntegrations.reduce((acc, integration) => {
    const category = integration.category || 'other';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(integration);
    return acc;
  }, {} as Record<string, IntegrationType[]>);

  // Define category display names and icons
  const categoryConfig = {
    document: {
      name: "Document Sources",
      icon: <DocumentIcon className="h-5 w-5" />
    },
    code: {
      name: "Code Repositories",
      icon: <CodeBracketIcon className="h-5 w-5" />
    },
    data: {
      name: "Data Sources",
      icon: <ServerIcon className="h-5 w-5" />
    },
    other: {
      name: "Other Integrations",
      icon: <CogIcon className="h-5 w-5" />
    }
  };

  // We're no longer restricting to a single data source
  // But we'll keep track of which data source types are already connected
  const connectedDataSourceTypes = projectDataSources.reduce((acc, ds) => {
    if (!acc.includes(ds.type)) {
      acc.push(ds.type);
    }
    return acc;
  }, [] as string[]);

  // Filter integrations based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredIntegrations(integrations);
      return;
    }

    const query = searchQuery.toLowerCase();
    const filtered = integrations.filter(integration => 
      integration.name.toLowerCase().includes(query) || 
      (integration.description && integration.description.toLowerCase().includes(query))
    );
    
    setFilteredIntegrations(filtered);
  }, [searchQuery, integrations]);

  // Handle integration selection
  const handleIntegrationClick = (integration: IntegrationType) => {
    setSelectedIntegration(integration);
    // CSV Upload
    if (integration.id === 'csv_upload') {
      setShowCsvUploadModal(true);
      return;
    }
    // Excel Upload
    if (integration.id === 'xlsx_upload') {
      setShowExcelUploadModal(true);
      return;
    }
    // Generic File Upload (use both id and category)
    if (integration.id === 'generic_file_upload') {
      setShowGenericUploadModal({ category: integration.category as 'document' | 'code' });
      return;
    }
    // For other integrations, show the DataSourceModal
    setSelectedDataSourceForModal(integration);
    setShowDataSourceModal(true);
  };

  // Add helper function to prepare data source for modal
  const prepareDataSourceForModal = (dataSource: IntegrationType) => {
    // Function to capitalize first letter of each word in a string
    const capitalizeWords = (str: string): string => {
      return str.replace(/\b\w/g, (char) => char.toUpperCase());
    };

    // Process required fields to capitalize field names
    const processedFields = (dataSource.required_fields || []).map(field => ({
      ...field,
      name: capitalizeWords(field.name)
    }));

    return {
      id: dataSource.id,
      name: dataSource.name,
      requiredFields: processedFields
    };
  };

  // Function to check if an integration should be disabled
  const isIntegrationDisabled = (integration: IntegrationType) => {
    // CSV and Excel uploads are always enabled
    if (integration.id === 'csv_upload' || integration.id === 'excel_upload') {
      return false;
    }
    
    // If it's already connected, it's not disabled
    if (projectDataSources.some(ds => ds.type === integration.id)) {
      return false;
    }
    
    // No other restrictions - all data sources are available
    return false;
  };

  // Function to get the appropriate button text based on integration state
  const getButtonText = (integration: IntegrationType) => {
    // For CSV and Excel, always show "Upload"
    if (integration.id === 'csv_upload' || integration.id === 'excel_upload') {
      return "Upload";
    }
    
    if (projectDataSources.some(ds => ds.type === integration.id)) {
      return "Manage";
    }
    
    if (isIntegrationDisabled(integration)) {
      return "Unavailable";
    }
    
    return "Connect";
  };

  return (
    <Transition.Root show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-4xl sm:p-6">
                <div className="absolute right-0 top-0 hidden pr-4 pt-4 sm:block">
                  <button
                    type="button"
                    className="rounded-md bg-white dark:bg-gray-800 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-lime-500 focus:ring-offset-2"
                    onClick={onClose}
                  >
                    <span className="sr-only">Close</span>
                    <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                  </button>
                </div>
                
                <div className="sm:flex sm:items-start">
                  <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full">
                    <Dialog.Title as="h3" className="text-xl font-semibold leading-6 text-gray-900 dark:text-white">
                      Add Data Source
                    </Dialog.Title>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Connect your data sources to train and improve your AI assistant.
                      </p>
                    </div>
                    
                    {/* Search Bar */}
                    <div className="mt-4 mb-6">
                      <div className="relative rounded-md shadow-sm">
                        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                          <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" aria-hidden="true" />
                        </div>
                        <input
                          type="text"
                          className="block w-full rounded-md border-0 py-2 pl-10 text-gray-900 dark:text-white dark:bg-gray-700 ring-1 ring-inset ring-gray-300 dark:ring-gray-600 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-lime-600 sm:text-sm sm:leading-6"
                          placeholder="Search integrations..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                        />
                      </div>
                    </div>
                    
                    {/* Tabs for Categories */}
                    <Tab.Group>
                      <Tab.List className="flex space-x-1 rounded-xl bg-gray-100 dark:bg-gray-700 p-1 mb-6">
                        {Object.entries(categoryConfig).map(([category, { name }]) => (
                          <Tab
                            key={category}
                            className={({ selected }) =>
                              `w-full rounded-lg py-2.5 text-sm font-medium leading-5 
                              ${
                                selected
                                  ? 'bg-white dark:bg-gray-600 shadow text-lime-600 dark:text-lime-400'
                                  : 'text-gray-700 dark:text-gray-300 hover:bg-white/[0.12] hover:text-lime-600 dark:hover:text-lime-400'
                              }`
                            }
                          >
                            {name}
                          </Tab>
                        ))}
                      </Tab.List>
                      <Tab.Panels>
                        {Object.entries(categoryConfig).map(([category, { name, icon }]) => (
                          <Tab.Panel key={category} className="space-y-4">
                            {groupedIntegrations[category]?.length > 0 ? (
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {groupedIntegrations[category].map((integration) => {
                                  const isConnected = projectDataSources.some(ds => ds.type === integration.id);
                                  const isDisabled = isIntegrationDisabled(integration);
                                  
                                  return (
                                    <div 
                                      key={`${integration.id}-${integration.category}`} 
                                      className={`bg-white dark:bg-gray-700 rounded-lg border ${
                                        isConnected 
                                          ? 'border-green-200 dark:border-green-800' 
                                          : isDisabled 
                                            ? 'border-gray-200 dark:border-gray-600 opacity-60' 
                                            : 'border-gray-200 dark:border-gray-600'
                                      } p-4 relative`}
                                    >
                                      <div className="flex items-start">
                                        <div className="flex-shrink-0 h-10 w-10 flex items-center justify-center rounded-full bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 shadow-sm">
                                          <img
                                            src={`/icons/${integration.id}.svg`}
                                            alt={integration.name}
                                            className="h-6 w-6 "
                                            onError={(e) => {
                                              (e.target as HTMLImageElement).src = "/icons/generic-integration.svg";
                                            }}
                                          />
                                        </div>
                                        <div className="ml-3 flex-1">
                                          <h3 className="text-sm font-medium text-gray-900 dark:text-white flex items-center">
                                            {integration.name}
                                            {isConnected && (
                                              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                                                Connected
                                              </span>
                                            )}
                                          </h3>
                                          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                                            {integration.description || `Connect to your ${integration.name} data.`}
                                          </p>
                                        </div>
                                      </div>
                                      
                                      <div className="mt-4 flex justify-end">
                                        <button
                                          type="button"
                                          onClick={() => !isDisabled && handleIntegrationClick(integration)}
                                          disabled={isDisabled}
                                          className={`inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md ${
                                            isConnected
                                              ? 'bg-white dark:bg-gray-600 text-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-500'
                                              : isDisabled
                                                ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                                                : 'bg-lime-600 text-white hover:bg-lime-700 focus:ring-lime-500'
                                          } shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2`}
                                        >
                                          {getButtonText(integration)}
                                        </button>
                                      </div>
                                      
                                      {/* Removed the warning tooltip about data source restrictions */}
                                    </div>
                                  );
                                })}
                              </div>
                            ) : (
                              <div className="text-center py-8">
                                <p className="text-gray-500 dark:text-gray-400">
                                  {searchQuery 
                                    ? `No ${name.toLowerCase()} found matching "${searchQuery}".` 
                                    : `No ${name.toLowerCase()} available.`}
                                </p>
                              </div>
                            )}
                          </Tab.Panel>
                        ))}
                      </Tab.Panels>
                    </Tab.Group>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
        {/* Add DataSourceModal */}
        {selectedDataSourceForModal && (
          <DataSourceModal
            isOpen={showDataSourceModal}
            onClose={() => {
              setShowDataSourceModal(false);
              setSelectedDataSourceForModal(null);
            }}
            dataSource={prepareDataSourceForModal(selectedDataSourceForModal)}
            projectId={projectId}
          />
        )}
      </Dialog>

      {/* Upload modals rendered outside the Dialog but inside Transition.Root */}
      <CsvUploadModal
        isOpen={showCsvUploadModal}
        onClose={() => setShowCsvUploadModal(false)}
        projectId={projectId}
      />
      <ExcelUploadModal
        isOpen={showExcelUploadModal}
        onClose={() => setShowExcelUploadModal(false)}
        projectId={projectId}
      />
      <GenericFileUploadModal
        isOpen={!!showGenericUploadModal}
        onClose={() => setShowGenericUploadModal(null)}
        projectId={projectId}
        category={showGenericUploadModal?.category || 'document'}
      />
    </Transition.Root>
  );
}
