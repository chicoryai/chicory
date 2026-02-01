// Type definitions for Playground API

// Main Playground entity
export interface Playground {
  id: string;
  agent_id: string;
  project_id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  settings?: Record<string, any>;
  metadata?: Record<string, any>;
}

// Payload for creating a playground
export interface PlaygroundCreate {
  name: string;
  description?: string;
  settings?: Record<string, any>;
  metadata?: Record<string, any>;
}

// Payload for updating a playground
export interface PlaygroundUpdate {
  name?: string;
  description?: string;
  settings?: Record<string, any>;
  metadata?: Record<string, any>;
}

// Response from API for a single playground
export interface PlaygroundResponse extends Playground {
  invocation_count?: number;
}

// Response for listing playgrounds
export interface PlaygroundList {
  playgrounds: PlaygroundResponse[];
  total?: number;
  has_more?: boolean;
}

// Playground Invocation entity - matches actual API response
export interface PlaygroundInvocation {
  invocation_id: string;
  user_task_id: string;
  assistant_task_id?: string;  // May be null if still processing
  created_at: string;
  playground_id?: string;
  agent_id?: string;
  project_id?: string;
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

// Payload for creating an invocation
export interface InvocationCreate {
  content: string;  // API expects 'content' not 'input'
  metadata?: Record<string, any>;
  settings?: Record<string, any>;
}

// Response from API for a single invocation
export interface InvocationResponse extends PlaygroundInvocation {
  cost_usd?: number;
}

// Response for listing invocations
export interface InvocationList {
  invocations: InvocationResponse[];
  total?: number;
  has_more?: boolean;
}

// Type guards for runtime type checking
export function isPlayground(obj: any): obj is Playground {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    typeof obj.id === 'string' &&
    typeof obj.agent_id === 'string' &&
    typeof obj.project_id === 'string' &&
    typeof obj.name === 'string'
  );
}

export function isPlaygroundResponse(obj: any): obj is PlaygroundResponse {
  return isPlayground(obj);
}

export function isPlaygroundList(obj: any): obj is PlaygroundList {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    Array.isArray(obj.playgrounds) &&
    obj.playgrounds.every(isPlaygroundResponse)
  );
}

export function isPlaygroundInvocation(obj: any): obj is PlaygroundInvocation {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    typeof obj.invocation_id === 'string' &&
    typeof obj.user_task_id === 'string' &&
    typeof obj.created_at === 'string'
  );
}

export function isInvocationResponse(obj: any): obj is InvocationResponse {
  return isPlaygroundInvocation(obj);
}

export function isInvocationList(obj: any): obj is InvocationList {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    Array.isArray(obj.invocations) &&
    obj.invocations.every(isInvocationResponse)
  );
}