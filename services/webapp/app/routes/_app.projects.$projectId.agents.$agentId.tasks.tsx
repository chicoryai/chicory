import { json, redirect } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { useFetcher, useLoaderData } from "@remix-run/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { clsx } from "clsx";
import { getUserOrgDetails } from "~/auth/auth.server";
import { getAgentTasks, type AgentTask } from "~/services/chicory.server";
import { InvocationHistory } from "~/components/agent/playground/InvocationHistory";
import { AuditTrailPanel } from "~/components/panels/AuditTrailPanel";
import TaskFeedbackModal, { type TaskFeedbackEntry } from "~/components/TaskFeedbackModal";
import { useAgentContext } from "./_app.projects.$projectId.agents.$agentId";
import type { TrailItem } from "~/types/auditTrail";
import { ClipboardDocumentListIcon } from "@heroicons/react/24/outline";

type LoaderData = {
  tasks: AgentTask[];
  hasMore: boolean;
  nextSkip: number;
  isLoadMore: boolean;
};

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
  const limit = 50;

  const taskResult = await getAgentTasks(projectId, agentId, limit, "desc", undefined, skip);
  const tasks = taskResult.tasks ?? [];
  const hasMore = Boolean(taskResult.has_more);
  const nextSkip = skip + tasks.length;

  return json<LoaderData>({
    tasks,
    hasMore,
    nextSkip,
    isLoadMore: skip > 0
  });
}

type AuditPanelState = {
  taskId: string;
  s3Url?: string;
  s3Bucket?: string | null;
  s3Key?: string | null;
  agentTrail?: TrailItem[];
};

type FeedbackModalState = {
  taskId: string;
  agentId: string;
  taskLabel?: string;
  existingFeedback?: TaskFeedbackEntry | null;
  defaultRating: 'positive' | 'negative';
};

