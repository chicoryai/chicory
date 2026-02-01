/**
 * Authentication utilities - provider-agnostic wrappers for auth operations.
 *
 * This module replaces the PropelAuth-specific propelauth.server.ts with
 * provider-agnostic functions that work with both local auth and PropelAuth.
 */

import { getAuth } from '~/auth/auth.server';

/**
 * Create an organization
 */
export async function createOrganization(name: string, userId: string) {
  const auth = await getAuth();
  return auth.createOrganization(name, userId);
}

/**
 * Add a user to an organization
 */
export async function addUserToOrg(userId: string, orgId: string, role: string = 'Owner') {
  const auth = await getAuth();
  return auth.addUserToOrg(userId, orgId, role);
}

/**
 * Create an API key for an organization/resource
 */
export async function createApiKey(
  orgId: string,
  resourceId: string,
  resourceType: 'agent' | 'gateway' = 'agent',
  expiresAtSeconds?: number
): Promise<{ apiKeyId: string; apiKeyToken: string }> {
  const auth = await getAuth();
  return auth.createApiKey({
    orgId,
    resourceId,
    resourceType,
    expiresAtSeconds,
    metadata: {
      created_at: new Date().toISOString(),
    },
  });
}

/**
 * Update user metadata
 */
export async function updateUserMetadata(
  userId: string,
  metadata: {
    firstName?: string;
    lastName?: string;
    pictureUrl?: string;
    username?: string;
  }
): Promise<void> {
  const auth = await getAuth();
  return auth.updateUserMetadata(userId, metadata);
}

/**
 * Fetch complete user data
 */
export async function fetchUserData(userId: string, includeOrgs: boolean = true) {
  const auth = await getAuth();
  return auth.fetchUserData(userId, includeOrgs);
}

/**
 * Invite a user to an organization
 */
export async function inviteUserToOrg(
  email: string,
  orgId: string,
  role: string
): Promise<boolean> {
  const auth = await getAuth();
  return auth.inviteUserToOrg(email, orgId, role);
}

/**
 * Fetch users in an organization
 */
export async function fetchUsersInOrg(
  orgId: string,
  pageSize: number = 100,
  pageNumber: number = 0
) {
  const auth = await getAuth();
  return auth.fetchUsersInOrg(orgId, pageSize, pageNumber);
}

/**
 * Fetch organization details
 */
export async function fetchOrgDetails(orgId: string) {
  const auth = await getAuth();
  return auth.fetchOrg(orgId);
}

/**
 * Validate an API key from a request's Authorization header
 */
export async function validateApiKeyFromRequest(request: Request) {
  try {
    const authHeader = request.headers.get('Authorization');

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      console.log('Missing or invalid Authorization header');
      return null;
    }

    const apiKey = authHeader.substring(7); // Remove 'Bearer ' prefix

    if (!apiKey) {
      console.log('Empty API key');
      return null;
    }

    const auth = await getAuth();
    return auth.validateApiKey(apiKey);
  } catch (error) {
    console.error('Error validating API key:', error);
    return null;
  }
}

/**
 * Change a user's role in an organization
 */
export async function changeUserRoleInOrg(
  userId: string,
  orgId: string,
  newRole: string
): Promise<boolean> {
  try {
    const auth = await getAuth();
    await auth.changeUserRoleInOrg(userId, orgId, newRole);
    return true;
  } catch (error) {
    console.error('Error changing user role in organization:', error);
    throw error;
  }
}

/**
 * Remove a user from an organization
 */
export async function removeUserFromOrg(
  userId: string,
  orgId: string
): Promise<boolean> {
  try {
    const auth = await getAuth();
    await auth.removeUserFromOrg(userId, orgId);
    return true;
  } catch (error) {
    console.error('Error removing user from organization:', error);
    throw error;
  }
}

// ============================================================================
// Legacy exports for backward compatibility
// These are kept to minimize changes required in existing route files
// ============================================================================

/**
 * @deprecated Use createOrganization instead
 */
export const createOrganizationTest = createOrganization;
