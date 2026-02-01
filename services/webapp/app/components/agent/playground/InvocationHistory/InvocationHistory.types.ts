import type { AgentTask } from "~/services/chicory.server";
import type { PlaygroundInvocation } from "~/types/playground";
import type { TaskFeedbackEntry } from "~/components/TaskFeedbackModal";

export interface InvocationHistoryProps {
  paginatedInvocations: PlaygroundInvocation[];
  currentTaskMap: Record<string, AgentTask>;
  overrideTasks?: AgentTask[];
  currentStreamTaskId: string | null;
  isStreaming: boolean;
  user: {
    firstName?: string | null;
    email: string | null;
  };
  agentId: string;
  hasMore: boolean;
  isLoadingMore: boolean;
  onLoadMore: () => void;
  taskListRef: React.RefObject<HTMLDivElement>;
  composerHeight?: number;
  onShowFeedbackPanel?: (options: {
    taskId: string;
    agentId: string;
    taskLabel?: string;
    anchorRect: DOMRect;
    existingFeedback?: TaskFeedbackEntry | null;
    defaultRating: 'positive' | 'negative';
  }) => void;
}

export interface DisplayTask extends AgentTask {
  isStreamingTask?: boolean;
}
