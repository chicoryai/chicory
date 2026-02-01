import { json, type LoaderFunctionArgs, type ActionFunctionArgs } from "@remix-run/node";
import { useLoaderData, useFetcher } from "@remix-run/react";
import { auth } from "~/auth/auth.server";
import { useState, useEffect, useRef } from "react";
import { ChevronDownIcon } from "@heroicons/react/24/outline";
import { GiVintageRobot } from "react-icons/gi";
import {
  listWorkzones,
  createWorkzone,
  getWorkzone,
  updateWorkzone,
  deleteWorkzone,
  createWorkzoneInvocation,
  listWorkzoneInvocations,
  getWorkzoneInvocation
} from "~/services/chicory-workzone.server";
import { getProjectsByOrgId, getAgents, getAgentTask } from "~/services/chicory.server";
import type { WorkzoneResponse, InvocationResponse, StreamingMessage } from "~/types/workzone";
import { useWorkzoneStream } from "~/hooks/workzone/useWorkzoneStream";
import { streamEventBus } from "~/utils/streaming/eventBus";
import { StreamEventType } from "~/utils/streaming/eventTypes";
import { MarkdownRenderer } from "~/components/MarkdownRenderer";
import { StreamingMessageList } from "~/components/StreamingMessageList";
import type { AssistantMessageBlock } from "~/types/auditTrail";

type SessionStatus = string; // Can be any status from the backend: pending, processing, completed, failed, etc.

interface Session {
  id?: string;
  title?: string;
  repository?: string;
  status: SessionStatus;
  gitStats?: {
    additions: number;
    deletions: number;
  } | null;
  createdAt?: string;
  invocationId?: string;
  agentId?: string;
  projectId?: string;
  description?: string;
  userTaskContent?: string | null;
}

export async function action({ request }: ActionFunctionArgs) {
  const user = await auth.getUser(request, {});

  if (!user) {
    return json({ success: false, error: "Unauthorized" }, { status: 401 });
  }

  const formData = await request.formData();
  const intent = formData.get("intent") as string;

  if (intent === "createInvocation") {
    try {
      // Extract form data
      const content = formData.get("content") as string;
      const workzoneId = formData.get("workzoneId") as string;
      const agentId = formData.get("agentId") as string;
      const projectId = formData.get("projectId") as string;
      const orgId = formData.get("orgId") as string;
      const userId = user.userId;

      // Validation
      if (!content?.trim()) {
        return json({ success: false, error: "Content is required" }, { status: 400 });
      }

      if (!agentId || !projectId || !workzoneId || !orgId) {
        return json({ success: false, error: "Missing required fields" }, { status: 400 });
      }

      // Create workzone invocation
      const invocation = await createWorkzoneInvocation(workzoneId, {
        org_id: orgId,
        project_id: projectId,
        agent_id: agentId,
        user_id: userId,
        content: content.trim(),
        metadata: {
          created_from: "workzone"
        }
      });

      return json({ success: true, invocation });
    } catch (error) {
      console.error("[workzone] Error creating invocation:", error);
      return json(
        { success: false, error: "Failed to create invocation" },
        { status: 500 }
      );
    }
  }

  return json({ success: false, error: "Invalid intent" }, { status: 400 });
}

