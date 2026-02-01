import { ClockIcon, CheckCircleIcon, HandThumbUpIcon, HandThumbDownIcon, FunnelIcon, ChevronLeftIcon, ChevronRightIcon, PlusIcon, StopIcon, XCircleIcon } from "@heroicons/react/24/outline";
import { useState, useMemo } from "react";
import type { AgentTask } from "~/services/chicory.server";
import { TaskFeedbackModal } from "~/components/TaskFeedbackModal";
import { TaskDetailsModal } from "~/components/TaskDetailsModal";
import { AddTasksToEvaluationModal } from "~/components/evaluation/AddTasksToEvaluationModal";
import { formatLocalDateTime } from "~/utils/date";

export interface TaskPair {
  id: string;
  userTask: AgentTask;
  assistantTask: AgentTask;
  userQuery: string;
  response: string; // Raw response with markdown (for modal)
  responseStripped?: string; // Stripped response for table display
  timestamp: string;
  status: string;
  latency: number;
  agentId: string;
  playgroundName?: string;
  source?: string;
  feedback?: {
    rating?: 'positive' | 'negative';
    comment?: string;
  };
}

interface ManageTableProps {
  taskPairs: TaskPair[];
  projectId: string;
  agentId: string;
  totalExecutions: number;
  hasMore: boolean;
  hasPrevious: boolean;
  onNext: () => void;
  onPrevious: () => void;
  isLoading: boolean;
  onStopTask?: (taskId: string) => void;
  stoppingTaskId?: string | null;
}

function formatLatency(milliseconds: number): string {
  if (milliseconds < 1000) {
    return `${milliseconds.toFixed(0)}ms`;
  }
  return `${(milliseconds / 1000).toFixed(2)}s`;
}

