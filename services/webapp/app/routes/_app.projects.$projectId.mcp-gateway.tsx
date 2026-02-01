import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { json, redirect } from "@remix-run/node";
import { Outlet, useLoaderData, useFetcher, useParams, useNavigate } from "@remix-run/react";
import { useState, useEffect } from "react";
import { getUserOrgDetails } from "~/auth/auth.server";
import { createApiKey } from "~/utils/propelauth.server";
import { verifyProjectAccess } from "~/utils/rbac.server";
import {
  getMcpGateways,
  createMcpGateway,
  updateMcpGateway,
  deleteMcpGateway,
  type MCPGateway
} from "~/services/chicory.server";
import { PlusIcon } from "@heroicons/react/24/outline";
import {
  GatewayModal,
  AlertBanner
} from "~/components/mcp-gateway";

interface LoaderData {
  projectId: string;
  gateways: MCPGateway[];
}

interface ActionData {
  success?: boolean;
  error?: string;
  message?: string;
  gateway?: MCPGateway;
  _action?: string;
}

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { projectId } = params;

  if (!projectId) {
    throw new Response("Project ID is required", { status: 400 });
  }

  // Verify user has access to this project
  await verifyProjectAccess(request, projectId);

  try {
    const gateways = await getMcpGateways(projectId);
    
    return json<LoaderData>({
      projectId,
      gateways
    });
  } catch (error) {
    console.error("Error loading MCP gateways:", error);
    return json<LoaderData>({
      projectId,
      gateways: []
    });
  }
}

export async function action({ request, params }: ActionFunctionArgs) {
  try {
    const userDetails = await getUserOrgDetails(request);
  
    if (userDetails instanceof Response) {
      return userDetails;
    }

    const { projectId } = params;

    if (!projectId) {
      return redirect("/new");
    }
    const formData = await request.formData();
    const actionType = formData.get("_action") as string;
    
    try {
      switch (actionType) {
        case "create": {
          const name = formData.get("name") as string;
          const description = formData.get("description") as string;
          
          if (!name) {
            return json<ActionData>({ 
              error: "Gateway name is required",
              _action: actionType
            }, { status: 400 });
          }
          
          // Step 1: Create the gateway
          const gateway = await createMcpGateway(projectId, {
            name,
            description: description || undefined,
          });
          
          // Step 2: Generate API key for the gateway
          // Get orgId from userDetails
          const orgId = userDetails.orgId;
          if (!orgId) {
            throw new Error("Organization ID is required for creating API key");
          }
          
          const { apiKeyToken } = await createApiKey(
            orgId,
            gateway.id,
            'gateway'  // Specify this is for a gateway
          );
          
          // Step 3: Update the gateway with the API key
          const updatedGateway = await updateMcpGateway(
            projectId,
            gateway.id,
            { api_key: apiKeyToken }
          );
          
          return json<ActionData>({
            success: true,
            message: "Gateway created successfully with API key",
            gateway: updatedGateway,
            _action: actionType
          });
        }
        
        case "update": {
          const gatewayId = formData.get("gatewayId") as string;
          const name = formData.get("name") as string;
          const description = formData.get("description") as string;
          const api_key = formData.get("api_key") as string;
          const enabled = formData.get("enabled") === "true";
          
          if (!gatewayId) {
            return json<ActionData>({ 
              error: "Gateway ID is required",
              _action: actionType
            }, { status: 400 });
          }
          
          const gateway = await updateMcpGateway(projectId, gatewayId, {
            name: name || undefined,
            description: description || undefined,
            api_key: api_key || undefined,
            enabled
          });
          
          return json<ActionData>({
            success: true,
            message: "Gateway updated successfully",
            gateway,
            _action: actionType
          });
        }
        
        case "delete": {
          const gatewayId = formData.get("gatewayId") as string;
          
          if (!gatewayId) {
            return json<ActionData>({ 
              error: "Gateway ID is required",
              _action: actionType
            }, { status: 400 });
          }
          
          await deleteMcpGateway(projectId, gatewayId);
          
          return json<ActionData>({
            success: true,
            message: "Gateway deleted successfully",
            _action: actionType
          });
        }
        
        case "toggle": {
          const gatewayId = formData.get("gatewayId") as string;
          const enabled = formData.get("enabled") === "true";
          
          if (!gatewayId) {
            return json<ActionData>({ 
              error: "Gateway ID is required",
              _action: actionType
            }, { status: 400 });
          }
          
          const gateway = await updateMcpGateway(projectId, gatewayId, {
            enabled
          });
          
          return json<ActionData>({
            success: true,
            message: enabled ? "Gateway enabled" : "Gateway disabled",
            gateway,
            _action: actionType
          });
        }
        
        default:
          return json<ActionData>({ 
            error: "Invalid action",
            _action: actionType
          }, { status: 400 });
      }
    } catch (error) {
      console.error("[MCP Gateway Action] Action error:", error);
      return json<ActionData>({ 
        error: error instanceof Error ? error.message : "An error occurred",
        _action: actionType
      }, { status: 500 });
    }
  } catch (outerError) {
    console.error('[MCP Gateway Action] OUTER ERROR:', outerError);
    return json<ActionData>({ 
      error: outerError instanceof Error ? outerError.message : "An unexpected error occurred",
      _action: "unknown"
    }, { status: 500 });
  }
}