export async function loader({ request }: LoaderFunctionArgs) {
  const user = await auth.getUser(request, {});

  if (!user) {
    throw new Response("Unauthorized", { status: 401 });
  }

  // Get the organization ID from user
  const orgId = user.orgIdToUserOrgInfo ? Object.keys(user.orgIdToUserOrgInfo)[0] : null;

  if (!orgId) {
    throw new Response("No organization found", { status: 400 });
  }

  // Parallel requests for optimistic loading
  const [workzoneList, allProjects] = await Promise.all([
    listWorkzones(orgId, 1, 0),
    getProjectsByOrgId(orgId)
  ]);

  // Filter projects to only those the user is a member of
  const projects = allProjects.filter(project =>
    project.members?.includes(user.userId)
  );

  // Get or create workzone for this organization
  let workzone: WorkzoneResponse | null = null;
  if (workzoneList.workzones && workzoneList.workzones.length > 0) {
    // Use the first workzone
    workzone = workzoneList.workzones[0];
    console.log(`[workzone] Using existing workzone ${workzone.id} for org ${orgId}`);
  } else {
    // Create a new workzone for this org
    try {
      workzone = await createWorkzone({
        name: "Default Workzone",
        org_id: orgId,
        description: "Automatically created workzone"
      });
      console.log(`[workzone] Created new workzone ${workzone.id} for org ${orgId}`);
    } catch (error) {
      console.error("[workzone] Error creating workzone:", error);
      throw new Response("Failed to initialize workzone", { status: 500 });
    }
  }

  // Get all agents for all projects in parallel
  const agentsPromises = projects.map(project =>
    getAgents(project.id).catch(err => {
      console.error(`[workzone] Failed to get agents for project ${project.id}:`, err);
      return [];
    })
  );

  const agentsArrays = await Promise.all(agentsPromises);

  // Flatten all agents and add project info
  const allAgents = agentsArrays.flatMap((agents, index) =>
    agents.map(agent => ({
      ...agent,
      projectId: projects[index].id,
      projectName: projects[index].name
    }))
  );

  // Filter to only enabled agents
  const enabledAgents = allAgents.filter(agent => agent.state === 'enabled');

  // Get workzone invocations if workzone exists
  let invocations: InvocationResponse[] = [];
  if (workzone) {
    try {
      const invocationList = await listWorkzoneInvocations(workzone.id, orgId, 50, 0, 'desc', user.userId);
      invocations = invocationList.invocations || [];
      console.log(`[workzone] Fetched ${invocations.length} invocations for workzone ${workzone.id}`);
    } catch (error) {
      console.error("[workzone] Error fetching invocations:", error);
    }
  }

  // Fetch task details in parallel for better performance
  // Create parallel promises for all task fetches
  const taskFetchPromises = invocations.flatMap((invocation) => {
    const promises = [];

    // Fetch assistant task
    if (invocation.assistant_task_id && invocation.project_id && invocation.agent_id) {
      promises.push(
        getAgentTask(invocation.project_id, invocation.agent_id, invocation.assistant_task_id)
          .then(task => ({ invocationId: invocation.invocation_id, type: 'assistant', task }))
          .catch(error => {
            console.error('[workzone] Error fetching assistant task:', invocation.assistant_task_id, error);
            return { invocationId: invocation.invocation_id, type: 'assistant', task: null };
          })
      );
    }

    // Fetch user task
    if (invocation.user_task_id && invocation.project_id && invocation.agent_id) {
      promises.push(
        getAgentTask(invocation.project_id, invocation.agent_id, invocation.user_task_id)
          .then(task => ({ invocationId: invocation.invocation_id, type: 'user', task }))
          .catch(error => {
            console.error('[workzone] Error fetching user task:', invocation.user_task_id, error);
            return { invocationId: invocation.invocation_id, type: 'user', task: null };
          })
      );
    }

    return promises;
  });

  // Wait for all tasks to complete in parallel
  const taskResults = await Promise.all(taskFetchPromises);

  // Build a map of results by invocation ID
  const taskMap = new Map<string, { assistantTask?: any; userTask?: any }>();
  taskResults.forEach(result => {
    if (!taskMap.has(result.invocationId)) {
      taskMap.set(result.invocationId, {});
    }
    const entry = taskMap.get(result.invocationId)!;
    if (result.type === 'assistant') {
      entry.assistantTask = result.task;
    } else {
      entry.userTask = result.task;
    }
  });

  // Enrich invocations with task details
  const invocationsWithDetails = invocations.map((invocation) => {
    const agent = allAgents.find(a => a.id === invocation.agent_id);
    const project = projects.find(p => p.id === invocation.project_id);
    const tasks = taskMap.get(invocation.invocation_id) || {};

    // Ensure status is always a string
    const taskStatus: string = tasks.assistantTask?.status || 'pending';
    const userContent: string | null = tasks.userTask?.content || null;

    return {
      ...invocation,
      agent,
      project,
      status: taskStatus,
      userTaskContent: userContent
    };
  });

  const invocationsWithAgents = invocationsWithDetails;

  // Map to sessions format for backwards compatibility
  const sessionsWithTasks = invocationsWithDetails.map((invocation) => {
    return {
      id: invocation.invocation_id,
      title: invocation.agent?.name || 'Unknown Agent',
      repository: invocation.project?.name || 'Unknown Project',
      status: invocation.status, // Use the actual task status
      gitStats: null, // TODO: Add git stats if available in metadata
      createdAt: invocation.created_at,
      invocationId: invocation.invocation_id,
      agentId: invocation.agent_id,
      projectId: invocation.project_id,
      description: invocation.agent?.description || '',
      userTaskContent: invocation.userTaskContent // Add the user task content
    };
  });

  const sessions = sessionsWithTasks;

  return json({
    sessions,
    workzone,
    orgId,
    user,
    projects,
    allAgents: enabledAgents,
    invocations: invocationsWithAgents,
  });
}

