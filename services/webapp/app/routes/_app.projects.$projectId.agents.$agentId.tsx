/**
 * Parent Layout Route for Agent Pages
 * Handles shared agent data loading and navigation
 */

import { json, redirect } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { Outlet, useLoaderData, useLocation, useOutletContext, useRouteError, useParams, useMatches, useRevalidator } from "@remix-run/react";
import { useState, useMemo } from "react";
import { getUserOrgDetails } from "~/auth/auth.server";
import { getAgent, type Agent } from "~/services/chicory.server";
import { TopNavBar } from "~/components/TopNavBar";
import { PlaygroundHeader } from "~/components/agent/playground/PlaygroundHeader";
import MCPAvailableToolsModal from "~/components/modals/MCPAvailableToolsModal";
import AddMCPToolModal from "~/components/modals/AddMCPToolModal";
import AddEnvVariableModal from "~/components/modals/AddEnvVariableModal";
import type { loader as playgroundLoader } from "./_app.projects.$projectId.agents.$agentId.playground";
import type { SerializeFrom } from "@remix-run/node";
import { useToast } from "~/hooks/useToast";

type PlaygroundLoaderData = SerializeFrom<typeof playgroundLoader>;

/**
 * Prevent unnecessary revalidation of parent layout
 * The parent layout only needs to reload when agent name changes
 */
export function shouldRevalidate({ actionResult, defaultShouldRevalidate }: any) {
  // Don't revalidate parent layout on instruction updates
  // Agent name, ID, project_id, and other core agent fields don't change
  if (actionResult?.intent === 'updateInstructions') {
    return false;
  }

  return defaultShouldRevalidate;
}

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { agentId, projectId } = params;

  if (!agentId || !projectId) {
    throw new Response("Agent ID and Project ID are required", { status: 400 });
  }

  // Auth and project validation (ONCE for all child routes)
  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) return userDetails;

  // Load agent data (ONCE for all child routes)
  try {
    const start = Date.now();
    const agent = await getAgent(projectId, agentId);
    const duration = Date.now() - start;

    if (!agent) {
      console.error(`Agent not found - ID: ${agentId}, Project: ${projectId} - duration: ${duration}ms`);
      throw new Response("Agent not found", { status: 404 });
    }

    // Extract user information
    const firstName = 'firstName' in userDetails ? (userDetails as any).firstName : null;
    const email = 'email' in userDetails ? (userDetails as any).email : null;

    console.log(`Agent loaded: {Agent_id: ${agent.id}, project_id: ${agent.project_id}, name: ${agent.name}} - duration: ${duration}ms`);
    return json({
      agent,
      projectId,
      user: {
        firstName,
        email
      }
    });
  } catch (error) {
    console.error("Error loading agent in parent layout:", {
      agentId,
      projectId,
      error: error instanceof Error ? error.message : error
    });
    
    // If it's already a Response error, re-throw it
    if (error instanceof Response) {
      throw error;
    }
    
    // For other errors, provide more context
    throw new Response("Failed to load agent data", { status: 500 });
  }
}

// Define context type for child routes
interface AgentLayoutContext {
  agent: Agent;
  projectId: string;
  user: {
    firstName: string | null;
    email: string | null;
  };
}

