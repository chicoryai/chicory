/**
 * Playground Route
 * Handles the main chat/build interface for agents
 * This replaces the default index route for the Build view
 */

import { json, redirect } from "@remix-run/node";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { useFetcher, useLoaderData, useRevalidator, Outlet, useMatches } from "@remix-run/react";
import type { ShouldRevalidateFunctionArgs } from "@remix-run/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { clsx } from "clsx";
import { TaskInput } from "~/components/TaskInput";
import { InvocationHistory } from "~/components/agent/playground/InvocationHistory";
import TaskFeedbackModal, { type TaskFeedbackEntry } from "~/components/TaskFeedbackModal";
import { usePlaygroundStream } from "~/hooks/agent/usePlaygroundStream";
import { useInvocationPagination } from "~/hooks/agent/useInvocationPagination";
import { usePlaygroundData } from "~/hooks/agent/usePlaygroundData";
import { handleCreateInvocation } from "~/utils/agent/playground-actions";
import { addToolToAgent, updateAgent } from "~/services/chicory.server";
import { handleDeleteTool } from "~/utils/agent/configuration";
import {
  getAgentTools,
  getDataSourceTools,
  getMcpGateways,
  getProjectDataSources,
  getDataSourceTypes,
  getAgentTask,
  getAgentEnvVariables,
  createAgentEnvVariable,
  deleteAgentEnvVariable
} from "~/services/chicory.server";
import {
  createPlayground,
  listPlaygrounds,
  listPlaygroundInvocations
} from "~/services/chicory-playground.server";
import { getUserOrgDetails } from "~/auth/auth.server";
import { useAgentContext } from "./_app.projects.$projectId.agents.$agentId";
import type { PlaygroundResponse } from "~/types/playground";
import type { AgentTask } from "~/services/chicory.server";

