// Workzone API integration for Chicory backend
// Uses process.env.CHICORY_API_URL as base URL

import type {
  Workzone,
  WorkzoneCreate,
  WorkzoneUpdate,
  WorkzoneResponse,
  WorkzoneList,
  WorkzoneInvocation,
  InvocationCreate,
  InvocationResponse,
  InvocationList
} from '../types/workzone';

const BASE_URL = process.env.CHICORY_API_URL || "http://localhost:8000";
console.log('[chicory-workzone.server] BASE_URL configured as:', BASE_URL);

/**
 * Creates a new workzone for an organization
 * @param data The workzone creation data (includes org_id)
 * @returns The created workzone
 */
export async function createWorkzone(
  data: WorkzoneCreate
): Promise<WorkzoneResponse> {
  console.log(`[createWorkzone] Creating workzone for org ${data.org_id}:`, { name: data.name });

  try {
    const response = await fetch(
      `${BASE_URL}/workzones`,
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
      console.error(`[createWorkzone] Failed to create workzone for org ${data.org_id}:`, errorData);
      throw new Error(`Failed to create workzone: ${JSON.stringify(errorData)}`);
    }

    const result = await response.json();
    console.log(`[createWorkzone] Successfully created workzone ${result.id} for org ${data.org_id}`);
    return result;
  } catch (error) {
    console.error(`[createWorkzone] Error creating workzone for org ${data.org_id}:`, error);
    throw error;
  }
}

/**
 * Lists workzones for an organization with pagination
 * @param orgId The ID of the organization
 * @param limit Maximum number of workzones to return (default: 10)
 * @param skip Number of items to skip for pagination (default: 0)
 * @returns List of workzones with pagination info
 */
export async function listWorkzones(
  orgId: string,
  limit: number = 10,
  skip: number = 0
): Promise<WorkzoneList> {
  console.log(`[listWorkzones] Fetching workzones for org ${orgId} (limit: ${limit}, skip: ${skip})`);

  try {
    const url = `${BASE_URL}/workzones?org_id=${encodeURIComponent(orgId)}&limit=${limit}&skip=${skip}`;

    const response = await fetch(url);

    if (!response.ok) {
      console.error(`[listWorkzones] Failed to fetch workzones for org ${orgId}:`, response.statusText);
      return { workzones: [], has_more: false };
    }

    const data = await response.json();
    const result = {
      workzones: data.workzones || [],
      total: data.total,
      has_more: data.has_more || false
    };
    console.log(`[listWorkzones] Successfully fetched ${result.workzones.length} workzones for org ${orgId} (has_more: ${result.has_more})`);
    return result;
  } catch (error) {
    console.error(`[listWorkzones] Error fetching workzones for org ${orgId}:`, error);
    return { workzones: [], has_more: false };
  }
}

/**
 * Gets a single workzone by ID
 * @param workzoneId The ID of the workzone to get
 * @param orgId The ID of the organization
 * @returns The workzone or null if not found
 */
export async function getWorkzone(
  workzoneId: string,
  orgId: string
): Promise<WorkzoneResponse | null> {
  console.log(`[getWorkzone] Fetching workzone ${workzoneId} for org ${orgId}`);

  try {
    const response = await fetch(
      `${BASE_URL}/workzones/${encodeURIComponent(workzoneId)}?org_id=${encodeURIComponent(orgId)}`
    );

    if (!response.ok) {
      if (response.status === 404) {
        console.log(`[getWorkzone] Workzone ${workzoneId} not found (404)`);
        return null;
      }
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      console.error(`[getWorkzone] Failed to get workzone ${workzoneId}:`, errorData);
      throw new Error(`Failed to get workzone: ${JSON.stringify(errorData)}`);
    }

    const result = await response.json();
    console.log(`[getWorkzone] Successfully fetched workzone ${workzoneId} (name: ${result.name})`);
    return result;
  } catch (error) {
    console.error(`[getWorkzone] Error getting workzone ${workzoneId}:`, error);
    return null;
  }
}

/**
 * Updates a workzone
 * @param workzoneId The ID of the workzone to update
 * @param orgId The ID of the organization
 * @param updates The updates to apply
 * @returns The updated workzone
 */
export async function updateWorkzone(
  workzoneId: string,
  orgId: string,
  updates: WorkzoneUpdate
): Promise<WorkzoneResponse> {
  console.log(`[updateWorkzone] Updating workzone ${workzoneId} for org ${orgId}:`, updates);

  try {
    const response = await fetch(
      `${BASE_URL}/workzones/${encodeURIComponent(workzoneId)}?org_id=${encodeURIComponent(orgId)}`,
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
      console.error(`[updateWorkzone] Failed to update workzone ${workzoneId}:`, errorData);
      throw new Error(`Failed to update workzone: ${JSON.stringify(errorData)}`);
    }

    const result = await response.json();
    console.log(`[updateWorkzone] Successfully updated workzone ${workzoneId}`);
    return result;
  } catch (error) {
    console.error(`[updateWorkzone] Error updating workzone ${workzoneId}:`, error);
    throw error;
  }
}

/**
 * Deletes a workzone
 * @param workzoneId The ID of the workzone to delete
 * @param orgId The ID of the organization
 * @returns True if deletion was successful
 */
