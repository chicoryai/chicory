/**
 * Type definitions for Claude Code messages
 * Based on the Python dataclass structure from the backend
 */

// ============================================
// Content Block Types
// ============================================

export interface TextBlock {
  type: 'text';
  text: string;
}

export interface ThinkingBlock {
  type: 'thinking';
  thinking: string;
  signature: string;
}

export interface ToolUseBlock {
  type: 'tool_use';
  id: string;
  name: string;
  input: Record<string, any>;
}

export interface ToolResultBlock {
  type: 'tool_result';
  tool_use_id: string;
  content?: string | Record<string, any>[] | null;
  is_error?: boolean | null;
}

// Union type for all content blocks
export type ContentBlock = TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock;

// ============================================
// Message Types
// ============================================

export interface UserMessage {
  type: 'UserMessage';
  content: string | ContentBlock[];
}

export interface AssistantMessage {
  type: 'AssistantMessage';
  content: ContentBlock[];
  model?: string;
}

export interface SystemMessage {
  type: 'SystemMessage';
  subtype: string;
  data: Record<string, any>;
}

export interface ResultMessage {
  type: 'ResultMessage';
  subtype: string;
  duration_ms: number;
  duration_api_ms: number;
  is_error: boolean;
  num_turns: number;
  session_id: string;
  total_cost_usd?: number | null;
  usage?: Record<string, any> | null;
  result?: string | null;
}

// Union type for all messages
export type Message = UserMessage | AssistantMessage | SystemMessage | ResultMessage;

// ============================================
// Event Types
// ============================================

export interface ClaudeCodeMessageEvent {
  id: string;
  message_id: string;
  message_type: 'UserMessage' | 'AssistantMessage' | 'SystemMessage' | 'ResultMessage';
  message: string; // String representation of the message
  timestamp: string;
  structured_data?: {
    type: string;
    content?: any;
    [key: string]: any;
  };
}

// ============================================
// Type Guards
// ============================================

// Content block type guards
export function isTextBlock(block: ContentBlock): block is TextBlock {
  return block.type === 'text';
}

export function isToolUseBlock(block: ContentBlock): block is ToolUseBlock {
  return block.type === 'tool_use';
}

export function isThinkingBlock(block: ContentBlock): block is ThinkingBlock {
  return block.type === 'thinking';
}

export function isToolResultBlock(block: ContentBlock): block is ToolResultBlock {
  return block.type === 'tool_result';
}

// Message type guards
export function isAssistantMessage(msg: any): msg is AssistantMessage {
  return msg && msg.type === 'AssistantMessage';
}

export function isUserMessage(msg: any): msg is UserMessage {
  return msg && msg.type === 'UserMessage';
}

export function isSystemMessage(msg: any): msg is SystemMessage {
  return msg && msg.type === 'SystemMessage';
}

export function isResultMessage(msg: any): msg is ResultMessage {
  return msg && msg.type === 'ResultMessage';
}

// ============================================
// Helper Types
// ============================================

// Parsed content structure for UI rendering
export interface ParsedClaudeContent {
  blocks: Array<{
    type: 'text' | 'tool_use' | 'thinking' | 'tool_result' | 'result' | 'raw';
    content?: string;
    name?: string;
    id?: string;
    input?: Record<string, any>;
    duration_ms?: string | null;
    cost?: string | null;
    turns?: string | null;
    raw?: string;
  }>;
}

// UI display states
export interface ClaudeCodeUIState {
  expandedBlocks: Record<string, boolean>;
  searchQuery: string;
  filterType: 'all' | 'UserMessage' | 'AssistantMessage' | 'SystemMessage' | 'ResultMessage';
}

// ============================================
// Utility Functions
// ============================================

/**
 * Parse Python-style dictionary/JSON strings to JavaScript objects
 */