export async function loader({ request, params }: LoaderFunctionArgs) {
  const startTime = Date.now();
  const { agentId, projectId } = params;

  if (!agentId || !projectId) {
    throw new Response("Agent ID and Project ID are required", { status: 400 });
  }

  // Get user details for project validation
  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }

  // Get pagination parameters from URL
  const url = new URL(request.url);
  const skip = url.searchParams.get("skip") ? parseInt(url.searchParams.get("skip")!) : 0;

  try {
    // First, get or create a default playground for this agent
    let playground: PlaygroundResponse | null = null;

    // Check if a default playground exists
    const playgroundsList = await listPlaygrounds(projectId, agentId, 1, 0);

    if (playgroundsList.playgrounds.length > 0) {
      // Use the first playground as default
      playground = playgroundsList.playgrounds[0];
    } else {
      // Create a default playground
      playground = await createPlayground(projectId, agentId, {
        name: "Default Playground",
        description: "Default playground for testing and development"
      });
    }

    // Fetch invocations and other data in parallel
    const [
      invocations,
      agentTools,
      dataSourceTools,
      gateways,
      projectDataSources,
      dataSourceTypes,
      envVariables
    ] = await Promise.all([
      listPlaygroundInvocations(projectId, agentId, playground.id, 50, skip, 'desc'),
      getAgentTools(projectId, agentId),
      getDataSourceTools(projectId),
      getMcpGateways(projectId),
      getProjectDataSources(projectId),
      getDataSourceTypes(),
      getAgentEnvVariables(projectId, agentId)
    ]);

 
    // Fetch actual task data for all invocations
    let taskMap: Record<string, AgentTask> = {};
    if (invocations.invocations && invocations.invocations.length > 0) {
      // Collect all task IDs
      const taskIds = invocations.invocations.flatMap(inv => {
        const ids = [inv.user_task_id];
        if (inv.assistant_task_id) {
          ids.push(inv.assistant_task_id);
        }
        return ids;
      });

      // Batch fetch all tasks
      const tasks = await Promise.all(
        taskIds.map(taskId => getAgentTask(projectId, agentId, taskId))
      );

      // Create a map for quick lookup
      tasks.forEach(task => {
        if (task) {
          taskMap[task.id] = task;
        }
      });
    }

    // Combine agent tools and datasource tools
    const tools = [...agentTools, ...dataSourceTools];

    const endTime = Date.now();
    console.log(`Loaded playground in ${endTime - startTime}ms`);
    return json({
      playground,
      invocations,
      taskMap,  // Include the task map
      tools,
      gateways,
      projectDataSources,
      dataSourceTypes,
      envVariables,
      isLoadMore: skip > 0
    });
  } catch (error) {
    console.error("Error fetching playground data:", error);
    if (error instanceof Response) {
      throw error;
    }
    throw new Response("Failed to load playground data", { status: 500 });
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

  console.log("[PLAYGROUND ACTION]", {
    agentId,
    projectId,
    intent
  });

  if (intent === "updateAgentName") {
    const rawName = (formData.get("name") || "").toString().trim();

    if (!rawName) {
      return json({ success: false, error: "Name is required" }, { status: 400 });
    }

    if (rawName.length > 50) {
      return json({ success: false, error: "Name must be 50 characters or fewer" }, { status: 400 });
    }

    try {
      const updated = await updateAgent(projectId, agentId, rawName);
      console.log("[PLAYGROUND ACTION] Agent name updated", { agentId, name: updated.name });
      return json({ success: true, name: updated.name });
    } catch (error) {
      console.error("[PLAYGROUND ACTION] Error updating agent name", {
        agentId,
        error: error instanceof Error ? error.message : error
      });
      return json({ success: false, error: "Failed to update agent name" }, { status: 500 });
    }
  }

  if (intent === "addTool") {
    const toolName = (formData.get("toolName") as string)?.trim();
    const toolDescription = (formData.get("toolDescription") as string) || "";
    const toolProvider = (formData.get("toolProvider") as string) || "MCP";
    const toolType = (formData.get("toolType") as string) || (formData.get("type") as string) || "mcp";
    const rawConfig = formData.get("toolConfig") as string | null;

    if (!toolName) {
      return json({ success: false, error: "Tool name is required" }, { status: 400 });
    }

    let toolConfig: Record<string, unknown> = {};
    if (rawConfig) {
      try {
        toolConfig = JSON.parse(rawConfig);
      } catch (error) {
        return json({ success: false, error: "Invalid tool configuration" }, { status: 400 });
      }
    }

    try {
      const created = await addToolToAgent(projectId, agentId, {
        name: toolName,
        description: toolDescription,
        provider: toolProvider,
        tool_type: toolType,
        config: toolConfig
      });
      console.log("[PLAYGROUND ACTION] Tool added", {
        agentId,
        projectId,
        toolId: created.id,
        provider: created.provider
      });
      return json({ success: true, tool: created, intent: "addTool" });
    } catch (error) {
      console.error("[PLAYGROUND ACTION] Error adding tool", {
        agentId,
        projectId,
        error: error instanceof Error ? error.message : error
      });
      return json({ success: false, error: "Failed to add tool" }, { status: 500 });
    }
  }

  if (intent === "deleteTool") {
    return handleDeleteTool(projectId, agentId, formData);
  }

  // Environment Variable Actions
  if (intent === "addEnvVariable") {
    const key = (formData.get("key") as string)?.trim();
    const value = formData.get("value") as string;
    const description = (formData.get("description") as string)?.trim() || undefined;

    if (!key) {
      return json({ success: false, error: "Variable name is required" }, { status: 400 });
    }

    if (!value) {
      return json({ success: false, error: "Value is required" }, { status: 400 });
    }

    try {
      const created = await createAgentEnvVariable(projectId, agentId, {
        key,
        value,
        description
      });
      console.log("[PLAYGROUND ACTION] Env variable added", {
        agentId,
        projectId,
        envVarId: created.id,
        key: created.key
      });
      return json({ success: true, envVariable: created, intent: "addEnvVariable" });
    } catch (error) {
      console.error("[PLAYGROUND ACTION] Error adding env variable", {
        agentId,
        projectId,
        error: error instanceof Error ? error.message : error
      });
      const errorMsg = error instanceof Error ? error.message : "Failed to add environment variable";
      // Check for duplicate key error
      if (errorMsg.includes("already exists")) {
        return json({ success: false, error: `Variable '${key}' already exists for this agent` }, { status: 400 });
      }
      return json({ success: false, error: "Failed to add environment variable" }, { status: 500 });
    }
  }

  if (intent === "deleteEnvVariable") {
    const envVarId = formData.get("envVarId") as string;

    if (!envVarId) {
      return json({ success: false, error: "Environment variable ID is required" }, { status: 400 });
    }

    try {
      await deleteAgentEnvVariable(projectId, agentId, envVarId);
      console.log("[PLAYGROUND ACTION] Env variable deleted", {
        agentId,
        projectId,
        envVarId
      });
      return json({ success: true, intent: "deleteEnvVariable" });
    } catch (error) {
      console.error("[PLAYGROUND ACTION] Error deleting env variable", {
        agentId,
        projectId,
        envVarId,
        error: error instanceof Error ? error.message : error
      });
      return json({ success: false, error: "Failed to delete environment variable" }, { status: 500 });
    }
  }

  if (intent === "cancelTask") {
    const taskId = formData.get("taskId") as string;

    if (!taskId) {
      return json({ success: false, error: "Task ID is required" }, { status: 400 });
    }

    try {
      const { cancelTask } = await import("~/services/chicory.server");
      const cancelledTask = await cancelTask(projectId, agentId, taskId);
      return json({ success: true, task: cancelledTask, intent: "cancelTask" });
    } catch (error) {
      console.error("[PLAYGROUND ACTION] Error cancelling task", {
        agentId,
        projectId,
        taskId,
        error: error instanceof Error ? error.message : error
      });
      return json({ success: false, error: "Failed to cancel task" }, { status: 500 });
    }
  }

  if (intent === "updateInstructions") {
    const systemInstructions = formData.get("systemInstructions")?.toString() || "";
    const outputFormat = formData.get("outputFormat")?.toString() || "";

    console.log("[PLAYGROUND ACTION] Starting updateInstructions", {
      agentId,
      instructionsLength: systemInstructions.length,
      hasScriptTag: systemInstructions.includes('<script'),
      hasSql: systemInstructions.toLowerCase().includes('select')
    });

    try {
      const updated = await updateAgent(
        projectId,
        agentId,
        undefined, // name
        undefined, // description
        systemInstructions,
        outputFormat,
        undefined, // deployed
        undefined, // api_key
        undefined, // state
        undefined, // capabilities
        undefined, // metadata
        userDetails.userId // updated_by for version tracking
      );

      console.log("[PLAYGROUND ACTION] Agent instructions updated successfully", {
        agentId,
        instructionsLength: updated.instructions?.length,
        outputFormatLength: updated.output_format?.length
      });

      return json({
        success: true,
        intent: "updateInstructions",
        instructions: updated.instructions,
        outputFormat: updated.output_format
      });
    } catch (error: any) {
      console.error("[PLAYGROUND ACTION] Error updating instructions", {
        agentId,
        errorType: error?.constructor?.name,
        errorStatus: error?.status,
        errorMessage: error?.message,
        errorStack: error?.stack?.substring(0, 200)
      });

      // Detect WAF block (403 or HTML response instead of JSON)
      const isWafBlock =
        error?.status === 403 ||
        error?.message?.includes("turbo-stream") ||
        error?.message?.includes("Unable to decode") ||
        error?.message?.includes("Unexpected token '<'") ||
        error?.message?.includes("Unexpected end of JSON") ||
        (error?.response && typeof error.response === 'string' && error.response.includes('<!DOCTYPE'));

      if (isWafBlock) {
        console.warn("[PLAYGROUND ACTION] WAF block detected - returning 200 with error", {
          agentId,
          errorStatus: error?.status,
          errorMessage: error?.message,
          willPreventErrorBoundary: true
        });

        // Return 200 status to prevent ErrorBoundary from triggering
        // This allows the configure component to display inline error
        return json(
          {
            success: false,
            intent: "updateInstructions",
            error: "Unable to save configuration. Please try again or contact support."
          },
          { status: 200 }
        );
      }

      // For other errors, still return 200 to prevent error boundary
      // but with different message
      console.warn("[PLAYGROUND ACTION] Non-WAF error - returning 200 with error", {
        agentId,
        errorStatus: error?.status,
        errorMessage: error?.message
      });

      return json({
        success: false,
        intent: "updateInstructions",
        error: error?.message || "Failed to update agent instructions"
      }, { status: 200 }); // Changed from error status to 200
    }
  }

  // Playground should only handle task submission or supported intents
  if (intent && intent !== "createInvocation") {
    return json({
      success: false,
      error: `Action '${intent}' is not supported in playground. Please use the appropriate route.`
    }, { status: 400 });
  }

  // Default action: create invocation (task submission)
  return handleCreateInvocation(projectId, agentId, formData);
}