export async function deleteWorkzone(
  workzoneId: string,
  orgId: string
): Promise<boolean> {
  console.log(`[deleteWorkzone] Attempting to delete workzone ${workzoneId} for org ${orgId}`);

  try {
    const url = `${BASE_URL}/workzones/${encodeURIComponent(workzoneId)}?org_id=${encodeURIComponent(orgId)}`;

    const response = await fetch(url, {
      method: 'DELETE'
    });

    // Success responses for DELETE
    if (response.ok || response.status === 204) {
      console.log(`[deleteWorkzone] Successfully deleted workzone ${workzoneId}`);
      return true;
    }

    if (response.status === 404) {
      console.log(`[deleteWorkzone] Workzone ${workzoneId} not found (already deleted?)`);
      return true;
    }

    // Handle error responses
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    console.error(`[deleteWorkzone] Delete workzone ${workzoneId} failed with status ${response.status}:`, errorData);
    throw new Error(`Failed to delete workzone: ${JSON.stringify(errorData)}`);
  } catch (error) {
    console.error(`[deleteWorkzone] Error deleting workzone ${workzoneId}:`, error);
    throw error;
  }
}

/**
 * Creates a new invocation for a workzone
 * @param workzoneId The ID of the workzone
 * @param data The invocation creation data (includes org_id, project_id, agent_id, and user_id)
 * @returns The created invocation
 */
export async function createWorkzoneInvocation(
  workzoneId: string,
  data: InvocationCreate
): Promise<InvocationResponse> {
  console.log(`[createWorkzoneInvocation] Creating invocation for workzone ${workzoneId}:`, {
    contentLength: data.content?.length,
    orgId: data.org_id,
    projectId: data.project_id,
    agentId: data.agent_id,
    userId: data.user_id
  });

  try {
    const response = await fetch(
      `${BASE_URL}/workzones/${encodeURIComponent(workzoneId)}/invocations`,
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
      console.error(`[createWorkzoneInvocation] Failed to create invocation for workzone ${workzoneId}:`, errorData);
      throw new Error(`Failed to create workzone invocation: ${JSON.stringify(errorData)}`);
    }

    const result = await response.json();
    console.log(`[createWorkzoneInvocation] Successfully created invocation ${result.invocation_id} for workzone ${workzoneId}`);
    return result;
  } catch (error) {
    console.error(`[createWorkzoneInvocation] Error creating invocation for workzone ${workzoneId}:`, error);
    throw error;
  }
}

/**
 * Lists invocations for a workzone with pagination
 * @param workzoneId The ID of the workzone
 * @param orgId The ID of the organization
 * @param limit Maximum number of invocations to return (default: 10)
 * @param skip Number of items to skip for pagination (default: 0)
 * @param sortOrder Sort order for results ('asc' or 'desc', default: 'desc')
 * @param userId Optional user ID to filter invocations by specific user
 * @returns List of invocations with pagination info
 */
export async function listWorkzoneInvocations(
  workzoneId: string,
  orgId: string,
  limit: number = 10,
  skip: number = 0,
  sortOrder: 'asc' | 'desc' = 'desc',
  userId?: string
): Promise<InvocationList> {
  console.log(`[listWorkzoneInvocations] Fetching invocations for workzone ${workzoneId}, org ${orgId}${userId ? `, user ${userId}` : ''} (limit: ${limit}, skip: ${skip}, sort: ${sortOrder})`);

  try {
    let url = `${BASE_URL}/workzones/${encodeURIComponent(workzoneId)}/invocations?org_id=${encodeURIComponent(orgId)}&limit=${limit}&skip=${skip}&sort_order=${sortOrder}`;

    if (userId) {
      url += `&user_id=${encodeURIComponent(userId)}`;
    }

    const response = await fetch(url);

    if (!response.ok) {
      console.error(`[listWorkzoneInvocations] Failed to fetch invocations for workzone ${workzoneId}:`, response.statusText);
      return { invocations: [], has_more: false };
    }

    const data = await response.json();
    const result = {
      invocations: data.invocations || [],
      total: data.total,
      has_more: data.has_more || false
    };
    console.log(`[listWorkzoneInvocations] Successfully fetched ${result.invocations.length} invocations for workzone ${workzoneId} (has_more: ${result.has_more})`);
    return result;
  } catch (error) {
    console.error(`[listWorkzoneInvocations] Error fetching invocations for workzone ${workzoneId}:`, error);
    return { invocations: [], has_more: false };
  }
}

/**
 * Gets a single invocation by ID
 * @param workzoneId The ID of the workzone
 * @param invocationId The ID of the invocation to get
 * @param orgId The ID of the organization
 * @returns The invocation or null if not found
 */
export async function getWorkzoneInvocation(
  workzoneId: string,
  invocationId: string,
  orgId: string
): Promise<InvocationResponse | null> {
  console.log(`[getWorkzoneInvocation] Fetching invocation ${invocationId} for workzone ${workzoneId}, org ${orgId}`);

  try {
    const response = await fetch(
      `${BASE_URL}/workzones/${encodeURIComponent(workzoneId)}/invocations/${encodeURIComponent(invocationId)}?org_id=${encodeURIComponent(orgId)}`
    );

    if (!response.ok) {
      if (response.status === 404) {
        console.log(`[getWorkzoneInvocation] Invocation ${invocationId} not found (404)`);
        return null;
      }
      const errorData = await response.json().catch(() => ({ detail: response.statusText }));
      console.error(`[getWorkzoneInvocation] Failed to get invocation ${invocationId}:`, errorData);
      throw new Error(`Failed to get invocation: ${JSON.stringify(errorData)}`);
    }

    const result = await response.json();
    console.log(`[getWorkzoneInvocation] Successfully fetched invocation ${invocationId} (status: ${result.status})`);
    return result;
  } catch (error) {
    console.error(`[getWorkzoneInvocation] Error getting invocation ${invocationId} for workzone ${workzoneId}:`, error);
    return null;
  }
}