function StatusBadge({ status }: { status: SessionStatus | string }) {
  // Normalize status to only show valid values
  const normalizeStatusText = (status: string | undefined): string => {
    if (!status) return 'Pending';

    const normalized = status.toLowerCase().trim();

    // Map of valid statuses
    const statusMap: Record<string, string> = {
      'pending': 'Pending',
      'queued': 'Queued',
      'processing': 'Processing',
      'completed': 'Completed',
      'failed': 'Failed'
    };

    // Check if it's a valid status
    if (statusMap[normalized]) {
      return statusMap[normalized];
    }

    // For any active/streaming state that's not completed or failed, show Processing
    // This includes things like "Gathering Context", "Rendering Output", etc.
    if (normalized !== 'completed' && normalized !== 'failed') {
      return 'Processing';
    }

    return 'Processing';
  };

  const displayStatus = normalizeStatusText(status);
  const normalizedStatus = displayStatus.toLowerCase();

  // Determine styling based on status
  const getStatusStyle = () => {
    if (normalizedStatus === 'completed') {
      return {
        bg: 'bg-emerald-100 dark:bg-emerald-900/30',
        text: 'text-emerald-700 dark:text-emerald-400',
        border: 'border-emerald-200 dark:border-emerald-800',
        icon: (
          <svg className="w-3 h-3" viewBox="0 0 12 12" fill="none">
            <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        )
      };
    }

    if (normalizedStatus === 'processing' || normalizedStatus === 'queued') {
      return {
        bg: 'bg-blue-100 dark:bg-blue-900/30',
        text: 'text-blue-700 dark:text-blue-400',
        border: 'border-blue-200 dark:border-blue-800',
        icon: (
          <svg className="w-3 h-3 animate-spin" viewBox="0 0 12 12" fill="none">
            <circle className="opacity-25" cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.5"/>
            <path className="opacity-75" fill="currentColor" d="M6 1a5 5 0 0 1 5 5h-2a3 3 0 0 0-3-3V1z"/>
          </svg>
        )
      };
    }

    if (normalizedStatus === 'failed') {
      return {
        bg: 'bg-red-100 dark:bg-red-900/30',
        text: 'text-red-700 dark:text-red-400',
        border: 'border-red-200 dark:border-red-800',
        icon: (
          <svg className="w-3 h-3" viewBox="0 0 12 12" fill="none">
            <path d="M9 3L3 9M3 3l6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        )
      };
    }

    // Default/pending style
    return {
      bg: 'bg-gray-100 dark:bg-gray-900/30',
      text: 'text-gray-700 dark:text-gray-400',
      border: 'border-gray-200 dark:border-gray-800',
      icon: (
        <svg className="w-3 h-3" viewBox="0 0 12 12" fill="none">
          <circle cx="6" cy="6" r="4" stroke="currentColor" strokeWidth="1.5"/>
        </svg>
      )
    };
  };

  const style = getStatusStyle();

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium ${style.bg} ${style.text} border ${style.border}`}>
      {style.icon}
      {displayStatus}
    </span>
  );
}

function GitStats({ additions, deletions }: { additions: number; deletions: number }) {
  return (
    <div className="inline-flex items-center gap-1.5 text-xs font-mono text-gray-600 dark:text-gray-400">
      <span className="text-green-600 dark:text-green-400">+{additions}</span>
      <span className="text-red-600 dark:text-red-400">-{deletions}</span>
    </div>
  );
}

function SessionItem({ session, onClick, isSelected }: { session: Session; onClick?: () => void; isSelected?: boolean }) {
  // Format the creation time
  const formatCreationTime = (dateString?: string) => {
    if (!dateString) return null;
    try {
      // Ensure the timestamp has a Z suffix for UTC timezone
      const timestamp = dateString.endsWith('Z') ? dateString : `${dateString}Z`;
      const date = new Date(timestamp);
      const now = new Date();
      const isToday = date.toDateString() === now.toDateString();

      if (isToday) {
        // Show time only for today's items
        return date.toLocaleTimeString('en-US', {
          hour: 'numeric',
          minute: '2-digit',
          hour12: true
        });
      } else {
        // Show date and time for older items
        return date.toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
          hour12: true
        });
      }
    } catch (error) {
      return null;
    }
  };

  const creationTime = formatCreationTime(session.createdAt);

  return (
    <div
      className={`group relative rounded-lg border-2 transition-all duration-200 ${
        isSelected
          ? "border-purple-500 dark:border-purple-500 bg-whitePurple-100 dark:bg-whitePurple-200/20 shadow-md"
          : "border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600"
      } backdrop-blur-sm`}
    >
      <div
        onClick={onClick}
        className="p-4 cursor-pointer"
      >
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-600 dark:text-gray-400">
              {session.repository || 'Unknown Project'}
            </p>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white font-['Sora']">
              {session.title || 'Unknown Agent'}
            </h3>
            {creationTime && (
              <p className="text-xs text-gray-500 dark:text-gray-500 mt-0.5">
                {creationTime}
              </p>
            )}
          </div>
          <StatusBadge status={session.status} />
        </div>

        <div className="flex items-center justify-between">
          {session.gitStats && (
            <GitStats additions={session.gitStats.additions} deletions={session.gitStats.deletions} />
          )}
        </div>
      </div>
    </div>
  );
}

interface Agent {
  id: string;
  name: string;
  projectId: string;
  projectName: string;
  description?: string;
}

function AgentDescriptionButton({ agent }: { agent: Agent }) {
  const [isPopoverOpen, setIsPopoverOpen] = useState(false);

  return (
    <div className="relative mt-2">
      <button
        onClick={() => setIsPopoverOpen(!isPopoverOpen)}
        className="text-xs text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300 font-medium transition-colors"
      >
        View agent description
      </button>

      {isPopoverOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsPopoverOpen(false)}
          />
          <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20 p-4 max-w-md">
            <div className="flex items-start justify-between mb-2">
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                {agent.name}
              </h4>
              <button
                onClick={() => setIsPopoverOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
              {agent.description || 'No description available'}
            </p>
          </div>
        </>
      )}
    </div>
  );
}

function AgentSelector({
  agents,
  selectedAgent,
  onSelectAgent
}: {
  agents: Agent[];
  selectedAgent: Agent | null;
  onSelectAgent: (agent: Agent) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative flex-1">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full gap-2 px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm hover:bg-white dark:hover:bg-gray-800 transition-colors text-sm font-medium text-gray-700 dark:text-gray-300"
      >
        <div className="flex items-center gap-2 min-w-0">
          <GiVintageRobot className="w-4 h-4 flex-shrink-0" />
          <span className="truncate">
            {selectedAgent ? selectedAgent.name : "Select agent"}
          </span>
        </div>
        <ChevronDownIcon className="w-4 h-4 flex-shrink-0" />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-20 max-h-64 overflow-y-auto">
            {agents.length === 0 ? (
              <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                No agents available
              </div>
            ) : (
              agents.map((agent) => (
                <button
                  key={agent.id}
                  onClick={() => {
                    onSelectAgent(agent);
                    setIsOpen(false);
                  }}
                  className={`block w-full text-left px-4 py-2.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                    selectedAgent?.id === agent.id
                      ? "bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
                      : "text-gray-700 dark:text-gray-300"
                  }`}
                >
                  <div className="font-medium">{agent.name}</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {agent.projectName}
                  </div>
                </button>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}


function SessionsEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center w-full h-full p-8 text-center">
      <div className="w-16 h-16 rounded-full bg-whitePurple-100 dark:bg-whitePurple-200/20 flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
      </div>
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 font-['Sora']">
        No tasks yet
      </h3>
      <p className="text-xs text-gray-500 dark:text-gray-400 font-['Plus_Jakarta_Sans']">
        Start issuing tasks to complete some work
      </p>
    </div>
  );
}

interface AssistantMessage {
  id: string;
  message_type: string;
  blocks: AssistantMessageBlock[];
  timestamp: number;
}

interface InvocationViewerProps {
  invocation: any;
  streamingMessages: StreamingMessage[];
  finalResponse: string | null;
  taskStatus: string;
  onUpdateContent: (data: {
    streamingMessages?: StreamingMessage[];
    finalResponse?: string | null;
    taskStatus?: string;
  }) => void;
}

function InvocationViewer({
  invocation,
  streamingMessages,
  finalResponse,
  taskStatus,
  onUpdateContent
}: InvocationViewerProps) {
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [statusText, setStatusText] = useState("");
  const [shouldRender, setShouldRender] = useState(false);
  const [showTaskInput, setShowTaskInput] = useState(false);

  // Use refs to avoid closing over props in event handlers
  const streamingMessagesRef = useRef<StreamingMessage[]>(streamingMessages);
  const onUpdateContentRef = useRef(onUpdateContent);

  // Update refs when props change
  useEffect(() => {
    streamingMessagesRef.current = streamingMessages;
    onUpdateContentRef.current = onUpdateContent;
  }, [streamingMessages, onUpdateContent]);

  const { isStreaming, canStream, error } = useWorkzoneStream({
    invocationId: invocation.invocation_id,
    projectId: invocation.project_id,
    agentId: invocation.agent_id,
    assistantTaskId: invocation.assistant_task_id,
    userTaskId: invocation.user_task_id,
    enabled: true
  });

  // Normalize status to only show valid values
  const normalizeStatus = (status: string | undefined): string => {
    if (!status) return 'Pending';

    const normalized = status.toLowerCase().trim();

    // Map of valid statuses
    const statusMap: Record<string, string> = {
      'pending': 'Pending',
      'queued': 'Queued',
      'processing': 'Processing',
      'completed': 'Completed',
      'failed': 'Failed'
    };

    // Check if it's a valid status
    if (statusMap[normalized]) {
      return statusMap[normalized];
    }

    // For any active/streaming state that's not completed or failed, show Processing
    // This includes things like "Gathering Context", "Rendering Output", etc.
    if (normalized !== 'completed' && normalized !== 'failed') {
      return 'Processing';
    }

    // Default fallback
    return 'Processing';
  };

  // Reset local state when invocation changes (but keep parent state)
  useEffect(() => {
    setMessages([]);
    setStatusText("");
    setShouldRender(finalResponse !== null || streamingMessages.length > 0);
  }, [invocation.invocation_id, finalResponse, streamingMessages]);

  // If we have content and not streaming, mark as completed
  useEffect(() => {
    if (!isStreaming && (finalResponse || streamingMessages.length > 0) && taskStatus !== 'completed') {
      onUpdateContentRef.current({ taskStatus: 'completed' });
    }
  }, [isStreaming, finalResponse, streamingMessages, taskStatus]);

  // Subscribe to streaming events
  useEffect(() => {
    const taskId = invocation.assistant_task_id;
    if (!taskId) return;

    const unsubscribers = [
      // Handle status updates from message chunks
      streamEventBus.subscribe(StreamEventType.MESSAGE_CHUNK, (payload) => {
        if (payload.taskId === taskId) {
          // Update status if present
          if (payload.status) {
            setStatusText(payload.status);
            // Update task status to "processing" when we get status updates
            if (taskStatus !== 'completed' && taskStatus !== 'failed') {
              onUpdateContentRef.current({ taskStatus: 'processing' });
            }
          }

          // Check if this has the final response content
          // The parser already extracts the response field, so payload.content is the markdown string
          if (payload.content && typeof payload.content === 'string' && payload.content.trim().length > 0) {
            // Clear streaming messages and show only final response
            onUpdateContentRef.current({
              streamingMessages: [],
              finalResponse: payload.content,
              taskStatus: 'completed'
            });
            setShouldRender(true);
          }
        }
      }),

      // Handle thinking blocks
      streamEventBus.subscribe(StreamEventType.THINKING_BLOCK, (payload) => {
        if (payload.taskId === taskId) {
          onUpdateContentRef.current({
            streamingMessages: [
              ...streamingMessagesRef.current,
              {
                type: 'thinking',
                thinking: payload.thinking,
                signature: payload.signature,
                timestamp: Date.now()
              }
            ]
          });
        }
      }),

      // Handle text blocks
      streamEventBus.subscribe(StreamEventType.TEXT_BLOCK, (payload) => {
        if (payload.taskId === taskId) {
          onUpdateContentRef.current({
            streamingMessages: [
              ...streamingMessagesRef.current,
              {
                type: 'text',
                text: payload.text,
                timestamp: Date.now()
              }
            ]
          });
        }
      }),

      // Handle completed tool executions (tool use + result)
      streamEventBus.subscribe(StreamEventType.TOOL_USE_COMPLETE, (payload) => {
        if (payload.taskId === taskId) {
          onUpdateContentRef.current({
            streamingMessages: [
              ...streamingMessagesRef.current,
              {
                type: 'tool',
                toolId: payload.toolId,
                toolName: payload.toolName,
                input: payload.input,
                result: payload.result,
                isError: payload.isError,
                timestamp: Date.now()
              }
            ]
          });
        }
      }),

      // Handle claude_code_message events - accumulate as structured blocks (backwards compatibility)
      streamEventBus.subscribe(StreamEventType.ASSISTANT_SECTION, (payload: any) => {
        if (payload.taskId === taskId && payload.blocks) {
          setMessages(prev => [
            ...prev,
            {
              id: `message-${Date.now()}-${Math.random()}`,
              message_type: payload.messageType || 'AssistantMessage',
              blocks: payload.blocks,
              timestamp: Date.now()
            }
          ]);
        }
      }),

      // Handle stream completion
      streamEventBus.subscribe(StreamEventType.STREAM_END, (payload) => {
        if (payload.taskId === taskId) {
          setStatusText("Completed");
          setShouldRender(true); // Render on completion even if no final response
          onUpdateContentRef.current({ taskStatus: 'completed' }); // Mark as completed when stream ends
        }
      })
    ];

    return () => {
      unsubscribers.forEach(unsub => unsub());
    };
  }, [invocation.assistant_task_id, taskStatus]);

  // Helper to extract text from a block
  const extractBlockText = (block: AssistantMessageBlock): string => {
    if (!block || typeof block !== 'object') return '';

    const blockAny = block as any;
    if (blockAny.type === 'TextBlock' && typeof blockAny.text === 'string') {
      return blockAny.text;
    }

    if (typeof blockAny.text === 'string') {
      return blockAny.text;
    }

    if (typeof blockAny.content === 'string') {
      return blockAny.content;
    }

    return '';
  };

  // Helper to check if block is a tool use
  const isToolUse = (block: AssistantMessageBlock): boolean => {
    const blockAny = block as any;
    return blockAny.type === 'ToolUseBlock' && blockAny.name;
  };

  // Helper to check if block is thinking
  const isThinking = (block: AssistantMessageBlock): boolean => {
    const blockAny = block as any;
    return (blockAny.type === 'ThinkingBlock' || blockAny.type === 'thinking') && blockAny.thinking;
  };

  // Function to download content as markdown file
  const handleDownload = () => {
    let content = '';

    // Get content from finalResponse or streaming messages
    if (finalResponse) {
      content = finalResponse;
    } else if (streamingMessages.length > 0) {
      // Combine streaming messages into markdown
      content = streamingMessages.map(msg => {
        if (msg.type === 'text') {
          return msg.text;
        } else if (msg.type === 'thinking') {
          return `> **Thinking**: ${msg.thinking}`;
        } else if (msg.type === 'tool') {
          return `\n**Tool: ${msg.toolName}**\n\`\`\`json\n${JSON.stringify(msg.input, null, 2)}\n\`\`\`\n${msg.isError ? '❌ Error' : '✅ Success'}\n`;
        }
        return '';
      }).join('\n\n');
    }

    if (!content.trim()) {
      content = 'No content available';
    }

    // Create blob and download
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${invocation.agent?.name || 'agent'}-${invocation.invocation_id?.slice(0, 8) || 'output'}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Render accumulated messages when shouldRender is true
  const renderMessages = () => {
    // If we have a final response, show only that
    if (finalResponse) {
      return (
        <MarkdownRenderer
          content={finalResponse}
          variant="task"
          className="prose prose-sm max-w-none text-gray-900 dark:text-gray-100"
        />
      );
    }

    // If we have streaming messages, show them
    if (streamingMessages.length > 0) {
      return <StreamingMessageList messages={streamingMessages} />;
    }

    // Fallback to old rendering logic for backwards compatibility
    if (!shouldRender || messages.length === 0) {
      return (
        <div className="text-sm text-gray-400 dark:text-gray-500">
          {isStreaming ? "Waiting for response..." : "No response yet"}
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {messages.map((message) => (
          <div key={message.id} className="space-y-2">
            {message.blocks.map((block, idx) => {
              // Render text blocks
              if (!isToolUse(block) && !isThinking(block)) {
                const text = extractBlockText(block);
                if (text) {
                  return (
                    <MarkdownRenderer
                      key={`${message.id}-block-${idx}`}
                      content={text}
                      variant="task"
                      className="prose prose-sm max-w-none text-gray-900 dark:text-gray-100"
                    />
                  );
                }
              }

              // Render tool use blocks
              if (isToolUse(block)) {
                const toolBlock = block as any;
                return (
                  <div key={`${message.id}-tool-${idx}`} className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-md border border-purple-200 dark:border-purple-800">
                    <div className="flex items-center gap-2 text-xs font-medium text-purple-700 dark:text-purple-300">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      <span>Tool: {toolBlock.name}</span>
                    </div>
                  </div>
                );
              }

              // Render thinking blocks
              if (isThinking(block)) {
                const thinkingBlock = block as any;
                return (
                  <div key={`${message.id}-thinking-${idx}`} className="p-3 bg-gray-50 dark:bg-gray-900/50 rounded-md border border-gray-200 dark:border-gray-700 italic text-sm text-gray-600 dark:text-gray-400">
                    {thinkingBlock.thinking}
                  </div>
                );
              }

              return null;
            })}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="flex-1 overflow-y-auto p-8 space-y-6">
        {/* Assistant Response Card */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900/50">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
            <div className="flex items-center gap-3">
              {/* Agent avatar */}
              <div className="flex h-10 w-10 items-center justify-center rounded-full overflow-hidden">
                <img
                  src="/icons/chicory-icon.png"
                  alt="Agent"
                  className="w-full h-full object-cover"
                />
              </div>

              {/* Agent name */}
              <div>
                <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                  {invocation.agent?.name || "Assistant"}
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {invocation.project?.name || "Project"}
                </p>
              </div>
            </div>

            {/* Status badge and download button */}
            <div className="flex items-center gap-2">
              {isStreaming ? (
                <div className="flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 dark:border-blue-800 dark:bg-blue-900/20">
                  <svg className="w-4 h-4 text-blue-600 dark:text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 74 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span className="text-sm font-medium text-blue-600 dark:text-blue-400">Running</span>
                </div>
              ) : normalizeStatus(taskStatus).toLowerCase() === 'completed' ? (
                <>
                  <div className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 dark:border-emerald-800 dark:bg-emerald-900/20">
                    <svg className="w-4 h-4 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-sm font-medium text-emerald-600 dark:text-emerald-400">Completed</span>
                  </div>
                  <button
                    onClick={() => setShowTaskInput(!showTaskInput)}
                    className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 transition-colors"
                    title="View original task input"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span>Task Input</span>
                    <svg className={`w-3 h-3 transition-transform ${showTaskInput ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  <button
                    onClick={handleDownload}
                    className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 transition-colors"
                    title="Download as markdown file"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    <span>Download</span>
                  </button>
                </>
              ) : normalizeStatus(taskStatus).toLowerCase() === 'failed' ? (
                <div className="flex items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-3 py-1.5 dark:border-rose-800 dark:bg-rose-900/20">
                  <svg className="w-4 h-4 text-rose-600 dark:text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  <span className="text-sm font-medium text-rose-600 dark:text-rose-400">Failed</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 dark:border-slate-700 dark:bg-slate-800">
                  <span className="text-sm font-medium text-slate-600 dark:text-slate-400">{normalizeStatus(taskStatus)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Task Input Dropdown */}
          <div
            className={`border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 overflow-hidden transition-all duration-300 ease-in-out ${
              showTaskInput && invocation.userTaskContent ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
            }`}
          >
            <div className="px-6 py-4">
              <div className="flex items-center gap-2 mb-3">
                <svg className="w-4 h-4 text-slate-600 dark:text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Original Task Input</h3>
              </div>
              <div className="rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 p-4">
                <div className="prose prose-sm max-w-none">
                  <MarkdownRenderer content={invocation.userTaskContent || ''} />
                </div>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 space-y-4">

            {!canStream && (
              <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                <p className="text-sm text-yellow-800 dark:text-yellow-200">
                  Connection limit reached. Close other streams to view this response.
                </p>
              </div>
            )}

            {error && (
              <div className="p-3 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg">
                <p className="text-sm text-rose-800 dark:text-rose-200">{error}</p>
              </div>
            )}

            {renderMessages()}

            {taskStatus === 'failed' && (
              <div className="p-4 bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg">
                <p className="text-sm text-rose-800 dark:text-rose-200 font-medium">
                  {invocation.error || "Task failed"}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center space-y-6">
        {/* Chicory Icon */}
        <div className="inline-block">
          <div className="w-32 h-32 relative flex items-center justify-center">
            <img
              src="/icons/chicory-icon.png"
              alt="Chicory"
              className="w-full h-full object-contain"
            />
          </div>
        </div>

        <p className="text-gray-600 dark:text-gray-400 font-['Plus_Jakarta_Sans'] text-base">
          Let's get some work done
        </p>
      </div>
    </div>
  );
}

export default function WorkzoneRoute() {
  const { sessions: initialSessions, workzone, orgId, projects, allAgents, invocations } = useLoaderData<typeof loader>();
  const fetcher = useFetcher<{ success: boolean; invocation?: InvocationResponse; error?: string }>();
  const [filterStatus, setFilterStatus] = useState<"all" | "active" | "completed">("all");
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(
    allAgents.length > 0 ? allAgents[0] : null
  );
  const [content, setContent] = useState("");
  const [selectedInvocationId, setSelectedInvocationId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [sessions, setSessions] = useState(initialSessions);

  // Store streaming content by invocation ID to persist across session switches
  const [invocationContent, setInvocationContent] = useState<Record<string, {
    streamingMessages: StreamingMessage[];
    finalResponse: string | null;
    taskStatus: string;
  }>>({});

  const SESSIONS_PER_PAGE = 5;

  // Get the selected invocation details
  const selectedInvocation = invocations.find(inv => inv.invocation_id === selectedInvocationId);

  // Get or initialize content for selected invocation
  const selectedInvocationContent = selectedInvocationId && invocationContent[selectedInvocationId]
    ? invocationContent[selectedInvocationId]
    : {
        streamingMessages: [],
        finalResponse: null,
        taskStatus: selectedInvocation?.status || 'pending'
      };

  // Callback to update invocation content
  const handleUpdateContent = (invocationId: string, data: {
    streamingMessages?: StreamingMessage[];
    finalResponse?: string | null;
    taskStatus?: string;
  }) => {
    setInvocationContent(prev => ({
      ...prev,
      [invocationId]: {
        streamingMessages: data.streamingMessages ?? prev[invocationId]?.streamingMessages ?? [],
        finalResponse: data.finalResponse ?? prev[invocationId]?.finalResponse ?? null,
        taskStatus: data.taskStatus ?? prev[invocationId]?.taskStatus ?? 'pending'
      }
    }));
  };

  // Filter sessions based on status
  const filteredSessions = sessions.filter((session) => {
    const normalizedStatus = session.status.toLowerCase().trim();

    if (filterStatus === "all") {
      return true;
    } else if (filterStatus === "active") {
      // Active includes: pending, queued, processing
      return normalizedStatus === "pending" ||
             normalizedStatus === "queued" ||
             normalizedStatus === "processing";
    } else if (filterStatus === "completed") {
      // Completed includes: completed and failed
      return normalizedStatus === "completed" ||
             normalizedStatus === "failed";
    }
    return true;
  });

  // Calculate pagination
  const totalPages = Math.ceil(filteredSessions.length / SESSIONS_PER_PAGE);
  const startIndex = currentPage * SESSIONS_PER_PAGE;
  const paginatedSessions = filteredSessions.slice(startIndex, startIndex + SESSIONS_PER_PAGE);

  // Update sessions when loader data changes
  useEffect(() => {
    setSessions(initialSessions);
  }, [initialSessions]);

  // Reset to first page when filter changes
  useEffect(() => {
    setCurrentPage(0);
  }, [filterStatus]);

  // Initialize selected agent when data loads
  useEffect(() => {
    if (allAgents.length > 0 && !selectedAgent) {
      setSelectedAgent(allAgents[0]);
    }
  }, [allAgents, selectedAgent]);

  // Subscribe to SSE events to update session statuses in real-time
  useEffect(() => {
    const updateSessionStatus = (invocationId: string, status: string) => {
      setSessions(prev => prev.map(session =>
        session.invocationId === invocationId
          ? { ...session, status }
          : session
      ));
    };

    const unsubscribers = [
      // Update status when status chunks come in
      streamEventBus.subscribe(StreamEventType.MESSAGE_CHUNK, (payload) => {
        const invocation = invocations.find(inv => inv.assistant_task_id === payload.taskId);
        if (invocation && payload.status) {
          updateSessionStatus(invocation.invocation_id, payload.status);
        }
      }),

      // Mark as completed when stream ends (skip FINAL_RESPONSE/message_content)
      streamEventBus.subscribe(StreamEventType.STREAM_END, (payload) => {
        const invocation = invocations.find(inv => inv.assistant_task_id === payload.taskId);
        if (invocation) {
          updateSessionStatus(invocation.invocation_id, 'completed');
        }
      })
    ];

    return () => {
      unsubscribers.forEach(unsub => unsub());
    };
  }, [invocations]);

  // Log data for debugging
  useEffect(() => {
    console.log('[workzone] Loaded data:', {
      workzone,
      projectsCount: projects.length,
      agentsCount: allAgents.length,
      invocationsCount: invocations.length,
      selectedAgent
    });
  }, [workzone, projects, allAgents, invocations, selectedAgent]);

  // Handle successful form submission
  useEffect(() => {
    if (fetcher.data?.success && fetcher.data.invocation) {
      console.log('[workzone] Invocation created successfully:', fetcher.data.invocation);
      setContent(""); // Clear the textarea
      setSelectedInvocationId(fetcher.data.invocation.invocation_id); // Auto-select the new invocation
      setCurrentPage(0); // Go to first page where the new invocation will appear
    }
  }, [fetcher.data]);

  // Cleanup on unmount - stop all active streams
  useEffect(() => {
    return () => {
      // The connection pool will handle cleanup of individual streams
      // But we can clear the selected invocation to stop any active stream
      setSelectedInvocationId(null);
    };
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-gradient-to-br from-white via-purple-50/20 to-lime-50/20 dark:from-gray-900 dark:via-purple-950/20 dark:to-lime-950/10">
      {/* Left Panel - Sessions */}
      <div className="w-[600px] border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-6">
          <div className="mb-4">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white font-['Outfit'] mb-1">
              Agent Workzone
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Command your agents to execute their work
            </p>
          </div>

          {/* Agent Selector */}
          <div className="mb-4">
            <div className="flex gap-2">
              <AgentSelector
                agents={allAgents}
                selectedAgent={selectedAgent}
                onSelectAgent={setSelectedAgent}
              />
            </div>
            {selectedAgent && (
              <AgentDescriptionButton agent={selectedAgent} />
            )}
          </div>

          {/* Input Field */}
          <fetcher.Form method="post" className="relative">
            <input type="hidden" name="intent" value="createInvocation" />
            <input type="hidden" name="workzoneId" value={workzone?.id || ""} />
            <input type="hidden" name="orgId" value={orgId || ""} />
            <input type="hidden" name="agentId" value={selectedAgent?.id || ""} />
            <input type="hidden" name="projectId" value={selectedAgent?.projectId || ""} />
            <textarea
              name="content"
              placeholder="Task your agent with work..."
              rows={6}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              disabled={fetcher.state === "submitting"}
              className="w-full px-4 py-3 pr-14 rounded-lg border border-gray-300 dark:border-gray-600 bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm text-sm text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 dark:focus:ring-purple-400 focus:border-transparent transition-all font-['Plus_Jakarta_Sans'] resize-none disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={!selectedAgent || !content.trim() || fetcher.state === "submitting"}
              className="absolute right-3 bottom-3 p-2.5 rounded-md bg-whitePurple-100 dark:bg-whitePurple-200/20 hover:bg-whitePurple-200 dark:hover:bg-whitePurple-200/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {fetcher.state === "submitting" ? (
                <svg className="w-5 h-5 text-purple-600 dark:text-purple-400 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <svg className="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              )}
            </button>
            {fetcher.data?.error && (
              <p className="mt-2 text-xs text-red-600 dark:text-red-400">
                {fetcher.data.error}
              </p>
            )}
          </fetcher.Form>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto flex flex-col">
          {/* Sessions Header */}
          <div className="p-6 pb-0">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white font-['Sora']">
                Tasks
              </h2>
              <div className="relative">
                <button
                  onClick={() => setIsFilterOpen(!isFilterOpen)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  {filterStatus === "all" ? "All" : filterStatus === "active" ? "Active" : "Completed"}
                  <ChevronDownIcon className={`w-3.5 h-3.5 transition-transform ${isFilterOpen ? 'rotate-180' : ''}`} />
                </button>

                {isFilterOpen && (
                  <div className="absolute right-0 mt-1 w-32 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-lg z-10 overflow-hidden">
                    <button
                      onClick={() => { setFilterStatus("all"); setIsFilterOpen(false); }}
                      className="block w-full px-3 py-2 text-left text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      All
                    </button>
                    <button
                      onClick={() => { setFilterStatus("active"); setIsFilterOpen(false); }}
                      className="block w-full px-3 py-2 text-left text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      Active
                    </button>
                    <button
                      onClick={() => { setFilterStatus("completed"); setIsFilterOpen(false); }}
                      className="block w-full px-3 py-2 text-left text-xs text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      Completed
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Session Items */}
          {filteredSessions.length === 0 ? (
            <div className="flex-1 flex items-start pt-8">
              <SessionsEmptyState />
            </div>
          ) : (
            <>
              <div className="p-6 pt-4">
                <div className="space-y-3">
                  {paginatedSessions.map((session) => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      onClick={() => setSelectedInvocationId(session.invocationId || null)}
                      isSelected={selectedInvocationId === session.invocationId}
                    />
                  ))}
                </div>
              </div>

              {/* Pagination Controls */}
              {filteredSessions.length > SESSIONS_PER_PAGE && (
                <div className="px-6 pb-4 flex items-center justify-between border-t border-gray-200 dark:border-gray-700 pt-4">
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
                    disabled={currentPage === 0}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                    Previous
                  </button>

                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    Page {currentPage + 1} of {totalPages}
                  </span>

                  <button
                    onClick={() => setCurrentPage(prev => Math.min(totalPages - 1, prev + 1))}
                    disabled={currentPage === totalPages - 1}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Right Panel */}
      {selectedInvocation ? (
        <InvocationViewer
          invocation={selectedInvocation}
          streamingMessages={selectedInvocationContent.streamingMessages}
          finalResponse={selectedInvocationContent.finalResponse}
          taskStatus={selectedInvocationContent.taskStatus}
          onUpdateContent={(data) => handleUpdateContent(selectedInvocation.invocation_id, data)}
        />
      ) : (
        <EmptyState />
      )}
    </div>
  );
}
