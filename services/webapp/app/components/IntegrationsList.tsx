import { Fragment } from "react";
import { Tab, Popover, Transition } from "@headlessui/react";
import { 
  EllipsisVerticalIcon, 
  PencilIcon,
  QuestionMarkCircleIcon,
  DocumentIcon,
  CodeBracketIcon,
  ServerIcon,
  CogIcon
} from '@heroicons/react/24/outline';
import type { DataSourceCredential, DataSourceTypeDefinition } from "~/services/chicory.server";
import FileUploadCard from "./FileUploadCard";

// Define the IntegrationType interface that extends DataSourceTypeDefinition
interface IntegrationType extends DataSourceTypeDefinition {
  connected: boolean;
  configuredSources: DataSourceCredential[];
  description?: string;
}

interface IntegrationsListProps {
  integrations: IntegrationType[];
  projectDataSources: DataSourceCredential[];
  onSelectIntegration: (dataSource: DataSourceTypeDefinition) => void;
}

export default function IntegrationsList({
  integrations,
  projectDataSources,
  onSelectIntegration,
  projectId
}: IntegrationsListProps & { projectId: string }) {
  const getDisplayName = (integration: IntegrationType) => {
    // Special case for generic file upload with code category
    if (integration.id === 'generic_file_upload' && integration.category === 'code') {
      return 'Code File Upload';
    }
    return integration.name;
  };

  // Group integrations by category
  const groupedIntegrations = integrations.reduce((acc: Record<string, IntegrationType[]>, integration: IntegrationType) => {
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
  const connectedDataSourceTypes = projectDataSources.reduce((acc: string[], ds) => {
    if (!acc.includes(ds.type)) {
      acc.push(ds.type);
    }
    return acc;
  }, [] as string[]);

  const isIntegrationDisabled = (integration: IntegrationType) => {
    // CSV and Excel uploads are always enabled
    if (integration.id === 'csv_upload' || integration.id === 'xlsx_upload') {
      return false;
    }
    
    // If it's already connected, it's not disabled
    if (projectDataSources.some(ds => ds.type === integration.id)) {
      return false;
    }
    
    // No other restrictions - all data sources are available
    return false;
  };

  const getButtonText = (integration: IntegrationType) => {
    // For CSV and Excel, always show "Upload"
    if (integration.id === 'csv_upload' || integration.id === 'xlsx_upload') {
      return "Upload";
    }
    
    if (projectDataSources.some(ds => ds.type === integration.id)) {
      return "Connected";
    }
    
    if (isIntegrationDisabled(integration)) {
      return "Unavailable";
    }
    
    return "Connect";
  };

  return (
    <div className="p-6 rounded-lg shadow-sm">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Available Data Sources
        </h2>
      </div>
      
      {/* Tabs for Categories */}
      <Tab.Group>
        <Tab.List className="flex space-x-2 rounded-xl bg-gray-50 dark:bg-gray-800 p-1.5 mb-8">
          {Object.entries(categoryConfig).map(([category, { name }]) => (
            <Tab
              key={category}
              className={({ selected }) =>
                `w-full rounded-lg py-3 text-sm font-medium leading-5 
                ${
                  selected
                    ? 'bg-white dark:bg-gray-600 text-lime-600 dark:text-lime-400'
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
            <Tab.Panel key={category} className="space-y-6">
              {groupedIntegrations[category]?.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Special handling for document and code categories */}
                  {(category === 'document' || category === 'code') && (
                    <FileUploadCard 
                      category={category as 'document' | 'code'} 
                      onUpload={() => {
                        // Find the generic file upload integration for this category
                        const uploadIntegration = integrations.find(
                          i => i.id === 'generic_file_upload' && i.category === category
                        );
                        if (uploadIntegration) {
                          onSelectIntegration(uploadIntegration);
                        }
                      }}
                    />
                  )}
                  
                  {/* Regular integrations */}
                  {groupedIntegrations[category]
                    .filter(integration => integration.id !== 'generic_file_upload') // Filter out generic file upload cards
                    .map((integration: IntegrationType) => {
                    const isConnected = projectDataSources.some(ds => ds.type === integration.id);
                    const isDisabled = isIntegrationDisabled(integration);
                    
                    return (
                      <div 
                        key={integration.id} 
                        className={`bg-gray-50 dark:bg-gray-800/40 rounded-lg border ${
                          isConnected 
                            ? 'border-green-200 dark:border-green-800' 
                            : isDisabled 
                              ? 'border-gray-100 dark:border-gray-700 opacity-60' 
                              : 'border-gray-100 dark:border-gray-700'
                        } p-5 relative hover:shadow-md transition-shadow duration-200`}
                      >
                        {/* Tooltip info - removed restriction message */}
                        
                        <div className="flex items-start">
                          <div className="flex-shrink-0 h-12 w-12 flex items-center justify-center rounded-full bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 shadow-sm">
                            <img
                              src={integration.id === 'generic_file_upload' && integration.category === 'code' 
                                ? '/icons/code_file_upload.svg' 
                                : `/icons/${integration.id}.svg`}
                              alt={getDisplayName(integration)}
                              className="h-7 w-7"
                              onError={(e) => {
                                (e.target as HTMLImageElement).src = "/icons/generic-integration.svg";
                              }}
                            />
                          </div>
                          <div className="ml-4 flex-1">
                            <h3 className="text-base font-medium text-gray-900 dark:text-white flex items-center">
                              {getDisplayName(integration)}
                              {isConnected && integration.id !== 'csv_upload' && integration.id !== 'excel_upload' && (
                                <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                                  Connected
                                </span>
                              )}
                              {isConnected && (integration.id === 'csv_upload' || integration.id === 'xlsx_upload') && (
                                <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                                  Available
                                </span>
                              )}
                            </h3>
                            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                              {integration.description || `Connect to your ${getDisplayName(integration)} data.`}
                            </p>
                          </div>
                        </div>
                        
                        {/* Menu for connected data sources (except CSV and Excel) */}
                        {isConnected && integration.id !== 'csv_upload' && integration.id !== 'excel_upload' && (
                          <div className="absolute top-3 right-3">
                            <Popover className="relative">
                              {({ open }) => (
                                <>
                                  <Popover.Button
                                    className="inline-flex items-center p-2 border border-transparent rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-lime-500"
                                  >
                                    <EllipsisVerticalIcon className="h-5 w-5" aria-hidden="true" />
                                  </Popover.Button>
                                  <Transition
                                    as={Fragment}
                                    enter="transition ease-out duration-200"
                                    enterFrom="opacity-0 translate-y-1"
                                    enterTo="opacity-100 translate-y-0"
                                    leave="transition ease-in duration-150"
                                    leaveFrom="opacity-100 translate-y-0"
                                    leaveTo="opacity-0 translate-y-1"
                                  >
                                    <Popover.Panel className="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-md bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                                      <div className="py-1">
                                        <button
                                          onClick={() => onSelectIntegration(integration)}
                                          className="flex w-full items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                                        >
                                          <PencilIcon className="h-4 w-4 mr-3 text-gray-500 dark:text-gray-400" aria-hidden="true" />
                                          Edit
                                        </button>
                                      </div>
                                    </Popover.Panel>
                                  </Transition>
                                </>
                              )}
                            </Popover>
                          </div>
                        )}
                        
                        {/* Connect/Upload button for available data sources */}
                        {/* For CSV and Excel, always show Upload button even when connected */}
                        {(!isConnected || integration.id === 'csv_upload' || integration.id === 'xlsx_upload') && (
                          <div className="mt-4 flex justify-end">
                            <button
                              onClick={() => onSelectIntegration(integration)}
                              disabled={isDisabled}
                              className={`inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500 ${
                                isDisabled
                                  ? 'bg-gray-300 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed'
                                  : 'text-white bg-purple-500 hover:bg-lime-700'
                              }`}
                            >
                              {(integration.id === 'csv_upload' || integration.id === 'xlsx_upload') ? 'Upload' : 'Connect'}
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-500 dark:text-gray-400">
                    No integrations available in this category.
                  </p>
                </div>
              )}
            </Tab.Panel>
          ))}
        </Tab.Panels>
      </Tab.Group>
    </div>
  );
}
