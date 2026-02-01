import { useState, useRef, useCallback, useEffect } from "react";
import { streamEventBus } from "~/utils/streaming/eventBus";
import { StreamEventType } from "~/utils/streaming/eventTypes";
import { parseSSEEvent } from "~/utils/streaming/eventParser";

export interface UsePlaygroundStreamOptions {
  agentId: string;
  projectId: string;
  onStreamComplete?: () => void;
}

export interface UsePlaygroundStreamReturn {
  isStreaming: boolean;
  currentStreamTaskId: string | null;
  startStreaming: (userTaskId: string, invocationId: string, assistantTaskId?: string) => void;
  stopStreaming: () => void;
}

export function usePlaygroundStream({
  agentId,
  projectId,
  onStreamComplete
}: UsePlaygroundStreamOptions): UsePlaygroundStreamReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamTaskId, setCurrentStreamTaskId] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const completedTasksRef = useRef<Set<string>>(new Set());
  const isStreamingRef = useRef(false);
  const activeAgentRef = useRef<string | null>(null);
  const activeTaskRef = useRef<string | null>(null);

  const stopStreaming = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsStreaming(false);
    isStreamingRef.current = false;
    setCurrentStreamTaskId(null);
    const taskId = activeTaskRef.current;
    const activeAgentId = activeAgentRef.current;
    if (taskId && activeAgentId) {
      streamEventBus.emit(StreamEventType.STREAM_END, {
        taskId,
        agentId: activeAgentId
      });
    }
    activeTaskRef.current = null;
    activeAgentRef.current = null;
  }, []);

  useEffect(() => {
    completedTasksRef.current.clear();
    stopStreaming();
    return () => {
      stopStreaming();
      completedTasksRef.current.clear();
    };
  }, [agentId, projectId, stopStreaming]);

  const startStreaming = useCallback((_userTaskId: string, _invocationId: string, assistantTaskId?: string) => {
    // Safety check: assistantTaskId is required for streaming
    if (!assistantTaskId) {
      console.error("Cannot start streaming: assistantTaskId is missing");
      return;
    }

    // Check if we've already completed streaming for this task
    if (completedTasksRef.current.has(assistantTaskId)) {
      console.log(`[STREAM] Task ${assistantTaskId} already completed, skipping stream`);
      return;
    }

    // Prevent multiple EventSource creation
    if (isStreamingRef.current || eventSourceRef.current) {
      console.log(`[STREAM] Already streaming, skipping duplicate call`);
      return;
    }

    console.log(`[STREAM] startStreaming called for assistant task ${assistantTaskId}`);

    setIsStreaming(true);
    isStreamingRef.current = true;
    setCurrentStreamTaskId(assistantTaskId);
    activeTaskRef.current = assistantTaskId;
    activeAgentRef.current = agentId;

    // Emit stream start event
    streamEventBus.emit(StreamEventType.STREAM_START, { taskId: assistantTaskId, agentId });

    // Connect to SSE stream using the assistant_task_id
    const streamUrl = `/projects/${projectId}/agents/${agentId}/tasks/${assistantTaskId}/stream`;
    const eventSource = new EventSource(streamUrl);
    eventSourceRef.current = eventSource;

    console.log(`[STREAM] EventSource created for task ${assistantTaskId} at ${new Date().toISOString()}`);

    // Handle errors
    eventSource.onerror = (error) => {
      console.error("Stream error:", error);
      streamEventBus.emit(StreamEventType.STREAM_ERROR, {
        taskId: assistantTaskId,
        agentId,
        error: "Error connecting to stream"
      });
      stopStreaming();
    };

    // Register event listeners that use our parser
    // Note: 'done' is handled separately below, so we don't include it here
    const eventTypes = ['message_start', 'message_chunk', 'message_complete', 'claude_code_message'];
    eventTypes.forEach(eventType => {
      eventSource.addEventListener(eventType, (event) => {
        parseSSEEvent(event, assistantTaskId, agentId);
      });
    });

    // Handle stream completion - only register this once
    eventSource.addEventListener("done", (event) => {
      // Mark this task as completed to prevent re-streaming
      completedTasksRef.current.add(assistantTaskId);
      console.log(`[STREAM] Marked task ${assistantTaskId} as completed`);

      // Parse the done event to emit necessary events
      parseSSEEvent(event, assistantTaskId, agentId);

      // Then stop streaming
      stopStreaming();

      // Call the completion callback if provided
      if (onStreamComplete) {
        onStreamComplete();
      }

      // Note: We removed fetcher.load() here to prevent infinite loops
      // The playground will be refreshed when needed through other mechanisms
    });
  }, [agentId, projectId, stopStreaming, onStreamComplete]);

  return {
    isStreaming,
    currentStreamTaskId,
    startStreaming,
    stopStreaming
  };
}