function StatusBadge({ 
  status, 
  taskId, 
  onStop, 
  isStopping 
}: { 
  status: string; 
  taskId?: string;
  onStop?: (taskId: string) => void;
  isStopping?: boolean;
}) {
  const isCompleted = status === 'completed';
  const isProcessing = status === 'processing';
  const isCancelled = status === 'cancelled';
  const isError = status === 'error' || status === 'failed';

  // Determine badge styling based on status
  let badgeClasses = '';
  if (isCompleted) {
    badgeClasses = 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400';
  } else if (isCancelled) {
    badgeClasses = 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400';
  } else if (isError) {
    badgeClasses = 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400';
  } else if (isProcessing) {
    badgeClasses = 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400';
  } else {
    badgeClasses = 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400';
  }

  return (
    <div className="flex items-center gap-2">
      <div className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${badgeClasses}`}>
        {isCompleted ? (
          <CheckCircleIcon className="h-3.5 w-3.5" />
        ) : isCancelled ? (
          <XCircleIcon className="h-3.5 w-3.5" />
        ) : isError ? (
          <XCircleIcon className="h-3.5 w-3.5" />
        ) : isProcessing ? (
          <svg className="h-3.5 w-3.5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        ) : (
          <ClockIcon className="h-3.5 w-3.5" />
        )}
        <span className="capitalize">{status}</span>
      </div>
      {isProcessing && taskId && onStop && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onStop(taskId);
          }}
          disabled={isStopping}
          className="inline-flex items-center gap-1 rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white shadow-sm transition-colors hover:bg-red-500 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50"
          title="Stop this task"
        >
          <StopIcon className="h-3 w-3" />
          {isStopping ? 'Stopping...' : 'Stop'}
        </button>
      )}
    </div>
  );
}

function FeedbackCell({
  feedback,
  taskId,
  agentId,
  projectId
}: {
  feedback?: { rating?: 'positive' | 'negative'; comment?: string },
  taskId: string,
  agentId: string,
  projectId: string
}) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedRating, setSelectedRating] = useState<'positive' | 'negative'>('positive');

  const handleFeedbackClick = (rating: 'positive' | 'negative') => {
    setSelectedRating(rating);
    setIsModalOpen(true);
  };

  const handleFeedbackSubmitted = () => {
    // Reload the page to refresh the data
    window.location.reload();
  };

  if (feedback && (feedback.rating || feedback.comment)) {
    return (
      <>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsModalOpen(true)}
            className={`rounded p-1 transition-colors ${
              feedback.rating === 'positive'
                ? 'text-green-600 dark:text-green-400'
                : 'text-slate-300 dark:text-slate-600'
            }`}
            title={feedback.comment || 'View feedback'}
          >
            <HandThumbUpIcon className="h-4 w-4" />
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className={`rounded p-1 transition-colors ${
              feedback.rating === 'negative'
                ? 'text-red-600 dark:text-red-400'
                : 'text-slate-300 dark:text-slate-600'
            }`}
            title={feedback.comment || 'View feedback'}
          >
            <HandThumbDownIcon className="h-4 w-4" />
          </button>
        </div>
        <TaskFeedbackModal
          isOpen={isModalOpen}
          taskId={taskId}
          agentId={agentId}
          projectId={projectId}
          defaultRating={feedback.rating as 'positive' | 'negative' || 'positive'}
          onClose={() => setIsModalOpen(false)}
          existingFeedback={feedback}
          onSubmitted={handleFeedbackSubmitted}
        />
      </>
    );
  }

  return (
    <>
      <div className="flex items-center gap-2">
        <button
          onClick={() => handleFeedbackClick('positive')}
          className="rounded p-1 text-slate-300 hover:bg-slate-100 hover:text-green-600 dark:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-green-400 transition-colors"
          title="Positive feedback"
        >
          <HandThumbUpIcon className="h-4 w-4" />
        </button>
        <button
          onClick={() => handleFeedbackClick('negative')}
          className="rounded p-1 text-slate-300 hover:bg-slate-100 hover:text-red-600 dark:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-red-400 transition-colors"
          title="Negative feedback"
        >
          <HandThumbDownIcon className="h-4 w-4" />
        </button>
      </div>
      <TaskFeedbackModal
        isOpen={isModalOpen}
        taskId={taskId}
        agentId={agentId}
        projectId={projectId}
        defaultRating={selectedRating}
        onClose={() => setIsModalOpen(false)}
        onSubmitted={handleFeedbackSubmitted}
      />
    </>
  );
}

type FeedbackFilter = 'all' | 'rated' | 'positive' | 'negative';
type StatusFilter = 'all' | 'completed' | 'processing' | 'pending' | 'cancelled';
type SourceFilter = 'all' | 'Playground' | 'API' | 'MCP Gateway' | 'Workzone';

export function ManageTable({ taskPairs, projectId, agentId, totalExecutions, hasMore, hasPrevious, onNext, onPrevious, isLoading, onStopTask, stoppingTaskId }: ManageTableProps) {
  const [selectedTask, setSelectedTask] = useState<TaskPair | null>(null);

  // Selection state for adding to evaluation
  const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set());
  const [showAddToEvaluationModal, setShowAddToEvaluationModal] = useState(false);

  // No client-side pagination needed - all handled by server

  // Filter state
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [feedbackFilter, setFeedbackFilter] = useState<FeedbackFilter>('all');
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all');

  // Apply filters (client-side only - filters current page of 50 pairs)
  // TODO: Move to server-side filtering for better UX across all pages
  const filteredTaskPairs = useMemo(() => {
    return taskPairs.filter(pair => {
      // Status filter
      if (statusFilter !== 'all') {
        if (statusFilter === 'completed' && pair.status !== 'completed') return false;
        if (statusFilter === 'processing' && pair.status !== 'processing') return false;
        if (statusFilter === 'pending' && pair.status !== 'pending' && pair.status !== 'queued') return false;
        if (statusFilter === 'cancelled' && pair.status !== 'cancelled') return false;
      }

      // Feedback filter
      if (feedbackFilter === 'rated' && !pair.feedback?.rating) return false;
      if (feedbackFilter === 'positive' && pair.feedback?.rating !== 'positive') return false;
      if (feedbackFilter === 'negative' && pair.feedback?.rating !== 'negative') return false;

      // Source filter
      if (sourceFilter !== 'all' && pair.source !== sourceFilter) return false;

      return true;
    });
  }, [taskPairs, statusFilter, feedbackFilter, sourceFilter]);

  // Server-side pagination - show all filtered tasks (already limited to 50 by backend)
  const paginatedTaskPairs = filteredTaskPairs;

  // Selection helpers
  const toggleTaskSelection = (taskId: string) => {
    const newSelection = new Set(selectedTaskIds);
    if (newSelection.has(taskId)) {
      newSelection.delete(taskId);
    } else {
      newSelection.add(taskId);
    }
    setSelectedTaskIds(newSelection);
  };

  const toggleAllTasksSelection = () => {
    if (selectedTaskIds.size === paginatedTaskPairs.length) {
      // Deselect all
      setSelectedTaskIds(new Set());
    } else {
      // Select all on current page (50 tasks)
      const allIds = new Set(paginatedTaskPairs.map(pair => pair.id));
      setSelectedTaskIds(allIds);
    }
  };

  const getSelectedTasks = (): TaskPair[] => {
    return taskPairs.filter(pair => selectedTaskIds.has(pair.id));
  };

  // Calculate metrics from current page only
  // NOTE: These metrics reflect only the current page's data (50 pairs), not total agent performance
  // TODO: Calculate these metrics on the backend for accurate total statistics across all tasks
  const averageLatency = taskPairs.length > 0
    ? taskPairs.reduce((sum, pair) => sum + pair.latency, 0) / taskPairs.length
    : 0;

  const feedbackStats = taskPairs.reduce(
    (stats, pair) => {
      if (pair.feedback?.rating === 'positive') {
        stats.positive++;
        stats.total++;
      } else if (pair.feedback?.rating === 'negative') {
        stats.total++;
      }
      return stats;
    },
    { positive: 0, total: 0 }
  );

  const acceptanceRate = feedbackStats.total > 0
    ? (feedbackStats.positive / feedbackStats.total) * 100
    : 0;

  if (taskPairs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-sm text-gray-500 dark:text-gray-400">No task executions found</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Metrics Bar */}
      <div className="flex items-center gap-6 rounded-xl border border-slate-200 bg-white px-6 py-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
            <CheckCircleIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Total Executions
            </div>
            <div className="font-mono text-lg font-semibold text-slate-900 dark:text-slate-100">
              {totalExecutions}
            </div>
          </div>
        </div>

        <div className="h-10 w-px bg-slate-200 dark:bg-slate-700" />

        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900/30">
            <ClockIcon className="h-5 w-5 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Avg Latency
            </div>
            <div className="font-mono text-lg font-semibold text-slate-900 dark:text-slate-100">
              {formatLatency(averageLatency)}
            </div>
          </div>
        </div>

        <div className="h-10 w-px bg-slate-200 dark:bg-slate-700" />

        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
            <CheckCircleIcon className="h-5 w-5 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Acceptance Rate
            </div>
            <div className="font-mono text-lg font-semibold text-slate-900 dark:text-slate-100">
              {feedbackStats.total > 0 ? `${acceptanceRate.toFixed(1)}%` : 'N/A'}
              <span className="ml-2 text-xs font-normal text-slate-500 dark:text-slate-400">
                ({feedbackStats.positive}/{feedbackStats.total})
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col gap-4 rounded-xl bg-white px-4 py-4 shadow-sm dark:bg-slate-900 md:flex-row md:items-center md:justify-between">
        {/* Add to Evaluation Button */}
        <button
          onClick={() => setShowAddToEvaluationModal(true)}
          disabled={selectedTaskIds.size === 0}
          className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-purple-600"
        >
          <PlusIcon className="h-4 w-4" />
          {selectedTaskIds.size > 0 ? `Add ${selectedTaskIds.size} to Evaluation` : 'Add to Evaluation'}
        </button>

        <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-4">
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-5 w-5 text-slate-400" />
            <span className="text-sm font-ui font-medium text-slate-700 dark:text-slate-300">Filters:</span>
          </div>
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <label htmlFor="status-filter" className="text-sm font-ui font-medium text-slate-600 dark:text-slate-400">
              Status:
            </label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-ui text-slate-900 transition-colors focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-400/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="all">All</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="pending">Pending</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          {/* Feedback Filter */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-ui font-medium text-slate-600 dark:text-slate-400">Feedback:</span>
            <div className="flex gap-1">
              <button
                onClick={() => setFeedbackFilter('all')}
                className={`rounded-lg px-3 py-1.5 text-sm font-ui font-medium transition-colors ${
                  feedbackFilter === 'all'
                    ? 'bg-purple-400 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFeedbackFilter('rated')}
                className={`rounded-lg px-3 py-1.5 text-sm font-ui font-medium transition-colors ${
                  feedbackFilter === 'rated'
                    ? 'bg-purple-400 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600'
                }`}
              >
                Rated
              </button>
              <button
                onClick={() => setFeedbackFilter('positive')}
                className={`rounded-lg px-3 py-1.5 text-sm font-ui font-medium transition-colors ${
                  feedbackFilter === 'positive'
                    ? 'bg-green-500 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600'
                }`}
              >
                Positive
              </button>
              <button
                onClick={() => setFeedbackFilter('negative')}
                className={`rounded-lg px-3 py-1.5 text-sm font-ui font-medium transition-colors ${
                  feedbackFilter === 'negative'
                    ? 'bg-red-500 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600'
                }`}
              >
                Negative
              </button>
            </div>
          </div>

          {/* Source Filter */}
          <div className="flex items-center gap-2">
            <label htmlFor="source-filter" className="text-sm font-ui font-medium text-slate-600 dark:text-slate-400">
              Source:
            </label>
            <select
              id="source-filter"
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value as SourceFilter)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-ui text-slate-900 transition-colors focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-400/20 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="all">All</option>
              <option value="Playground">Playground</option>
              <option value="API">API</option>
              <option value="MCP Gateway">MCP Gateway</option>
              <option value="Workzone">Workzone</option>
            </select>
          </div>

          {/* Clear Filters */}
          {(statusFilter !== 'all' || feedbackFilter !== 'all' || sourceFilter !== 'all') && (
            <button
              onClick={() => {
                setStatusFilter('all');
                setFeedbackFilter('all');
                setSourceFilter('all');
              }}
              className="text-sm font-ui font-medium text-purple-600 hover:text-purple-700 dark:text-purple-400 dark:hover:text-purple-300"
            >
              Clear Filters
            </button>
          )}
        </div>
      </div>

      {/* Table with Vertical Scrolling */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="max-h-[calc(100vh-28rem)] overflow-y-auto">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
            <thead className="sticky top-0 z-10 bg-slate-50 shadow-sm dark:bg-slate-800/50">
            <tr>
              <th className="px-4 py-3 text-left">
                <input
                  type="checkbox"
                  checked={paginatedTaskPairs.length > 0 && selectedTaskIds.size === paginatedTaskPairs.length}
                  onChange={toggleAllTasksSelection}
                  className="h-4 w-4 rounded border-gray-300 bg-white text-purple-600 focus:ring-purple-500 dark:border-slate-600 dark:bg-slate-800 accent-purple-600 dark:accent-purple-400"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600 dark:text-slate-300">
                ID
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600 dark:text-slate-300">
                User Query
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600 dark:text-slate-300">
                Response
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600 dark:text-slate-300">
                Timestamp
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600 dark:text-slate-300">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600 dark:text-slate-300">
                Latency
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600 dark:text-slate-300">
                Source
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600 dark:text-slate-300">
                Feedback
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-700 dark:bg-slate-900">
            {paginatedTaskPairs.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-sm text-slate-500 dark:text-slate-400">
                  No results found with current filters
                </td>
              </tr>
            ) : (
              paginatedTaskPairs.map((pair) => (
              <tr
                key={pair.id}
                className="group transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50"
              >
                <td className="whitespace-nowrap px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedTaskIds.has(pair.id)}
                    onChange={() => toggleTaskSelection(pair.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="h-4 w-4 rounded border-gray-300 bg-white text-purple-600 focus:ring-purple-500 dark:border-slate-600 dark:bg-slate-800 accent-purple-600 dark:accent-purple-400"
                  />
                </td>
                <td className="whitespace-nowrap px-4 py-3">
                  <button
                    onClick={() => setSelectedTask(pair)}
                    className="font-mono text-xs text-purple-600 hover:text-purple-700 dark:text-purple-400 dark:hover:text-purple-300 hover:underline"
                    title={pair.id}
                  >
                    {pair.id.substring(0, 8)}...
                  </button>
                </td>
                <td className="max-w-md px-4 py-3">
                  <div
                    className="truncate text-sm text-slate-900 dark:text-slate-100"
                    title={pair.userQuery}
                  >
                    {pair.userQuery}
                  </div>
                </td>
                <td className="max-w-xs px-4 py-3">
                  <div
                    className="truncate text-sm text-slate-600 dark:text-slate-400"
                    title={pair.responseStripped || pair.response}
                  >
                    {pair.responseStripped || pair.response}
                  </div>
                </td>
                <td className="whitespace-nowrap px-4 py-3">
                  <div className="text-sm text-slate-600 dark:text-slate-400">
                    {formatLocalDateTime(pair.timestamp)}
                  </div>
                </td>
                <td className="whitespace-nowrap px-4 py-3">
                  <StatusBadge 
                    status={pair.status} 
                    taskId={pair.assistantTask.id}
                    onStop={onStopTask}
                    isStopping={stoppingTaskId === pair.assistantTask.id}
                  />
                </td>
                <td className="whitespace-nowrap px-4 py-3">
                  <div className="font-mono text-sm text-slate-900 dark:text-slate-100">
                    {formatLatency(pair.latency)}
                  </div>
                </td>
                <td className="whitespace-nowrap px-4 py-3">
                  <div className="text-sm text-slate-600 dark:text-slate-400">
                    {pair.source || '-'}
                  </div>
                </td>
                <td className="whitespace-nowrap px-4 py-3">
                  <FeedbackCell
                    feedback={pair.feedback}
                    taskId={pair.id}
                    agentId={agentId}
                    projectId={projectId}
                  />
                </td>
              </tr>
              ))
            )}
          </tbody>
        </table>
        </div>

        {/* Pagination Controls */}
        {filteredTaskPairs.length > 0 && (
          <div className="flex border-t border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/50">
            <div className="flex w-full items-center justify-end">
              <div className="flex gap-2">
                <button
                  onClick={onPrevious}
                  disabled={!hasPrevious || isLoading}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-ui font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                  aria-label="Previous page"
                >
                  <ChevronLeftIcon className="h-4 w-4" />
                  Previous
                </button>
                <button
                  onClick={onNext}
                  disabled={!hasMore || isLoading}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-ui font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                  aria-label="Next page"
                >
                  {isLoading ? 'Loading...' : 'Next'}
                  <ChevronRightIcon className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Task Details Modal */}
      {selectedTask && (
        <TaskDetailsModal
          isOpen={!!selectedTask}
          onClose={() => setSelectedTask(null)}
          taskPair={selectedTask}
        />
      )}

      {/* Add to Evaluation Modal */}
      <AddTasksToEvaluationModal
        isOpen={showAddToEvaluationModal}
        onClose={() => setShowAddToEvaluationModal(false)}
        selectedTasks={getSelectedTasks()}
        projectId={projectId}
        agentId={agentId}
      />
    </div>
  );
}
