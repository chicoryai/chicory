import { useCallback, useMemo, useRef } from 'react';
import { AgentTask } from '~/services/chicory.server';
import { twMerge } from 'tailwind-merge';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import MarkdownRenderer from './MarkdownRenderer';
import ToolUse from './ToolUse';
import AuditTrailPanelButton from './AuditTrailPanelButton';
import TaskFeedbackButtons from './TaskFeedbackButtons';
import type { TaskFeedbackEntry } from './TaskFeedbackModal';
import type { TrailItem } from '~/types/auditTrail';

export interface TaskMessageItemProps {
  task: AgentTask;
  user: string | null;
  isStreaming?: boolean;
  toolUse?: { name: string; input: any; id: string } | null;
  agentTrail?: TrailItem[];
  agentId: string;
  onShowFeedbackPanel?: (options: {
    taskId: string;
    agentId: string;
    taskLabel?: string;
    anchorRect: DOMRect;
    existingFeedback?: TaskFeedbackEntry | null;
    defaultRating: 'positive' | 'negative';
  }) => void;
}

/**
 * Component for displaying a single agent task with formatted timestamp and markdown support
 */
export function TaskMessageItem({ task, user, isStreaming, toolUse, agentTrail, agentId, onShowFeedbackPanel }: TaskMessageItemProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Format the date in a more readable format
  const formatDate = (dateString: string) => {
    const normalized = /z$/i.test(dateString) ? dateString : `${dateString}Z`;
    const date = new Date(normalized);
    return date.toLocaleString('en-US', {
      month: 'numeric',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

   // Check if the message is from the user
   const isUserMessage = task.role === 'user';
   const isAssistantMessage = task.role === 'assistant';
   const isFailedTask = task.status === 'failed';
   
   
  // Get the first initial for user avatar (default to 'U' if no name is available)
  const getInitial = () => {
    // Try to get name from user or use "User" as default
    const name = user || "User";
    return name.charAt(0).toUpperCase();
  };

  // Get the content to display (let MarkdownRenderer handle processing for assistant messages)
  const contentToDisplay = task.content || task.response || '';
  const metadata = task.metadata as Record<string, unknown> | undefined;
  const auditTrailUrl = typeof metadata?.audit_trail === 'string'
    ? metadata.audit_trail
    : typeof (metadata as any)?.s3_url === 'string'
      ? (metadata as any)?.s3_url
      : undefined;
  const s3Bucket = typeof (metadata as any)?.s3_bucket === 'string' ? (metadata as any)?.s3_bucket : null;
  const s3Key = typeof (metadata as any)?.s3_key === 'string' ? (metadata as any)?.s3_key : null;
  const derivedAgentTrail = agentTrail ?? (Array.isArray((metadata as any)?.agent_trail) ? (metadata as any)?.agent_trail as TrailItem[] : undefined);
  const effectiveAgentId = task.agent_id || agentId;
  const feedbackEntry: TaskFeedbackEntry | null = Array.isArray((metadata as any)?.feedback)
    ? ((metadata as any)?.feedback as TaskFeedbackEntry[])[0] ?? null
    : null;

  const taskSummary = useMemo(() => {
    const rawResponse = typeof task.response === 'string' ? task.response : null;
    const rawContent = typeof task.content === 'string' ? task.content : null;
    const rawName = typeof task.name === 'string' ? task.name : null;
    const source = rawResponse?.trim() || rawContent?.trim() || rawName?.trim() || '';
    const normalized = source.replace(/\s+/g, ' ').trim();
    if (!normalized) {
      return undefined;
    }
    return normalized.length > 120 ? `${normalized.slice(0, 117)}…` : normalized;
  }, [task.content, task.name, task.response]);

  const handleFeedbackSelect = useCallback((selected: 'positive' | 'negative') => {
    if (!onShowFeedbackPanel) {
      return;
    }
    const anchorRect = containerRef.current?.getBoundingClientRect();
    if (!anchorRect) {
      return;
    }
    onShowFeedbackPanel({
      taskId: task.id,
      agentId: effectiveAgentId,
      taskLabel: taskSummary,
      anchorRect,
      existingFeedback: feedbackEntry,
      defaultRating: selected
    });
  }, [effectiveAgentId, feedbackEntry, onShowFeedbackPanel, task.id, taskSummary]);

  // Check if content is a status message from SSE (JSON with just a status field)
  const isStatusMessage = (() => {
    try {
      const parsed = JSON.parse(contentToDisplay.trim());
      return parsed && typeof parsed === 'object' && 'status' in parsed && Object.keys(parsed).length === 1;
    } catch {
      return false;
    }
  })();
  
  // Don't render status messages - let GenerationStatus component handle them
  if (isStatusMessage) {
    return null;
  }

  const timestampSource = task.completed_at || task.updated_at || task.created_at;
  const timestamp = timestampSource ? formatDate(timestampSource) : null;

  return (
      <div ref={containerRef} className={twMerge(
        // Ensure max width matches input area (max-w-3xl + center + min-w-0)
        "relative z-0 mb-4 flex w-full justify-center rounded-lg p-4 overflow-visible",
        isUserMessage ? "border border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20" : ""
      )}>
        {/* Gradient backgrounds for user messages */}
        {isUserMessage && (
          <>
            {/* Light mode gradient */}
            <div 
              className="absolute inset-0 dark:hidden pointer-events-none"
              style={{
                background: 'radial-gradient(circle at center, rgba(255, 255, 255, 0.9) 95%, rgba(245, 243, 255, 0.6) 100%)',
              }}
            />
            {/* Dark mode gradient */}
            <div 
              className="absolute inset-0 hidden dark:block pointer-events-none"
              style={{
                background: 'radial-gradient(circle at center, rgba(17, 24, 39, 0.9) 95%, rgba(88, 28, 135, 0.2) 100%)',
              }}
            />
          </>
        )}
        <div className="relative z-10 w-full">
          {timestamp && (
            <div className="mb-2 flex justify-start text-xs text-gray-500 dark:text-gray-400">
              <span>{timestamp}</span>
            </div>
          )}
            <div className="flex items-start gap-3">
            {isUserMessage && (
              <div className="flex-shrink-0">
                <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-medium">
                  {getInitial()}
                </div>
              </div>
            )}
            <div className="flex-1 w-full max-w-3xl min-w-0 dark:text-white text-gray-800">
              {isFailedTask ? (
                <div className="flex items-center text-red-600 dark:text-red-400 font-medium">
                  <ExclamationTriangleIcon className="h-5 w-5 mr-2" />
                  <span>Task failed: An error occurred processing this task</span>
                </div>
            ) : isAssistantMessage ? (
              <>
                <div className="flex flex-wrap items-start gap-3 sm:flex-nowrap sm:justify-between">
                  <div className="flex-1">
                    {toolUse && (
                      <div className="mb-2">
                        <ToolUse {...toolUse} />
                      </div>
                    )}
                    <MarkdownRenderer 
                      content={contentToDisplay}
                      variant="task"
                      isStreaming={isStreaming}
                    />
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <AuditTrailPanelButton taskId={task.id} />
                    <TaskFeedbackButtons
                      currentRating={feedbackEntry?.rating ?? null}
                      onSelect={handleFeedbackSelect}
                    />
                  </div>
                </div>
                {task.metadata?.footnote && (
                  <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {task.metadata.footnote}
                    </span>
                  </div>
                )}
              </>
            ) : (
              <div className="whitespace-pre-wrap">{contentToDisplay}</div>
            )}
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  export default TaskMessageItem;
