import { useState, useEffect, useRef, useCallback } from 'react';
import { sseConnectionPool } from '~/utils/streaming/connectionPool';
import { streamEventBus } from '~/utils/streaming/eventBus';
import { parseSSEEvent } from '~/utils/streaming/eventParser';
import { StreamEventType } from '~/utils/streaming/eventTypes';

export interface UseWorkzoneStreamOptions {
  invocationId: string | null;
  projectId: string | null;
  agentId: string | null;
  assistantTaskId: string | null;
  userTaskId: string | null;
  enabled?: boolean;
}

export interface UseWorkzoneStreamReturn {
  isStreaming: boolean;
  canStream: boolean;
  error: string | null;
  startStream: () => void;
  stopStream: () => void;
}

/**
 * Custom hook for streaming workzone invocation responses
 * Manages SSE connections with a global connection pool limit
 */
export function useWorkzoneStream(options: UseWorkzoneStreamOptions): UseWorkzoneStreamReturn {
  const {
    invocationId,
    projectId,
    agentId,
    assistantTaskId,
    userTaskId,
    enabled = true
  } = options;

  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const completedInvocationsRef = useRef<Set<string>>(new Set());

  // Check if we can start a new stream based on connection pool capacity
  const canStream = sseConnectionPool.canConnect();

  /**
   * Start streaming the assistant response
   */
  const startStream = useCallback(() => {
    // Validation checks
    if (!invocationId || !projectId || !agentId || !assistantTaskId) {
      console.warn('[useWorkzoneStream] Missing required IDs for streaming:', {
        invocationId,
        projectId,
        agentId,
        assistantTaskId
      });
      return;
    }

    // Don't re-stream completed invocations
    if (completedInvocationsRef.current.has(invocationId)) {
      console.log(`[useWorkzoneStream] Invocation ${invocationId} already completed, skipping stream`);
      return;
    }

    // Don't start if already streaming
    if (eventSourceRef.current) {
      console.log(`[useWorkzoneStream] Already streaming invocation ${invocationId}`);
      return;
    }

    // Check connection pool capacity
    if (!sseConnectionPool.canConnect()) {
      const errorMsg = `Cannot start stream: Connection limit reached (${sseConnectionPool.getActiveCount()}/${sseConnectionPool.getMaxConnections()})`;
      console.warn(`[useWorkzoneStream] ${errorMsg}`);
      setError(errorMsg);
      return;
    }

    console.log(`[useWorkzoneStream] Starting stream for invocation ${invocationId}, task ${assistantTaskId}`);

    // Build stream URL
    const streamUrl = `/projects/${projectId}/agents/${agentId}/tasks/${assistantTaskId}/stream`;

    try {
      // Create EventSource
      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      // Add to connection pool
      const added = sseConnectionPool.addConnection(invocationId, eventSource);
      if (!added) {
        console.error('[useWorkzoneStream] Failed to add connection to pool');
        eventSource.close();
        eventSourceRef.current = null;
        setError('Failed to establish connection');
        return;
      }

      setIsStreaming(true);
      setError(null);

      // Emit stream start event
      streamEventBus.emit(StreamEventType.STREAM_START, {
        taskId: assistantTaskId,
        agentId
      });

      // Set up event listeners for different event types
      const eventTypes = ['message_start', 'message_chunk', 'message_complete', 'claude_code_message', 'done', 'task_timeout'];

      eventTypes.forEach(eventType => {
        eventSource.addEventListener(eventType, (event: Event) => {
          const messageEvent = event as MessageEvent;
          parseSSEEvent(messageEvent, assistantTaskId, agentId);
        });
      });

      // Handle connection open
      eventSource.addEventListener('open', () => {
        console.log(`[useWorkzoneStream] Connection opened for invocation ${invocationId}`);
      });

      // Handle errors
      eventSource.addEventListener('error', (event) => {
        console.error(`[useWorkzoneStream] Stream error for invocation ${invocationId}:`, event);

        const errorMsg = 'Stream connection error';
        setError(errorMsg);

        // Emit error event
        streamEventBus.emit(StreamEventType.STREAM_ERROR, {
          taskId: assistantTaskId,
          agentId,
          error: errorMsg
        });

        // Close the stream
        stopStream();
      });

    } catch (err) {
      console.error('[useWorkzoneStream] Error creating EventSource:', err);
      setError(err instanceof Error ? err.message : 'Failed to start stream');
      setIsStreaming(false);
    }
  }, [invocationId, projectId, agentId, assistantTaskId]);

  /**
   * Stop streaming
   */
  const stopStream = useCallback(() => {
    if (eventSourceRef.current && invocationId) {
      console.log(`[useWorkzoneStream] Stopping stream for invocation ${invocationId}`);

      // Remove from connection pool (this also closes the EventSource)
      sseConnectionPool.removeConnection(invocationId);

      eventSourceRef.current = null;
      setIsStreaming(false);
    }
  }, [invocationId]);

  // Subscribe to stream end events to mark invocation as completed
  useEffect(() => {
    if (!assistantTaskId) return;

    const unsubscribe = streamEventBus.subscribe(
      StreamEventType.STREAM_END,
      (payload) => {
        if (payload.taskId === assistantTaskId && invocationId) {
          console.log(`[useWorkzoneStream] Stream ended for invocation ${invocationId}`);
          completedInvocationsRef.current.add(invocationId);
          stopStream();
        }
      }
    );

    return unsubscribe;
  }, [assistantTaskId, invocationId, stopStream]);

  // Auto-start streaming if enabled
  useEffect(() => {
    if (enabled && invocationId && projectId && agentId && assistantTaskId) {
      startStream();
    }

    // Cleanup on unmount or when invocation changes
    return () => {
      stopStream();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    // Note: startStream and stopStream are intentionally excluded from dependencies
    // to prevent infinite re-renders. The IDs in the dependency array are sufficient
    // to trigger re-runs when needed, and the callbacks already check these values.
  }, [enabled, invocationId, projectId, agentId, assistantTaskId]);

  return {
    isStreaming,
    canStream,
    error,
    startStream,
    stopStream
  };
}
