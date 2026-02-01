import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { redirect } from "@remix-run/node";
import { useLoaderData, useFetcher, useNavigate } from "@remix-run/react";
import { getUserOrgDetails } from "~/auth/auth.server";
import { verifyProjectAccess } from "~/utils/rbac.server";
import {
  getMcpGateway,
  getMcpGatewayTools,
  updateMcpGateway,
  updateMcpGatewayTool,
  deleteMcpGateway,
  createMcpGatewayTool,
  deleteMcpGatewayTool,
  getAgents,
  type MCPGateway,
  type MCPTool,
  type Agent
} from "~/services/chicory.server";
import {
  ClipboardDocumentIcon,
  CheckIcon,
  TrashIcon,
  PlusIcon,
  PencilIcon
} from "@heroicons/react/24/outline";
import { useState, useEffect, useRef } from "react";
import { DeleteConfirmationModal, AddToolModal, EditToolModal, DeploymentLoader } from "~/components/mcp-gateway";


export async function loader({ request, params }: LoaderFunctionArgs) {
  const { gatewayId, projectId } = params;

  if (!gatewayId || !projectId) {
    throw new Response("Gateway ID and Project ID are required", { status: 400 });
  }

  // Verify user has access to this project
  await verifyProjectAccess(request, projectId);

  try {
    const gateway = await getMcpGateway(projectId, gatewayId);
    
    if (!gateway) {
      throw new Response("Gateway not found", { status: 404 });
    }
    
    // Fetch tools for this gateway
    const tools = await getMcpGatewayTools(projectId, gatewayId);
    
    // Fetch agents for the project
    const agents = await getAgents(projectId);
    
    return {
      gateway,
      projectId,
      tools,
      agents,
      chicoryApiUrl: process.env.CHICORY_API_URL || ''
    };
  } catch (error) {
    console.error("Error loading MCP gateway:", error);
    throw new Response("Gateway not found", { status: 404 });
  }
}

export async function action({ request, params }: ActionFunctionArgs) {
  console.log('[MCP Gateway Detail Action] Called');
  const { gatewayId, projectId } = params;
  
  if (!gatewayId || !projectId) {
    return { error: "Gateway ID and Project ID are required" };
  }
  
  const userDetails = await getUserOrgDetails(request);
  
  if (userDetails instanceof Response) {
    return userDetails;
  }
  const formData = await request.formData();
  const actionType = formData.get("_action") as string;
  
  console.log('[MCP Gateway Detail Action] Action type:', actionType);
  
  try {
    switch (actionType) {
      case "toggle-gateway": {
        const gatewayIdParam = formData.get("gatewayId") as string;
        const enabled = formData.get("enabled") === "true";
        
        console.log('[MCP Gateway Detail Action] Toggling gateway:', { gatewayIdParam, enabled });
        
        if (!gatewayIdParam) {
          return { error: "Gateway ID is required" };
        }
        
        await updateMcpGateway(projectId, gatewayIdParam, { enabled });
        
        return { success: true, message: `Gateway ${enabled ? 'enabled' : 'disabled'} successfully` };
      }
      
      case "toggle-tool": {
        const toolId = formData.get("toolId") as string;
        const enabled = formData.get("enabled") === "true";
        
        console.log('[MCP Gateway Detail Action] Toggling tool:', { toolId, enabled });
        
        if (!toolId) {
          return { error: "Tool ID is required" };
        }
        
        await updateMcpGatewayTool(projectId, gatewayId, toolId, { enabled });
        
        return { success: true, message: `Tool ${enabled ? 'enabled' : 'disabled'} successfully` };
      }
      
      case "update-tool": {
        const toolId = formData.get("toolId") as string;
        const updatesJson = formData.get("updates") as string;
        
        console.log('[MCP Gateway Detail Action] Updating tool:', { toolId, updatesJson });
        
        if (!toolId) {
          return { error: "Tool ID is required" };
        }
        
        let updates: any = {};
        try {
          updates = JSON.parse(updatesJson);
        } catch (e) {
          return { error: "Invalid update data" };
        }
        
        await updateMcpGatewayTool(projectId, gatewayId, toolId, updates);
        
        return { success: true, message: "Tool updated successfully" };
      }
      
      case "delete": {
        console.log('[MCP Gateway Detail Action] Deleting gateway:', gatewayId);
        
        await deleteMcpGateway(projectId, gatewayId);
        
        // Redirect to gateway list after successful deletion
        return redirect(`/projects/${projectId}/mcp-gateway`);
      }
      
      case "add-tool": {
        const agentId = formData.get("agentId") as string;
        
        console.log('[MCP Gateway Detail Action] Adding tool:', { agentId, gatewayId });
        
        if (!agentId) {
          return { error: "Agent ID is required" };
        }
        
        await createMcpGatewayTool(projectId, gatewayId, agentId);
        
        return { success: true, message: "Tool added successfully" };
      }
      
      case "delete-tool": {
        const toolId = formData.get("toolId") as string;
        
        console.log('[MCP Gateway Detail Action] Deleting tool:', { toolId, gatewayId });
        
        if (!toolId) {
          return { error: "Tool ID is required" };
        }
        
        await deleteMcpGatewayTool(projectId, gatewayId, toolId);
        
        return { success: true, message: "Tool deleted successfully" };
      }
      
      default:
        return { error: "Invalid action" };
    }
  } catch (error) {
    console.error("[MCP Gateway Detail Action] Error:", error);
    return { error: error instanceof Error ? error.message : "An error occurred" };
  }
}

