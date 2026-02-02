import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useParams } from '@remix-run/react';
import { streamEventBus } from '~/utils/streaming/eventBus';
import { StreamEventType } from '~/utils/streaming/eventTypes';
import MarkdownRenderer from './MarkdownRenderer';
import { twMerge } from 'tailwind-merge';
import { ExclamationTriangleIcon, WrenchScrewdriverIcon, ArrowDownTrayIcon, FilmIcon, DocumentIcon } from '@heroicons/react/24/outline';
import AuditTrailPanelButton from './AuditTrailPanelButton';
import TaskFeedbackButtons from './TaskFeedbackButtons';
import MCPGatewayIcon from '~/components/icons/MCPGatewayIcon';
import type { TaskFeedbackEntry } from './TaskFeedbackModal';

interface Artifact {
  filename: string;
  size: number;
  last_modified: string | null;
  download_url: string;
}

interface ToolCall {
  id: string;
  name: string;
  input: Record<string, any>;
  status: 'running' | 'complete' | 'error';
  result?: any;
  error?: string;
}

interface StreamingMessageProps {
  taskId: string;
  initialContent?: string;
  initialRole?: 'user' | 'assistant';
  user?: string | null;
  metadata?: any;
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

const formatToolName = (name: string) => {
  return name
    .replace(/^mcp__/, '')
    .replace(/_/g, ' ')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, (l) => l.toUpperCase())
    .trim();
};

const formatInputValue = (value: any): string => {
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return value.toString();
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
};

