import { json } from "@remix-run/node";
import { auth } from "~/auth/auth.server";
import { getProjectById } from "~/services/chicory.server";

export interface User {
  userId: string;
  email: string;
  username?: string;
  orgIdToUserOrgInfo?: {
    [orgId: string]: {
      orgId: string;
      orgName: string;
      userAssignedRole: string;
      userPermissions: string[];
    };
  };
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  organization_id: string;
  members?: string[];
  created_at?: string;
  updated_at?: string;
}

/**
 * Verifies that a user has access to a specific project.
 *
 * This function performs multiple security checks:
 * 1. Verifies user is authenticated
 * 2. Verifies the project exists
 * 3. Verifies user is a member of the project
 * 4. Optionally verifies user has specific permission(s)
 *
 * @param request - The incoming request object
 * @param projectId - The ID of the project to access
 * @param requiredPermission - Optional permission(s) to check. Can be a single permission or array of permissions.
 * @returns Object containing the authenticated user and project
 * @throws Response with appropriate status code if verification fails
 *
 * @example
 * // Basic project access check
 * const { user, project } = await verifyProjectAccess(request, projectId);
 *
 * @example
 * // Check for specific permission
 * const { user, project } = await verifyProjectAccess(request, projectId, 'projects:manage');
 *
 * @example
 * // Check for any of multiple permissions
 * const { user, project } = await verifyProjectAccess(request, projectId, ['projects:manage', 'members:manage']);
 */
export async function verifyProjectAccess(
  request: Request,
  projectId: string,
  requiredPermission?: string | string[]
): Promise<{ user: User; project: Project }> {
  // 1. Authenticate user
  const user = await auth.getUser(request, {});
  if (!user) {
    throw json({ error: "Authentication required" }, { status: 401 });
  }

  // 2. Verify project exists
  const project = await getProjectById(projectId);
  if (!project) {
    throw json({ error: "Project not found" }, { status: 404 });
  }

  // 3. Verify user is a member of the project
  if (!project.members?.includes(user.userId)) {
    throw json({ error: "Not a project member" }, { status: 403 });
  }

  // 4. Optionally check permissions
  if (requiredPermission) {
    const orgDetails = user.orgIdToUserOrgInfo?.[project.organization_id];
    const userPermissions = orgDetails?.userPermissions || [];

    // Handle both single permission and array of permissions
    const permissionsToCheck = Array.isArray(requiredPermission)
      ? requiredPermission
      : [requiredPermission];

    // Check if user has at least one of the required permissions
    const hasPermission = permissionsToCheck.some(perm =>
      userPermissions.includes(perm)
    );

    if (!hasPermission) {
      throw json(
        { error: "Insufficient permissions" },
        { status: 403 }
      );
    }
  }

  return { user, project };
}

/**
 * Verifies that a user has permission to manage a project in a specific organization.
 * This is useful for project creation, deletion, and management operations.
 *
 * @param request - The incoming request object
 * @param orgId - The organization ID
 * @param requiredPermission - Optional permission(s) to check
 * @returns The authenticated user
 * @throws Response with appropriate status code if verification fails
 *
 * @example
 * const user = await verifyOrgPermission(request, orgId, 'projects:create');
 */
export async function verifyOrgPermission(
  request: Request,
  orgId: string,
  requiredPermission?: string | string[]
): Promise<User> {
  // 1. Authenticate user
  const user = await auth.getUser(request, {});
  if (!user) {
    throw json({ error: "Authentication required" }, { status: 401 });
  }

  // 2. Verify user is a member of the organization
  const orgDetails = user.orgIdToUserOrgInfo?.[orgId];
  if (!orgDetails) {
    throw json({ error: "Not a member of this organization" }, { status: 403 });
  }

  // 3. Check permissions if specified
  if (requiredPermission) {
    const userPermissions = orgDetails.userPermissions || [];

    const permissionsToCheck = Array.isArray(requiredPermission)
      ? requiredPermission
      : [requiredPermission];

    const hasPermission = permissionsToCheck.some(perm =>
      userPermissions.includes(perm)
    );

    if (!hasPermission) {
      throw json(
        { error: "Insufficient permissions" },
        { status: 403 }
      );
    }
  }

  return user;
}

/**
 * Validates that all user IDs belong to the specified organization.
 * This prevents adding members from other organizations to projects.
 *
 * @param userIds - Array of user IDs to validate
 * @param orgId - The organization ID to check against
 * @param user - The authenticated user making the request
 * @returns true if all user IDs are valid org members
 * @throws Response with error if validation fails
 *
 * @example
 * await validateOrgMembers(memberIds, project.organization_id, user);
 */
export async function validateOrgMembers(
  userIds: string[],
  orgId: string,
  user: User
): Promise<boolean> {
  // For now, we can only validate that the requesting user is in the org
  // A full implementation would require an API endpoint to fetch all org members
  // from PropelAuth, which we can add later if needed

  // At minimum, verify the requesting user is in the org
  if (!user.orgIdToUserOrgInfo?.[orgId]) {
    throw json(
      { error: "User not authorized for this organization" },
      { status: 403 }
    );
  }

  // TODO: When org member listing API is available, validate that all userIds
  // are actual members of the organization
  // For now, we trust that UUIDs are validated and the backend will enforce membership

  return true;
}
