import { Fragment, useMemo, useState } from "react";
import { Popover, Transition } from "@headlessui/react";
import { CubeTransparentIcon } from "@heroicons/react/24/outline";
import type { DataSourceCredential, DataSourceTypeDefinition } from "~/services/chicory.server";
import { resolveIntegrationIcon } from "~/utils/integrationIcons";

type IntegrationGroup = "documents" | "code" | "data" | "tools";

type ProjectIntegration = {
  id: string;
  name: string;
  typeId: string;
  typeName: string;
  description?: string | null;
  icon: string;
  group: IntegrationGroup;
};

type FilterOption = {
  id: string;
  label: string;
  count: number;
  disabled?: boolean;
};

interface ProjectIntegrationsPopoverProps {
  dataSources: DataSourceCredential[];
  dataSourceTypes: DataSourceTypeDefinition[];
}

const CATEGORY_LABELS: Record<IntegrationGroup, string> = {
  documents: "Documents",
  code: "Code",
  data: "Data",
  tools: "Tools"
};

const CATEGORY_PRIORITY: IntegrationGroup[] = ["documents", "code", "data", "tools"];

function getIntegrationGroup(category?: string): IntegrationGroup {
  const normalized = category?.toLowerCase();

  if (!normalized) {
    return "tools";
  }

  if (["document", "documents", "files", "cloud_storage"].includes(normalized)) {
    return "documents";
  }

  if (normalized === "code") {
    return "code";
  }

  if (["databases", "database", "analytics", "data", "warehouse"].includes(normalized)) {
    return "data";
  }

  return "tools";
}

export function ProjectIntegrationsPopover({ dataSources, dataSourceTypes }: ProjectIntegrationsPopoverProps) {
  const typeDefinitionsById = useMemo(() => {
    const map = new Map<string, DataSourceTypeDefinition>();
    dataSourceTypes.forEach(definition => {
      map.set(definition.id, definition);
    });
    return map;
  }, [dataSourceTypes]);

  const integrations = useMemo<ProjectIntegration[]>(() => {
    return dataSources.map(source => {
      const definition = typeDefinitionsById.get(source.type);
      const name = source.name || definition?.name || source.type;
      const group = getIntegrationGroup(definition?.category);

      return {
        id: source.id,
        name,
        typeId: source.type,
        typeName: definition?.name || source.type,
        description: definition?.description,
        icon: resolveIntegrationIcon(definition?.id, source.type, source.name),
        group
      } satisfies ProjectIntegration;
    });
  }, [dataSources, typeDefinitionsById]);

  const groupCounts = useMemo(() => {
    const counts: Record<IntegrationGroup, number> = {
      documents: 0,
      code: 0,
      data: 0,
      tools: 0
    };

    integrations.forEach(integration => {
      counts[integration.group] += 1;
    });

    return counts;
  }, [integrations]);

  const totalCount = integrations.length;

  const filters: FilterOption[] = useMemo(() => {
    const groupedFilters: FilterOption[] = CATEGORY_PRIORITY.map(group => ({
      id: group,
      label: CATEGORY_LABELS[group],
      count: groupCounts[group],
      disabled: groupCounts[group] === 0
    }));

    return [
      {
        id: "all",
        label: "All",
        count: totalCount,
        disabled: totalCount === 0
      },
      ...groupedFilters
    ];
  }, [groupCounts, totalCount]);

  const [activeFilter, setActiveFilter] = useState<string>("all");

  const filteredIntegrations = useMemo(() => {
    if (activeFilter === "all") {
      return integrations;
    }

    return integrations.filter(integration => integration.group === activeFilter);
  }, [integrations, activeFilter]);

  return (
    <Popover className="relative">
      <Popover.Button
        className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-2.5 py-1 text-sm font-medium text-gray-600 transition hover:border-purple-200 hover:text-purple-600 dark:border-gray-700 dark:text-gray-300 dark:hover:border-purple-700 dark:hover:text-purple-300"
        aria-label="View project integrations"
      >
        <CubeTransparentIcon className="h-4 w-4 text-gray-500 dark:text-gray-300" aria-hidden="true" />
        <span>Integrations</span>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-300">
          {totalCount}
        </span>
      </Popover.Button>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Popover.Panel className="absolute right-0 z-20 mt-2 w-[460px] rounded-xl border border-gray-200 bg-white p-4 shadow-lg focus:outline-none dark:border-gray-700 dark:bg-gray-800">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">Project integrations</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Connected data sources available to this agent.
              </p>
            </div>
            <span className="rounded-full bg-purple-100 px-2.5 py-1 text-xs font-medium text-purple-600 dark:bg-purple-900/40 dark:text-purple-200">
              {totalCount} connected
            </span>
          </div>

          <div className="mt-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Type</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {filters.map(filter => {
                const isActive = activeFilter === filter.id;
                return (
                  <button
                    key={filter.id}
                    type="button"
                    onClick={() => setActiveFilter(filter.id)}
                    disabled={filter.disabled}
                    className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-purple-300 disabled:cursor-not-allowed disabled:opacity-50 dark:focus:ring-purple-700 ${
                      isActive
                        ? "border-whitePurple-200/60 bg-whitePurple-50 text-purple-600 dark:border-whitePurple-200/40 dark:bg-purple-900/30 dark:text-purple-200"
                        : "border-slate-200 bg-white text-slate-600 hover:border-purple-200 hover:text-purple-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:text-purple-200"
                    }`}
                  >
                    <span className="truncate" title={filter.label}>{filter.label}</span>
                    <span className={`inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded-full px-1.5 text-[10px] ${
                      isActive
                        ? "bg-purple-500/20 text-purple-700 dark:bg-purple-500/20 dark:text-purple-200"
                        : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300"
                    }`}>
                      {filter.count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mt-4 max-h-96 overflow-y-auto">
            {filteredIntegrations.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-400">
                No integrations match the selected filter yet.
              </div>
            ) : (
              <div className="space-y-1.5">
                {filteredIntegrations.map(integration => (
                  <div
                    key={integration.id}
                    className="flex items-center gap-2.5 rounded-lg border border-gray-100 bg-white py-1.5 px-2.5 transition hover:border-purple-200 dark:border-gray-700 dark:bg-slate-900/95 dark:hover:border-purple-700"
                    title={integration.description || integration.name}
                  >
                    <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-slate-100 dark:bg-slate-800">
                      <img src={integration.icon} alt="Integration icon" className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1 flex items-center gap-2">
                      <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">
                        {CATEGORY_LABELS[integration.group]}
                      </span>
                      <span className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                        {integration.name}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Popover.Panel>
      </Transition>
    </Popover>
  );
}
