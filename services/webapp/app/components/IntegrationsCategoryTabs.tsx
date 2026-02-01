import { Fragment } from "react";
import { Tab } from "@headlessui/react";
import type { DataSourceCredential } from "~/services/chicory.server";
import { IntegrationCard, type IntegrationType } from "~/components/IntegrationCard";

interface CategoryConfig {
  [key: string]: {
    name: string;
    icon: JSX.Element;
  };
}

interface IntegrationsCategoryTabsProps {
  categoryConfig: CategoryConfig;
  groupedIntegrations: Record<string, IntegrationType[]>;
  projectDataSources: DataSourceCredential[];
  projectId: string;
  isIntegrationDisabled: (integration: IntegrationType) => boolean;
  handleDataSourceClick: (integration: IntegrationType) => void;
}

export function IntegrationsCategoryTabs({
  categoryConfig,
  groupedIntegrations,
  projectDataSources,
  projectId,
  isIntegrationDisabled,
  handleDataSourceClick
}: IntegrationsCategoryTabsProps) {
  return (
    <Tab.Group>
      <Tab.List className="flex space-x-2 rounded-xl bg-gray-50 dark:bg-gray-800 p-1.5 mb-8">
        {Object.entries(categoryConfig).map(([category, { name }]) => (
          <Tab
            key={category}
            className={({ selected }) =>
              `w-full rounded-lg py-3 text-sm font-medium leading-5 \
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
        {Object.entries(categoryConfig).map(([category, { name }]) => (
          <Tab.Panel key={category} className="space-y-6">
            {groupedIntegrations[category]?.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {groupedIntegrations[category].map((integration: IntegrationType) => {
                  const isConnected = projectDataSources.some(ds => ds.type === integration.id);
                  const isDisabled = isIntegrationDisabled(integration);
                  return (
                    <IntegrationCard
                      key={`${integration.id}-${integration.category}`}
                      integration={integration}
                      projectDataSources={projectDataSources}
                      projectId={projectId}
                      isConnected={isConnected}
                      isDisabled={isDisabled}
                      handleDataSourceClick={handleDataSourceClick}
                    />
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-12">
                <p className="text-gray-500 dark:text-gray-400">
                  No {name.toLowerCase()} available.
                </p>
              </div>
            )}
          </Tab.Panel>
        ))}
      </Tab.Panels>
    </Tab.Group>
  );
}