export function StreamingMessage({
  taskId,
  initialContent = '',
  initialRole = 'assistant',
  user,
  metadata,
  agentId,
  onShowFeedbackPanel
}: StreamingMessageProps) {
  // Progressive display state
  const [currentSection, setCurrentSection] = useState(initialContent);
  const [sectionTools, setSectionTools] = useState<ToolCall[]>([]);
  const [finalResponse, setFinalResponse] = useState<string | null>(null);

  // Legacy state for streaming chunks
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeoutMessage, setTimeoutMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [role] = useState(initialRole);
  
  // Animation states
  const [showMessage, setShowMessage] = useState(false);
  const [showFinalResponse, setShowFinalResponse] = useState(false);
  const [shouldAnimateContent, setShouldAnimateContent] = useState(false);

  // User message slide animation
  const [isNewUserMessage, setIsNewUserMessage] = useState(false);
  const [slideDistance, setSlideDistance] = useState(0);
  const messageRef = useRef<HTMLDivElement>(null);
  const hasAnimatedContent = useRef(false);

  // Artifact state
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const params = useParams();
  const projectId = params.projectId;

  const isUserMessage = role === 'user';
  const isAssistantMessage = role === 'assistant';

  const feedbackEntry: TaskFeedbackEntry | null = Array.isArray(metadata?.feedback)
    ? (metadata.feedback as TaskFeedbackEntry[])[0] ?? null
    : null;

  const feedbackSummarySource = useMemo(
    () => (finalResponse || currentSection || streamingContent || initialContent || '').toString(),
    [finalResponse, currentSection, streamingContent, initialContent]
  );

  const taskSummary = useMemo(() => {
    const normalized = feedbackSummarySource.replace(/\s+/g, ' ').trim();
    if (!normalized) {
      return undefined;
    }
    return normalized.length > 120 ? `${normalized.slice(0, 117)}…` : normalized;
  }, [feedbackSummarySource]);

  const handleFeedbackSelect = useCallback((selected: 'positive' | 'negative') => {
    if (!onShowFeedbackPanel) {
      return;
    }
    const anchorRect = messageRef.current?.getBoundingClientRect();
    if (!anchorRect) {
      return;
    }
    onShowFeedbackPanel({
      taskId,
      agentId,
      taskLabel: taskSummary,
      anchorRect,
      existingFeedback: feedbackEntry,
      defaultRating: selected
    });
  }, [agentId, feedbackEntry, onShowFeedbackPanel, taskId, taskSummary]);

  useEffect(() => {
    const getStatusFromChunk = (rawChunk: string): string | null => {
      if (!rawChunk) return null;
      const trimmed = rawChunk.trim();
      if (!trimmed) return null;

      // Remove wrapping quotes if present
      const normalized = trimmed.replace(/^['"]+/, '').replace(/['"]+$/, '');
      if (!normalized) return null;

      // Skip multi-line chunks
      if (normalized.includes('\n')) return null;

      // Recognize local file paths we don't want to render as content
      const lower = normalized.toLowerCase();
      const mediaExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.heic', '.webp'];
      const hasKnownExtension = mediaExtensions.some(ext => lower.endsWith(ext));
      const isLocalPath = normalized.startsWith('/Users/') || normalized.startsWith('~/');

      if (!hasKnownExtension || !isLocalPath) {
        return null;
      }

      const fileName = normalized.split('/').filter(Boolean).pop();
      if (!fileName) return null;

      return `Processing ${fileName}`;
    };

    // Subscribe to streaming events for this specific task
    const unsubscribers = [
      streamEventBus.subscribe(StreamEventType.MESSAGE_START, (payload) => {
        if (payload.taskId === taskId) {
          setIsStreaming(true);
          setStreamingContent('');
          setCurrentSection('');
          setSectionTools([]);
          setFinalResponse(null);
          setError(null);
          setTimeoutMessage(null);
          setStatusMessage(null);
          setShowFinalResponse(false);
          // Trigger fade-in animation
          setTimeout(() => setShowMessage(true), 50);
        }
      }),

      streamEventBus.subscribe(StreamEventType.MESSAGE_CHUNK, (payload) => {
        if (payload.taskId === taskId) {
          const normalizedStatus = typeof payload.status === 'string'
            ? payload.status.trim()
            : null;

          if (normalizedStatus) {
            setStatusMessage(normalizedStatus);
          }

          const chunkContent = payload.content ?? '';

          if (!chunkContent || chunkContent.trim().length === 0) {
            if (!normalizedStatus) {
              const derivedStatus = getStatusFromChunk(chunkContent);
              if (derivedStatus) {
                setStatusMessage(derivedStatus);
              }
            }
            return;
          }

          setStatusMessage(null);
          setStreamingContent(prev => prev + chunkContent);
        }
      }),

      streamEventBus.subscribe(StreamEventType.ASSISTANT_SECTION, (payload) => {
        if (payload.taskId === taskId) {
          // New assistant section replaces the current one
          setCurrentSection(payload.text);
          setSectionTools([]); // Clear tools for new section
          setStatusMessage(null);
          // Ensure message is shown with animation
          if (!showMessage) {
            setTimeout(() => setShowMessage(true), 50);
          }
        }
      }),

      streamEventBus.subscribe(StreamEventType.FINAL_RESPONSE, (payload) => {
        if (payload.taskId === taskId) {
          setTimeoutMessage(null);
          // Final response replaces everything
          setFinalResponse(payload.response);
          setCurrentSection('');
          setSectionTools([]);
          setStreamingContent('');
          setStatusMessage(null);
          // Trigger fade-in for final response
          setShowFinalResponse(false);
          setTimeout(() => setShowFinalResponse(true), 100);
        }
      }),

      streamEventBus.subscribe(StreamEventType.TOOL_USE_START, (payload) => {
        if (payload.taskId === taskId) {
          setSectionTools(prev => [...prev, {
            id: payload.toolId,
            name: payload.toolName,
            input: payload.input,
            status: 'running'
          }]);
        }
      }),

      streamEventBus.subscribe(StreamEventType.TOOL_USE_COMPLETE, (payload) => {
        if (payload.taskId === taskId) {
          setSectionTools(prev => prev.map(tool =>
            tool.id === payload.toolId
              ? { ...tool, status: 'complete', result: payload.result }
              : tool
          ));
        }
      }),

      streamEventBus.subscribe(StreamEventType.TOOL_USE_ERROR, (payload) => {
        if (payload.taskId === taskId) {
          setSectionTools(prev => prev.map(tool =>
            tool.id === payload.toolId
              ? { ...tool, status: 'error', error: payload.error }
              : tool
          ));
        }
      }),

      streamEventBus.subscribe(StreamEventType.MESSAGE_COMPLETE, (payload) => {
        if (payload.taskId === taskId) {
          setIsStreaming(false);
          setStatusMessage(null);
        }
      }),

      streamEventBus.subscribe(StreamEventType.STREAM_ERROR, (payload) => {
        if (payload.taskId === taskId && payload.agentId === agentId) {
          setIsStreaming(false);
          setTimeoutMessage(null);
          setError(typeof payload.error === 'string' ? payload.error : 'Stream connection error');
          setStatusMessage(null);
        }
      }),

      streamEventBus.subscribe(StreamEventType.TASK_TIMEOUT, (payload) => {
        if (payload.taskId === taskId) {
          setIsStreaming(false);
          setTimeoutMessage(payload.message ?? 'Error: Task timed out');
          setError(null);
          setFinalResponse(null);
          setStatusMessage(null);
          setShowFinalResponse(false);
          // Ensure the message container is visible
          if (!showMessage) {
            setTimeout(() => setShowMessage(true), 50);
          }
        }
      })
    ];

    return () => {
      unsubscribers.forEach(unsub => unsub());
    };
  }, [taskId, showMessage, agentId]);
  
  // Listen for user message submit events to trigger slide animation
  useEffect(() => {
    if (role === 'user' && initialContent) {
      const unsubscribe = streamEventBus.subscribe(StreamEventType.USER_MESSAGE_SUBMIT, (payload) => {
        // Check if this message matches the submitted text
        if (payload.text === initialContent.trim()) {
          // Calculate slide distance after a brief delay to ensure element is rendered
          setTimeout(() => {
            if (messageRef.current) {
              const rect = messageRef.current.getBoundingClientRect();
              const distance = window.innerHeight - rect.top - 100; // 100px offset from bottom
              setSlideDistance(distance);
              setIsNewUserMessage(true);
              // Remove the flag after animation completes
              setTimeout(() => {
                setIsNewUserMessage(false);
                setSlideDistance(0);
              }, 700);
            }
          }, 50);
        }
      });
      
      return () => unsubscribe();
    }
  }, [role, initialContent]);
  
  // Trigger initial animation if we have initial content
  useEffect(() => {
    if (initialContent) {
      setTimeout(() => setShowMessage(true), 50);
    }
  }, []);

  useEffect(() => {
    if (isAssistantMessage && showMessage && !hasAnimatedContent.current) {
      setShouldAnimateContent(true);
      hasAnimatedContent.current = true;
      const timeoutId = setTimeout(() => setShouldAnimateContent(false), 600);
      return () => clearTimeout(timeoutId);
    }
  }, [isAssistantMessage, showMessage]);

  // Fetch artifacts when task completes (streaming ends) or has artifacts_prefix in metadata
  const [streamingEnded, setStreamingEnded] = useState(false);
  const prevIsStreaming = useRef(isStreaming);

  useEffect(() => {
    if (prevIsStreaming.current && !isStreaming) {
      setStreamingEnded(true);
    }
    prevIsStreaming.current = isStreaming;
  }, [isStreaming]);

  useEffect(() => {
    if (!isAssistantMessage || !projectId || !agentId) return;
    if (!streamingEnded && !metadata?.artifacts_prefix) return;

    const controller = new AbortController();
    const maxAttempts = 3;
    const baseDelay = 2000;

    const fetchArtifacts = async () => {
      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        if (controller.signal.aborted) return;
        // Delay before retries only (not the first attempt)
        if (attempt > 0) {
          const delay = baseDelay * Math.pow(2, attempt - 1);
          await new Promise(r => setTimeout(r, delay));
          if (controller.signal.aborted) return;
        }
        try {
          const res = await fetch(`/api/artifacts/${projectId}/${agentId}/${taskId}`, { signal: controller.signal });
          if (res.ok) {
            const data = await res.json();
            if (data.artifacts && data.artifacts.length > 0) {
              setArtifacts(data.artifacts);
              return;
            }
          }
        } catch (err) {
          if (err instanceof DOMException && err.name === 'AbortError') return;
          console.error('Failed to fetch artifacts:', err);
        }
      }
    };

    fetchArtifacts();
    return () => controller.abort();
  }, [isAssistantMessage, projectId, agentId, taskId, streamingEnded, metadata?.artifacts_prefix]);

  // Get the first initial for user avatar
  const getInitial = () => {
    const name = user || "User";
    return name.charAt(0).toUpperCase();
  };

  // Determine what content to display
  const hasStreamingContent = streamingContent.trim().length > 0;
  const displayContent = finalResponse || (hasStreamingContent ? streamingContent : currentSection);
  const displayTools = finalResponse ? [] : sectionTools; // No tools if showing final response

  return (
    <div 
      ref={messageRef}
      className={twMerge(
        "mb-4 p-4 rounded-lg w-full flex justify-center relative overflow-hidden",
        isUserMessage ? "border border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20" : "",
        isAssistantMessage ? "transition-all duration-700 ease-out" : "",
        isAssistantMessage ? (showMessage || initialContent ? "opacity-100" : "opacity-0") : "",
        // User message slide-up animation
        isUserMessage && isNewUserMessage ? "animate-slide-up-message" : "",
        isUserMessage ? "will-change-transform" : "",
        // Respect reduced motion preference
        "motion-reduce:transition-none motion-reduce:animate-none"
      )}
      style={isUserMessage && isNewUserMessage && slideDistance > 0 ? {
        '--slide-distance': `${slideDistance}px`
      } as React.CSSProperties : {}}
    >
      {/* Gradient backgrounds for user messages */}
      {isUserMessage && (
        <>
          <div
            className="absolute inset-0 dark:hidden pointer-events-none"
            style={{
              background: 'radial-gradient(circle at center, rgba(255, 255, 255, 0.9) 95%, rgba(245, 243, 255, 0.6) 100%)',
            }}
          />
          <div
            className="absolute inset-0 hidden dark:block pointer-events-none"
            style={{
              background: 'radial-gradient(circle at center, rgba(17, 24, 39, 0.9) 95%, rgba(88, 28, 135, 0.2) 100%)',
            }}
          />
        </>
      )}

      {/* User avatar */}
      {isUserMessage && (
        <div className="flex-shrink-0 mr-3 relative z-10">
          <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-medium">
            {getInitial()}
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 w-full max-w-3xl min-w-0 relative z-10">
        <div className="dark:text-white text-gray-800">
          {timeoutMessage ? (
            <div className="flex items-center text-red-600 dark:text-red-400 font-medium">
              <ExclamationTriangleIcon className="h-5 w-5 mr-2" />
              <span>{timeoutMessage}</span>
            </div>
          ) : error ? (
            <div className="flex items-center text-red-600 dark:text-red-400 font-medium">
              <ExclamationTriangleIcon className="h-5 w-5 mr-2" />
              <span>{error}</span>
            </div>
          ) : isAssistantMessage ? (
            <>
              <div className="flex flex-wrap items-start gap-3 sm:flex-nowrap sm:justify-between">
                <div className="flex-1 min-w-0">
                  {/* Main content - show first if we have final response or current section */}
                  {displayContent && (
                    <div className={twMerge(
                      displayTools.length > 0 ? "mb-3" : "",
                      shouldAnimateContent ? "animate-fadeIn" : "",
                      "transition-all duration-500 ease-out",
                      finalResponse 
                        ? (showFinalResponse ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2")
                        : (showMessage ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2")
                    )}>
                      <MarkdownRenderer
                        content={displayContent}
                        variant="task"
                        isStreaming={isStreaming && !finalResponse}
                      />
                    </div>
                  )}

                  {/* Tool calls display - shown as sub-items under current section */}
                  {displayTools.length > 0 && (
                    <div className="ml-4 border-l-2 border-gray-200 dark:border-gray-700 pl-4 space-y-3">
                      {displayTools.map((tool, index) => (
                        <ToolCallItem
                          key={tool.id}
                          tool={tool}
                          index={index}
                          showMessage={showMessage}
                        />
                      ))}
                    </div>
                  )}

                  {/* Streaming indicator if no content yet */}
                  {isStreaming && !displayContent && displayTools.length === 0 && (
                    <div className="flex items-center space-x-2">
                      <svg className="animate-spin h-4 w-4 text-purple-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span className="text-gray-500">{statusMessage ?? 'Processing...'}</span>
                    </div>
                  )}

                  {/* Artifacts display */}
                  {artifacts.length > 0 && (
                    <div className="mt-3 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                      <div className="px-3 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                        <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                          Generated Files ({artifacts.length})
                        </span>
                      </div>
                      <div className="divide-y divide-gray-200 dark:divide-gray-700">
                        {artifacts.map((artifact) => {
                          const isSafeUrl = /^https?:\/\//i.test(artifact.download_url);
                          const isVideo = /\.(mp4|webm|mov)$/i.test(artifact.filename);
                          const isImage = /\.(png|jpg|jpeg|gif|webp)$/i.test(artifact.filename);
                          const sizeStr = artifact.size < 1024
                            ? `${artifact.size} B`
                            : artifact.size < 1048576
                              ? `${(artifact.size / 1024).toFixed(1)} KB`
                              : `${(artifact.size / 1048576).toFixed(1)} MB`;

                          return (
                            <div key={artifact.filename} className="px-3 py-2">
                              {isSafeUrl && isVideo && (
                                <video
                                  controls
                                  preload="metadata"
                                  className="w-full max-w-lg rounded mb-2"
                                  src={artifact.download_url}
                                >
                                  Your browser does not support the video tag.
                                </video>
                              )}
                              {isSafeUrl && isImage && (
                                <img
                                  src={artifact.download_url}
                                  alt={artifact.filename}
                                  loading="lazy"
                                  className="max-w-lg rounded mb-2"
                                />
                              )}
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 min-w-0">
                                  {isVideo ? (
                                    <FilmIcon className="h-4 w-4 text-purple-500 flex-shrink-0" />
                                  ) : (
                                    <DocumentIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
                                  )}
                                  <span className="text-sm text-gray-700 dark:text-gray-300 truncate">
                                    {artifact.filename}
                                  </span>
                                  <span className="text-xs text-gray-400 flex-shrink-0">{sizeStr}</span>
                                </div>
                                {isSafeUrl && (
                                  <a
                                    href={artifact.download_url}
                                    download={artifact.filename}
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1 text-xs text-purple-600 hover:text-purple-700 dark:text-purple-400 dark:hover:text-purple-300 flex-shrink-0"
                                  >
                                    <ArrowDownTrayIcon className="h-3.5 w-3.5" />
                                    Download
                                  </a>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Audit trail buttons */}
                <div className="flex-shrink-0 self-start">
                  <div className="flex flex-col items-end gap-2">
                    <AuditTrailPanelButton
                      taskId={taskId}
                      className="ml-0"
                    />
                    <TaskFeedbackButtons
                      currentRating={feedbackEntry?.rating ?? null}
                      onSelect={handleFeedbackSelect}
                    />
                  </div>
                </div>
              </div>

              {/* Footer metadata */}
              {metadata?.footnote && (
                <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {metadata.footnote}
                  </span>
                </div>
              )}
            </>
          ) : (
            <div className="whitespace-pre-wrap">{displayContent}</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default StreamingMessage;

interface ToolCallItemProps {
  tool: ToolCall;
  index: number;
  showMessage: boolean;
}

interface TodoInput {
  content: string;
  status?: string;
  activeForm?: string;
}

const TOOL_STATUS_STYLES: Record<ToolCall['status'], {
  label: string;
  badgeClass: string;
  accentClass: string;
  iconClass: string;
}> = {
  running: {
    label: 'Running',
    badgeClass: 'bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-100',
    accentClass: 'bg-purple-500/50 dark:bg-purple-400/60',
    iconClass: 'text-purple-500 dark:text-purple-300'
  },
  complete: {
    label: 'Complete',
    badgeClass: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200',
    accentClass: 'bg-emerald-500/50 dark:bg-emerald-400/70',
    iconClass: 'text-emerald-500 dark:text-emerald-300'
  },
  error: {
    label: 'Error',
    badgeClass: 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-200',
    accentClass: 'bg-rose-500/60 dark:bg-rose-400/70',
    iconClass: 'text-rose-500 dark:text-rose-300'
  }
};

function ToolCallItem({ tool, index, showMessage }: ToolCallItemProps) {
  const statusStyles = TOOL_STATUS_STYLES[tool.status];
  const nameLower = tool.name.toLowerCase();
  const isMcpTool = nameLower.includes('mcp');
  const isTodoWrite = nameLower.includes('todowrite');
  const transitionDelay = `${150 + (index * 100)}ms`;
  const inputEntries = Object.entries(tool.input || {});
  const filteredEntries = inputEntries.filter(([key]) => {
    const lowered = key.toLowerCase();
    return lowered !== 'chicory_project_id' && lowered !== 'todos';
  });
  const todoItems = Array.isArray((tool.input as { todos?: TodoInput[] })?.todos)
    ? ((tool.input as { todos?: TodoInput[] }).todos ?? [])
    : [];

  return (
    <div
      className={twMerge(
        'relative overflow-hidden rounded-lg border border-gray-200/70 bg-white/70 p-3 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-white/40 dark:border-gray-700/60 dark:bg-slate-900/50',
        'transition-all duration-500 ease-out',
        showMessage ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'
      )}
      style={{ transitionDelay }}
    >
      <span
        aria-hidden="true"
        className={twMerge(
          'absolute left-0 top-3 h-[calc(100%-1.5rem)] w-1 rounded-full',
          statusStyles.accentClass
        )}
      />

      <div className="flex items-start justify-between gap-3 pl-2">
        <div className="flex items-center gap-3">
          {isMcpTool ? (
            <MCPGatewayIcon size={20} className="shrink-0" />
          ) : (
            <WrenchScrewdriverIcon
              className={twMerge('h-5 w-5 shrink-0', statusStyles.iconClass)}
              aria-hidden="true"
            />
          )}
          <div>
            <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">
              {formatToolName(tool.name)}
            </span>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {tool.status === 'running' ? 'Using tool' : 'Tool invocation'}
            </div>
          </div>
        </div>
        <span className={twMerge('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', statusStyles.badgeClass)}>
          {statusStyles.label}
        </span>
      </div>

      {isTodoWrite && todoItems.length > 0 && (
        <TodoList todos={todoItems} />
      )}

      {filteredEntries.length > 0 && (
        <div className="mt-3 space-y-2 pl-2 text-xs text-gray-600 dark:text-gray-300">
          {filteredEntries.map(([key, value]) => {
            const label = key.replace(/_/g, ' ');
            const isMultilineString = typeof value === 'string' && (value.includes('\n') || value.length > 120);
            const displayValue = formatInputValue(value);

            return (
              <div key={key} className="space-y-1">
                <span className="font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  {label}:
                </span>
                {isMultilineString ? (
                  <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-md border border-gray-200 bg-gray-50 px-3 py-2 font-mono text-[11px] leading-relaxed text-gray-700 dark:border-gray-700 dark:bg-slate-900/60 dark:text-gray-200">
                    {displayValue}
                  </pre>
                ) : (
                  <span className="font-mono text-gray-700 dark:text-gray-200">
                    {displayValue}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {tool.error && (
        <div className="mt-3 pl-2 text-xs font-medium text-rose-600 dark:text-rose-400">
          Error: {tool.error}
        </div>
      )}
    </div>
  );
}

function TodoList({ todos }: { todos: TodoInput[] }) {
  return (
    <div className="mt-3 space-y-3 pl-2">
      {todos.map((todo, idx) => {
        const isInProgress = todo.status === 'in_progress';
        const indicatorClass = isInProgress
          ? 'bg-purple-500'
          : 'bg-gray-300 dark:bg-gray-600';
        const text = isInProgress ? todo.activeForm ?? todo.content : todo.content;

        return (
          <div
            key={`${todo.content}-${idx}`}
            className="rounded-md border border-gray-200/60 bg-gray-50/80 p-3 text-sm text-gray-700 shadow-sm dark:border-gray-700/60 dark:bg-slate-900/60 dark:text-gray-200"
          >
            <div className="flex items-start gap-3">
              <span className={twMerge('mt-1 h-2.5 w-2.5 rounded-full', indicatorClass)} aria-hidden="true" />
              <div className="flex-1">
                <div className="font-medium">{text}</div>
                {todo.status && (
                  <div className="mt-1 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    {todo.status.replace(/_/g, ' ')}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
