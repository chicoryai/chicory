/**
 * Deploy Route
 * Handles agent deployment configuration and management
 * Includes API deployment and MCP Gateway deployment options
 */

import { json, redirect } from "@remix-run/node";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import {
  useLoaderData,
  useSubmit,
  useActionData,
  useNavigation
} from "@remix-run/react";
import { getUserOrgDetails } from "~/auth/auth.server";
import { getMcpGateways } from "~/services/chicory.server";
import {
  handleDeployAgent,
  handleUndeployAgent,
  handleUpdateAgentStatus
} from "~/utils/agent/deployment";
import { handleToggleMcpTool } from "~/utils/agent/playground-actions";
import { useAgentContext } from "./_app.projects.$projectId.agents.$agentId";
import { useState, useCallback, useEffect, useMemo } from "react";
import GatewaySelector from "~/components/agents/GatewaySelector";
import { ToggleSwitch } from "~/components/ui/ToggleSwitch";
import {
  ServerIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  EyeSlashIcon,
  ClipboardDocumentIcon,
  CodeBracketIcon,
  ArrowPathIcon,
  PowerIcon
} from "@heroicons/react/24/outline";
type AgentGatewayDeployment = {
  gateway_id: string;
  tool_id?: string;
  name: string;
  enabled: boolean;
  description?: string;
};

type SampleEndpoint = "create" | "retrieve";
type SampleLanguage = "curl";

type SampleVariant = Record<SampleEndpoint, string>;
type SampleMap = Record<SampleLanguage, SampleVariant>;

const API_BASE_URL = "https://app.chicory.ai/api/v1";

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { agentId, projectId } = params;

  if (!agentId || !projectId) {
    throw new Response("Agent ID and Project ID are required", { status: 400 });
  }

  // Get user details for project validation
  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }

  const orgId = 'orgId' in userDetails ? (userDetails as any).orgId : undefined;
  if (!orgId) {
    return redirect("/new");
  }

  // Fetch deployment-specific data only (agent is loaded in parent)
  try {
    const gateways = await getMcpGateways(projectId);

    return json({
      gateways,
      projectId
    });
  } catch (error) {
    console.error("Error fetching deployment data:", error);
    if (error instanceof Response) {
      throw error;
    }
    throw new Response("Failed to load deployment data", { status: 500 });
  }
}

export async function action({ request, params }: ActionFunctionArgs) {
  const { agentId, projectId } = params;

  if (!agentId || !projectId) {
    throw new Response("Agent ID and Project ID are required", { status: 400 });
  }

  // Get user details to validate access
  const userDetails = await getUserOrgDetails(request);

  if (userDetails instanceof Response) {
    return userDetails;
  }

  // Parse form data
  const formData = await request.formData();
  const intent = formData.get("intent") as string;

  if (intent === "deploy") {
    return handleDeployAgent(projectId, agentId, formData, userDetails);
  } else if (intent === "undeploy") {
    return handleUndeployAgent(projectId, agentId, formData);
  } else if (intent === "toggle-mcp-tool") {
    return handleToggleMcpTool(projectId, agentId, formData);
  } else if (intent === "updateStatus") {
    return handleUpdateAgentStatus(projectId, agentId, formData);
  }

  return json({ success: false, error: "Unknown intent" }, { status: 400 });
}

