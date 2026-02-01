import { Fragment, useState } from "react";
import { Popover, Transition } from "@headlessui/react";
import {
  QuestionMarkCircleIcon,
  EllipsisVerticalIcon,
  PencilIcon
} from "@heroicons/react/24/outline";
import type { DataSourceCredential as BaseDataSourceCredential } from "~/services/chicory.server";

// Extend DataSourceCredential to include category
export interface DataSourceCredential extends BaseDataSourceCredential {
  category?: string;
}

// Define the integration type that extends DataSourceTypeDefinition
export interface IntegrationType {
  id: string;
  name: string;
  category?: string;
  required_fields: any[];
  connected?: boolean;
  configuredSources?: DataSourceCredential[];
  description?: string;
}

interface IntegrationCardProps {
  integration: IntegrationType;
  projectDataSources: DataSourceCredential[];
  projectId: string;
  isConnected: boolean;
  isDisabled: boolean;
  handleDataSourceClick: (integration: IntegrationType) => void;
}

export function IntegrationCard({
  integration,
  projectDataSources,
  projectId,
  isConnected,
  isDisabled,
  handleDataSourceClick
}: IntegrationCardProps) {
  const getDisplayName = (integration: IntegrationType) => {
    // Special case for generic file upload with code category
    if (integration.id === 'generic_file_upload' && integration.category === 'code') {
      return 'Code File Upload';
    }
    return integration.name;
  };

  const handleConnect = () => {
    // For all integrations, use the parent handler
    handleDataSourceClick(integration);
  };

  return (
    <div 
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
            {isConnected && (integration.id === 'csv_upload' || integration.id === 'excel_upload') && (
              <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                Upload
              </span>
            )}
          </h3>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            {integration.description || (
              integration.id === 'csv_upload' || integration.id === 'xlsx_upload' 
              ? `Upload your ${getDisplayName(integration)} data.` 
              : `Connect to your ${getDisplayName(integration)} data.`)}
          </p>
        </div>
      </div>
      
      {/* Menu for connected data sources (except CSV and Excel) */}
      {isConnected && integration.id !== 'csv_upload' && integration.id !== 'xlsx_upload' && (
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
                        onClick={() => handleDataSourceClick(integration)}
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
      {(!isConnected || integration.id === 'csv_upload' || integration.id === 'excel_upload') && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleConnect}
            disabled={isDisabled}
            className={`inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 ${
              isDisabled
                ? 'bg-gray-300 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed'
                : 'text-white bg-purple-500 hover:bg-purple-700'
            }`}
          >
            {integration.id.includes('upload') ? 'Upload' : 'Connect'}
          </button>
        </div>
      )}
    </div>
  );
}
