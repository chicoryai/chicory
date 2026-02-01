// Type definitions for Workzone API

// Main Workzone entity
export interface Workzone {
  id: string;
  org_id: string;
  name: string;
  description?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// Payload for creating a workzone
export interface WorkzoneCreate {
  org_id: string;
  name: string;
  description?: string;
  metadata?: Record<string, any>;
}

// Payload for updating a workzone
export interface WorkzoneUpdate {
  name?: string;
  description?: string;
  metadata?: Record<string, any>;
}

// Response from API for a single workzone
export interface WorkzoneResponse extends Workzone {
  invocation_count?: number;
}

// Response for listing workzones
export interface WorkzoneList {
  workzones: WorkzoneResponse[];
  has_more: boolean;
  total?: number;
}

// Workzone Invocation entity - matches actual API response
export interface WorkzoneInvocation {
  invocation_id: string;
  user_task_id: string;
  assistant_task_id?: string;  // May be null if still processing
  created_at: string;
  workzone_id?: string;
  org_id: string;
  project_id: string;
  agent_id: string;
  status?: 'pending' | 'processing' | 'completed' | 'failed';
  error?: string;
  updated_at?: string;
  metadata?: Record<string, any>;
  duration_ms?: number;
  token_usage?: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
  };
}

// Payload for creating a workzone invocation
export interface InvocationCreate {
  org_id: string;
  project_id: string;
  agent_id: string;
  user_id: string;
  content: string;
  metadata?: Record<string, any>;
}

// Response from API for a single invocation
export interface InvocationResponse extends WorkzoneInvocation {
  cost_usd?: number;
}

// List item for invocation listing
export interface InvocationListItem {
  invocation_id: string;
  user_task_id: string;
  assistant_task_id: string;
  org_id: string;
  project_id: string;
  agent_id: string;
  created_at: string;
}

// Response for listing invocations
export interface InvocationList {
  invocations: InvocationListItem[];
  has_more: boolean;
  total?: number;
}

// Type guards for runtime type checking
export function isWorkzone(obj: any): obj is Workzone {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    typeof obj.id === 'string' &&
    typeof obj.org_id === 'string' &&
    typeof obj.name === 'string'
  );
}

export function isWorkzoneResponse(obj: any): obj is WorkzoneResponse {
  return isWorkzone(obj);
}

export function isWorkzoneList(obj: any): obj is WorkzoneList {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    Array.isArray(obj.workzones) &&
    obj.workzones.every(isWorkzoneResponse) &&
    typeof obj.has_more === 'boolean'
  );
}

export function isWorkzoneInvocation(obj: any): obj is WorkzoneInvocation {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    typeof obj.invocation_id === 'string' &&
    typeof obj.user_task_id === 'string' &&
    typeof obj.created_at === 'string'
  );
}

export function isInvocationResponse(obj: any): obj is InvocationResponse {
  return isWorkzoneInvocation(obj);
}

export function isInvocationList(obj: any): obj is InvocationList {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    Array.isArray(obj.invocations) &&
    obj.invocations.every(isWorkzoneInvocation) &&
    typeof obj.has_more === 'boolean'
  );
}

// ============================================
// Streaming message types for workzone
// ============================================

export interface ThinkingMessage {
  type: 'thinking';
  thinking: string;
  signature?: string;
  timestamp: number;
}

export interface TextMessage {
  type: 'text';
  text: string;
  timestamp: number;
}

export interface ToolExecutionMessage {
  type: 'tool';
  toolId: string;
  toolName: string;
  input: Record<string, any>;
  result?: any;
  isError?: boolean;
  timestamp: number;
}

export type StreamingMessage = ThinkingMessage | TextMessage | ToolExecutionMessage;