export function shouldRevalidate({
  actionResult,
  defaultShouldRevalidate
}: ShouldRevalidateFunctionArgs) {
  // Don't revalidate parent when configure subroute submits
  if (actionResult?.intent === 'updateInstructions') {
    return false; // Configure will handle its own revalidation
  }
  return defaultShouldRevalidate;
}

// Playground view component
export default function PlaygroundView() {
  const { playground, invocations, taskMap } = useLoaderData<typeof loader>();
  const { agent, projectId, user } = useAgentContext();
  

  // Use custom hooks
  const {
    isStreaming,
    currentStreamTaskId,
    startStreaming,
    stopStreaming
  } = usePlaygroundStream({
    agentId: agent.id,
    projectId
  });

  const {
    paginatedInvocations,
    currentTaskMap,
    hasMore,
    isLoadingMore,
    loadMore
  } = useInvocationPagination({
    agentId: agent.id,
    projectId,
    initialInvocations: invocations,
    initialTaskMap: taskMap
  });

  const composerRef = useRef<HTMLDivElement | null>(null);
  const [composerHeight, setComposerHeight] = useState<number>(0);

  const streamingAgentRef = useRef(agent.id);

  useEffect(() => {
    const agentChanged = streamingAgentRef.current !== agent.id;
    if (agentChanged) {
      streamingAgentRef.current = agent.id;
      return;
    }

    if (isStreaming) {
      return;
    }

    if (!paginatedInvocations.length) {
      return;
    }

    const latestInvocation = paginatedInvocations.find(invocation => !!invocation.assistant_task_id);

    if (!latestInvocation || !latestInvocation.assistant_task_id) {
      return;
    }

    const assistantTaskId = latestInvocation.assistant_task_id;
    const assistantTask = currentTaskMap[assistantTaskId];
    const assistantStatus = assistantTask?.status;

    if (typeof assistantStatus === 'string' && assistantStatus.toLowerCase() === 'completed') {
      return;
    }

    startStreaming(
      latestInvocation.user_task_id,
      latestInvocation.invocation_id,
      assistantTaskId
    );
  }, [
    paginatedInvocations,
    currentTaskMap,
    isStreaming,
    startStreaming,
    agent.id
  ]);

  useEffect(() => {
    if (!composerRef.current) {
      return;
    }

    const element = composerRef.current;

    const updateHeight = () => {
      const nextHeight = element.getBoundingClientRect().height;
      setComposerHeight(prev => (Math.abs(prev - nextHeight) > 1 ? nextHeight : prev));
    };

    updateHeight();

    const resizeObserver = new ResizeObserver(() => {
      updateHeight();
    });

    resizeObserver.observe(element);

    return () => resizeObserver.disconnect();
  }, []);

  // Memoize the callback to prevent infinite re-renders
  const onNewInvocation = useCallback(({ userTaskId, invocationId, assistantTaskId }: {
    userTaskId: string;
    invocationId: string;
    assistantTaskId?: string;
  }) => {
    if (!assistantTaskId) {
      console.log(`[PLAYGROUND] No assistantTaskId provided, skipping stream`);
      return;
    }

    // Check if already streaming this task
    if (currentStreamTaskId === assistantTaskId) {
      console.log(`[PLAYGROUND] Already streaming task ${assistantTaskId}, skipping`);
      return;
    }

    // Check the assistant task status from the existing taskMap
    const assistantTask = currentTaskMap[assistantTaskId];

    // Only start streaming if:
    // 1. Task doesn't exist in taskMap (might be new), OR
    // 2. Task exists but is not completed/errored
    if (!assistantTask ||
        (assistantTask.status !== 'completed' &&
         assistantTask.status !== 'error' &&
         assistantTask.status !== 'failed')) {
      console.log(`[PLAYGROUND] Starting stream for task ${assistantTaskId}, status: ${assistantTask?.status || 'new'}`);
      startStreaming(userTaskId, invocationId, assistantTaskId);
    } else {
      console.log(`[PLAYGROUND] Skipping stream for completed task ${assistantTaskId}, status: ${assistantTask.status}`);
    }
  }, [currentTaskMap, currentStreamTaskId, startStreaming]);

  const { taskListRef, error } = usePlaygroundData({
    agentId: agent.id,
    onNewInvocation
  });

  const revalidator = useRevalidator();
  const cancelTaskFetcher = useFetcher<{
    success?: boolean;
    error?: string;
    task?: AgentTask;
    intent?: string;
  }>();

  // Both instructions and audit are now handled by subroutes
  const [feedbackModalState, setFeedbackModalState] = useState<{
    taskId: string;
    agentId: string;
    defaultRating: 'positive' | 'negative';
    existingFeedback?: TaskFeedbackEntry | null;
  } | null>(null);

  // Detect if configure or audit subroute is active (for sidebar rendering)
  const matches = useMatches();
  const configureMatch = matches.find(m =>
    m.id === "routes/_app.projects.$projectId.agents.$agentId.playground.configure"
  );
  const auditMatch = matches.find(m =>
    m.id === "routes/_app.projects.$projectId.agents.$agentId.playground.audit.$taskId"
  );
  const isConfigureOpen = !!configureMatch;
  const isAuditOpen = !!auditMatch;

  const isSidePanelOpen = isConfigureOpen || isAuditOpen;
  const mainFlexBasis = isAuditOpen ? '66%' : isSidePanelOpen ? '50%' : '100%';
  const panelFlexBasis = isAuditOpen ? '34%' : '50%';
  const panelMaxWidth = isAuditOpen ? 560 : 720;
  const panelMinWidth = isAuditOpen ? 420 : 480;

  const handleCloseFeedbackModal = useCallback(() => {
    setFeedbackModalState(null);
  }, []);

  const handleFeedbackSubmitted = useCallback((_: TaskFeedbackEntry) => {
    setFeedbackModalState(null);
    revalidator.revalidate();
  }, [revalidator]);

  const handleShowFeedbackPanel = useCallback((options: {
    taskId: string;
    agentId: string;
    taskLabel?: string;
    anchorRect: DOMRect;
    existingFeedback?: TaskFeedbackEntry | null;
    defaultRating: 'positive' | 'negative';
  }) => {
    setFeedbackModalState({
      taskId: options.taskId,
      agentId: options.agentId,
      defaultRating: options.defaultRating,
      existingFeedback: options.existingFeedback
    });
  }, []);

  const handleStopTask = useCallback((taskId: string) => {
    // Stop the streaming immediately for better UX
    stopStreaming();
    
    // Submit the cancel request to the server
    const formData = new FormData();
    formData.set('intent', 'cancelTask');
    formData.set('taskId', taskId);
    cancelTaskFetcher.submit(formData, { method: 'post' });
  }, [stopStreaming, cancelTaskFetcher]);

  // Handle cancel task fetcher response
  useEffect(() => {
    if (cancelTaskFetcher.state === 'idle' && cancelTaskFetcher.data) {
      // Only revalidate for cancel task actions, not other actions
      if (cancelTaskFetcher.data.intent !== 'cancelTask') {
        return;
      }

      if (cancelTaskFetcher.data.success) {
        // Revalidate to refresh the task list
        revalidator.revalidate();
      } else if (cancelTaskFetcher.data.error) {
        console.error('Failed to cancel task:', cancelTaskFetcher.data.error);
      }
    }
  }, [cancelTaskFetcher.state, cancelTaskFetcher.data, revalidator]);

  // Check if there are any invocations to display
  const hasInvocations = paginatedInvocations.length > 0;

  return (
    <div className="playground-shell relative z-0 flex flex-1 overflow-hidden bg-transparent">
      <div
        className={clsx(
          "flex h-full min-w-0 flex-col overflow-hidden transition-[flex-basis] duration-300 ease-in-out",
          isSidePanelOpen ? "flex-none" : "flex-1"
        )}
        style={{ flexBasis: mainFlexBasis }}
      >
        {!hasInvocations ? (
          <div className="flex flex-1 items-center justify-center">
            <div className="w-full max-w-4xl px-4">
              <h1 className="mb-8 text-center text-3xl font-bold text-purple-500 dark:text-purple-400">
                Welcome to Playground
              </h1>
              <div className="w-full">
                {error && (
                  <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
                    <p className="text-red-600 dark:text-red-400">{error}</p>
                  </div>
                )}
                <TaskInput
                  projectId={projectId}
                  agentId={agent.id}
                  isDisabled={!!error}
                  additionalFormData={{ playgroundId: playground.id }}
                  isConfigureOpen={isConfigureOpen}
                  isStreaming={isStreaming}
                  currentStreamTaskId={currentStreamTaskId}
                  onStopTask={handleStopTask}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="relative z-10 flex flex-1 flex-col overflow-hidden">
            <InvocationHistory
              paginatedInvocations={paginatedInvocations}
              currentTaskMap={currentTaskMap}
              currentStreamTaskId={currentStreamTaskId}
              isStreaming={isStreaming}
              user={user}
              agentId={agent.id}
              hasMore={hasMore}
              isLoadingMore={isLoadingMore}
              onLoadMore={loadMore}
              taskListRef={taskListRef}
              composerHeight={composerHeight}
              onShowFeedbackPanel={handleShowFeedbackPanel}
            />

            <div ref={composerRef} className="p-4">
              {error && (
                <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
                  <p className="text-red-600 dark:text-red-400">{error}</p>
                </div>
              )}
              <TaskInput
                projectId={projectId}
                agentId={agent.id}
                isDisabled={!!error}
                additionalFormData={{ playgroundId: playground.id }}
                isConfigureOpen={isConfigureOpen}
                isStreaming={isStreaming}
                currentStreamTaskId={currentStreamTaskId}
                onStopTask={handleStopTask}
              />
            </div>
          </div>
        )}
      </div>

      <AnimatePresence initial={false}>
        {isSidePanelOpen && (
          <motion.aside
            key={isAuditOpen ? 'audit' : 'configure'}
            initial={{ x: "100%", opacity: 0 }}
            animate={{ x: "0%", opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="relative z-30 flex h-full flex-col gap-6 overflow-hidden rounded-3xl bg-transparent px-6 py-6 dark:bg-gray-900"
            style={{
              flexBasis: panelFlexBasis,
              maxWidth: `${panelMaxWidth}px`,
              minWidth: `${panelMinWidth}px`,
              maxHeight: "calc(100vh - 64px)",
              width: '90%',
              marginLeft: 'auto',
              marginRight: 'auto'
            }}
          >
            {(isConfigureOpen || isAuditOpen) ? (
              <Outlet context={{ agent, projectId, user }} />
            ) : null}
          </motion.aside>
        )}
      </AnimatePresence>

      {feedbackModalState ? (
        <TaskFeedbackModal
          isOpen={Boolean(feedbackModalState)}
          taskId={feedbackModalState.taskId}
          agentId={feedbackModalState.agentId}
          projectId={projectId}
          defaultRating={feedbackModalState.defaultRating}
          existingFeedback={feedbackModalState.existingFeedback ?? null}
          onClose={handleCloseFeedbackModal}
          onSubmitted={handleFeedbackSubmitted}
        />
      ) : null}
    </div>
  );
}
