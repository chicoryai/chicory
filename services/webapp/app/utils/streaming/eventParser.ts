/**
 * Parser for SSE events from the streaming API
 */

import { streamEventBus } from './eventBus';
import { StreamEventType } from './eventTypes';
import type { MessageChunkPayload } from './eventTypes';

// Map to track pending tool uses waiting for their results
// Key: tool_use_id, Value: { taskId, toolName, input }
const pendingToolUses = new Map<string, { taskId: string; toolName: string; input: Record<string, any> }>();

/**
 * Parse SSE events and emit to the event bus
 */
export function parseSSEEvent(event: MessageEvent, taskId: string, agentId: string): void {
  try {
    // Parse the event data
    const data = event.data ? JSON.parse(event.data) : {};

    switch (event.type) {
      case 'message_start':
        handleMessageStart(taskId, agentId, data);
        break;

      case 'message_chunk':
        handleMessageChunk(taskId, agentId, data);
        break;

      case 'message_complete':
        handleMessageComplete(taskId, agentId, data);
        break;

      case 'claude_code_message':
        handleClaudeCodeMessage(taskId, agentId, data);
        break;

      case 'done':
        handleStreamComplete(taskId, agentId);
        break;

      case 'task_timeout':
        handleTaskTimeout(taskId, agentId, data);
        break;

      default:
        console.log(`[EventParser] Unknown event type: ${event.type}`, data);
    }
  } catch (error) {
    console.error(`[EventParser] Error parsing SSE event:`, error, event);
    streamEventBus.emit(StreamEventType.STREAM_ERROR, {
      taskId,
      agentId,
      error: error instanceof Error ? error : new Error(String(error))
    });
  }
}

function handleMessageStart(taskId: string, agentId: string, data: any): void {
  streamEventBus.emit(StreamEventType.MESSAGE_START, {
    taskId,
    role: 'assistant'
  });
}

function handleMessageChunk(taskId: string, agentId: string, data: any): void {
  // Parse the nested JSON in content_chunk
  if (data.content_chunk) {
    try {
      const chunkContent = JSON.parse(data.content_chunk);
      const responseText = chunkContent?.response;
      const statusText = chunkContent?.status;

      const payload: MessageChunkPayload = { taskId };

      if (typeof statusText === 'string') {
        const normalizedStatus = statusText.trim();
        if (normalizedStatus.length > 0) {
          payload.status = normalizedStatus;
        }
      }

      if (typeof responseText === 'string') {
        payload.content = responseText;
      }

      if (payload.status !== undefined || payload.content !== undefined) {
        streamEventBus.emit(StreamEventType.MESSAGE_CHUNK, payload);
      }
    } catch (error) {
      console.error('[EventParser] Error parsing message_chunk content:', error);
    }
  }
}

function handleMessageComplete(taskId: string, agentId: string, data: any): void {
  // Skip message_content - don't emit FINAL_RESPONSE
  // if (data && data.message_content && data.message_content.response) {
  //   // Emit final response that replaces everything
  //   streamEventBus.emit(StreamEventType.FINAL_RESPONSE, {
  //     taskId,
  //     response: data.message_content.response
  //   });
  // }

  streamEventBus.emit(StreamEventType.MESSAGE_COMPLETE, {
    taskId
  });
}

function handleClaudeCodeMessage(taskId: string, agentId: string, data: any): void {
  if (data.message_type === 'AssistantMessage') {
    try {
      const parsed = JSON.parse(data.structured_data);
      const content = parsed.content || [];

      // Emit the full assistant section with structured blocks (backwards compatibility)
      streamEventBus.emit(StreamEventType.ASSISTANT_SECTION, {
        taskId,
        text: '',
        blocks: content,
        messageType: 'AssistantMessage',
        isComplete: false
      });

      // Emit individual block events for fine-grained handling
      content.forEach((block: any) => {
        if (block.type === 'ThinkingBlock' || block.type === 'thinking') {
          streamEventBus.emit(StreamEventType.THINKING_BLOCK, {
            taskId,
            thinking: block.thinking || '',
            signature: block.signature
          });
        } else if (block.type === 'TextBlock') {
          streamEventBus.emit(StreamEventType.TEXT_BLOCK, {
            taskId,
            text: block.text || ''
          });
        } else if (block.type === 'ToolUseBlock') {
          const toolId = block.id || `tool-${Date.now()}`;

          // Store pending tool use for later matching with result
          pendingToolUses.set(toolId, {
            taskId,
            toolName: block.name,
            input: block.input || {}
          });

          // Also emit TOOL_USE_START for backwards compatibility
          streamEventBus.emit(StreamEventType.TOOL_USE_START, {
            taskId,
            toolId,
            toolName: block.name,
            input: block.input || {}
          });
        }
      });
    } catch (error) {
      console.error('[EventParser] Error parsing AssistantMessage:', error);
    }
  } else if (data.message_type === 'UserMessage') {
    try {
      const parsed = JSON.parse(data.structured_data);
      const content = parsed.content || [];

      // Extract tool results and match with pending tool uses
      content.forEach((block: any) => {
        if (block.type === 'ToolResultBlock') {
          const toolUseId = block.tool_use_id;

          // Emit the tool result event
          streamEventBus.emit(StreamEventType.TOOL_RESULT, {
            taskId,
            toolUseId,
            content: block.content,
            isError: block.is_error || false
          });

          // Check if we have a pending tool use for this result
          const pendingTool = pendingToolUses.get(toolUseId);
          if (pendingTool) {
            // Emit combined tool use + result event
            streamEventBus.emit(StreamEventType.TOOL_USE_COMPLETE, {
              taskId,
              toolId: toolUseId,
              toolName: pendingTool.toolName,
              input: pendingTool.input,
              result: block.content,
              isError: block.is_error || false
            });

            // Clean up the pending tool use
            pendingToolUses.delete(toolUseId);
          }
        }
      });
    } catch (error) {
      console.error('[EventParser] Error parsing UserMessage:', error);
    }
  } else if (data.message_type === 'ResultMessage') {
    console.log('[EventParser] ResultMessage received:', data);
  }
}

function handleStreamComplete(taskId: string, agentId: string): void {
  streamEventBus.emit(StreamEventType.MESSAGE_COMPLETE, { taskId });
  streamEventBus.emit(StreamEventType.STREAM_END, { taskId, agentId });

  // Clean up any pending tool uses for this task
  for (const [toolId, pendingTool] of pendingToolUses.entries()) {
    if (pendingTool.taskId === taskId) {
      pendingToolUses.delete(toolId);
    }
  }
}

function handleTaskTimeout(taskId: string, agentId: string, data: any): void {
  const message = getTimeoutMessage(data);

  streamEventBus.emit(StreamEventType.TASK_TIMEOUT, {
    taskId,
    message
  });

  // Ensure UI consumers stop treating this task as streaming
  streamEventBus.emit(StreamEventType.MESSAGE_COMPLETE, { taskId });
  streamEventBus.emit(StreamEventType.STREAM_END, { taskId, agentId });
}

function getTimeoutMessage(data: any): string | undefined {
  const candidates = [
    data?.message,
    data?.task,
    data?.detail,
    data?.error,
    data?.reason
  ];

  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.trim().length > 0) {
      return candidate.trim();
    }
  }

  return undefined;
}
