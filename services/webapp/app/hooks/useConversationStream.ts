import { useState, useRef, useCallback, useEffect, useMemo } from "react";

// Block ID generation - ensures stable keys across renders
let blockIdCounter = 0;
const generateBlockId = (type: string) => `${type}-${Date.now()}-${++blockIdCounter}`;

// Streaming content block - represents blocks being built during streaming
export interface StreamingTextBlock {
  type: 'text';
  id: string;
  text: string;
}

export interface StreamingThinkingBlock {
  type: 'thinking';
  id: string;
  thinking: string;
  signature?: string; // May not be available until stream complete
}

export interface StreamingToolUseBlock {
  type: 'tool_use';
  id: string;
  name: string;
  input: Record<string, unknown>;
  output: string | null;
  is_error: boolean;
  active_description?: string;
}

export type StreamingContentBlock = StreamingTextBlock | StreamingThinkingBlock | StreamingToolUseBlock;

// Legacy type for backwards compatibility
export interface StreamingMessage {
  type: 'text' | 'tool_use' | 'tool_result' | 'thinking';
  content: string;
  toolName?: string;
  toolId?: string;
  toolInput?: Record<string, unknown>;
  isError?: boolean;
  signature?: string; // For thinking blocks
}

// Stream completion result with final content blocks
export interface StreamCompleteResult {
  isError: boolean;
  sessionId?: string;
  finalContentBlocks: StreamingContentBlock[];
}

export interface UseConversationStreamOptions {
  projectId: string;
  conversationId: string;
  maxRetries?: number;        // default: 3
  retryDelayMs?: number;      // default: 1000
  onMessage?: (message: StreamingMessage) => void;
  onContentBlock?: (block: StreamingContentBlock) => void;
  onComplete?: (result: StreamCompleteResult) => void;
  onError?: (error: string) => void;
}

export interface UseConversationStreamReturn {
  isStreaming: boolean;
  streamedContent: string;
  streamedThinking: string;
  contentBlocks: StreamingContentBlock[];
  toolCalls: StreamingMessage[]; // Legacy - kept for backwards compatibility
  startStreaming: (messageId: string) => void;
  stopStreaming: () => void;
  resetStream: () => void;
}

// Stream state for validation
type StreamState = 'idle' | 'streaming' | 'completing' | 'completed' | 'error';

