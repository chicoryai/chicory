import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { StreamingMessage } from "~/components/StreamingMessage";
import { TaskMessageItem } from "~/components/TaskMessageItem";
import { streamEventBus } from "~/utils/streaming/eventBus";
import { StreamEventType } from "~/utils/streaming/eventTypes";
import type { AgentTask } from "~/services/chicory.server";
import type { InvocationHistoryProps } from "./InvocationHistory.types";

// Helper to create tasks from invocation and task map
function invocationToTasks(
  invocation: import("~/types/playground").PlaygroundInvocation,
  taskMap: Record<string, AgentTask>
): AgentTask[] {
  const tasks: AgentTask[] = [];

  // Add assistant task first if it exists
  if (invocation.assistant_task_id) {
    const assistantTask = taskMap[invocation.assistant_task_id];
    if (assistantTask) {
      tasks.push(assistantTask);
    }
  }

  // Add user task second
  const userTask = taskMap[invocation.user_task_id];
  if (userTask) {
    tasks.push(userTask);
  }

  return tasks;
}

const useIsomorphicLayoutEffect = typeof window !== "undefined" ? useLayoutEffect : useEffect;

export function InvocationHistory({
  paginatedInvocations,
  currentTaskMap,
  overrideTasks,
  currentStreamTaskId,
  isStreaming,
  user,
  agentId,
  hasMore,
  isLoadingMore,
  onLoadMore,
  taskListRef,
  composerHeight,
  onShowFeedbackPanel
}: InvocationHistoryProps) {
  const [streamingTasks, setStreamingTasks] = useState<Set<string>>(new Set());
  const [hasPinnedScroll, setHasPinnedScroll] = useState(false);
  const [pinnedTaskId, setPinnedTaskId] = useState<string | null>(null);
  const [pinnedTaskRole, setPinnedTaskRole] = useState<'user' | 'assistant' | null>(null);
  const [containerHeight, setContainerHeight] = useState(0);

  useEffect(() => {
    if (!taskListRef.current) {
      return;
    }

    const element = taskListRef.current;

    const updateHeight = () => {
      const nextHeight = element.clientHeight;
      setContainerHeight(prev => (Math.abs(prev - nextHeight) > 1 ? nextHeight : prev));
    };

    updateHeight();

    const resizeObserver = new ResizeObserver(updateHeight);
    resizeObserver.observe(element);

    return () => resizeObserver.disconnect();
  }, [taskListRef]);

  useEffect(() => {
    // Subscribe to stream events to track which tasks are streaming
    const unsubscribers = [
      streamEventBus.subscribe(StreamEventType.STREAM_START, ({ taskId, agentId: streamAgentId }) => {
        if (streamAgentId !== agentId) {
          return;
        }
        setStreamingTasks(prev => new Set(prev).add(taskId));
      }),
      streamEventBus.subscribe(StreamEventType.STREAM_END, ({ taskId, agentId: streamAgentId }) => {
        if (streamAgentId !== agentId) {
          return;
        }
        setStreamingTasks(prev => {
          const next = new Set(prev);
          next.delete(taskId);
          return next;
        });
      }),
      streamEventBus.subscribe(StreamEventType.STREAM_ERROR, ({ taskId, agentId: streamAgentId }) => {
        if (streamAgentId !== agentId) {
          return;
        }
        setStreamingTasks(prev => {
          const next = new Set(prev);
          next.delete(taskId);
          return next;
        });
      }),
      streamEventBus.subscribe(StreamEventType.TASK_TIMEOUT, ({ taskId }) => {
        setStreamingTasks(prev => {
          const next = new Set(prev);
          next.delete(taskId);
          return next;
        });
      })
    ];

    return () => {
      unsubscribers.forEach(unsub => unsub());
    };
  }, [agentId]);

  // Convert invocations to tasks for display
  const displayTasksDescending: AgentTask[] = useMemo(() => {
    const tasks: AgentTask[] = [];

    if (overrideTasks && overrideTasks.length > 0) {
      tasks.push(...overrideTasks);
    } else {
      paginatedInvocations.forEach(invocation => {
        const invocationTasks = invocationToTasks(invocation, currentTaskMap);
        tasks.push(...invocationTasks);
      });
    }

    return tasks;
  }, [overrideTasks, paginatedInvocations, currentTaskMap]);

  const displayTasks: AgentTask[] = useMemo(
    () => [...displayTasksDescending].reverse(),
    [displayTasksDescending]
  );

  const latestUserTask = useMemo(() => {
    for (let index = displayTasks.length - 1; index >= 0; index -= 1) {
      if (displayTasks[index]?.role === 'user') {
        return displayTasks[index];
      }
    }
    return null;
  }, [displayTasks]);

  const isInitialPin = useRef(true);

  useEffect(() => {
    if (!latestUserTask) {
      if (pinnedTaskId || pinnedTaskRole) {
        setPinnedTaskId(null);
        setPinnedTaskRole(null);
        setHasPinnedScroll(false);
      }
      return;
    }

    if (isInitialPin.current) {
      isInitialPin.current = false;
      if (pinnedTaskId !== latestUserTask.id) {
        setPinnedTaskId(latestUserTask.id);
        setPinnedTaskRole('user');
      }
      return;
    }

    if (pinnedTaskId !== latestUserTask.id) {
      setPinnedTaskId(latestUserTask.id);
      setPinnedTaskRole('user');
      setHasPinnedScroll(false);
    }
  }, [displayTasks.length, latestUserTask, pinnedTaskId, pinnedTaskRole]);

  const hasActiveStream = isStreaming || streamingTasks.size > 0;

  const trailingSpacerHeight = useMemo(() => {
    const base = (composerHeight ?? 0) + 24;
    return hasActiveStream ? Math.max(base, containerHeight) : base;
  }, [composerHeight, containerHeight, hasActiveStream]);

  const hasPerformedInitialScroll = useRef(false);

  useIsomorphicLayoutEffect(() => {
    if (!taskListRef.current || !pinnedTaskId || hasPinnedScroll) {
      return;
    }

    const container = taskListRef.current;
    const target = container.querySelector<HTMLElement>(`[data-task-id="${pinnedTaskId}"]`);

    if (target) {
      const styles = getComputedStyle(container);
      const paddingTop = parseFloat(styles.paddingTop || "0");
      const containerRect = container.getBoundingClientRect();
      const targetRect = target.getBoundingClientRect();
      const relativeOffset = targetRect.top - containerRect.top + container.scrollTop;
      const maxScrollTop = Math.max(container.scrollHeight - container.clientHeight, 0);
      const desiredScrollTop = Math.min(Math.max(relativeOffset - paddingTop, 0), maxScrollTop);

      const prefersReducedMotion = (() => {
        if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
          return false;
        }
        try {
          return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        } catch {
          return false;
        }
      })();

      const behavior: ScrollBehavior = !hasPerformedInitialScroll.current || prefersReducedMotion ? 'auto' : 'smooth';

      const previousBehavior = container.style.scrollBehavior;
      container.style.scrollBehavior = behavior;
      container.scrollTo({ top: desiredScrollTop, behavior });
      container.style.scrollBehavior = previousBehavior;

      hasPerformedInitialScroll.current = true;

      setHasPinnedScroll(true);
    }
  }, [pinnedTaskId, hasPinnedScroll, taskListRef]);

  return (
    <div ref={taskListRef} className="audit-trail-scroll flex-1 px-4 py-4 scroll-smooth">
      {/* Load more button */}
      {hasMore && (
        <div className="text-center py-4">
          <button
            onClick={onLoadMore}
            disabled={isLoadingMore}
            className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white disabled:opacity-50"
          >
            {isLoadingMore ? "Loading..." : "Load older messages"}
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="mx-auto flex w-full max-w-3xl flex-col space-y-4">
        {displayTasks.map(task => {
          const isTaskStreaming = streamingTasks.has(task.id) || (task.id === currentStreamTaskId && isStreaming);
          const hasVisibleContent = Boolean(task.content?.trim().length) || Boolean(task.response?.trim().length);
          const needsStreamingSpacer = task.role === 'assistant' && isTaskStreaming && !hasVisibleContent;
          const spacerClass = needsStreamingSpacer ? 'min-h-[60vh]' : null;

          return (
            <div key={task.id} data-task-id={task.id}>
              {/* Use StreamingMessage for assistant tasks that might stream */}
              {task.role === 'assistant' ? (
                <StreamingMessage
                  taskId={task.id}
                  initialContent={task.content || ''}
                  initialRole="assistant"
                  user={user.firstName || user.email}
                  metadata={task.metadata}
                  agentId={agentId}
                  onShowFeedbackPanel={onShowFeedbackPanel}
                />
              ) : (
                <TaskMessageItem
                  task={task}
                  user={user.firstName || user.email}
                  isStreaming={false}
                  toolUse={null}
                  agentId={agentId}
                  onShowFeedbackPanel={onShowFeedbackPanel}
                />
              )}
              {spacerClass && (
                <div className={`w-full ${spacerClass}`} aria-hidden="true" />
              )}
            </div>
          );
        })}
        <div aria-hidden="true" style={{ minHeight: trailingSpacerHeight }} />
      </div>
    </div>
  );
}
