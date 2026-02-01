// Conversation API integration for Chicory Agent
// Connects to backend-api conversation endpoints

import { fetchWithRetry } from "~/utils/fetch.server";

const BASE_URL = process.env.CHICORY_API_URL || "http://localhost:8000";

// Types matching backend-api schemas
export interface Conversation {
  id: string;
  project_id: string;
  name: string | null;
  status: 'active' | 'archived';
  message_count: number;
  session_id: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// Content block types based on Anthropic Agent SDK pattern
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
  input: Record<string, unknown>;
  output: string | null; // null while tool is executing
  is_error: boolean;
}

export type ContentBlock = TextBlock | ThinkingBlock | ToolUseBlock;

// Message metadata from the backend
export interface MessageMetadata {
  duration_ms?: number;
  num_turns?: number;
  is_error?: boolean;
  result?: string;
  [key: string]: unknown;
}

export interface Message {
  id: string;
  conversation_id: string;
  project_id: string;
  role: 'user' | 'assistant' | 'system';
  content_blocks: ContentBlock[];
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | null;
  parent_message_id: string | null;
  turn_number: number;
  metadata: MessageMetadata | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

// Legacy ToolCall interface - kept for reference during migration
/** @deprecated Use ToolUseBlock from content_blocks instead */
export interface ToolCall {
  tool_name: string;
  tool_id: string;
  input: Record<string, unknown>;
  output?: string;
  is_error?: boolean;
}

// Helper functions for working with content blocks
export function getTextContent(message: Message): string {
  return message.content_blocks
    .filter((block): block is TextBlock => block.type === 'text')
    .map(block => block.text)
    .join('');
}

export function getToolUseBlocks(message: Message): ToolUseBlock[] {
  return message.content_blocks.filter((block): block is ToolUseBlock => block.type === 'tool_use');
}

export function getThinkingBlocks(message: Message): ThinkingBlock[] {
  return message.content_blocks.filter((block): block is ThinkingBlock => block.type === 'thinking');
}

export function hasToolCalls(message: Message): boolean {
  return message.content_blocks.some(block => block.type === 'tool_use');
}

export interface SendMessageResponse {
  user_message_id: string;
  assistant_message_id: string;
}

// List conversations for a project
export async function getConversations(
  projectId: string,
  status?: 'active' | 'archived'
): Promise<Conversation[]> {
  const url = new URL(`${BASE_URL}/projects/${projectId}/conversations`);
  if (status) {
    url.searchParams.set('status', status);
  }

  const res = await fetchWithRetry(url.toString());
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to fetch conversations: ${err}`);
  }

  const data = await res.json();
  return data.conversations || [];
}

// Create a new conversation
export async function createConversation(
  projectId: string,
  name?: string
): Promise<Conversation> {
  const res = await fetchWithRetry(
    `${BASE_URL}/projects/${projectId}/conversations`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name || null }),
    }
  );

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to create conversation: ${err}`);
  }

  return await res.json();
}

// Get a single conversation
export async function getConversation(
  projectId: string,
  conversationId: string
): Promise<Conversation | null> {
  try {
    const res = await fetchWithRetry(
      `${BASE_URL}/projects/${projectId}/conversations/${conversationId}`
    );

    if (!res.ok) {
      if (res.status === 404) return null;
      const err = await res.text();
      throw new Error(`Failed to fetch conversation: ${err}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Error fetching conversation:", error);
    return null;
  }
}

// Archive (soft delete) a conversation
export async function archiveConversation(
  projectId: string,
  conversationId: string
): Promise<void> {
  const res = await fetchWithRetry(
    `${BASE_URL}/projects/${projectId}/conversations/${conversationId}`,
    { method: "DELETE" }
  );

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to archive conversation: ${err}`);
  }
}

// Get messages for a conversation
export async function getMessages(
  projectId: string,
  conversationId: string,
  limit?: number,
  beforeId?: string
): Promise<Message[]> {
  const url = new URL(
    `${BASE_URL}/projects/${projectId}/conversations/${conversationId}/messages`
  );
  if (limit) url.searchParams.set('limit', limit.toString());
  if (beforeId) url.searchParams.set('before_id', beforeId);

  const res = await fetchWithRetry(url.toString());
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to fetch messages: ${err}`);
  }

  const data = await res.json();
  return data.messages || [];
}

// Send a message and get the response message IDs
export async function sendMessage(
  projectId: string,
  conversationId: string,
  content: string
): Promise<SendMessageResponse> {
  const res = await fetchWithRetry(
    `${BASE_URL}/projects/${projectId}/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    }
  );

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to send message: ${err}`);
  }

  return await res.json();
}

// Cancel an in-progress message
export async function cancelMessage(
  projectId: string,
  conversationId: string,
  messageId: string
): Promise<void> {
  const res = await fetchWithRetry(
    `${BASE_URL}/projects/${projectId}/conversations/${conversationId}/messages/${messageId}/cancel`,
    { method: "POST" }
  );

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to cancel message: ${err}`);
  }
}

// Get the SSE stream URL for a message (used by client-side)
export function getMessageStreamUrl(
  projectId: string,
  conversationId: string,
  messageId: string
): string {
  return `/api/conversations/${conversationId}/stream?projectId=${projectId}&messageId=${messageId}`;
}