export function useConversationStream({
  projectId,
  conversationId,
  maxRetries = 3,
  retryDelayMs = 1000,
  onMessage,
  onContentBlock,
  onComplete,
  onError
}: UseConversationStreamOptions): UseConversationStreamReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [contentBlocks, setContentBlocks] = useState<StreamingContentBlock[]>([]);
  const [toolCalls, setToolCalls] = useState<StreamingMessage[]>([]); // Legacy

  // Refs for mutable state (avoid re-renders during streaming)
  const eventSourceRef = useRef<EventSource | null>(null);
  const contentBlocksRef = useRef<StreamingContentBlock[]>([]);
  const thinkingIdRef = useRef<string | null>(null);
  const currentTextBlockIdRef = useRef<string | null>(null);

  // RAF-based batching for backpressure handling
  const pendingUpdatesRef = useRef<StreamingContentBlock[] | null>(null);
  const rafIdRef = useRef<number | null>(null);

  // Reconnection state
  const retryCountRef = useRef(0);
  const currentMessageIdRef = useRef<string | null>(null);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Event validation state
  const streamStateRef = useRef<StreamState>('idle');
  const receivedToolUseIds = useRef<Set<string>>(new Set());
  const receivedToolResultIds = useRef<Set<string>>(new Set());
  const pendingToolResults = useRef<Map<string, { output: string; is_error: boolean }>>(new Map());

  // Store callbacks in refs to avoid recreating startStreaming
  const onMessageRef = useRef(onMessage);
  const onContentBlockRef = useRef(onContentBlock);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  // Update refs when callbacks change
  useEffect(() => {
    onMessageRef.current = onMessage;
    onContentBlockRef.current = onContentBlock;
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;
  }, [onMessage, onContentBlock, onComplete, onError]);

  // Store connection params in refs
  const projectIdRef = useRef(projectId);
  const conversationIdRef = useRef(conversationId);
  const maxRetriesRef = useRef(maxRetries);
  const retryDelayMsRef = useRef(retryDelayMs);

  useEffect(() => {
    projectIdRef.current = projectId;
    conversationIdRef.current = conversationId;
    maxRetriesRef.current = maxRetries;
    retryDelayMsRef.current = retryDelayMs;
  }, [projectId, conversationId, maxRetries, retryDelayMs]);

  // Derive streamedContent and streamedThinking from contentBlocks (single source of truth)
  const streamedContent = useMemo(() =>
    contentBlocks
      .filter((b): b is StreamingTextBlock => b.type === 'text')
      .map(b => b.text)
      .join(''),
    [contentBlocks]
  );

  const streamedThinking = useMemo(() =>
    contentBlocks
      .filter((b): b is StreamingThinkingBlock => b.type === 'thinking')
      .map(b => b.thinking)
      .join(''),
    [contentBlocks]
  );

  // Schedule batched React update using RAF for backpressure handling
  const scheduleUpdate = useCallback((newBlocks: StreamingContentBlock[]) => {
    pendingUpdatesRef.current = newBlocks;

    if (rafIdRef.current === null) {
      rafIdRef.current = requestAnimationFrame(() => {
        if (pendingUpdatesRef.current) {
          setContentBlocks(pendingUpdatesRef.current);
          pendingUpdatesRef.current = null;
        }
        rafIdRef.current = null;
      });
    }
  }, []);

  // Comprehensive cleanup
  const cleanupStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    pendingToolResults.current.clear();
    receivedToolUseIds.current.clear();
    receivedToolResultIds.current.clear();
    pendingUpdatesRef.current = null;
  }, []);

  const stopStreaming = useCallback(() => {
    cleanupStream();
    retryCountRef.current = 0;
    streamStateRef.current = 'idle';
    setIsStreaming(false);
  }, [cleanupStream]);

  const resetStream = useCallback(() => {
    stopStreaming();
    setContentBlocks([]);
    setToolCalls([]);
    contentBlocksRef.current = [];
    thinkingIdRef.current = null;
    currentTextBlockIdRef.current = null;
    currentMessageIdRef.current = null;
  }, [stopStreaming]);

  // Cleanup on unmount or conversation change
  useEffect(() => {
    return () => {
      cleanupStream();
    };
  }, [conversationId, cleanupStream]);

  // Stable startStreaming that doesn't change unless absolutely necessary
  const startStreaming = useCallback((messageId: string) => {
    // Prevent multiple EventSource creation
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Store message ID for potential reconnection
    currentMessageIdRef.current = messageId;

    // Reset state for new stream (only on first attempt, not retries)
    if (retryCountRef.current === 0) {
      setContentBlocks([]);
      setToolCalls([]);
      contentBlocksRef.current = [];
      thinkingIdRef.current = null;
      currentTextBlockIdRef.current = null;
      pendingToolResults.current.clear();
      receivedToolUseIds.current.clear();
      receivedToolResultIds.current.clear();
    }

    streamStateRef.current = 'streaming';
    setIsStreaming(true);

    // Use refs for current values
    const currentProjectId = projectIdRef.current;
    const currentConversationId = conversationIdRef.current;

    // Connect to SSE stream
    const streamUrl = `/api/conversations/${currentConversationId}/stream?projectId=${currentProjectId}&messageId=${messageId}`;
    const eventSource = new EventSource(streamUrl);
    eventSourceRef.current = eventSource;

    console.log(`[ConversationStream] EventSource created for message ${messageId} (attempt ${retryCountRef.current + 1})`);

    // Reset retry count on successful connection
    eventSource.onopen = () => {
      console.log(`[ConversationStream] Connection opened for message ${messageId}`);
      retryCountRef.current = 0;
    };

    // Handle connection errors with reconnection
    eventSource.onerror = (error) => {
      console.error("[ConversationStream] Stream error:", error);

      // Only attempt reconnection if the connection was closed
      if (eventSource.readyState === EventSource.CLOSED) {
        eventSourceRef.current?.close();
        eventSourceRef.current = null;

        const currentMaxRetries = maxRetriesRef.current;
        const currentRetryDelay = retryDelayMsRef.current;

        if (retryCountRef.current < currentMaxRetries) {
          const delay = currentRetryDelay * Math.pow(2, retryCountRef.current);
          retryCountRef.current++;
          console.log(`[ConversationStream] Attempting reconnection in ${delay}ms (attempt ${retryCountRef.current}/${currentMaxRetries})`);

          retryTimeoutRef.current = setTimeout(() => {
            if (currentMessageIdRef.current) {
              startStreaming(currentMessageIdRef.current);
            }
          }, delay);
        } else {
          console.error(`[ConversationStream] Max retries (${currentMaxRetries}) exceeded`);
          streamStateRef.current = 'error';
          onErrorRef.current?.(`Connection failed after ${currentMaxRetries} retries`);
          setIsStreaming(false);
        }
      }
    };

    // Handle message chunks (text) with backpressure handling
    eventSource.addEventListener("message_chunk", (event) => {
      try {
        const data = JSON.parse(event.data);
        const textChunk = data.content_chunk || data.text;
        if (textChunk) {
          // Update ref immediately (no React render)
          const blocks = contentBlocksRef.current;
          const lastBlock = blocks[blocks.length - 1];

          if (lastBlock?.type === 'text' && currentTextBlockIdRef.current) {
            // Mutate existing text block in ref
            (lastBlock as StreamingTextBlock).text += textChunk;
          } else {
            // Create new text block with stable ID
            const newTextId = generateBlockId('text');
            currentTextBlockIdRef.current = newTextId;
            blocks.push({ type: 'text', id: newTextId, text: textChunk });
          }

          // Schedule batched React update
          scheduleUpdate([...blocks]);

          onMessageRef.current?.({ type: 'text', content: textChunk });
          // Pass block with full accumulated text
          const currentTextBlock = blocks.find(b => b.type === 'text' && b.id === currentTextBlockIdRef.current) as StreamingTextBlock | undefined;
          if (currentTextBlock) {
            onContentBlockRef.current?.(currentTextBlock);
          }
        }
      } catch (e) {
        console.error("[useConversationStream] Error parsing message_chunk:", e);
      }
    });

    // Handle thinking events with stable ID tracking
    eventSource.addEventListener("thinking", (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.thinking) {
          const blocks = contentBlocksRef.current;

          // Get or create thinking block ID
          const thinkingId = thinkingIdRef.current || generateBlockId('thinking');
          thinkingIdRef.current = thinkingId;

          const existingIdx = blocks.findIndex(b => b.type === 'thinking' && b.id === thinkingId);

          if (existingIdx >= 0) {
            // Update existing thinking block
            const existingBlock = blocks[existingIdx] as StreamingThinkingBlock;
            existingBlock.thinking += data.thinking;
            if (data.signature) {
              existingBlock.signature = data.signature;
            }
          } else {
            // Add new thinking block at the beginning
            const thinkingBlock: StreamingThinkingBlock = {
              type: 'thinking',
              id: thinkingId,
              thinking: data.thinking,
              signature: data.signature
            };
            blocks.unshift(thinkingBlock);
          }

          scheduleUpdate([...blocks]);

          onMessageRef.current?.({
            type: 'thinking',
            content: data.thinking,
            signature: data.signature
          });

          const currentThinkingBlock = blocks.find(b => b.type === 'thinking' && b.id === thinkingId) as StreamingThinkingBlock | undefined;
          if (currentThinkingBlock) {
            onContentBlockRef.current?.(currentThinkingBlock);
          }
        }
      } catch (e) {
        console.error("[ConversationStream] Error parsing thinking:", e);
      }
    });

    // Handle tool use with pending result check
    eventSource.addEventListener("tool_use", (event) => {
      try {
        const data = JSON.parse(event.data);
        const toolName = data.tool_name || data.name;
        const toolId = data.tool_id || data.id;

        // Track for validation
        receivedToolUseIds.current.add(toolId);

        // Check for pending result (handles race condition)
        const pendingResult = pendingToolResults.current.get(toolId);

        const toolBlock: StreamingToolUseBlock = {
          type: 'tool_use',
          id: toolId,
          name: toolName,
          input: data.input || {},
          output: pendingResult?.output ?? null,
          is_error: pendingResult?.is_error ?? false,
          active_description: data.active_description
        };

        if (pendingResult) {
          pendingToolResults.current.delete(toolId);
          console.log(`[ConversationStream] Applied pending result for tool ${toolId}`);
        }

        // Reset text block ID so next text chunk creates new block
        currentTextBlockIdRef.current = null;

        contentBlocksRef.current.push(toolBlock);
        scheduleUpdate([...contentBlocksRef.current]);

        // Legacy support
        const toolMessage: StreamingMessage = {
          type: 'tool_use',
          content: `Using tool: ${toolName}`,
          toolName: toolName,
          toolId: toolId,
          toolInput: data.input
        };
        setToolCalls(prev => [...prev, toolMessage]);

        onMessageRef.current?.(toolMessage);
        onContentBlockRef.current?.(toolBlock);
      } catch (e) {
        console.error("[ConversationStream] Error parsing tool_use:", e);
      }
    });

    // Handle tool result with race condition handling
    eventSource.addEventListener("tool_result", (event) => {
      try {
        const data = JSON.parse(event.data);
        const toolId = data.tool_id || data.id;

        // Check for duplicate
        if (receivedToolResultIds.current.has(toolId)) {
          console.warn(`[ConversationStream] Duplicate tool_result for ${toolId}, ignoring`);
          return;
        }
        receivedToolResultIds.current.add(toolId);

        const blocks = contentBlocksRef.current;
        const toolBlockIdx = blocks.findIndex(b => b.type === 'tool_use' && b.id === toolId);

        if (toolBlockIdx >= 0) {
          // Tool block exists, update it
          const toolBlock = blocks[toolBlockIdx] as StreamingToolUseBlock;
          toolBlock.output = data.output || '';
          toolBlock.is_error = data.is_error || false;

          // Reset text block ID so next text chunk creates new block
          currentTextBlockIdRef.current = null;

          scheduleUpdate([...blocks]);
        } else {
          // Tool block doesn't exist yet (race condition), queue the result
          console.log(`[ConversationStream] Queueing result for pending tool ${toolId}`);
          pendingToolResults.current.set(toolId, {
            output: data.output || '',
            is_error: data.is_error || false
          });
        }

        // Legacy support
        const resultMessage: StreamingMessage = {
          type: 'tool_result',
          content: data.output || '',
          toolId: toolId,
          isError: data.is_error
        };
        setToolCalls(prev => [...prev, resultMessage]);

        onMessageRef.current?.(resultMessage);
      } catch (e) {
        console.error("[ConversationStream] Error parsing tool_result:", e);
      }
    });

    // Handle completion with validation
    const handleComplete = (data: { is_error?: boolean; session_id?: string }) => {
      // Validate: warn if there are pending tool results
      const pendingTools = [...receivedToolUseIds.current]
        .filter(id => !receivedToolResultIds.current.has(id));

      if (pendingTools.length > 0) {
        console.warn(`[ConversationStream] Stream completed with pending tool results:`, pendingTools);
      }

      if (pendingToolResults.current.size > 0) {
        console.warn(`[ConversationStream] Stream completed with unmatched tool results:`, [...pendingToolResults.current.keys()]);
      }

      streamStateRef.current = 'completed';

      // Flush any pending RAF updates before completing
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
      }
      if (pendingUpdatesRef.current) {
        setContentBlocks(pendingUpdatesRef.current);
        pendingUpdatesRef.current = null;
      }

      // Provide final content blocks to completion callback
      onCompleteRef.current?.({
        isError: data.is_error || false,
        sessionId: data.session_id,
        finalContentBlocks: [...contentBlocksRef.current]
      });

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setIsStreaming(false);
    };

    // Handle completion - backend sends "message_complete" event
    eventSource.addEventListener("message_complete", (event) => {
      try {
        const data = JSON.parse(event.data);
        handleComplete(data);
      } catch (e) {
        console.error("[useConversationStream] Error parsing message_complete:", e);
        handleComplete({});
      }
    });

    // Also listen for "result" for backwards compatibility
    eventSource.addEventListener("result", (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("[ConversationStream] Stream complete (result):", data);
        handleComplete(data);
      } catch (e) {
        console.error("[ConversationStream] Error parsing result:", e);
        handleComplete({});
      }
    });

    // Handle error events from SSE
    eventSource.addEventListener("error", (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data);
        console.error("[ConversationStream] Error event:", data);
        streamStateRef.current = 'error';
        onErrorRef.current?.(data.error || "Unknown error");
      } catch {
        // Not a JSON error event, handled by onerror
        console.error("[ConversationStream] Error event (non-JSON):", event);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setIsStreaming(false);
    });

  }, [scheduleUpdate]); // Only depends on scheduleUpdate which is stable

  return {
    isStreaming,
    streamedContent,
    streamedThinking,
    contentBlocks,
    toolCalls, // Legacy
    startStreaming,
    stopStreaming,
    resetStream
  };
}
