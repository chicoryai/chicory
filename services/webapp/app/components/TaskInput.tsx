import React, { useState, useEffect, useRef } from 'react';
import { Form, useNavigation, useSubmit, Link } from '@remix-run/react';
import { streamEventBus } from '~/utils/streaming/eventBus';
import { StreamEventType } from '~/utils/streaming/eventTypes';

interface TaskInputProps {
  projectId: string;
  agentId: string;
  isDisabled?: boolean;
  additionalFormData?: Record<string, string>;
  isConfigureOpen?: boolean;
  isStreaming?: boolean;
  currentStreamTaskId?: string | null;
  onStopTask?: (taskId: string) => void;
}

/**
 * Component for task input with auto-resize and submission handling
 */
export function TaskInput({ projectId, agentId, isDisabled = false, additionalFormData, isConfigureOpen = false, isStreaming = false, currentStreamTaskId, onStopTask }: TaskInputProps) {
  const [inputValue, setInputValue] = useState("");
  const [streamingDisabled, setStreamingDisabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const navigation = useNavigation();
  const submit = useSubmit();
  const isSubmitting = navigation.state === "submitting";
  const prevNavigationStateRef = useRef(navigation.state);

  // Subscribe to streaming events
  useEffect(() => {
    const unsubscribers = [
      streamEventBus.subscribe(StreamEventType.STREAM_START, ({ agentId: streamAgentId }) => {
        if (streamAgentId !== agentId) {
          return;
        }
        setStreamingDisabled(true);
        setError(null);
      }),
      streamEventBus.subscribe(StreamEventType.STREAM_END, ({ agentId: streamAgentId }) => {
        if (streamAgentId !== agentId) {
          return;
        }
        setStreamingDisabled(false);
      }),
      streamEventBus.subscribe(StreamEventType.STREAM_ERROR, ({ agentId: streamAgentId }) => {
        if (streamAgentId !== agentId) {
          return;
        }
        setStreamingDisabled(false);
        setError('Connection error - please try again');
      })
    ];

    return () => {
      unsubscribers.forEach(unsub => unsub());
    };
  }, [agentId]);

  useEffect(() => {
    setStreamingDisabled(false);
    setError(null);
  }, [agentId]);

  // Auto-resize textarea as user types
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 280)}px`;
    }
  }, [inputValue]);

  // Clear input after successful submission
  useEffect(() => {
    const prevState = prevNavigationStateRef.current;
    const currentState = navigation.state;
    prevNavigationStateRef.current = currentState;
    
    // If we were submitting and now we're idle, clear the input
    if (prevState === "submitting" && currentState === "idle") {
      setInputValue("");
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  }, [navigation.state]);

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inputValue.trim()) {
      return;
    }
    
    // Capture position before submission for animation
    if (textareaRef.current) {
      const rect = textareaRef.current.getBoundingClientRect();
      streamEventBus.emit(StreamEventType.USER_MESSAGE_SUBMIT, {
        text: inputValue.trim(),
        initialPosition: {
          bottom: window.innerHeight - rect.top,
          left: rect.left,
          width: rect.width
        },
        timestamp: Date.now()
      });
    }
    
    // Manually submit the form
    const formData = new FormData(formRef.current || undefined);
    submit(formData, { method: "post" });
    
    // Clear the input immediately after submission
    setInputValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const inputDisabled = isSubmitting || isDisabled || streamingDisabled;

  return (
    <div className="w-full flex justify-center">
      <div className="w-full max-w-3xl">
      {error && (
        <div className="mb-2 p-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded">
          {error}
        </div>
      )}
      <Form
        ref={formRef}
        method="post"
        className="w-full"
        onSubmit={handleSubmit}
      >
        {/* Add hidden inputs for additional form data */}
        {additionalFormData && Object.entries(additionalFormData).map(([key, value]) => (
          <input key={key} type="hidden" name={key} value={value} />
        ))}

        <div className="relative">
          {inputDisabled && (
            <div
              aria-hidden="true"
              className="pointer-events-none absolute -z-10"
              style={{
                top: '-4px',
                left: '-4px',
                width: 'calc(100% + 8px)',
                height: 'calc(100% + 8px)',
                borderRadius: '1.5rem'
              }}
            >
              <div className="relative h-full w-full">
                <div className="absolute inset-0 rounded-[1.5rem] border border-purple-400/40 shadow-[0_0_24px_rgba(168,85,247,0.25)]" />
                <div
                  className="absolute inset-0 flex items-center justify-center rounded-[1.5rem]"
                  style={{
                    padding: '3px',
                    boxSizing: 'border-box',
                    borderRadius: '1.5rem',
                    WebkitMask: 'linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)',
                    mask: 'linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)',
                    WebkitMaskComposite: 'xor',
                    maskComposite: 'exclude'
                  } as React.CSSProperties}
                >
                  <div
                    className="h-[510%] w-[28px] origin-center rounded-full bg-gradient-to-r from-purple-200/10 via-purple-500 to-purple-200/10 opacity-0 shadow-[0_0_35px_rgba(168,85,247,0.4)] animate-glow-sweep motion-reduce:animate-none"
                    style={{ animationFillMode: 'both' }}
                  />
                </div>
              </div>
            </div>
          )}
          <div
            className={`relative z-10 overflow-hidden rounded-2xl bg-transparent shadow-md shadow-whitePurple-50/60 dark:bg-transparent dark:shadow-purple-900/30 ${
              inputDisabled
                ? 'border border-transparent'
                : 'border border-whitePurple-100/60 dark:border-whitePurple-200/30'
            }`}
          >
            <textarea
              ref={textareaRef}
              name="task"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className={`relative z-10 block w-full px-5 py-5 pb-20 pr-24 bg-white dark:bg-slate-900 border-none text-base leading-relaxed text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-0 resize-none min-h-[160px] transition-opacity duration-200 ${isSubmitting ? 'opacity-60' : 'opacity-100'}`}
              placeholder="Give me a task..."
              required
              disabled={inputDisabled}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (inputValue.trim()) {
                    handleSubmit(e);
                  }
                }
              }}
            />
            <div className="absolute inset-x-4 bottom-4 z-20 flex items-center justify-end gap-3">
              <Link
                to={isConfigureOpen ? "../?closed=true" : "configure"}
                relative="path"
                preventScrollReset
                className={`group inline-flex items-center gap-1 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-purple-400 ring-offset-2 ring-offset-white dark:ring-offset-gray-900 ${
                  isConfigureOpen
                    ? 'text-purple-600 underline dark:text-purple-300'
                    : 'text-purple-600 hover:text-purple-500 dark:text-purple-300 dark:hover:text-purple-200'
                }`}
              >
                Agent Prompt and Output Format
                <span className="inline-flex h-1 w-6 origin-left scale-x-0 rounded-full bg-purple-500 transition group-hover:scale-x-100" aria-hidden="true" />
              </Link>

              {isStreaming && currentStreamTaskId && onStopTask ? (
                <button
                  type="button"
                  onClick={() => onStopTask(currentStreamTaskId)}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-red-500/30 transition hover:bg-red-500 focus:outline-none focus:ring-2 focus:ring-red-500 ring-offset-2 ring-offset-white dark:ring-offset-gray-900"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
                    <path fillRule="evenodd" d="M4.5 7.5a3 3 0 013-3h9a3 3 0 013 3v9a3 3 0 01-3 3h-9a3 3 0 01-3-3v-9z" clipRule="evenodd" />
                  </svg>
                  Stop
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={inputDisabled || !inputValue.trim()}
                  className="inline-flex items-center justify-center rounded-xl bg-purple-600 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-purple-500/30 transition hover:bg-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500 ring-offset-2 ring-offset-white dark:ring-offset-gray-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
                    <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>
      </Form>
      </div>
    </div>
  );
}

export default TaskInput;
