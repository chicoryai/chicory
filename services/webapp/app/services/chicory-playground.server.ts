// Playground API integration for Chicory backend
// Uses process.env.CHICORY_API_URL as base URL

import type {
  Playground,
  PlaygroundCreate,
  PlaygroundUpdate,
  PlaygroundResponse,
  PlaygroundList,
  PlaygroundInvocation,
  InvocationCreate,
  InvocationResponse,
  InvocationList
} from '../types/playground';

const BASE_URL = process.env.CHICORY_API_URL || "http://localhost:8000";
console.log('[chicory-playground.server] BASE_URL configured as:', BASE_URL);

/**
 * Creates a new playground for an agent
 * @param projectId The ID of the project
 * @param agentId The ID of the agent to create a playground for
 * @param data The playground creation data
 * @returns The created playground
 */
export async function createPlayground(
  projectId: string,
  agentId: string,
  data: PlaygroundCreate
): Promise<PlaygroundResponse> {
  try {
    const response = await fetch(
      `${BASE_URL}/projects/${encodeURIComponent(projectId)}/agents/${encodeURIComponent(agentId)}/playgrounds`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(`Failed to create playground: ${JSON.stringify(errorData)}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error creating playground for agent ${agentId} in project ${projectId}:`, error);
    throw error;
  }
}

/**
 * Lists playgrounds for an agent with pagination
 * @param projectId The ID of the project
 * @param agentId The ID of the agent to list playgrounds for
 * @param limit Maximum number of playgrounds to return (default: 10)
 * @param skip Number of items to skip for pagination (default: 0)
 * @returns List of playgrounds with pagination info
 */
export async function listPlaygrounds(
  projectId: string,
  agentId: string,
  limit: number = 10,
  skip: number = 0
): Promise<PlaygroundList> {
  try {
    const url = `${BASE_URL}/projects/${encodeURIComponent(projectId)}/agents/${encodeURIComponent(agentId)}/playgrounds?limit=${limit}&skip=${skip}`;

    const response = await fetch(url);

    if (!response.ok) {
      console.error(`Failed to fetch playgrounds for agent ${agentId}:`, response.statusText);
      return { playgrounds: [], has_more: false };
    }

    const data = await response.json();
    return {
      playgrounds: data.playgrounds || [],
      total: data.total,
      has_more: data.has_more || false
    };
  } catch (error) {
    console.error(`Error fetching playgrounds for agent ${agentId} in project ${projectId}:`, error);
    return { playgrounds: [], has_more: false };
  }
}

/**
 * Gets a single playground by ID
 * @param projectId The ID of the project
 * @param agentId The ID of the agent
 * @param playgroundId The ID of the playground to get
 * @returns The playground or null if not found
 */
export async function getPlayground(
  projectId: string,
  agentId: string,
  playgroundId: string
): Promise<PlaygroundResponse | null> {
  try {
    const response = await fetch(
      `${BASE_URL}/projects/${encodeURIComponent(projectId)}/agents/${encodeURIComponent(agentId)}/playgrounds/${encodeURIComponent(playgroundId)}`
    );

    if (!response.ok) {
      if (response.status === 404) return null;
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(`Failed to get playground: ${JSON.stringify(errorData)}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error getting playground ${playgroundId} for agent ${agentId} in project ${projectId}:`, error);
    return null;
  }
}

/**
 * Updates a playground
 * @param projectId The ID of the project
 * @param agentId The ID of the agent
 * @param playgroundId The ID of the playground to update
 * @param updates The updates to apply
 * @returns The updated playground
 */
export async function updatePlayground(
  projectId: string,
  agentId: string,
  playgroundId: string,
  updates: PlaygroundUpdate
): Promise<PlaygroundResponse> {
  try {
    const response = await fetch(
      `${BASE_URL}/projects/${encodeURIComponent(projectId)}/agents/${encodeURIComponent(agentId)}/playgrounds/${encodeURIComponent(playgroundId)}`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updates)
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(`Failed to update playground: ${JSON.stringify(errorData)}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error updating playground ${playgroundId} for agent ${agentId} in project ${projectId}:`, error);
    throw error;
  }
}

/**
 * Deletes a playground
 * @param projectId The ID of the project
 * @param agentId The ID of the agent
 * @param playgroundId The ID of the playground to delete
 * @returns True if deletion was successful
 */
export async function deletePlayground(
  projectId: string,
  agentId: string,
  playgroundId: string
): Promise<boolean> {
  try {
    const url = `${BASE_URL}/projects/${encodeURIComponent(projectId)}/agents/${encodeURIComponent(agentId)}/playgrounds/${encodeURIComponent(playgroundId)}`;
    console.log(`Attempting to delete playground at: ${url}`);

    const response = await fetch(url, {
      method: 'DELETE'
    });

    // Success responses for DELETE
    if (response.ok || response.status === 204) {
      console.log(`Successfully deleted playground ${playgroundId}`);
      return true;
    }

    if (response.status === 404) {
      console.log(`Playground ${playgroundId} not found (already deleted?)`);
      return true;
    }

    // Handle error responses
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    console.error(`Delete playground failed with status ${response.status}:`, errorData);
    throw new Error(`Failed to delete playground: ${JSON.stringify(errorData)}`);
  } catch (error) {
    console.error(`Error deleting playground ${playgroundId} for agent ${agentId} in project ${projectId}:`, error);
    throw error;
  }
}

/**
 * Creates a new invocation for a playground
 * @param projectId The ID of the project
 * @param agentId The ID of the agent
 * @param playgroundId The ID of the playground
 * @param data The invocation creation data
 * @returns The created invocation
 */
export async function createPlaygroundInvocation(
  projectId: string,
  agentId: string,
  playgroundId: string,
  data: InvocationCreate
): Promise<InvocationResponse> {
  try {
    const response = await fetch(
      `${BASE_URL}/projects/${encodeURIComponent(projectId)}/agents/${encodeURIComponent(agentId)}/playgrounds/${encodeURIComponent(playgroundId)}/invocations`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(`Failed to create playground invocation: ${JSON.stringify(errorData)}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error creating invocation for playground ${playgroundId} in agent ${agentId}:`, error);
    throw error;
  }
}

/**
 * Lists invocations for a playground with pagination
 * @param projectId The ID of the project
 * @param agentId The ID of the agent
 * @param playgroundId The ID of the playground
 * @param limit Maximum number of invocations to return (default: 10)
 * @param skip Number of items to skip for pagination (default: 0)
 * @param sortOrder Sort order for results ('asc' or 'desc', default: 'desc')
 * @returns List of invocations with pagination info
 */
export async function listPlaygroundInvocations(
  projectId: string,
  agentId: string,
  playgroundId: string,
  limit: number = 10,
  skip: number = 0,
  sortOrder: 'asc' | 'desc' = 'desc'
): Promise<InvocationList> {
  try {
    const url = `${BASE_URL}/projects/${encodeURIComponent(projectId)}/agents/${encodeURIComponent(agentId)}/playgrounds/${encodeURIComponent(playgroundId)}/invocations?limit=${limit}&skip=${skip}&sort_order=${sortOrder}`;

    const response = await fetch(url);

    if (!response.ok) {
      console.error(`Failed to fetch invocations for playground ${playgroundId}:`, response.statusText);
      return { invocations: [], has_more: false };
    }

    const data = await response.json();
    return {
      invocations: data.invocations || [],
      total: data.total,
      has_more: data.has_more || false
    };
  } catch (error) {
    console.error(`Error fetching invocations for playground ${playgroundId}:`, error);
    return { invocations: [], has_more: false };
  }
}

/**
 * Gets a single invocation by ID
 * @param projectId The ID of the project
 * @param agentId The ID of the agent
 * @param playgroundId The ID of the playground
 * @param invocationId The ID of the invocation to get
 * @returns The invocation or null if not found
 */
export async function getPlaygroundInvocation(
  projectId: string,
  agentId: string,
  playgroundId: string,
  invocationId: string
): Promise<InvocationResponse | null> {
  try {
    const response = await fetch(
      `${BASE_URL}/projects/${encodeURIComponent(projectId)}/agents/${encodeURIComponent(agentId)}/playgrounds/${encodeURIComponent(playgroundId)}/invocations/${encodeURIComponent(invocationId)}`
    );

    if (!response.ok) {
      if (response.status === 404) return null;
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(`Failed to get invocation: ${JSON.stringify(errorData)}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error getting invocation ${invocationId} for playground ${playgroundId}:`, error);
    return null;
  }
}