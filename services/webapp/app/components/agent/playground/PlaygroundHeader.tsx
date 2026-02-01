import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Popover, Transition } from "@headlessui/react";
import { useFetcher, useRevalidator } from "@remix-run/react";
import { WrenchScrewdriverIcon, TrashIcon, KeyIcon, EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import type { Agent, Tool, DataSourceCredential, DataSourceTypeDefinition, EnvVariable } from "~/services/chicory.server";
import { ProjectIntegrationsPopover } from "./ProjectIntegrationsPopover";

interface PlaygroundHeaderProps {
  agent: Agent;
  projectId: string;
  tools: Tool[];
  envVariables?: EnvVariable[];
  projectDataSources?: DataSourceCredential[];
  dataSourceTypes?: DataSourceTypeDefinition[];
  actionPath?: string;
  className?: string;
  onOpenToolModal?: (config: { name: string; availableTools: any[] }) => void;
  onAddMcpTool?: () => void;
  onAddEnvVariable?: () => void;
  children?: (slots: { left: ReactNode; right: ReactNode }) => ReactNode;
}

type RenameFetcherData = {
  success?: boolean;
  error?: string;
  name?: string;
};

type ToolFetcherData = {
  success?: boolean;
  error?: string;
  intent?: string;
};

function formatStatus(status: string | null | undefined) {
  if (status === "enabled") return "Deployed";
  if (status === "disabled") return "Stopped";
  return "Unknown";
}

function statusStyles(status: string | null | undefined) {
  switch (status) {
    case "enabled":
      return "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200";
    case "disabled":
      return "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-200";
    default:
      return "bg-gray-100 text-gray-700 dark:bg-gray-800/60 dark:text-gray-200";
  }
}

export function PlaygroundHeader({
  agent,
  projectId,
  tools,
  envVariables = [],
  projectDataSources = [],
  dataSourceTypes = [],
  actionPath = ".",
  className = "",
  onOpenToolModal,
  onAddMcpTool,
  onAddEnvVariable,
  children
}: PlaygroundHeaderProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draftName, setDraftName] = useState(agent.name);
  const fetcher = useFetcher<RenameFetcherData>();
  const toolFetcher = useFetcher<ToolFetcherData>();
  const envVarFetcher = useFetcher<ToolFetcherData>();
  const revalidator = useRevalidator();
  const handledSubmissionRef = useRef(false);
  const renameError = fetcher.data?.error;
  const isSubmitting = fetcher.state !== "idle";
  const [toolError, setToolError] = useState<string | null>(null);
  const [pendingConfirmationId, setPendingConfirmationId] = useState<string | null>(null);
  const [envVarError, setEnvVarError] = useState<string | null>(null);
  const [pendingEnvVarDeleteId, setPendingEnvVarDeleteId] = useState<string | null>(null);
  const [visibleEnvVarIds, setVisibleEnvVarIds] = useState<Set<string>>(new Set());
  
  useEffect(() => {
    if (fetcher.state !== "idle") {
      handledSubmissionRef.current = true;
      return;
    }

    if (handledSubmissionRef.current) {
      handledSubmissionRef.current = false;
      if (fetcher.data?.success) {
        setIsEditing(false);
        setDraftName(fetcher.data.name ?? agent.name);
        revalidator.revalidate();
      }
    }
  }, [fetcher.state, fetcher.data, agent.name, revalidator]);

  useEffect(() => {
    if (!isEditing) {
      setDraftName(agent.name);
    }
  }, [agent.name, isEditing]);

  useEffect(() => {
    if (toolFetcher.state !== "idle") {
      return;
    }

    if (!toolFetcher.data) {
      return;
    }

    if (toolFetcher.data.success && toolFetcher.data.intent === "deleteTool") {
      setToolError(null);
      setPendingConfirmationId(null);
      revalidator.revalidate();
    } else if (toolFetcher.data.error) {
      setToolError(toolFetcher.data.error);
    }
  }, [toolFetcher.state, toolFetcher.data, revalidator]);

  // Handle env variable deletion
  useEffect(() => {
    if (envVarFetcher.state !== "idle") {
      return;
    }

    if (!envVarFetcher.data) {
      return;
    }

    if (envVarFetcher.data.success && envVarFetcher.data.intent === "deleteEnvVariable") {
      setEnvVarError(null);
      setPendingEnvVarDeleteId(null);
      // Note: fetcher automatically triggers revalidation after successful action
    } else if (envVarFetcher.data.error) {
      setEnvVarError(envVarFetcher.data.error);
    }
  }, [envVarFetcher.state, envVarFetcher.data]);

  const pendingDeleteId = (toolFetcher.formData?.get("toolId") as string | undefined) ?? null;
  const pendingEnvVarDelete = (envVarFetcher.formData?.get("envVarId") as string | undefined) ?? null;

  const allTools = useMemo(
    () =>
      tools.map(tool => {
        const name = (tool as any).tool_name || tool.name;
        const provider = (tool as any).provider || (tool as any).tool_provider;
        return {
          ...tool,
          __displayName: typeof name === "string" ? name : "Unnamed Tool",
          __displayProvider: typeof provider === "string" ? provider : ""
        };
      }),
    [tools]
  );

  const hasAnyMcpTools = useMemo(
    () =>
      allTools.some(tool => {
        const label = (tool.__displayName || tool.name || "").toLowerCase();
        return label.includes("mcp");
      }),
    [allTools]
  );

  const formatToolLabel = (name?: string | null) => {
    if (!name) return "Unnamed Tool";
    return name
      .split(/[_\s]+/)
      .filter(Boolean)
      .map(part => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  };

  const editNameButton = (
    <button
      type="button"
      onClick={() => setIsEditing(true)}
      className="inline-flex h-7 w-7 items-center justify-center rounded-md text-gray-500 transition hover:border-purple-200 hover:text-purple-500 dark:border-gray-700 dark:text-gray-400 dark:hover:border-purple-700 dark:hover:text-purple-300"
      aria-label="Edit agent name"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
        <path d="M5.433 13.072l.198-.792 7.075-7.075 1.486 1.486-7.075 7.075-.792.198a.75.75 0 01-.892-.892z" />
        <path fillRule="evenodd" d="M16.862 4.487l-1.349-1.35a1.75 1.75 0 00-2.475 0l-.98.98 3.824 3.825.98-.98a1.75 1.75 0 000-2.475z" clipRule="evenodd" />
        <path d="M3.5 17a1.5 1.5 0 01-1.447-1.894l.516-2.064a.75.75 0 01.198-.356l8.4-8.4 3.824 3.825-8.4 8.4a.75.75 0 01-.356.198l-2.064.516A1.5 1.5 0 013.5 17z" />
      </svg>
    </button>
  );

  const nameHeading = (
    <h2 className="truncate text-base font-semibold text-gray-900 dark:text-white" title={agent.name}>
      {agent.name}
    </h2>
  );

  const nameForm = (
    <fetcher.Form
      method="post"
      action={actionPath}
      className="flex items-center gap-2"
      onSubmit={event => {
        if (!draftName.trim()) {
          event.preventDefault();
          return;
        }
      }}
    >
      <input type="hidden" name="intent" value="updateAgentName" />
      <input
        name="name"
        value={draftName}
        maxLength={50}
        onChange={event => setDraftName(event.target.value)}
        className="w-64 rounded-md bg-white px-2 py-1 text-sm text-gray-900 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
        aria-label="Agent name"
        autoFocus
      />
      <div className="flex items-center gap-1">
        <button
          type="submit"
          disabled={isSubmitting || !draftName.trim()}
          className="inline-flex items-center rounded-md bg-purple-600 px-2 py-1 text-sm font-medium text-white transition hover:bg-purple-500 disabled:opacity-50"
        >
          {isSubmitting ? "Saving…" : "Save"}
        </button>
        <button
          type="button"
          onClick={() => setIsEditing(false)}
          className="inline-flex items-center rounded-md border border-transparent px-2 py-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          Cancel
        </button>
      </div>
    </fetcher.Form>
  );

  const leftPrimaryRow = !isEditing
    ? (
        <>
          {nameHeading}
          {editNameButton}
        </>
      )
    : (
        <>
          {nameForm}
        </>
      );

  const leftContent = (
    <div className="flex min-w-0 flex-col gap-1">
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        {leftPrimaryRow}
      </div>
      {isEditing && renameError && (
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {renameError}
        </p>
      )}
    </div>
  );

  const rightContent = (
    <div className="flex items-center gap-3">
      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${statusStyles(agent.state)}`}>
        <span className="h-1.5 w-1.5 rounded-full bg-current" />
        {formatStatus(agent.state)}
      </span>

      <ProjectIntegrationsPopover
        dataSources={projectDataSources}
        dataSourceTypes={dataSourceTypes}
      />

      <Popover className="relative">
        {({ close }) => (
          <>
            <Popover.Button
              className="inline-flex items-center gap-2 rounded-md border border-gray-200 px-2.5 py-1 text-sm font-medium text-gray-600 transition hover:border-purple-200 hover:text-purple-600 dark:border-gray-700 dark:text-gray-300 dark:hover:border-purple-700 dark:hover:text-purple-300"
              aria-label="View MCP tools"
            >
              <span className="inline-flex items-center gap-1">
                <img
                  src="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/mcp.svg"
                  alt="MCP logo"
                  className="h-4 w-4 dark:invert"
                />
                <span className="whitespace-nowrap">MCP Tools</span>
              </span>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                {allTools.length}
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
              <Popover.Panel className="absolute right-0 z-20 mt-2 w-96 rounded-xl border border-gray-200 bg-white p-4 shadow-lg focus:outline-none dark:border-gray-700 dark:bg-gray-800">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
                    {hasAnyMcpTools ? "MCP Tools" : "Tools"}
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      onAddMcpTool?.();
                      close();
                    }}
                    className="flex h-6 w-6 items-center justify-center rounded-md border border-purple-200 text-purple-600 transition hover:bg-purple-50 dark:border-purple-800 dark:text-purple-300 dark:hover:bg-purple-900/30"
                    aria-label="Add MCP tool"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                      <path d="M10 3a.75.75 0 01.75.75V9.25H16a.75.75 0 010 1.5h-5.25V16a.75.75 0 01-1.5 0v-5.25H4a.75.75 0 010-1.5h5.25V3.75A.75.75 0 0110 3z" />
                    </svg>
                  </button>
                </div>
                {toolError && (
                  <p className="mt-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-900/40 dark:text-red-200">
                    {toolError}
                  </p>
                )}
                <div className="mt-2 space-y-2">
                  {allTools.length === 0 ? (
                    <p className="text-sm text-gray-500 dark:text-gray-400">No tools configured.</p>
                  ) : (
                    allTools.map(tool => {
                      const availableTools = Array.isArray((tool as any).configuration?.available_tools)
                        ? (tool as any).configuration?.available_tools
                        : Array.isArray((tool as any).config?.available_tools)
                          ? (tool as any).config?.available_tools
                          : [];
                      const rawToolName = tool.__displayName as string | undefined;
                      const normalizedName = (rawToolName || tool.name || "").toLowerCase();
                      const isMcpTool = normalizedName.includes("mcp");
                      const isDefaultTool = tool.name === "default_tools";
                      const isConfirmingDelete = pendingConfirmationId === tool.id;
                      return (
                        <div
                          key={tool.id}
                          className={`relative rounded-lg border border-gray-100 p-3 text-sm dark:border-gray-700 ${
                            isConfirmingDelete ? "bg-red-50 dark:bg-red-900/20" : ""
                          }`}
                        >
                          {!isDefaultTool && !isConfirmingDelete && (
                            <button
                              type="button"
                              onClick={() => {
                                setToolError(null);
                                setPendingConfirmationId(tool.id);
                              }}
                              className="absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center text-red-500 transition hover:text-red-600 dark:text-red-300 dark:hover:text-red-200"
                              aria-label={`Delete ${formatToolLabel(rawToolName)}`}
                            >
                              <TrashIcon className="h-5 w-5" />
                            </button>
                          )}
                          {isConfirmingDelete ? (
                            <div className="flex flex-col items-start gap-2 pr-6">
                              <p className="truncate text-sm font-semibold text-red-600 dark:text-red-200">
                                Delete {formatToolLabel(rawToolName)}?
                              </p>
                              <div className="flex items-center gap-2">
                                <button
                                  type="button"
                                  disabled={pendingDeleteId === tool.id}
                                  onClick={() => {
                                    setToolError(null);
                                    const formData = new FormData();
                                    formData.append("intent", "deleteTool");
                                    formData.append("toolId", tool.id);
                                    toolFetcher.submit(formData, {
                                      method: "post",
                                      action: actionPath
                                    });
                                    close();
                                  }}
                                  className="inline-flex items-center rounded-md bg-red-500 px-3 py-0.5 text-xs font-semibold text-white transition hover:bg-red-600 disabled:opacity-60 dark:bg-red-600 dark:hover:bg-red-500"
                                >
                                  {pendingDeleteId === tool.id ? "Deleting…" : "Delete"}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setPendingConfirmationId(null)}
                                  className="inline-flex items-center rounded-md border border-gray-200 px-3 py-0.5 text-xs font-medium text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800/60"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="flex items-start gap-3 pr-12">
                              <div className="flex min-w-0 items-start gap-2">
                                {isMcpTool ? (
                                  <img
                                    src="https://unpkg.com/@lobehub/icons-static-svg@latest/icons/mcp.svg"
                                    alt="MCP"
                                    className="mt-0.5 h-4 w-4 flex-shrink-0 dark:invert"
                                  />
                                ) : (
                                  <WrenchScrewdriverIcon className="mt-0.5 h-4 w-4 flex-shrink-0 text-gray-400 dark:text-gray-300" aria-hidden="true" />
                                )}
                                <div className="min-w-0">
                                  <p className="truncate font-semibold text-gray-800 dark:text-gray-100" title={rawToolName}>
                                    {formatToolLabel(rawToolName)}
                                  </p>
                                </div>
                              </div>
                              <div className="ml-auto flex flex-col items-end gap-1">
                                <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                                  <span>{availableTools.length} available</span>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      onOpenToolModal?.({
                                        name: formatToolLabel(rawToolName),
                                        availableTools
                                      });
                                      close();
                                    }}
                                    className="inline-flex items-center rounded-md border border-purple-200 px-2 py-0.5 text-xs font-medium text-purple-600 transition hover:bg-purple-50 dark:border-purple-800 dark:text-purple-300 dark:hover:bg-purple-900/20"
                                  >
                                    View
                                  </button>
                                </div>
                                {tool.enabled === false && (
                                  <span className="mt-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500 dark:bg-gray-700 dark:text-gray-300">
                                    Off
                                  </span>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              </Popover.Panel>
            </Transition>
          </>
        )}
      </Popover>

      {/* Environment Variables Popover */}
      <Popover className="relative">
        {({ close }) => (
          <>
            <Popover.Button
              className="inline-flex items-center gap-2 rounded-md border border-gray-200 px-2.5 py-1 text-sm font-medium text-gray-600 transition hover:border-purple-200 hover:text-purple-600 dark:border-gray-700 dark:text-gray-300 dark:hover:border-purple-700 dark:hover:text-purple-300"
              aria-label="View environment variables"
            >
              <span className="inline-flex items-center gap-1">
                <KeyIcon className="h-4 w-4" />
                <span className="whitespace-nowrap">Env Vars</span>
              </span>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                {envVariables.length}
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
              <Popover.Panel className="absolute right-0 z-20 mt-2 w-96 rounded-xl border border-gray-200 bg-white p-4 shadow-lg focus:outline-none dark:border-gray-700 dark:bg-gray-800">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
                    Environment Variables
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      onAddEnvVariable?.();
                      close();
                    }}
                    className="flex h-6 w-6 items-center justify-center rounded-md border border-purple-200 text-purple-600 transition hover:bg-purple-50 dark:border-purple-800 dark:text-purple-300 dark:hover:bg-purple-900/30"
                    aria-label="Add environment variable"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                      <path d="M10 3a.75.75 0 01.75.75V9.25H16a.75.75 0 010 1.5h-5.25V16a.75.75 0 01-1.5 0v-5.25H4a.75.75 0 010-1.5h5.25V3.75A.75.75 0 0110 3z" />
                    </svg>
                  </button>
                </div>
                {envVarError && (
                  <p className="mt-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-900/40 dark:text-red-200">
                    {envVarError}
                  </p>
                )}
                <div className="mt-2 space-y-2">
                  {envVariables.length === 0 ? (
                    <p className="text-sm text-gray-500 dark:text-gray-400">No environment variables configured.</p>
                  ) : (
                    envVariables.map(envVar => {
                      const isConfirmingDelete = pendingEnvVarDeleteId === envVar.id;
                      return (
                        <div
                          key={envVar.id}
                          className={`relative rounded-lg border border-gray-100 p-3 text-sm dark:border-gray-700 ${
                            isConfirmingDelete ? "bg-red-50 dark:bg-red-900/20" : ""
                          }`}
                        >
                          {!isConfirmingDelete && (
                            <button
                              type="button"
                              onClick={() => {
                                setEnvVarError(null);
                                setPendingEnvVarDeleteId(envVar.id);
                              }}
                              className="absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center text-red-500 transition hover:text-red-600 dark:text-red-300 dark:hover:text-red-200"
                              aria-label={`Delete ${envVar.key}`}
                            >
                              <TrashIcon className="h-5 w-5" />
                            </button>
                          )}
                          {isConfirmingDelete ? (
                            <div className="flex flex-col items-start gap-2 pr-6">
                              <p className="truncate text-sm font-semibold text-red-600 dark:text-red-200">
                                Delete {envVar.key}?
                              </p>
                              <div className="flex items-center gap-2">
                                <button
                                  type="button"
                                  disabled={pendingEnvVarDelete === envVar.id}
                                  onClick={() => {
                                    setEnvVarError(null);
                                    const formData = new FormData();
                                    formData.append("intent", "deleteEnvVariable");
                                    formData.append("envVarId", envVar.id);
                                    envVarFetcher.submit(formData, {
                                      method: "post",
                                      action: actionPath
                                    });
                                    close();
                                  }}
                                  className="inline-flex items-center rounded-md bg-red-500 px-3 py-0.5 text-xs font-semibold text-white transition hover:bg-red-600 disabled:opacity-60 dark:bg-red-600 dark:hover:bg-red-500"
                                >
                                  {pendingEnvVarDelete === envVar.id ? "Deleting…" : "Delete"}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setPendingEnvVarDeleteId(null)}
                                  className="inline-flex items-center rounded-md border border-gray-200 px-3 py-0.5 text-xs font-medium text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800/60"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="flex items-start gap-3 pr-12">
                              <KeyIcon className="mt-0.5 h-4 w-4 flex-shrink-0 text-purple-500 dark:text-purple-400" aria-hidden="true" />
                              <div className="min-w-0 flex-1">
                                <p className="truncate font-mono font-semibold text-gray-800 dark:text-gray-100" title={envVar.key}>
                                  {envVar.key}
                                </p>
                                <div className="mt-0.5 flex items-center gap-1">
                                  <p className="font-mono text-xs text-gray-500 dark:text-gray-400">
                                    {visibleEnvVarIds.has(envVar.id) ? envVar.value : "••••••••"}
                                  </p>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setVisibleEnvVarIds(prev => {
                                        const next = new Set(prev);
                                        if (next.has(envVar.id)) {
                                          next.delete(envVar.id);
                                        } else {
                                          next.add(envVar.id);
                                        }
                                        return next;
                                      });
                                    }}
                                    className="inline-flex h-5 w-5 items-center justify-center text-gray-400 transition hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
                                    aria-label={visibleEnvVarIds.has(envVar.id) ? "Hide value" : "Show value"}
                                  >
                                    {visibleEnvVarIds.has(envVar.id) ? (
                                      <EyeSlashIcon className="h-3.5 w-3.5" />
                                    ) : (
                                      <EyeIcon className="h-3.5 w-3.5" />
                                    )}
                                  </button>
                                </div>
                                {envVar.description && (
                                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 truncate" title={envVar.description}>
                                    {envVar.description}
                                  </p>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              </Popover.Panel>
            </Transition>
          </>
        )}
      </Popover>
    </div>
  );

  const content = children
    ? children({ left: leftContent, right: rightContent })
    : (
        <div className={`px-6 pb-3 ${className}`}>
          <div className="flex h-12 w-full items-center justify-between gap-4">
            {leftContent}
            {rightContent}
          </div>
        </div>
      );

  return content;
}