// Tool Card Component with SSE deployment monitoring
function ToolCard({ 
  tool, 
  projectId, 
  gatewayId, 
  agentName, 
  onEdit, 
  onDelete,
  onNavigateToAgent 
}: {
  tool: MCPTool;
  projectId: string;
  gatewayId: string;
  agentName: string;
  onEdit: () => void;
  onDelete: (e: React.MouseEvent) => void;
  onNavigateToAgent: () => void;
}) {
  const [currentTool, setCurrentTool] = useState(tool);
  const [isDeploying, setIsDeploying] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const fetcher = useFetcher();
  
  // Check if tool needs deployment (has "No description available")
  useEffect(() => {
    const needsDeployment = !currentTool.description || 
                           currentTool.description === "No description available" ||
                           currentTool.description.trim() === "";
    
    if (needsDeployment) {
      setIsDeploying(true);
      
      // Connect to SSE endpoint
      const eventSource = new EventSource(
        `/api/mcp-tool/${projectId}/${gatewayId}/${currentTool.id}/stream`
      );
      
      eventSourceRef.current = eventSource;
      
      eventSource.addEventListener('tool-update', (event) => {
        try {
          const toolData = JSON.parse(event.data);
          console.log('[ToolCard] Tool update received:', toolData);
          setCurrentTool(toolData);
        } catch (error) {
          console.error('[ToolCard] Error parsing tool update:', error);
        }
      });
      
      eventSource.addEventListener('complete', (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('[ToolCard] Deployment complete:', data);
          if (data.tool) {
            setCurrentTool(data.tool);
          }
          setIsDeploying(false);
          eventSource.close();
        } catch (error) {
          console.error('[ToolCard] Error parsing complete event:', error);
        }
      });
      
      eventSource.addEventListener('error', (event) => {
        console.error('[ToolCard] SSE error:', event);
        // Don't close on error, let it retry
      });
      
      eventSource.addEventListener('timeout', (event) => {
        console.log('[ToolCard] Deployment timeout:', event);
        setIsDeploying(false);
        eventSource.close();
      });
      
      eventSource.onerror = () => {
        console.error('[ToolCard] EventSource error');
        // Browser will automatically reconnect
      };
      
      return () => {
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      };
    }
  }, [currentTool.id, projectId, gatewayId]);
  
  // Update tool when prop changes
  useEffect(() => {
    setCurrentTool(tool);
  }, [tool]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);
  
  if (isDeploying) {
    return (
      <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 flex flex-col min-h-[250px]">
        <DeploymentLoader toolName={currentTool.tool_name} />
      </div>
    );
  }
  
  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 flex flex-col">
      {/* Tool Header with Status */}
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-medium text-sm flex-1">{currentTool.tool_name}</h3>
        <span className={`px-2 py-1 text-xs rounded-full ml-2 ${
          currentTool.enabled 
            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
            : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
        }`}>
          {currentTool.enabled ? 'Enabled' : 'Disabled'}
        </span>
      </div>
      
      {/* Description */}
      <p className="text-xs text-gray-600 dark:text-gray-400 mb-3 flex-1 line-clamp-3">
        {currentTool.description || 'No description available'}
      </p>
      
      {/* Agent Info */}
      <div className="text-xs text-gray-500 dark:text-gray-500 mb-3">
        <div>Agent: {agentName}</div>
        {currentTool.output_format && (
          <div>Output: {currentTool.output_format}</div>
        )}
      </div>
      
      {/* Actions */}
      <div className="flex items-center justify-between border-t border-gray-200 dark:border-gray-700 pt-3">
        {/* Toggle Switch */}
        <fetcher.Form method="post" className="flex items-center">
          <input type="hidden" name="_action" value="toggle-tool" />
          <input type="hidden" name="toolId" value={currentTool.id} />
          <input type="hidden" name="enabled" value={(!currentTool.enabled).toString()} />
          <button
            type="submit"
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              currentTool.enabled 
                ? 'bg-indigo-600' 
                : 'bg-gray-200 dark:bg-gray-700'
            }`}
            title={currentTool.enabled ? 'Disable tool' : 'Enable tool'}
          >
            <span className="sr-only">{currentTool.enabled ? 'Disable' : 'Enable'} tool</span>
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                currentTool.enabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </fetcher.Form>
        
        {/* Action Buttons */}
        <div className="flex items-center space-x-1">
          {/* Navigate to Agent */}
          <button
            onClick={onNavigateToAgent}
            className="p-1.5 text-indigo-600 hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
            title="View Agent"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
          
          {/* Edit */}
          <button
            onClick={onEdit}
            className="p-1.5 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Edit Tool"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
          
          {/* Delete */}
          <fetcher.Form method="post" className="inline">
            <input type="hidden" name="_action" value="delete-tool" />
            <input type="hidden" name="toolId" value={currentTool.id} />
            <button
              type="submit"
              className="p-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
              title="Delete Tool"
              onClick={onDelete}
            >
              <TrashIcon className="h-4 w-4" />
            </button>
          </fetcher.Form>
        </div>
      </div>
    </div>
  );
}

export default function McpGatewayDetailPage() {

  const { gateway, tools, projectId, agents, chicoryApiUrl } = useLoaderData<typeof loader>();
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showAddToolModal, setShowAddToolModal] = useState(false);
  const [editingTool, setEditingTool] = useState<MCPTool | null>(null);
  const fetcher = useFetcher();
  const navigate = useNavigate();

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };
  
  
  const agentName = (agentId: string) => {
    const agent = agents.find(agent => agent.id === agentId);
    return agent ? agent.name : 'Unknown Agent';
  };

  const obscureApiKey = (key: string) => {
    if (!key || key.length <= 12) return key;
    return `${key.slice(0, 8)}...${key.slice(-4)}`;
  };
  
  const getMcpEndpointUrl = () => {
    // Use CHICORY_API_URL from environment or fallback to current origin
    const baseUrl = 'https://app.chicory.ai';
    return `${baseUrl}/mcp/${projectId}/${gateway.id}`;
  };
  
  return (
    <div className="p-6">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-4 mb-2">
              <h1 className="text-2xl font-bold">{gateway.name}</h1>

              {/* Gateway Enable/Disable Toggle */}
              <fetcher.Form method="post" className="flex items-center">
                <input type="hidden" name="_action" value="toggle-gateway" />
                <input type="hidden" name="gatewayId" value={gateway.id} />
                <input type="hidden" name="enabled" value={(!gateway.enabled).toString()} />
                <button
                  type="submit"
                  className={`relative inline-flex h-7 w-14 items-center rounded-full transition-colors ${
                    gateway.enabled
                      ? 'bg-indigo-600 hover:bg-indigo-700'
                      : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600'
                  }`}
                  title={gateway.enabled ? 'Disable gateway' : 'Enable gateway'}
                >
                  <span className="sr-only">{gateway.enabled ? 'Disable' : 'Enable'} gateway</span>
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-lg transition-transform ${
                      gateway.enabled ? 'translate-x-7' : 'translate-x-1'
                    }`}
                  />
                </button>
              </fetcher.Form>
            </div>
            
            {gateway.description && (
              <p className="text-gray-600 dark:text-gray-400">{gateway.description}</p>
            )}
          </div>
          
          <span className={`px-3 py-1 text-sm rounded-full ml-4 ${
            gateway.enabled 
              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
              : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
          }`}>
            {gateway.enabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>
      </div>
      
      {/* Gateway Details */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Gateway Details</h2>
        <div className="space-y-4">
          {/* Gateway ID */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Gateway ID
            </label>
            <div className="flex items-center space-x-2">
              <code className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-900 rounded-lg text-sm font-mono break-all">
                {gateway.id}
              </code>
              <button
                onClick={() => copyToClipboard(gateway.id, 'id')}
                className="p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title="Copy Gateway ID"
              >
                {copiedField === 'id' ? (
                  <CheckIcon className="h-4 w-4 text-green-600" />
                ) : (
                  <ClipboardDocumentIcon className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
          
          {/* API Key */}
          {gateway.api_key && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                API Key
              </label>
              <div className="flex items-center space-x-2">
                <code className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-900 rounded-lg text-sm font-mono">
                  {obscureApiKey(gateway.api_key)}
                </code>
                <button
                  onClick={() => copyToClipboard(gateway.api_key || '', 'api_key')}
                  className="p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="Copy Full API Key"
                >
                  {copiedField === 'api_key' ? (
                    <CheckIcon className="h-4 w-4 text-green-600" />
                  ) : (
                    <ClipboardDocumentIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          )}
          
          {/* Timestamps */}
          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Created
              </label>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {gateway.created_at ? new Date(gateway.created_at).toLocaleString() : 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Example Usage */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Example Usage</h2>
        <div className="space-y-4">
          {/* MCP Endpoint URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              MCP Endpoint URL
            </label>
            <div className="flex items-center space-x-2">
              <code className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-900 rounded-lg text-sm font-mono break-all">
                {getMcpEndpointUrl()}
              </code>
              <button
                onClick={() => copyToClipboard(getMcpEndpointUrl(), 'endpoint')}
                className="p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 rounded-lg transition-colors"
                title="Copy Endpoint URL"
              >
                {copiedField === 'endpoint' ? (
                  <CheckIcon className="h-4 w-4 text-green-600" />
                ) : (
                  <ClipboardDocumentIcon className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
          
          {/* API Key */}
          {gateway.api_key && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                API Key
              </label>
              <div className="flex items-center space-x-2">
                <code className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-900 rounded-lg text-sm font-mono">
                  {obscureApiKey(gateway.api_key)}
                </code>
                <button
                  onClick={() => copyToClipboard(gateway.api_key || '', 'example_api_key')}
                  className="p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="Copy API Key"
                >
                  {copiedField === 'example_api_key' ? (
                    <CheckIcon className="h-4 w-4 text-green-600" />
                  ) : (
                    <ClipboardDocumentIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Tools Management */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Available Tools</h2>
        </div>
        {tools && tools.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {tools.map((tool) => (
              <ToolCard
                key={tool.id}
                tool={tool}
                projectId={projectId}
                gatewayId={gateway.id}
                agentName={agentName(tool.agent_id)}
                onEdit={() => setEditingTool(tool)}
                onDelete={(e) => {
                  if (!confirm(`Are you sure you want to delete the tool "${tool.tool_name}"?`)) {
                    e.preventDefault();
                  }
                }}
                onNavigateToAgent={() => navigate(`/projects/${projectId}/agents/${tool.agent_id}`)}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-600 dark:text-gray-400">
            No tools available for this gateway.
          </p>
        )}
      </div>
      
      {/* Danger Zone - Delete Gateway */}
      <div className="bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-200 dark:border-red-800 p-6">
        <h3 className="text-sm font-semibold text-red-900 dark:text-red-100 mb-2">
          Danger Zone
        </h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-red-800 dark:text-red-200">
              Delete this gateway permanently. This action cannot be undone.
            </p>
          </div>
          <button
            onClick={() => setShowDeleteModal(true)}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center"
          >
            <TrashIcon className="h-4 w-4 mr-2" />
            Delete Gateway
          </button>
        </div>
      </div>
      
      {/* Delete Confirmation Modal */}
      <DeleteConfirmationModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        gateway={gateway}
      />
      
      {/* Add Tool Modal */}
      <AddToolModal
        isOpen={showAddToolModal}
        onClose={() => setShowAddToolModal(false)}
        agents={agents}
        gatewayId={gateway.id}
      />
      
      {/* Edit Tool Modal */}
      <EditToolModal
        isOpen={!!editingTool}
        onClose={() => setEditingTool(null)}
        tool={editingTool}
        gatewayId={gateway.id}
      />
    </div>
  );
}
