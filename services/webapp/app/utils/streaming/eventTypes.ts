/**
 * Event types and payloads for the streaming system
 */

export enum StreamEventType {
  // Connection events
  STREAM_START = 'stream:start',
  STREAM_ERROR = 'stream:error',
  STREAM_END = 'stream:end',

  // Message events
  MESSAGE_START = 'message:start',
  MESSAGE_CHUNK = 'message:chunk',
  MESSAGE_COMPLETE = 'message:complete',

  // Tool events
  TOOL_USE_START = 'tool:start',
  TOOL_USE_COMPLETE = 'tool:complete',
  TOOL_USE_ERROR = 'tool:error',

  // Metadata events
  METADATA_UPDATE = 'metadata:update',

  // Progressive message events
  ASSISTANT_SECTION = 'assistant:section',
  FINAL_RESPONSE = 'final:response',

  // Streaming block events
  THINKING_BLOCK = 'block:thinking',
  TEXT_BLOCK = 'block:text',
  TOOL_RESULT = 'tool:result',

  // User interaction events
  USER_MESSAGE_SUBMIT = 'user:message:submit',

  // Task lifecycle events
  TASK_TIMEOUT = 'task:timeout'
}

// Event payload types
export interface StreamStartPayload {
  taskId: string;
  agentId: string;
}

export interface StreamErrorPayload {
  taskId: string;
  agentId: string;
  error: Error | string;
}

export interface StreamEndPayload {
  taskId: string;
  agentId: string;
}

export interface MessageStartPayload {
  taskId: string;
  role: 'assistant' | 'user';
}

export interface MessageChunkPayload {
  taskId: string;
  content?: string;
  status?: string;
}

export interface MessageCompletePayload {
  taskId: string;
}

export interface ToolUseStartPayload {
  taskId: string;
  toolId: string;
  toolName: string;
  input: Record<string, any>;
}

export interface ToolUseCompletePayload {
  taskId: string;
  toolId: string;
  toolName: string;
  input: Record<string, any>;
  result?: any;
  isError?: boolean;
}

export interface ToolUseErrorPayload {
  taskId: string;
  toolId: string;
  error: string;
}

export interface MetadataUpdatePayload {
  taskId: string;
  text?: string;
  metadata?: Record<string, any>;
}

export interface AssistantSectionPayload {
  taskId: string;
  text: string;
  blocks?: any[]; // Array of AssistantMessageBlock
  messageType?: string;
  isComplete?: boolean;
}

export interface FinalResponsePayload {
  taskId: string;
  response: string;
}

export interface UserMessageSubmitPayload {
  text: string;
  initialPosition: {
    bottom: number;
    left: number;
    width: number;
  };
  timestamp: number;
}

export interface TaskTimeoutPayload {
  taskId: string;
  message?: string;
}

export interface ThinkingBlockPayload {
  taskId: string;
  thinking: string;
  signature?: string;
}

export interface TextBlockPayload {
  taskId: string;
  text: string;
}

export interface ToolResultPayload {
  taskId: string;
  toolUseId: string;
  content: any;
  isError?: boolean;
}

// Type mapping for events
export interface StreamEventMap {
  [StreamEventType.STREAM_START]: StreamStartPayload;
  [StreamEventType.STREAM_ERROR]: StreamErrorPayload;
  [StreamEventType.STREAM_END]: StreamEndPayload;
  [StreamEventType.MESSAGE_START]: MessageStartPayload;
  [StreamEventType.MESSAGE_CHUNK]: MessageChunkPayload;
  [StreamEventType.MESSAGE_COMPLETE]: MessageCompletePayload;
  [StreamEventType.TOOL_USE_START]: ToolUseStartPayload;
  [StreamEventType.TOOL_USE_COMPLETE]: ToolUseCompletePayload;
  [StreamEventType.TOOL_USE_ERROR]: ToolUseErrorPayload;
  [StreamEventType.METADATA_UPDATE]: MetadataUpdatePayload;
  [StreamEventType.ASSISTANT_SECTION]: AssistantSectionPayload;
  [StreamEventType.FINAL_RESPONSE]: FinalResponsePayload;
  [StreamEventType.THINKING_BLOCK]: ThinkingBlockPayload;
  [StreamEventType.TEXT_BLOCK]: TextBlockPayload;
  [StreamEventType.TOOL_RESULT]: ToolResultPayload;
  [StreamEventType.USER_MESSAGE_SUBMIT]: UserMessageSubmitPayload;
  [StreamEventType.TASK_TIMEOUT]: TaskTimeoutPayload;
}
