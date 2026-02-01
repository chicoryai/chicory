import { json } from "@remix-run/node";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { useLoaderData, useSearchParams, useNavigation, useFetcher, useRevalidator } from "@remix-run/react";
import { useState, useCallback, useEffect } from "react";
import { getUserOrgDetails } from "~/auth/auth.server";
import { getAgentTasks, addTestCase, addTestCases, cancelTask, type AgentTask } from "~/services/chicory.server";
import { ManageTable, type TaskPair } from "~/components/ManageTable";
import { useAgentContext } from "./_app.projects.$projectId.agents.$agentId";

type LoaderData = {
  taskPairs: TaskPair[];
  hasMore: boolean;
  skip: number;
  startDate?: string;
  endDate?: string;
};

// Extract raw response with markdown preserved (for modal display)
function extractRawResponse(assistantTask: AgentTask): string {
  try {
    const content = assistantTask.content;
    if (typeof content === 'string') {
      const parsed = JSON.parse(content);
      if (parsed.response) {
        return parsed.response;
      }
    }
    return content;
  } catch (error) {
    return assistantTask.content;
  }
}

// Extract response text with markdown stripped (for table display)
function extractResponseText(assistantTask: AgentTask): string {
  try {
    // The assistant content is a JSON string with a "response" field
    const content = assistantTask.content;
    if (typeof content === 'string') {
      const parsed = JSON.parse(content);
      if (parsed.response) {
        // Remove markdown formatting and get plain text
        return parsed.response
          .replace(/#{1,6}\s/g, '') // Remove headers
          .replace(/\*\*/g, '') // Remove bold
          .replace(/\*/g, '') // Remove italic
          .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') // Remove links, keep text
          .replace(/`/g, '') // Remove code ticks
          .replace(/\n+/g, ' ') // Replace newlines with spaces
          .trim();
      }
    }
    return content.substring(0, 100);
  } catch (error) {
    return assistantTask.content.substring(0, 100);
  }
}

function groupTasksIntoPairs(tasks: AgentTask[]): TaskPair[] {
  const taskPairs: TaskPair[] = [];
  const taskMap = new Map<string, AgentTask>();
  const processedTasks = new Set<string>();

  // Create a map of all tasks by ID
  tasks.forEach(task => {
    taskMap.set(task.id, task);
  });

  // Find user tasks and pair them with their related assistant tasks
  tasks.forEach(task => {
    // Skip if already processed
    if (processedTasks.has(task.id)) {
      return;
    }

    let userTask: AgentTask | null = null;
    let assistantTask: AgentTask | null = null;

    // Check if this is a user task with a related assistant task
    if (task.role === 'user' && task.related_task_id) {
      userTask = task;
      assistantTask = taskMap.get(task.related_task_id) || null;

      if (assistantTask && assistantTask.role === 'assistant') {
        processedTasks.add(task.id);
        processedTasks.add(assistantTask.id);
      } else {
        assistantTask = null;
      }
    }
    // Check if this is an assistant task with a related user task
    else if (task.role === 'assistant' && task.related_task_id) {
      assistantTask = task;
      userTask = taskMap.get(task.related_task_id) || null;

      if (userTask && userTask.role === 'user') {
        processedTasks.add(task.id);
        processedTasks.add(userTask.id);
      } else {
        userTask = null;
      }
    }

    // Only create a pair if we have both user and assistant tasks
    if (userTask && assistantTask) {
      // Calculate latency
      const userCompletedAt = new Date(userTask.completed_at || userTask.created_at);
      const assistantCompletedAt = new Date(assistantTask.completed_at || assistantTask.created_at);
      const latency = assistantCompletedAt.getTime() - userCompletedAt.getTime();

      // Extract playground name from metadata
      const playgroundName = (userTask.metadata as any)?.playground_name ||
                            (assistantTask.metadata as any)?.playground_name;

      // Extract response text (stripped for table display)
      const responseStripped = extractResponseText(assistantTask);

      // Extract raw response (with markdown for modal display)
      const response = extractRawResponse(assistantTask);

      // Determine source from metadata
      const userMetadata = userTask.metadata as any;
      const assistantMetadata = assistantTask.metadata as any;
      
      let source = 'API';

      if (userMetadata?.gateway_id || assistantMetadata?.gateway_id) {
        source = 'MCP Gateway';
      } else if (userMetadata?.playground_id || assistantMetadata?.playground_id) {
        source = 'Playground';
      } else if (userMetadata?.workzone_id || assistantMetadata?.workzone_id) {
        source = 'Workzone';
      }

      // Extract feedback from metadata (prioritize assistant metadata)
      let feedbackRaw = assistantMetadata?.feedback || userMetadata?.feedback;
      let feedback: { rating?: 'positive' | 'negative'; comment?: string } | undefined = undefined;

      // Handle feedback as array or object
      if (feedbackRaw) {
        if (Array.isArray(feedbackRaw) && feedbackRaw.length > 0) {
          // Get the first feedback item from array
          const feedbackItem = feedbackRaw[0];
          const rating = feedbackItem.rating;
          feedback = {
            rating: rating === 'positive' || rating === 'negative' ? rating : undefined,
            comment: feedbackItem.feedback || feedbackItem.comment || feedbackItem.text
          };
        } else if (typeof feedbackRaw === 'object') {
          // Handle as single object
          const rating = feedbackRaw.rating;
          feedback = {
            rating: rating === 'positive' || rating === 'negative' ? rating : undefined,
            comment: feedbackRaw.feedback || feedbackRaw.comment || feedbackRaw.text
          };
        }
      }

      taskPairs.push({
        id: assistantTask.id,
        userTask: userTask,
        assistantTask: assistantTask,
        userQuery: userTask.content,
        response: response, // Raw markdown for modal
        responseStripped: responseStripped, // Stripped for table
        timestamp: userTask.created_at,
        status: assistantTask.status || 'unknown',
        latency: latency > 0 ? latency : 0,
        agentId: userTask.agent_id,
        playgroundName,
        source,
        feedback
      });
    }
  });

  // Sort by timestamp descending (newest first)
  return taskPairs.sort((a, b) =>
    new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );
}

export async function action({ request, params }: ActionFunctionArgs) {
  const { agentId, projectId } = params;

  if (!agentId || !projectId) {
    return json({ error: "Agent ID and Project ID are required" }, { status: 400 });
  }

  const userDetails = await getUserOrgDetails(request);

  if (userDetails instanceof Response) {
    return userDetails;
  }

  const formData = await request.formData();
  const intent = formData.get("intent");

  if (intent === "cancelTask") {
    const taskId = formData.get("taskId") as string;

    if (!taskId) {
      return json({ success: false, error: "Task ID is required", intent: "cancelTask" }, { status: 400 });
    }

    try {
      const cancelledTask = await cancelTask(projectId, agentId, taskId);
      return json({ success: true, task: cancelledTask, intent: "cancelTask" });
    } catch (error) {
      console.error("[MANAGE ACTION] Error cancelling task", {
        agentId,
        projectId,
        taskId,
        error: error instanceof Error ? error.message : error
      });
      return json({ success: false, error: "Failed to cancel task", intent: "cancelTask" }, { status: 500 });
    }
  }

  if (intent === "add-tasks-to-evaluation") {
    const evaluationId = formData.get("evaluationId") as string;
    const tasksJson = formData.get("tasks") as string;

    if (!evaluationId || !tasksJson) {
      return json({ error: "Evaluation ID and tasks are required" }, { status: 400 });
    }

    try {
      const tasks = JSON.parse(tasksJson) as Array<{
        userQuery: string;
        response: string;
        source?: string;
        timestamp: string;
      }>;

      // Convert tasks to test cases
      const testCases = tasks.map(task => ({
        task: task.userQuery,
        expected_output: task.response,
        evaluation_guideline: null, // User can fill this in later
        metadata: {
          source: task.source,
          timestamp: task.timestamp,
          added_from_manage: true
        }
      }));

      // Batch test cases into groups of 25
      const BATCH_SIZE = 25;
      const batches: typeof testCases[] = [];
      for (let i = 0; i < testCases.length; i += BATCH_SIZE) {
        batches.push(testCases.slice(i, i + BATCH_SIZE));
      }

      // Add test cases in batches
      let totalAdded = 0;
      for (const batch of batches) {
        await addTestCases(projectId, agentId, evaluationId, batch);
        totalAdded += batch.length;
      }

      return json({ success: true, message: `Added ${totalAdded} test case(s) to evaluation` });
    } catch (error) {
      console.error("Error adding tasks to evaluation:", error);
      return json({ error: "Failed to add tasks to evaluation" }, { status: 500 });
    }
  }

  return json({ error: "Invalid intent" }, { status: 400 });
}

export async function loader({ request, params }: LoaderFunctionArgs) {
  const { agentId, projectId } = params;

  if (!agentId || !projectId) {
    throw new Response("Agent ID and Project ID are required", { status: 400 });
  }

  const userDetails = await getUserOrgDetails(request);

  if (userDetails instanceof Response) {
    return userDetails;
  }

  const url = new URL(request.url);
  const skipParam = url.searchParams.get("skip");
  const skip = skipParam && !Number.isNaN(Number(skipParam)) ? Number(skipParam) : 0;
  const limit = 100; // Fetch 100 tasks to get 50 task pairs (each pair = 2 tasks)

  const taskResult = await getAgentTasks(projectId, agentId, limit, "desc", undefined, skip);
  const tasks = taskResult.tasks ?? [];
  const hasMore = Boolean(taskResult.has_more);

  // Group tasks into pairs
  const taskPairs = groupTasksIntoPairs(tasks);

  return json<LoaderData>({
    taskPairs,
    hasMore,
    skip
  });
}

export default function ManageView() {
  const { taskPairs, hasMore, skip } = useLoaderData<typeof loader>();
  const { agent, projectId } = useAgentContext();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigation = useNavigation();
  const revalidator = useRevalidator();
  const cancelTaskFetcher = useFetcher<{
    success?: boolean;
    error?: string;
    task?: AgentTask;
    intent?: string;
  }>();

  const [stoppingTaskId, setStoppingTaskId] = useState<string | null>(null);

  const isLoading = navigation.state === "loading";
  const hasPrevious = skip > 0;

  const handleNext = () => {
    const newSkip = skip + 100; // Skip 100 tasks to get next 50 pairs
    const params = new URLSearchParams(searchParams);
    params.set("skip", newSkip.toString());
    setSearchParams(params);
  };

  const handlePrevious = () => {
    const newSkip = Math.max(0, skip - 100); // Skip back 100 tasks to get previous 50 pairs
    const params = new URLSearchParams(searchParams);
    params.set("skip", newSkip.toString());
    setSearchParams(params);
  };

  const handleStopTask = useCallback((taskId: string) => {
    setStoppingTaskId(taskId);
    const formData = new FormData();
    formData.set('intent', 'cancelTask');
    formData.set('taskId', taskId);
    cancelTaskFetcher.submit(formData, { method: 'post' });
  }, [cancelTaskFetcher]);

  // Handle cancel task fetcher response
  useEffect(() => {
    if (cancelTaskFetcher.state === 'idle' && cancelTaskFetcher.data) {
      if (cancelTaskFetcher.data.intent !== 'cancelTask') {
        return;
      }

      setStoppingTaskId(null);

      if (cancelTaskFetcher.data.success) {
        // Revalidate to refresh the task list
        revalidator.revalidate();
      } else if (cancelTaskFetcher.data.error) {
        console.error('Failed to cancel task:', cancelTaskFetcher.data.error);
      }
    }
  }, [cancelTaskFetcher.state, cancelTaskFetcher.data, revalidator]);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-transparent">
      {/* Header */}
      <div className="px-6 py-6">
        <div className="mx-auto w-full max-w-[1600px]">
          <div className="mb-6">
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
              Task Executions
            </h1>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              View and manage all task executions for {agent.name}
            </p>
          </div>

          {/* Table */}
          <ManageTable
            taskPairs={taskPairs}
            projectId={projectId}
            agentId={agent.id}
            totalExecutions={Math.floor(agent.task_count / 2)}
            hasMore={hasMore}
            hasPrevious={hasPrevious}
            onNext={handleNext}
            onPrevious={handlePrevious}
            isLoading={isLoading}
            onStopTask={handleStopTask}
            stoppingTaskId={stoppingTaskId}
          />
        </div>
      </div>
    </div>
  );
}
