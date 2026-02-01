import { useState, useEffect, useCallback } from "react";
import { useFetcher } from "@remix-run/react";
import type { PlaygroundInvocation } from "~/types/playground";
import type { AgentTask } from "~/services/chicory.server";

export interface UseInvocationPaginationOptions {
  agentId: string;
  projectId: string;
  initialInvocations?: {
    invocations: PlaygroundInvocation[];
    hasMore: boolean;
    skip: number;
  };
  initialTaskMap?: Record<string, AgentTask>;
}

export interface UseInvocationPaginationReturn {
  paginatedInvocations: PlaygroundInvocation[];
  currentTaskMap: Record<string, AgentTask>;
  hasMore: boolean;
  isLoadingMore: boolean;
  currentSkip: number;
  loadMore: () => void;
  reset: () => void;
}

export function useInvocationPagination({
  agentId,
  projectId,
  initialInvocations,
  initialTaskMap = {}
}: UseInvocationPaginationOptions): UseInvocationPaginationReturn {
  const fetcher = useFetcher();
  const [paginatedInvocations, setPaginatedInvocations] = useState<PlaygroundInvocation[]>([]);
  const [currentTaskMap, setCurrentTaskMap] = useState<Record<string, AgentTask>>(initialTaskMap);
  const [hasMore, setHasMore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [currentSkip, setCurrentSkip] = useState<number>(0);

  // Initialize invocations and task map on load
  useEffect(() => {
    if (initialInvocations) {
      setPaginatedInvocations(initialInvocations.invocations);
      setHasMore(initialInvocations.hasMore);
      setCurrentSkip(initialInvocations.skip);
    }
  }, [initialInvocations]);

  // Update task map when initial task map changes
  useEffect(() => {
    if (initialTaskMap) {
      setCurrentTaskMap(initialTaskMap);
    }
  }, [initialTaskMap]);

  // Handle fetcher data updates for pagination
  useEffect(() => {
    if (fetcher.data && fetcher.state === 'idle') {
      const data = fetcher.data as any;
      if (data.invocations && data.isLoadMore) {
        // Append to existing invocations for pagination
        setPaginatedInvocations(prev => [...prev, ...data.invocations.invocations]);
        setHasMore(data.invocations.hasMore);
        setCurrentSkip(data.invocations.skip);

        // Merge new task map with existing
        if (data.taskMap) {
          setCurrentTaskMap(prev => ({ ...prev, ...data.taskMap }));
        }
      }
      setIsLoadingMore(false);
    }
  }, [fetcher.data, fetcher.state]);

  const loadMore = useCallback(() => {
    if (!hasMore || isLoadingMore) return;
    setIsLoadingMore(true);
    fetcher.load(`/projects/${projectId}/agents/${agentId}/playground?skip=${currentSkip}`);
  }, [hasMore, isLoadingMore, currentSkip, agentId, projectId, fetcher]);

  const reset = useCallback(() => {
    setPaginatedInvocations([]);
    setCurrentTaskMap({});
    setHasMore(false);
    setIsLoadingMore(false);
    setCurrentSkip(0);
  }, []);

  return {
    paginatedInvocations,
    currentTaskMap,
    hasMore,
    isLoadingMore,
    currentSkip,
    loadMore,
    reset
  };
}