function parsePythonDict(dictStr: string): any {
  try {
    // Handle Python None -> null, True -> true, False -> false
    let jsonStr = dictStr
      .replace(/None/g, 'null')
      .replace(/True/g, 'true')
      .replace(/False/g, 'false')
      .replace(/'/g, '"'); // Convert single quotes to double quotes
    
    return JSON.parse(jsonStr);
  } catch (e) {
    // If parsing fails, return the raw string
    return { raw: dictStr };
  }
}

/**
 * Parse content blocks from a Python dataclass string representation
 * Handles all block types: TextBlock, ToolUseBlock, ToolResultBlock, ThinkingBlock
 */
export function parseContentBlocksString(contentStr: string): ContentBlock[] {
  const blocks: ContentBlock[] = [];
  
  // Parse ToolUseBlock entries
  const toolUseRegex = /ToolUseBlock\(id='([^']+)',\s*name='([^']+)',\s*input=(\{[^}]*\})\)/g;
  let match;
  let lastIndex = 0;
  
  while ((match = toolUseRegex.exec(contentStr)) !== null) {
    blocks.push({
      type: 'tool_use',
      id: match[1],
      name: match[2],
      input: parsePythonDict(match[3])
    });
    lastIndex = match.index + match[0].length;
  }
  
  // Parse ToolResultBlock entries
  const toolResultRegex = /ToolResultBlock\(tool_use_id='([^']+)'(?:,\s*content=([^,)]+))?(?:,\s*is_error=(True|False))?\)/g;
  toolResultRegex.lastIndex = 0;
  
  while ((match = toolResultRegex.exec(contentStr)) !== null) {
    const block: ToolResultBlock = {
      type: 'tool_result',
      tool_use_id: match[1]
    };
    
    if (match[2]) {
      // Parse content - could be string or dict
      if (match[2].startsWith("'") && match[2].endsWith("'")) {
        block.content = match[2].slice(1, -1);
      } else {
        block.content = parsePythonDict(match[2]);
      }
    }
    
    if (match[3]) {
      block.is_error = match[3] === 'True';
    }
    
    blocks.push(block);
  }
  
  // Parse TextBlock entries
  const textBlockRegex = /TextBlock\(text='([^']+)'\)/g;
  textBlockRegex.lastIndex = 0;
  
  while ((match = textBlockRegex.exec(contentStr)) !== null) {
    blocks.push({
      type: 'text',
      text: match[1]
    });
  }
  
  // Parse ThinkingBlock entries
  const thinkingBlockRegex = /ThinkingBlock\(thinking='([^']+)',\s*signature='([^']+)'\)/g;
  thinkingBlockRegex.lastIndex = 0;
  
  while ((match = thinkingBlockRegex.exec(contentStr)) !== null) {
    blocks.push({
      type: 'thinking',
      thinking: match[1],
      signature: match[2]
    });
  }
  
  return blocks;
}

/**
 * Parse an AssistantMessage string representation into structured data
 * Handles strings like: "AssistantMessage(content=[ToolUseBlock(id='...', name='Read', input={...})])"
 */
export function parseAssistantMessageString(messageStr: string): ContentBlock[] {
  // Extract content array from AssistantMessage(content=[...])
  const contentMatch = messageStr.match(/AssistantMessage\(content=\[(.*)\]\)/s);
  if (!contentMatch) {
    // If it doesn't match the expected format, treat as plain text
    return [{ type: 'text', text: messageStr }];
  }
  
  const blocks = parseContentBlocksString(contentMatch[1]);
  
  // If no blocks were parsed, return the original string as text
  if (blocks.length === 0) {
    blocks.push({ type: 'text', text: messageStr });
  }
  
  return blocks;
}

/**
 * Parse a UserMessage string representation
 * Handles strings like: "UserMessage(content='...')" or "UserMessage(content=[...])"
 */
export function parseUserMessageString(messageStr: string): string | ContentBlock[] {
  // Try to match string content first
  const stringMatch = messageStr.match(/UserMessage\(content='([^']+)'\)/);
  if (stringMatch) {
    return stringMatch[1];
  }
  
  // Try to match array content
  const arrayMatch = messageStr.match(/UserMessage\(content=\[(.*)\]\)/s);
  if (arrayMatch) {
    return parseContentBlocksString(arrayMatch[1]);
  }
  
  // Fallback to the original string
  return messageStr;
}

/**
 * Parse a ResultMessage string representation
 * Handles strings like: "ResultMessage(subtype='...', duration_ms=123, ...)"
 */
export function parseResultMessageString(messageStr: string): ResultMessage | null {
  const match = messageStr.match(/ResultMessage\((.*)\)/s);
  if (!match) {
    return null;
  }
  
  const content = match[1];
  const result: Partial<ResultMessage> = {
    type: 'ResultMessage'
  };
  
  // Parse each field
  const subtypeMatch = content.match(/subtype='([^']+)'/);
  if (subtypeMatch) result.subtype = subtypeMatch[1];
  
  const durationMatch = content.match(/duration_ms=(\d+)/);
  if (durationMatch) result.duration_ms = parseInt(durationMatch[1]);
  
  const durationApiMatch = content.match(/duration_api_ms=(\d+)/);
  if (durationApiMatch) result.duration_api_ms = parseInt(durationApiMatch[1]);
  
  const isErrorMatch = content.match(/is_error=(True|False)/);
  if (isErrorMatch) result.is_error = isErrorMatch[1] === 'True';
  
  const numTurnsMatch = content.match(/num_turns=(\d+)/);
  if (numTurnsMatch) result.num_turns = parseInt(numTurnsMatch[1]);
  
  const sessionIdMatch = content.match(/session_id='([^']+)'/);
  if (sessionIdMatch) result.session_id = sessionIdMatch[1];
  
  const costMatch = content.match(/total_cost_usd=([\d.]+)/);
  if (costMatch) result.total_cost_usd = parseFloat(costMatch[1]);
  
  const resultTextMatch = content.match(/result='([^']+)'/);
  if (resultTextMatch) result.result = resultTextMatch[1];
  
  // Ensure required fields have defaults
  return {
    type: 'ResultMessage',
    subtype: result.subtype || '',
    duration_ms: result.duration_ms || 0,
    duration_api_ms: result.duration_api_ms || 0,
    is_error: result.is_error || false,
    num_turns: result.num_turns || 0,
    session_id: result.session_id || '',
    total_cost_usd: result.total_cost_usd,
    result: result.result
  };
}

