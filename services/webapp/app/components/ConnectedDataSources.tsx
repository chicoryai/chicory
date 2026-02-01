import { Fragment } from "react";
import { Popover, Transition } from "@headlessui/react";
import { 
  EllipsisVerticalIcon,
  PencilIcon,
  TrashIcon
} from '@heroicons/react/24/outline';
import type { DataSourceCredential, DataSourceTypeDefinition } from "~/services/chicory.server";

interface ConnectedDataSourcesProps {
  projectDataSources: DataSourceCredential[];
  onEditDataSource: (dataSource: DataSourceTypeDefinition) => void;
  onDeleteDataSource: (dataSource: DataSourceCredential) => void;
  integrations: any[]; // Using any here, but should match your IntegrationType
  formatDate: (dateString: string) => string;
}

export default function ConnectedDataSources({
  projectDataSources,
  onEditDataSource,
  onDeleteDataSource,
  integrations,
  formatDate
}: ConnectedDataSourcesProps) {
  return (
    <div className="p-6 rounded-lg shadow-sm">
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
        Connected Data Sources
      </h2>
      
      {projectDataSources.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {projectDataSources.map((dataSource: DataSourceCredential) => (
            <div 
              key={dataSource.id} 
              className="bg-gray-50 dark:bg-gray-800/40 rounded-lg p-5 border border-gray-100 dark:border-gray-700 hover:shadow-md transition-shadow duration-200 relative"
            >
              {/* Menu in top right */}
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
                              onClick={() => {
                                // Find the data source type definition
                                const dataSourceType = integrations.find(i => i.id === dataSource.type);
                                if (dataSourceType) {
                                  onEditDataSource(dataSourceType);
                                }
                              }}
                              className="flex w-full items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                            >
                              <PencilIcon className="h-4 w-4 mr-3 text-gray-500 dark:text-gray-400" aria-hidden="true" />
                              Edit
                            </button>
                            <button
                              onClick={() => onDeleteDataSource(dataSource)}
                              className="flex w-full items-center px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                            >
                              <TrashIcon className="h-4 w-4 mr-3 text-red-500 dark:text-red-400" aria-hidden="true" />
                              Delete
                            </button>
                          </div>
                        </Popover.Panel>
                      </Transition>
                    </>
                  )}
                </Popover>
              </div>
              
              <div className="flex items-start">
                <div className="flex-shrink-0 h-12 w-12 flex items-center justify-center rounded-full bg-gradient-to-br from-blue-100 to-blue-50 dark:from-blue-900 dark:to-blue-800 shadow-sm">
                  <img
                    src={`/icons/${dataSource.type}.svg`}
                    alt={dataSource.type}
                    className="h-7 w-7"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = "/icons/generic-integration.svg";
                    }}
                  />
                </div>
                <div className="ml-4">
                  <h3 className="text-base font-medium text-gray-900 dark:text-white">
                    {dataSource.name}
                  </h3>
                  <div className="mt-1 flex items-center text-xs text-gray-500 dark:text-gray-400">
                    <span className="truncate">Added on {formatDate(dataSource.created_at)}</span>
                  </div>
                  <span className="mt-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                    Active
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-md p-8 text-center">
          <p className="text-gray-500 dark:text-gray-400">
            No data sources connected yet. Add a data source from the options below.
          </p>
        </div>
      )}
    </div>
  );
}