export default function McpGatewayLayout() {
  const { projectId, gateways } = useLoaderData<typeof loader>();
  const fetcher = useFetcher();
  const params = useParams();
  const navigate = useNavigate();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingGateway, setEditingGateway] = useState<MCPGateway | null>(null);
  const [alert, setAlert] = useState<{status: 'success' | 'error' | null, message: string}>({
    status: null,
    message: ''
  });
  const [alertDismissing, setAlertDismissing] = useState(false);

  const selectedGatewayId = params.gatewayId;

  // Handle action responses
  useEffect(() => {
    if (fetcher.data && typeof fetcher.data === 'object' && 'success' in fetcher.data) {
      const actionData = fetcher.data as ActionData;
      if (actionData.success) {
        setAlert({
          status: 'success',
          message: actionData.message || 'Operation successful'
        });
        // Close modals on success
        setShowCreateModal(false);
        setEditingGateway(null);
        
        // Navigate to new gateway if created
        if (actionData._action === 'create' && actionData.gateway) {
          navigate(`/projects/${projectId}/mcp-gateway/${actionData.gateway.id}`);
        }
        
        // Navigate to gateway list if deleted (remove gateway ID from URL)
        if (actionData._action === 'delete') {
          navigate(`/projects/${projectId}/mcp-gateway`, { replace: true });
        }
      } else if (actionData.error) {
        setAlert({
          status: 'error',
          message: actionData.error
        });
      }
      
      // Auto-dismiss alert after 5 seconds
      const timer = setTimeout(() => {
        dismissAlert();
      }, 5000);
      
      return () => clearTimeout(timer);
    }
  }, [fetcher.data, navigate]);
  
  const dismissAlert = () => {
    setAlertDismissing(true);
    setTimeout(() => {
      setAlert({ status: null, message: '' });
      setAlertDismissing(false);
    }, 300);
  };
  
  const handleToggleGateway = (gateway: MCPGateway) => {
    const formData = new FormData();
    formData.append("_action", "toggle");
    formData.append("gatewayId", gateway.id);
    formData.append("enabled", (!gateway.enabled).toString());
    fetcher.submit(formData, { method: "post" });
  };
  
  const handleEdit = (gateway: MCPGateway) => {
    setEditingGateway(gateway);
  };
  
  const handleGatewayClick = (gatewayId: string) => {
    navigate(`/projects/${projectId}/mcp-gateway/${gatewayId}`);
  };
  
  return (
    <div className="flex h-full">
      {/* Alert */}
      <AlertBanner
        status={alert.status}
        message={alert.message}
        onDismiss={dismissAlert}
        dismissing={alertDismissing}
      />
      
      {/* Left Sidebar - Gateway List */}
      <div className="w-80 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 overflow-y-auto">
        <div className="p-4">
          {/* Header */}
          <div className="mb-4">
            <h1 className="text-xl font-bold mb-1">MCP Gateways</h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Manage Model Context Protocol gateways
            </p>
          </div>

          {/* Create Button */}
          <button
            onClick={() => setShowCreateModal(true)}
            className="w-full flex items-center justify-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors mb-4"
          >
            <PlusIcon className="h-5 w-5 mr-2" />
            Create Gateway
          </button>
          
          {/* Gateway List */}
          <div className="space-y-2">
            {gateways.length === 0 ? (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <p className="text-sm">No gateways yet</p>
                <p className="text-xs mt-1">Create your first gateway to get started</p>
              </div>
            ) : (
              gateways.map((gateway) => (
                <div
                  key={gateway.id}
                  onClick={() => handleGatewayClick(gateway.id)}
                  className={`
                    p-3 rounded-lg cursor-pointer transition-colors
                    ${selectedGatewayId === gateway.id 
                      ? 'bg-white dark:bg-gray-800 shadow-sm border border-indigo-500' 
                      : 'bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-750 border border-gray-200 dark:border-gray-700'
                    }
                  `}
                >
                  <div className="flex justify-between items-start mb-1">
                    <h3 className="font-medium text-sm truncate flex-1">{gateway.name}</h3>
                    <span className={`ml-2 px-1.5 py-0.5 text-xs rounded ${
                      gateway.enabled 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                        : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    }`}>
                      {gateway.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                    {gateway.id.substring(0, 8)}...
                  </p>
                  {gateway.description && (
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                      {gateway.description}
                    </p>
                  )}

                  {/* Edit button only */}
                  <div className="flex mt-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEdit(gateway);
                      }}
                      className="px-2 py-1 text-xs rounded hover:bg-gray-200 dark:hover:bg-gray-700"
                    >
                      Edit
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
      
      {/* Right Content - Outlet */}
      <div className="flex-1 overflow-y-auto">
        <Outlet />
      </div>
      
      {/* Modals */}
      <GatewayModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        mode="create"
        projectId={projectId}
      />
      
      <GatewayModal
        isOpen={!!editingGateway}
        onClose={() => setEditingGateway(null)}
        gateway={editingGateway}
        mode="edit"
        projectId={projectId}
      />
    </div>
  );
}