/**
 * Parse a Claude Code message from event data
 * Handles both structured data and string representations
 * Prioritizes the 'message' field which contains the Python dataclass string
 */
export function parseMessage(data: any): AssistantMessage | UserMessage | ResultMessage | SystemMessage | null {
  // First try to parse from the 'message' field (Python dataclass string)
  if (data.message && typeof data.message === 'string') {
    const messageStr = data.message;
    
    // Check message type from message_type field or detect from string
    if (data.message_type === 'AssistantMessage' || messageStr.startsWith('AssistantMessage(')) {
      return {
        type: 'AssistantMessage',
        content: parseAssistantMessageString(messageStr),
        model: data.model
      };
    }
    
    if (data.message_type === 'UserMessage' || messageStr.startsWith('UserMessage(')) {
      const content = parseUserMessageString(messageStr);
      return {
        type: 'UserMessage',
        content: content
      };
    }
    
    if (data.message_type === 'ResultMessage' || messageStr.startsWith('ResultMessage(')) {
      return parseResultMessageString(messageStr);
    }
    
    if (data.message_type === 'SystemMessage' || messageStr.startsWith('SystemMessage(')) {
      // For now, return a basic SystemMessage structure
      return {
        type: 'SystemMessage',
        subtype: data.subtype || 'unknown',
        data: data.data || {}
      };
    }
  }
  
  // Fallback: Check if it's already structured
  if (data.type === 'AssistantMessage' && data.content) {
    // If content is a string representation, parse it
    if (typeof data.content === 'string' && data.content.includes('AssistantMessage(')) {
      return {
        type: 'AssistantMessage',
        content: parseAssistantMessageString(data.content),
        model: data.model
      };
    }
    // Otherwise assume it's already structured
    return data as AssistantMessage;
  }
  
  if (data.type === 'UserMessage') {
    if (typeof data.content === 'string' && data.content.includes('UserMessage(')) {
      return {
        type: 'UserMessage',
        content: parseUserMessageString(data.content)
      };
    }
    return data as UserMessage;
  }
  
  if (data.type === 'ResultMessage') {
    if (typeof data.content === 'string' && data.content.includes('ResultMessage(')) {
      return parseResultMessageString(data.content);
    }
    return data as ResultMessage;
  }
  
  if (data.type === 'SystemMessage') {
    return data as SystemMessage;
  }
  
  return null;
}

/**
 * Parse a Claude Code message event and extract content blocks
 */
export function parseClaudeCodeMessage(event: ClaudeCodeMessageEvent): ContentBlock[] {
  const blocks: ContentBlock[] = [];
  
  // If we have structured data, use it
  if (event.structured_data) {
    const data = event.structured_data;
    
    if (isAssistantMessage(data)) {
      return data.content;
    } else if (isUserMessage(data)) {
      if (typeof data.content === 'string') {
        blocks.push({ type: 'text', text: data.content });
      } else {
        return data.content;
      }
    }
  }
  
  // Fallback to parsing the string representation
  // This would need the string parsing logic
  return blocks;
}

/**
 * Get a human-readable label for a message type
 */
export function getMessageTypeLabel(type: Message['type']): string {
  switch (type) {
    case 'UserMessage':
      return '👤 User';
    case 'AssistantMessage':
      return '🤖 Assistant';
    case 'SystemMessage':
      return '⚙️ System';
    case 'ResultMessage':
      return '📊 Result';
    default:
      return type;
  }
}

/**
 * Get a human-readable label for a content block type
 */
export function getBlockTypeLabel(block: ContentBlock): string {
  switch (block.type) {
    case 'text':
      return '📝 Text';
    case 'tool_use':
      return `Tool: ${(block as ToolUseBlock).name}`;
    case 'thinking':
      return '💭 Thinking';
    case 'tool_result':
      return '📋 Tool Result';
    default:
      // TypeScript exhaustiveness check
      const _exhaustive: never = block;
      return 'Unknown Block';
  }
}

// ============================================
// Export grouped utilities
// ============================================

export const ClaudeCodeUtils = {
  // Type guards
  guards: {
    isTextBlock,
    isToolUseBlock,
    isThinkingBlock,
    isToolResultBlock,
    isAssistantMessage,
    isUserMessage,
    isSystemMessage,
    isResultMessage,
  },
  
  // Utility functions
  parse: parseClaudeCodeMessage,
  parseMessage,
  parseAssistantMessageString,
  parseUserMessageString,
  parseResultMessageString,
  parseContentBlocksString,
  labels: {
    getMessageTypeLabel,
    getBlockTypeLabel,
  },
};
