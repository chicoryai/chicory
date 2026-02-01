// Type definitions for Audit Trail components

// Base trail item interface
export interface TrailItem {
  id: string;
  message_id: number;
  message_type: string;
  timestamp: string;
  structured_data: StructuredData;
}

// Structured data can be different types based on message_type
export type StructuredData = 
  | SystemMessageData 
  | AssistantMessageData 
  | UserMessageData 
  | ResultMessageData
  | DictMessageData;

// System message for initialization
export interface SystemMessageData {
  type: 'SystemMessage';
  content: {
    subtype: 'init';
    data: {
      type: 'system';
      subtype: 'init';
      cwd: string;
      session_id: string;
      tools: string[];
      mcp_servers: any[];
      model: string;
      permissionMode: string;
      slash_commands: string[];
      apiKeySource: string;
      output_style: string;
      uuid: string;
    };
  };
}

// Assistant message with content blocks
export interface ThinkingBlock {
  type: 'ThinkingBlock' | 'thinking';
  thinking: string;
  signature?: string;
}

export type AssistantMessageBlock = TextBlock | ToolUseBlock | ThinkingBlock | Record<string, unknown>;

export type AssistantMessageContent =
  | AssistantMessageBlock[]
  | {
      content?: AssistantMessageBlock[] | null;
      blocks?: AssistantMessageBlock[] | null;
      [key: string]: unknown;
    }
  | string
  | null
  | undefined;

export interface AssistantMessageData {
  type: 'AssistantMessage';
  content?: AssistantMessageContent;
}

export interface TextBlock {
  type: 'TextBlock';
  text: string;
}

export interface ToolUseBlock {
  type: 'ToolUseBlock';
  id: string;
  name: string;
  input: Record<string, any>;
}

// User message with tool results
export type UserMessageContent =
  | ToolResultBlock[]
  | {
      content?: ToolResultBlock[] | null;
      results?: ToolResultBlock[] | null;
      [key: string]: unknown;
    }
  | string
  | null
  | undefined;

export interface UserMessageData {
  type: 'UserMessage';
  content?: UserMessageContent;
}

export type ToolResultContent =
  | string
  | Array<{ [key: string]: unknown }>
  | Record<string, unknown>
  | null
  | undefined;

export interface ToolResultBlock {
  type: 'ToolResultBlock';
  tool_use_id: string;
  content: ToolResultContent;
  is_error?: boolean | null;
}

// Result message with execution metadata
export interface ResultMessageData {
  type: 'ResultMessage';
  content: {
    subtype: 'success' | 'error';
    duration_ms: number;
    duration_api_ms: number;
    is_error: boolean;
    num_turns: number;
    session_id: string;
    total_cost_usd: number;
    usage: string;
    result: string;
  };
}

// Dict message (fallback type)
export interface DictMessageData {
  role: string;
  content: {
    raw_content: string;
  };
}

// Helper type guards
export function isSystemMessage(data: StructuredData): data is SystemMessageData {
  return Boolean(data) && typeof (data as any).type === 'string' && (data as any).type === 'SystemMessage';
}

export function isAssistantMessage(data: StructuredData): data is AssistantMessageData {
  return Boolean(data) && typeof (data as any).type === 'string' && (data as any).type === 'AssistantMessage';
}

export function isUserMessage(data: StructuredData): data is UserMessageData {
  return Boolean(data) && typeof (data as any).type === 'string' && (data as any).type === 'UserMessage';
}

export function isResultMessage(data: StructuredData): data is ResultMessageData {
  return Boolean(data) && typeof (data as any).type === 'string' && (data as any).type === 'ResultMessage';
}

export function isDictMessage(data: StructuredData): data is DictMessageData {
  return Boolean(data) && typeof data === 'object' && data !== null && 'role' in data && !('type' in data);
}

// ============================================
// Helper extractors for flexible data shapes
// ============================================

const isAssistantBlocksArray = (value: unknown): value is AssistantMessageBlock[] =>
  Array.isArray(value) && value.every(block => block !== null && typeof block === 'object');

const isToolResultArray = (value: unknown): value is ToolResultBlock[] =>
  Array.isArray(value) && value.every(result => result && typeof result === 'object' && 'tool_use_id' in result);

export function extractAssistantBlocks(data?: AssistantMessageData | null): AssistantMessageBlock[] {
  if (!data) return [];
  const raw = data.content as any;

  if (isAssistantBlocksArray(raw)) {
    return raw;
  }

  if (raw && typeof raw === 'object') {
    if (isAssistantBlocksArray(raw.content)) {
      return raw.content;
    }

    if (isAssistantBlocksArray(raw.blocks)) {
      return raw.blocks;
    }

    if (typeof raw.type === 'string' && (raw.text || raw.content)) {
      return [raw];
    }
  }

  if (typeof raw === 'string' && raw.trim().length > 0) {
    return [{ type: 'TextBlock', text: raw } as AssistantMessageBlock];
  }

  return [];
}

export function extractToolResultBlocks(data?: UserMessageData | null): ToolResultBlock[] {
  if (!data) return [];
  const raw = data.content as any;

  if (isToolResultArray(raw)) {
    return raw;
  }

  if (raw && typeof raw === 'object') {
    if (isToolResultArray(raw.content)) {
      return raw.content;
    }
    if (isToolResultArray(raw.results)) {
      return raw.results;
    }
  }

  return [];
}

// ============================================
// Normalization helpers used across UI components
// ============================================

export function parseStructuredData(raw: unknown): StructuredData | Record<string, unknown> | null {
  if (raw == null) return null;
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw) as StructuredData;
    } catch (error) {
      console.warn('[auditTrail] Failed to parse structured_data JSON', { error });
      return null;
    }
  }
  if (typeof raw === 'object') {
    return raw as StructuredData | Record<string, unknown>;
  }
  return null;
}

export interface ShouldDisplayOptions {
  includeUserMessages?: boolean;
}

export function shouldDisplayTrailItem(
  item: { message_type?: string; structured_data?: unknown },
  parsed?: StructuredData | Record<string, unknown> | null,
  options: ShouldDisplayOptions = {}
): boolean {
  const { includeUserMessages = false } = options;

  if (item.message_type === 'SystemMessage') {
    return false;
  }

  if (!includeUserMessages && item.message_type === 'UserMessage') {
    return false;
  }

  const data = parsed ?? parseStructuredData(item.structured_data);

  if (data && typeof data === 'object') {
    if ('type' in data && typeof (data as any).type === 'string' && (data as any).type === 'SystemMessage') {
      return false;
    }

    if ('role' in data && typeof (data as any).role === 'string') {
      return false;
    }
  }

  return true;
}