export default function AgentDeployView() {
  const { gateways, projectId: loaderProjectId } = useLoaderData<typeof loader>();
  const { agent, projectId } = useAgentContext();
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();
  const submit = useSubmit();

  // Use projectId from loader (from params) for API endpoints
  const apiProjectId = loaderProjectId || projectId;
  const typedAgent = agent as unknown as { state?: string; status?: string };

  const initialMcpDeployments = useMemo<AgentGatewayDeployment[]>(() => {
    const rawMcpGateways = agent.metadata?.mcp_gateways;

    const entries: any[] = [];

    if (Array.isArray(rawMcpGateways)) {
      entries.push(...rawMcpGateways);
    } else if (rawMcpGateways && typeof rawMcpGateways === "object") {
      for (const [key, value] of Object.entries(rawMcpGateways)) {
        if (typeof value === "string") {
          entries.push({ gateway_id: value, tool_id: undefined });
        } else if (value && typeof value === "object") {
          entries.push({ gateway_id: (value as any).gateway_id ?? key, ...value });
        } else if (value === null) {
          entries.push({ gateway_id: key });
        }
      }
    } else if (typeof rawMcpGateways === "string") {
      entries.push({ gateway_id: rawMcpGateways });
    }

    const normalizeEnabled = (value: any) => {
      if (typeof value === "boolean") return value;
      if (typeof value === "number") return value === 1;
      if (typeof value === "string") {
        const lowered = value.toLowerCase();
        return lowered === "true" || lowered === "1";
      }
      return true;
    };

    return entries
      .map((entry) => {
        if (!entry) return null;

        if (typeof entry === "string") {
          const matchedGateway = gateways.find((gateway) => String(gateway.id) === entry);
          return {
            gateway_id: entry,
            tool_id: undefined,
            name: matchedGateway?.name || "Unknown Gateway",
            enabled: true,
            description: matchedGateway?.description
          } as AgentGatewayDeployment;
        }

        const gatewayId = entry.gateway_id ?? entry.id ?? entry.gatewayId;
        if (!gatewayId) {
          return null;
        }

        const gatewayIdString = String(gatewayId);
        const matchedGateway = gateways.find(
          (gateway) => String(gateway.id) === gatewayIdString
        );

        return {
          gateway_id: gatewayIdString,
          tool_id: entry.tool_id ?? entry.toolId,
          name:
            entry.name ||
            matchedGateway?.name ||
            (typeof entry === "object" && entry.gateway?.name) ||
            "Unknown Gateway",
          enabled: normalizeEnabled(entry.enabled),
          description:
            entry.description ||
            matchedGateway?.description ||
            (typeof entry === "object" && entry.gateway?.description)
        } as AgentGatewayDeployment;
      })
      .filter((candidate): candidate is AgentGatewayDeployment => Boolean(candidate?.gateway_id));
  }, [agent.metadata, gateways]);

  const [apiKey, setApiKey] = useState(agent.api_key || "");
  const [deploymentStatus, setDeploymentStatus] = useState<
    "idle" | "deploying" | "success" | "error"
  >(agent.api_key ? "success" : "idle");
  const [deploymentError, setDeploymentError] = useState<string | null>(null);
  const [showApiKey, setShowApiKey] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [mcpDeployments, setMcpDeployments] = useState<AgentGatewayDeployment[]>(
    initialMcpDeployments
  );
  const [selectedGatewayId, setSelectedGatewayId] = useState<string>("");
  const [isDeployingMcp, setIsDeployingMcp] = useState(false);
  const [mcpDeployError, setMcpDeployError] = useState<string | null>(null);
  const [pendingToggleTool, setPendingToggleTool] = useState<string | null>(null);
  const [pendingRemovalGateway, setPendingRemovalGateway] = useState<string | null>(null);
  const [agentStatus, setAgentStatus] = useState<string>(
    typedAgent.state || typedAgent.status || "disabled"
  );
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [activeSampleTab, setActiveSampleTab] = useState<SampleLanguage>("curl");

  useEffect(() => {
    setMcpDeployments(initialMcpDeployments);
  }, [initialMcpDeployments]);

  useEffect(() => {
    setApiKey(agent.api_key || "");
    setDeploymentStatus((prev) => {
      if (agent.api_key) {
        return "success";
      }
      return prev === "deploying" ? prev : "idle";
    });
    if (agent.api_key) {
      setDeploymentError(null);
    }
    const refreshedAgent = agent as unknown as { state?: string; status?: string };
    setAgentStatus(refreshedAgent.state || refreshedAgent.status || "disabled");
  }, [agent]);

  const overallDeployed = useMemo(
    () => Boolean(apiKey) || mcpDeployments.length > 0,
    [apiKey, mcpDeployments]
  );
  const activeGatewayCount = useMemo(
    () => mcpDeployments.filter((deployment) => deployment.enabled).length,
    [mcpDeployments]
  );
  const isApiConfigured = Boolean(apiKey);
  const isSubmitting = navigation.state === "submitting";

  const copyToClipboard = useCallback(
    (value: string, label: string) => {
      if (!value || typeof navigator === "undefined" || !navigator.clipboard) {
        return;
      }
      navigator.clipboard
        .writeText(value)
        .then(() => {
          setCopiedField(label);
          setTimeout(() => setCopiedField(null), 2000);
        })
        .catch(() => {
          setCopiedField(null);
        });
    },
    []
  );

  const handleApiDeploy = useCallback(() => {
    setDeploymentStatus("deploying");
    setDeploymentError(null);
    setPendingAction("deploy-api");
    const formData = new FormData();
    formData.append("intent", "deploy");
    formData.append("deploymentType", "api");
    submit(formData, { method: "post" });
  }, [submit]);

  const handleRegenerateApiKey = useCallback(() => {
    handleApiDeploy();
  }, [handleApiDeploy]);

  const handleUndeployApi = useCallback(() => {
    setPendingAction("undeploy-api");
    setDeploymentError(null);
    const formData = new FormData();
    formData.append("intent", "undeploy");
    formData.append("deploymentType", "api");
    submit(formData, { method: "post" });
  }, [submit]);

  const handleDeployToGateway = useCallback(() => {
    if (!selectedGatewayId) {
      setMcpDeployError("Please select a gateway to deploy to.");
      return;
    }
    setIsDeployingMcp(true);
    setMcpDeployError(null);
    setPendingAction("deploy-mcp");
    const formData = new FormData();
    formData.append("intent", "deploy");
    formData.append("deploymentType", "mcp-tool");
    formData.append("gatewayId", selectedGatewayId);
    submit(formData, { method: "post" });
  }, [selectedGatewayId, submit]);

  const handleToggleGateway = useCallback(
    (deployment: AgentGatewayDeployment, enabled: boolean) => {
      if (!deployment.tool_id) {
        setMcpDeployError(
          "Missing tool metadata for this gateway. Please redeploy the tool."
        );
        return;
      }
      setPendingToggleTool(deployment.tool_id);
      setPendingAction("toggle-mcp");
      const formData = new FormData();
      formData.append("intent", "toggle-mcp-tool");
      formData.append("toolId", deployment.tool_id);
      formData.append("gatewayId", deployment.gateway_id);
      formData.append("enabled", String(enabled));
      submit(formData, { method: "post" });
    },
    [submit]
  );

  const handleRemoveGateway = useCallback(
    (gatewayId: string) => {
      setPendingRemovalGateway(gatewayId);
      setPendingAction("undeploy-mcp");
      const formData = new FormData();
      formData.append("intent", "undeploy");
      formData.append("deploymentType", "mcp-tool");
      formData.append("gatewayId", gatewayId);
      submit(formData, { method: "post" });
    },
    [submit]
  );

  const handleToggleAgentStatus = useCallback(() => {
    const newState = agentStatus === "enabled" ? "disabled" : "enabled";
    setIsUpdatingStatus(true);
    setPendingAction("update-status");
    const formData = new FormData();
    formData.append("intent", "updateStatus");
    formData.append("state", newState);
    submit(formData, { method: "post" });
  }, [agentStatus, submit]);

  useEffect(() => {
    if (!actionData) return;
  const data = actionData as any;

  if (data.intent === "deploy") {
      if (data.success) {
        if (data.deploymentType === "api") {
          if (typeof data.apiKey === "string") {
            setApiKey(data.apiKey);
          }
          setDeploymentStatus("success");
          setDeploymentError(null);
        } else if (data.deploymentType === "mcp-tool") {
          setIsDeployingMcp(false);
          setMcpDeployError(null);
          const gatewayId = data.gatewayId as string | undefined;
          const toolId = data.toolId as string | undefined;
          if (gatewayId) {
            setMcpDeployments((prev) => {
              const gatewayIdString = String(gatewayId);
              const existing = prev.find((deployment) => deployment.gateway_id === gatewayIdString);
              const gateway = gateways.find((g) => String(g.id) === gatewayIdString);
              const base: AgentGatewayDeployment = {
                gateway_id: gatewayIdString,
                tool_id: toolId || existing?.tool_id,
                name: existing?.name || gateway?.name || "Unknown Gateway",
                enabled: true,
                description: existing?.description || gateway?.description
              };
              if (existing) {
                return prev.map((deployment) =>
                  deployment.gateway_id === gatewayIdString ? { ...deployment, ...base } : deployment
                );
              }
              return [...prev, base];
            });
          }
          setSelectedGatewayId("");
        }
      } else {
        if (data.deploymentType === "api") {
          setDeploymentStatus("error");
          setDeploymentError(data.error || "Failed to deploy agent.");
        } else {
          setIsDeployingMcp(false);
          setMcpDeployError(data.error || "Failed to deploy to gateway.");
        }
      }
      setPendingAction(null);
    } else if (data.intent === "undeploy") {
      if (data.success) {
        if (data.deploymentType === "api") {
          setApiKey("");
          setDeploymentStatus("idle");
          setDeploymentError(null);
        } else if (data.deploymentType === "mcp-tool") {
          if (pendingRemovalGateway) {
          setMcpDeployments((prev) =>
            prev.filter((deployment) => deployment.gateway_id !== String(pendingRemovalGateway))
          );
          }
        }
      } else {
        if (data.deploymentType === "api") {
          setDeploymentStatus("error");
          setDeploymentError(data.error || "Failed to disable API access.");
        } else {
          setMcpDeployError(data.error || "Failed to remove deployment.");
        }
      }
      setPendingRemovalGateway(null);
      setIsDeployingMcp(false);
      setPendingAction(null);
    } else if (data.intent === "toggle-mcp-tool") {
      if (data.success) {
        const toolId = data.toolId as string | undefined;
        if (toolId) {
          setMcpDeployments((prev) =>
            prev.map((deployment) =>
              deployment.tool_id === toolId
                ? { ...deployment, enabled: data.enabled }
                : deployment
            )
          );
        }
      } else {
        setMcpDeployError(data.error || "Failed to update tool state.");
      }
      setPendingToggleTool(null);
      setPendingAction(null);
    } else if (data.type === "state-updated") {
      if (data.success) {
        setAgentStatus(data.state as string);
      } else if (data.error) {
        setMcpDeployError(data.error);
      }
      setIsUpdatingStatus(false);
      setPendingAction(null);
    } else if (data.success === false && data.error) {
      setMcpDeployError(data.error);
      setPendingAction(null);
    }
  }, [actionData, gateways, pendingRemovalGateway]);

  const sampleKey = apiKey || "YOUR_API_KEY";
  const sampleTimestamp = new Date().toISOString();
  const runsEndpoint = `${API_BASE_URL}/projects/${apiProjectId}/runs`;
  const samples: SampleMap = {
    curl: {
      create: `curl -X POST ${runsEndpoint} \\
-H "Content-Type: application/json" \\
-H "Authorization: Bearer ${sampleKey}" \\
-d '{
  "agent_name": "${agent.id}",
  "input": [
    {
      "parts": [
        {
          "content_type": "text/plain",
          "content": "Your question or input here"
        }
      ],
      "created_at": "${sampleTimestamp}"
    }
  ]
}'`,
      retrieve: `curl -X GET ${runsEndpoint}/YOUR_RUN_ID \\
-H "Authorization: Bearer ${sampleKey}"`
    }
  };

  const hasApiKey = Boolean(apiKey);
  const apiKeyHelpText = hasApiKey
    ? "Store this key safely and rotate it if it is ever shared."
    : "Deploy API access to mint an auth token for this agent.";
  const isAgentEnabled = agentStatus === "enabled";
  const summaryStatusText = isAgentEnabled
    ? overallDeployed
      ? "Agent is live"
      : "Agent enabled"
    : "Agent disabled";

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto h-full max-w-6xl px-6 py-8">
        <div className="space-y-6">
          <div className="rounded-2xl border border-whitePurple-100/70 bg-transparent shadow-lg shadow-whitePurple-50/60 dark:border-whitePurple-200/30 dark:shadow-purple-900/30">
            <div className="flex flex-col gap-4 px-6 py-6 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-center gap-3">
                <div
                  className={`rounded-full p-2 ${
                    isAgentEnabled
                      ? "bg-emerald-200/80 dark:bg-emerald-500/20"
                      : "bg-gray-200/70 dark:bg-gray-800/60"
                  }`}
                >
                  <ServerIcon
                    className={`h-6 w-6 ${
                      isAgentEnabled
                        ? "text-emerald-700 dark:text-emerald-200"
                        : "text-gray-500 dark:text-gray-400"
                    }`}
                  />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    Deployment Summary
                  </p>
                  <p className="text-base font-semibold text-gray-900 dark:text-white">
                    {summaryStatusText}
                  </p>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <SummaryMetricCard
                  label="Agent status"
                  value={agentStatus === "enabled" ? "Enabled" : "Disabled"}
                  valueClassName={
                    agentStatus === "enabled"
                      ? "text-green-600 dark:text-green-300"
                      : "text-gray-500 dark:text-gray-400"
                  }
                />
                <SummaryMetricCard
                  label="API access"
                  value={isApiConfigured ? "Configured" : "Not configured"}
                  valueClassName={
                    isApiConfigured
                      ? "text-purple-600 dark:text-purple-300"
                      : "text-gray-500 dark:text-gray-400"
                  }
                />
                <SummaryMetricCard
                  label="Gateway deployments"
                  value={`${activeGatewayCount}/${mcpDeployments.length} active`}
                  valueClassName="text-gray-900 dark:text-gray-100"
                />
              </div>
              <div className="flex flex-col gap-2 text-sm">
                <button
                  type="button"
                  onClick={handleToggleAgentStatus}
                  disabled={isUpdatingStatus || isSubmitting || pendingAction === "update-status"}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-whitePurple-100/60 bg-transparent px-4 py-2 font-medium text-gray-800 shadow-sm hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-whitePurple-200/30 dark:bg-transparent dark:text-gray-200 dark:hover:bg-gray-800/60"
                >
                  <PowerIcon className="h-4 w-4" />
                  {agentStatus === "enabled" ? "Disable Agent" : "Enable Agent"}
                </button>
                {isUpdatingStatus && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">Updating status…</p>
                )}
              </div>
            </div>
          </div>

          {!overallDeployed && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-100">
              <div className="flex items-start gap-2">
                <ExclamationTriangleIcon className="mt-0.5 h-5 w-5" />
                <div>
                  <p className="font-medium">This agent is currently offline</p>
                  <p>Deploy the API or connect to a gateway to activate it.</p>
                </div>
              </div>
            </div>
          )}

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] lg:items-stretch">
            <div className="space-y-6">
            <div className="rounded-2xl border border-whitePurple-100/70 bg-transparent shadow-sm shadow-whitePurple-50/40 dark:border-whitePurple-200/25 dark:shadow-purple-900/30">
                <div className="border-b border-whitePurple-100/60 px-6 py-4 dark:border-whitePurple-200/25">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">API Access</h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Generate an API key and share this agent with your applications.
                  </p>
                </div>
                <div className="space-y-6 px-6 py-6">

                  {deploymentStatus === "deploying" && !apiKey ? (
                    <div className="flex items-center gap-2 rounded-lg border border-purple-200 bg-purple-50 px-4 py-3 text-sm text-purple-600 dark:border-purple-800 dark:bg-purple-900/20 dark:text-purple-200">
                      <ArrowPathIcon className="h-4 w-4 animate-spin" />
                      Configuring API access…
                    </div>
                  ) : null}

                  {deploymentStatus === "error" && deploymentError && (
                    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
                      {deploymentError}
                    </div>
                  )}

                  <div className="rounded-xl bg-transparent p-4 shadow-sm">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            API key
                          </span>
                          {hasApiKey && (
                            <div className="flex items-center gap-1.5">
                              <button
                                type="button"
                                onClick={() => copyToClipboard(apiKey, "apiKey")}
                                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-whitePurple-100/60 bg-transparent text-gray-600 hover:bg-gray-50 dark:border-whitePurple-200/30 dark:text-gray-300 dark:hover:bg-gray-800/60"
                              >
                                {copiedField === "apiKey" ? (
                                  <CheckCircleIcon className="h-4 w-4 text-green-500" />
                                ) : (
                                  <ClipboardDocumentIcon className="h-4 w-4" />
                                )}
                              </button>
                              <button
                                type="button"
                                onClick={() => setShowApiKey((value) => !value)}
                                className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-whitePurple-100/60 bg-transparent text-gray-600 hover:bg-gray-50 dark:border-whitePurple-200/30 dark:text-gray-300 dark:hover:bg-gray-800/60"
                              >
                                {showApiKey ? <EyeSlashIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
                              </button>
                            </div>
                          )}
                        </div>
                        <code className="mt-3 block w-full rounded-md border border-whitePurple-100/50 bg-transparent px-3 py-2 text-sm text-gray-900 break-all dark:border-whitePurple-200/30 dark:text-gray-100">
                          {apiKey ? (showApiKey ? apiKey : `••••${apiKey.slice(-4)}`) : "No API key generated"}
                        </code>
                        <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">{apiKeyHelpText}</p>
                      </div>
                      <div className="flex flex-col gap-2 lg:w-48">
                        {hasApiKey ? (
                          <>
                            <button
                              type="button"
                              onClick={handleRegenerateApiKey}
                              disabled={isSubmitting || pendingAction === "deploy-api"}
                              className="inline-flex items-center justify-center gap-2 rounded-md border border-purple-200 bg-purple-50 px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-purple-800 dark:bg-purple-900/20 dark:text-purple-200 dark:hover:bg-purple-900/40"
                            >
                              <ArrowPathIcon
                                className={`h-4 w-4 ${pendingAction === "deploy-api" ? "animate-spin" : ""}`}
                              />
                              Regenerate key
                            </button>
                            <button
                              type="button"
                              onClick={handleUndeployApi}
                              disabled={isSubmitting || pendingAction === "undeploy-api"}
                              className="inline-flex items-center justify-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300 dark:hover:bg-red-900/40"
                            >
                              Disable API access
                            </button>
                          </>
                        ) : (
                          <button
                            type="button"
                            onClick={handleApiDeploy}
                            disabled={isSubmitting || pendingAction === "deploy-api"}
                            className="inline-flex items-center justify-center gap-2 rounded-md bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {pendingAction === "deploy-api" ? (
                              <ArrowPathIcon className="h-4 w-4 animate-spin" />
                            ) : null}
                            Deploy API access
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="mt-4 border-t border-whitePurple-100/50 pt-4 dark:border-whitePurple-200/25">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            Runs endpoint
                          </span>
                          <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
                            Send POST requests here to create runs for this agent.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => copyToClipboard(runsEndpoint, "runsEndpoint")}
                          className="inline-flex items-center gap-1 text-xs font-medium text-purple-600 hover:text-purple-700 dark:text-purple-300 dark:hover:text-purple-200"
                        >
                          Copy
                          {copiedField === "runsEndpoint" ? (
                            <CheckCircleIcon className="h-3.5 w-3.5 text-green-500" />
                          ) : (
                            <ClipboardDocumentIcon className="h-3.5 w-3.5" />
                          )}
                        </button>
                      </div>
                      <code className="mt-3 block w-full truncate rounded-md border border-dashed border-whitePurple-100/50 bg-transparent px-3 py-2 text-xs text-gray-700 dark:border-whitePurple-200/25 dark:text-gray-300">
                        {runsEndpoint}
                      </code>
                    </div>
                  </div>

                  <div className="rounded-xl bg-transparent p-4 shadow-sm">
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white">
                        <CodeBracketIcon className="h-4 w-4 text-purple-500" />
                        Sample request
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 sm:text-right">
                        Test the deployment or share it with teammates using cURL.
                      </p>
                    </div>
                    <div className="mt-4">
                      <SampleCodeBlock
                        samples={samples}
                        activeTab={activeSampleTab}
                        onChangeTab={setActiveSampleTab}
                        onCopy={copyToClipboard}
                        copiedField={copiedField}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="self-start rounded-2xl border border-whitePurple-100/70 bg-transparent shadow-sm shadow-whitePurple-50/40 dark:border-whitePurple-200/30 dark:shadow-purple-900/30">
              <div className="border-b border-whitePurple-100/60 px-6 py-4 dark:border-whitePurple-200/25">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">MCP Gateways</h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Deploy this agent as a tool to your managed gateways.
                </p>
              </div>
              <div className="space-y-5 px-6 py-6">
                <GatewaySelector
                  projectId={projectId}
                  selectedGatewayId={selectedGatewayId}
                  onSelectGateway={setSelectedGatewayId}
                  gateways={gateways}
                  disabled={isDeployingMcp || isSubmitting}
                />
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
                  <button
                    type="button"
                    onClick={handleDeployToGateway}
                    disabled={!selectedGatewayId || isDeployingMcp || isSubmitting}
                    className="inline-flex items-center gap-2 rounded-md bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isDeployingMcp ? (
                      <ArrowPathIcon className="h-4 w-4 animate-spin" />
                    ) : (
                      <ServerIcon className="h-4 w-4" />
                    )}
                    {isDeployingMcp ? "Deploying…" : "Deploy to gateway"}
                  </button>
                  {mcpDeployError && (
                    <span className="text-sm text-red-500 dark:text-red-400">{mcpDeployError}</span>
                  )}
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm font-medium text-gray-600 dark:text-gray-300">
                    <span>Active deployments</span>
                    <span className="text-xs uppercase text-gray-400">{mcpDeployments.length}</span>
                  </div>
                  {mcpDeployments.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-whitePurple-100/60 bg-transparent px-4 py-6 text-center text-sm text-gray-500 dark:border-whitePurple-200/30 dark:text-gray-300">
                      No gateways configured yet.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="max-h-80 space-y-3 overflow-y-auto pr-1">
                        {mcpDeployments.map((deployment) => (
                          <div
                            key={deployment.gateway_id}
                            className="rounded-xl border border-whitePurple-100/60 bg-transparent p-4 shadow-sm shadow-whitePurple-50/30 dark:border-whitePurple-200/30 dark:shadow-purple-900/20"
                          >
                            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                              <div>
                                <p className="text-sm font-medium text-gray-900 dark:text-white">
                                  {deployment.name}
                                </p>
                                {deployment.description && (
                                  <p className="text-sm text-gray-600 dark:text-gray-400">
                                    {deployment.description}
                                  </p>
                                )}
                              </div>
                              <span
                                className={`inline-flex h-8 items-center rounded-full px-3 text-xs font-medium ${
                                  deployment.enabled
                                    ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                                    : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-300"
                                }`}
                              >
                                {deployment.enabled ? "Active" : "Disabled"}
                              </span>
                            </div>
                            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                              <div className="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                                <ToggleSwitch
                                  checked={deployment.enabled}
                                  onChange={(checked) => handleToggleGateway(deployment, checked)}
                                  disabled={
                                    !deployment.tool_id ||
                                    pendingToggleTool === deployment.tool_id ||
                                    isSubmitting
                                  }
                                  loading={pendingToggleTool === deployment.tool_id}
                                />
                                <span>Enable tool</span>
                                {pendingToggleTool === deployment.tool_id && (
                                  <ArrowPathIcon className="h-4 w-4 animate-spin text-purple-500" />
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

type SampleCodeBlockProps = {
  samples: SampleMap;
  activeTab: SampleLanguage;
  onChangeTab: (tab: SampleLanguage) => void;
  onCopy: (value: string, label: string) => void;
  copiedField: string | null;
};

function SampleCodeBlock({
  samples,
  activeTab,
  onChangeTab,
  onCopy,
  copiedField
}: SampleCodeBlockProps) {
  const tabs: Array<{ id: SampleLanguage; label: string }> = [
    { id: "curl", label: "cURL" }
  ];
  const endpointTabs: Array<{ id: SampleEndpoint; label: string }> = [
    { id: "create", label: "Create run" },
    { id: "retrieve", label: "Get run" }
  ];
  const [activeEndpoint, setActiveEndpoint] = useState<SampleEndpoint>("create");

  const baseCodeBlockClass =
    "whitespace-pre-wrap leading-relaxed rounded-xl border border-whitePurple-100/40 bg-transparent p-4 text-xs text-gray-800 shadow-inner overflow-x-auto dark:border-whitePurple-200/25 dark:text-gray-200";

  const handleCopy = () => {
    const label = `sample-${activeTab}-${activeEndpoint}`;
    onCopy(samples[activeTab][activeEndpoint], label);
  };

  return (
    <div className="space-y-3 text-xs text-gray-800 dark:text-gray-200">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => onChangeTab(tab.id)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-purple-600 text-white shadow-sm"
                  : "bg-transparent text-gray-600 ring-1 ring-inset ring-whitePurple-100/70 hover:bg-gray-50 dark:bg-transparent dark:text-gray-300 dark:ring-whitePurple-200/30 dark:hover:bg-gray-800/60"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1 text-xs font-medium text-purple-600 hover:text-purple-700 dark:text-purple-300 dark:hover:text-purple-200"
        >
          Copy
          {copiedField === `sample-${activeTab}-${activeEndpoint}` ? (
            <CheckCircleIcon className="h-3.5 w-3.5 text-green-500" />
          ) : (
            <ClipboardDocumentIcon className="h-3.5 w-3.5" />
          )}
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {endpointTabs.map((endpoint) => (
          <button
            key={endpoint.id}
            type="button"
            onClick={() => setActiveEndpoint(endpoint.id)}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              activeEndpoint === endpoint.id
                ? "bg-purple-100 text-purple-700 shadow-sm dark:bg-purple-900/50 dark:text-purple-200"
                : "bg-transparent text-gray-600 ring-1 ring-inset ring-whitePurple-100/70 hover:bg-gray-50 dark:bg-transparent dark:text-gray-300 dark:ring-whitePurple-200/30 dark:hover:bg-gray-800/60"
            }`}
          >
            {endpoint.label}
          </button>
        ))}
      </div>
      <pre className={baseCodeBlockClass}>
        {samples[activeTab][activeEndpoint]}
      </pre>
    </div>
  );
}

type SummaryMetricCardProps = {
  label: string;
  value: string;
  valueClassName?: string;
};

function SummaryMetricCard({ label, value, valueClassName }: SummaryMetricCardProps) {
  return (
    <div className="rounded-xl border border-whitePurple-100/60 bg-transparent p-3 text-sm shadow-sm shadow-whitePurple-50/30 dark:border-whitePurple-200/30 dark:shadow-purple-900/20">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {label}
      </p>
      <p className={`mt-1 text-base font-semibold ${valueClassName || "text-gray-900 dark:text-gray-100"}`}>
        {value}
      </p>
    </div>
  );
}