export default function AgentLayout() {
  const { agent, projectId, user } = useLoaderData<typeof loader>();
  const location = useLocation();
  const matches = useMatches();
  const playgroundMatch = matches.find(match => match.id === "routes/_app.projects.$projectId.agents.$agentId.playground");
  const playgroundData = playgroundMatch?.data as PlaygroundLoaderData | undefined;
  const [toolModalConfig, setToolModalConfig] = useState<{ name: string; availableTools: any[] } | null>(null);
  const [showAddMcpModal, setShowAddMcpModal] = useState(false);
  const [showAddEnvVarModal, setShowAddEnvVarModal] = useState(false);
  const revalidator = useRevalidator();

  // Memoize outlet context to prevent unnecessary child re-renders
  // Context object should only change when agent data actually changes
  const outletContext = useMemo(() => ({ agent, projectId, user }), [agent, projectId, user]);
  
  // Determine active view from URL
  let activeView: 'build' | 'evaluate' | 'deploy' | 'manage';
  if (location.pathname.includes('/manage')) {
    activeView = 'manage';
  } else if (location.pathname.includes('/evaluations')) {
    activeView = 'evaluate';
  } else if (location.pathname.includes('/deploy')) {
    activeView = 'deploy';
  } else {
    activeView = 'build'; // Default for playground and index
  }
  const navBar = activeView === 'build' && playgroundData
    ? (
        <PlaygroundHeader
          agent={agent}
          projectId={projectId}
          tools={playgroundData.tools ?? []}
          envVariables={playgroundData.envVariables ?? []}
          projectDataSources={playgroundData.projectDataSources ?? []}
          dataSourceTypes={playgroundData.dataSourceTypes ?? []}
          actionPath={`/projects/${projectId}/agents/${agent.id}/playground`}
          onOpenToolModal={config => setToolModalConfig(config)}
          onAddMcpTool={() => setShowAddMcpModal(true)}
          onAddEnvVariable={() => setShowAddEnvVarModal(true)}
        >
          {({ left, right }) => (
            <TopNavBar
              agent={agent}
              projectId={projectId}
              activeView={activeView}
              leftSlot={left}
              rightSlot={right}
            />
          )}
        </PlaygroundHeader>
      )
    : (
        <TopNavBar
          agent={agent}
          projectId={projectId}
          activeView={activeView}
        />
      );

  return (
    <div className="flex h-screen flex-col dark:bg-gray-900">
      <div className="sticky top-0 z-20 bg-transparent" data-playground-header>
        {navBar}
      </div>

      {/* Child routes render here with shared context */}
      <Outlet context={outletContext} />

      {toolModalConfig && (
        <MCPAvailableToolsModal
          isOpen={true}
          onClose={() => setToolModalConfig(null)}
          toolName={toolModalConfig.name}
          availableTools={toolModalConfig.availableTools}
        />
      )}

      {showAddMcpModal && (
        <AddMCPToolModal
          isOpen={true}
          onClose={() => setShowAddMcpModal(false)}
          agentId={agent.id}
          onSuccess={() => {
            setShowAddMcpModal(false);
            revalidator.revalidate();
          }}
          actionPath={`/projects/${projectId}/agents/${agent.id}/playground`}
        />
      )}

      {showAddEnvVarModal && (
        <AddEnvVariableModal
          isOpen={true}
          onClose={() => setShowAddEnvVarModal(false)}
          agentId={agent.id}
          onSuccess={() => {
            setShowAddEnvVarModal(false);
            // Note: fetcher automatically triggers revalidation after successful action
          }}
          actionPath={`/projects/${projectId}/agents/${agent.id}/playground`}
        />
      )}
    </div>
  );
}

// Export typed hook for child routes to access shared data
export function useAgentContext() {
  return useOutletContext<AgentLayoutContext>();
}

// Error boundary for agent-related errors
export function ErrorBoundary() {
  const error = useRouteError();
  const location = useLocation();
  const params = useParams();
  const revalidator = useRevalidator();
  const { showToast, ToastContainer } = useToast();

  // Log error details for debugging
  console.error("Agent route error:", {
    error,
    location: location.pathname,
    agentId: params.agentId
  });

  // Detect WAF block errors (403 or HTML response instead of JSON)
  const errorMessage = (error as any)?.message || (error as any)?.data?.message || "";
  const errorStatus = (error as any)?.status;

  const isWafBlock =
    errorStatus === 403 ||
    errorMessage.includes("turbo-stream") ||
    errorMessage.includes("Unable to decode") ||
    errorMessage.includes("Unexpected token '<'") ||
    errorMessage.includes("Unexpected end of JSON") ||
    errorMessage.includes("<!DOCTYPE");

  if (isWafBlock) {
    console.warn("WAF block detected in ErrorBoundary - showing toast instead of error page");

    // Show toast notification for WAF errors
    showToast(
      "Request blocked by security filter. Please try again or contact support if the issue persists.",
      "error",
      8000
    );

    // Return minimal UI with Try Again button instead of full error page
    return (
      <>
        <ToastContainer />
        <div className="flex items-center justify-center h-screen bg-gray-50 dark:bg-gray-900">
          <div className="text-center max-w-md">
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Unable to Load
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              The request was blocked by a security filter. This is usually temporary.
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => revalidator.revalidate()}
                className="inline-flex items-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              >
                Try Again
              </button>
              <a
                href={`/projects/${params.projectId}`}
                className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                Back to Project
              </a>
            </div>
          </div>
        </div>
      </>
    );
  }

  // For real errors (404, 500, etc.), show full error page
  let errorTitle = "Agent Not Found";
  let realErrorMessage = "The agent you're looking for doesn't exist or you don't have access to it.";

  if (error instanceof Response) {
    if (error.status === 500) {
      errorTitle = "Server Error";
      realErrorMessage = "There was a problem loading the agent data. Please try again.";
    }
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gray-50 dark:bg-gray-900">
      <div className="text-center max-w-md">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          {errorTitle}
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          {realErrorMessage}
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            Try Again
          </button>
          <a
            href="/"
            className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            Return to Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}