export default function AgentTasksView() {
  const initialData = useLoaderData<typeof loader>();
  const { agent, user, projectId } = useAgentContext();

  const [tasks, setTasks] = useState<AgentTask[]>(() => initialData.tasks);
  const [hasMore, setHasMore] = useState<boolean>(initialData.hasMore);
  const [nextSkip, setNextSkip] = useState<number>(initialData.nextSkip);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [auditPanelState, setAuditPanelState] = useState<AuditPanelState | null>(null);
  const [feedbackModalState, setFeedbackModalState] = useState<FeedbackModalState | null>(null);

  const taskListRef = useRef<HTMLDivElement>(null);
  const fetcher = useFetcher<typeof loader>();
  const auditTrailFetcher = useFetcher();

  useEffect(() => {
    setTasks(initialData.tasks);
    setHasMore(initialData.hasMore);
    setNextSkip(initialData.nextSkip);
  }, [initialData.tasks, initialData.hasMore, initialData.nextSkip]);

  useEffect(() => {
    if (fetcher.state === "idle") {
      setIsLoadingMore(false);
      const data = fetcher.data as LoaderData | undefined;

      if (data && data.isLoadMore) {
        setTasks(prev => [...prev, ...data.tasks]);
        setHasMore(data.hasMore);
        setNextSkip(data.nextSkip);
      } else if (data && !data.isLoadMore) {
        setTasks(data.tasks);
        setHasMore(data.hasMore);
        setNextSkip(data.nextSkip);
      }
    }
  }, [fetcher.state, fetcher.data]);

  const loadMore = useCallback(() => {
    if (!hasMore || isLoadingMore) {
      return;
    }
    setIsLoadingMore(true);
    fetcher.load(`/projects/${projectId}/agents/${agent.id}/tasks?skip=${nextSkip}`);
  }, [agent.id, fetcher, hasMore, isLoadingMore, nextSkip, projectId]);

  const taskMap = useMemo<Record<string, AgentTask>>(() => {
    return tasks.reduce<Record<string, AgentTask>>((acc, task) => {
      acc[task.id] = task;
      return acc;
    }, {});
  }, [tasks]);

  const assistantTaskCount = useMemo(() => {
    return tasks.reduce((count, task) => (task.role === 'assistant' ? count + 1 : count), 0);
  }, [tasks]);

  const taskSectionHeader = (
    <div className="px-4 pt-6">
      <div className="mx-auto flex w-full max-w-3xl flex-wrap items-center gap-3">
        <h2 className="truncate text-lg font-semibold text-gray-900 dark:text-white" title={agent.name}>
          {agent.name}
        </h2>
        <div className="inline-flex items-center gap-2 rounded-xl border border-purple-200/70 bg-white/80 px-3 py-1 text-sm font-semibold text-purple-600 shadow-sm shadow-whitePurple-50/60 backdrop-blur dark:border-purple-500/40 dark:bg-purple-900/40 dark:text-purple-200">
          <ClipboardDocumentListIcon className="h-4 w-4" />
          <span>Tasks</span>
          <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-bold text-purple-700 dark:bg-purple-950/80 dark:text-purple-200">
            {assistantTaskCount}
          </span>
        </div>
      </div>
    </div>
  );

  const handleShowAuditTrailPanel = useCallback((options: AuditPanelState) => {
    setAuditPanelState(options);
    setFeedbackModalState(null);

    const params = new URLSearchParams();
    if (options.s3Bucket) params.set("bucket", options.s3Bucket);
    if (options.s3Key) params.set("key", options.s3Key);
    if (options.s3Url && !params.get("url")) params.set("url", options.s3Url);

    const url = params.toString()
      ? `/api/audit-trail/${options.taskId}?${params.toString()}`
      : `/api/audit-trail/${options.taskId}`;

    auditTrailFetcher.load(url);
  }, [auditTrailFetcher]);

  const handleClosePanel = useCallback(() => {
    setAuditPanelState(null);
  }, []);

  const handleCloseFeedbackModal = useCallback(() => {
    setFeedbackModalState(null);
  }, []);

  const handleFeedbackSubmitted = useCallback((entry: TaskFeedbackEntry) => {
    if (feedbackModalState) {
      const targetTaskId = feedbackModalState.taskId;
      setTasks(prev =>
        prev.map(task => {
          if (task.id !== targetTaskId) {
            return task;
          }
          const nextMetadata = {
            ...(typeof task.metadata === 'object' && task.metadata !== null ? task.metadata : {}),
            feedback: [entry]
          };
          return {
            ...task,
            metadata: nextMetadata
          };
        })
      );
    }
    setFeedbackModalState(null);
  }, [feedbackModalState]);

  const handleShowFeedbackPanel = useCallback((options: FeedbackModalState & { anchorRect: DOMRect }) => {
    setAuditPanelState(null);
    setFeedbackModalState({
      taskId: options.taskId,
      agentId: options.agentId,
      taskLabel: options.taskLabel,
      existingFeedback: options.existingFeedback,
      defaultRating: options.defaultRating
    });
  }, []);

  const historicalTrail = useMemo<TrailItem[]>(() => {
    const data = auditTrailFetcher.data as { trail?: TrailItem[] } | undefined;
    if (Array.isArray(data?.trail)) {
      return data.trail as TrailItem[];
    }
    return [];
  }, [auditTrailFetcher.data]);

  const combinedAuditTrail = useMemo<TrailItem[]>(() => {
    return [
      ...historicalTrail,
      ...(auditPanelState?.agentTrail ?? [])
    ];
  }, [historicalTrail, auditPanelState]);

  const auditTrailError = (auditTrailFetcher.data as { error?: string } | undefined)?.error;
  const isAuditTrailLoading = auditTrailFetcher.state !== "idle";

  const isAuditPanelOpen = auditPanelState !== null;
  const mainFlexBasis = isAuditPanelOpen ? "66%" : "100%";
  const panelFlexBasis = "34%";
  const panelMaxWidth = 560;
  const panelMinWidth = 420;
  const hasTasks = tasks.length > 0;

  return (
    <div className="relative z-0 flex flex-1 overflow-hidden bg-transparent">
      <div
        className={clsx(
          "flex h-full min-w-0 flex-col overflow-hidden transition-[flex-basis] duration-300 ease-in-out",
          isAuditPanelOpen ? "flex-none" : "flex-1"
        )}
        style={{ flexBasis: mainFlexBasis }}
      >
        {hasTasks ? (
          <div className="relative z-10 flex flex-1 flex-col overflow-hidden">
            {taskSectionHeader}
            <InvocationHistory
              paginatedInvocations={[]}
              currentTaskMap={taskMap}
              overrideTasks={tasks}
              currentStreamTaskId={null}
              isStreaming={false}
              user={user}
              agentId={agent.id}
              hasMore={hasMore}
              isLoadingMore={isLoadingMore}
              onLoadMore={loadMore}
              taskListRef={taskListRef}
              onShowFeedbackPanel={handleShowFeedbackPanel}
            />
          </div>
        ) : (
          <div className="relative z-10 flex flex-1 flex-col overflow-hidden">
            {taskSectionHeader}
            <div className="flex flex-1 items-center justify-center">
              <p className="text-sm text-gray-500 dark:text-gray-400">No tasks yet for this agent.</p>
            </div>
          </div>
        )}
      </div>

      <AnimatePresence initial={false}>
        {isAuditPanelOpen && (
          <motion.aside
            key={`audit-${auditPanelState?.taskId ?? 'panel'}`}
            initial={{ x: "100%", opacity: 0 }}
            animate={{ x: "0%", opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="relative z-30 flex h-full flex-col overflow-hidden rounded-3xl bg-transparent px-6 py-6 dark:bg-gray-900"
            style={{
              flexBasis: panelFlexBasis,
              maxWidth: `${panelMaxWidth}px`,
              minWidth: `${panelMinWidth}px`,
              maxHeight: "calc(100vh - 64px)",
              width: "90%",
              marginLeft: "auto",
              marginRight: "auto"
            }}
          >
            {auditPanelState ? (
              <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-md shadow-purple-900/30 dark:border-slate-800 dark:bg-slate-900">
                <div className="flex-1 overflow-hidden rounded-xl bg-white shadow-inner dark:bg-slate-950/70">
                  <AuditTrailPanel
                    auditTrail={combinedAuditTrail}
                    onClose={handleClosePanel}
                    isStreaming={isAuditTrailLoading}
                  />
                </div>
                {auditTrailError && (
                  <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300">
                    {auditTrailError}
                  </div>
                )}
              </div>
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
