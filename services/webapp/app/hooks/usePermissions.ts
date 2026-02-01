import { useRouteLoaderData } from "@remix-run/react";

/**
 * Organization details for a user in PropelAuth
 */
export interface OrgInfo {
  orgId: string;
  orgName: string;
  userAssignedRole: string;
  userPermissions: string[];
}

/**
 * User object from PropelAuth with organization information
 */
export interface UserWithOrgs {
  userId: string;
  email: string;
  username?: string;
  activeOrgId?: string;
  orgIdToUserOrgInfo?: {
    [orgId: string]: OrgInfo;
  };
}

/**
 * Loader data from the _app route
 */
export interface AppLoaderData {
  user?: UserWithOrgs;
  orgId?: string;
  theme?: string | null;
  projects?: any[];
  activeProject?: any;
}

/**
 * Hook to check if the current user has a specific permission.
 *
 * @param permission - The permission string to check (e.g., 'members:manage', 'projects:create')
 * @param orgId - Optional organization ID to check permissions for. If not provided, uses the current org from route data.
 * @returns boolean - true if the user has the permission, false otherwise
 *
 * @example
 * ```tsx
 * const canManageMembers = usePermission('members:manage');
 *
 * return (
 *   <div>
 *     {canManageMembers && <button>Invite Member</button>}
 *   </div>
 * );
 * ```
 *
 * @example
 * ```tsx
 * // Check permission for a specific organization
 * const canManageMembers = usePermission('members:manage', specificOrgId);
 * ```
 */
export function usePermission(permission: string, orgId?: string): boolean {
  // Get data from the _app route (which contains user data)
  const data = useRouteLoaderData<AppLoaderData>("routes/_app");

  // Extract user from the loader data
  const user = data?.user;

  // Determine which org to check permissions for:
  // 1. Use provided orgId parameter
  // 2. Use orgId from route loader data
  // 3. Use user's activeOrgId
  // 4. Fall back to first org in user's organizations
  const targetOrgId =
    orgId ||
    data?.orgId ||
    user?.activeOrgId ||
    Object.keys(user?.orgIdToUserOrgInfo || {})[0];

  const orgDetails = user?.orgIdToUserOrgInfo?.[targetOrgId] || {};

  // Get userPermissions array from PropelAuth
  // PropelAuth returns userPermissions as part of the user object
  const userPermissions = orgDetails?.userPermissions || [];

  // Check if the user has the specific permission
  return userPermissions.includes(permission);
}

/**
 * Hook to check if the current user has all of the specified permissions.
 *
 * @param permissions - Array of permission strings to check
 * @param orgId - Optional organization ID to check permissions for. If not provided, uses the current org from route data.
 * @returns boolean - true if the user has ALL permissions, false otherwise
 *
 * @example
 * ```tsx
 * const canManageOrg = usePermissions(['members:manage', 'org:settings']);
 *
 * return (
 *   <div>
 *     {canManageOrg && <Link to="/org/settings">Organization Settings</Link>}
 *   </div>
 * );
 * ```
 */
export function usePermissions(permissions: string[], orgId?: string): boolean {
  const data = useRouteLoaderData<AppLoaderData>("routes/_app");
  const user = data?.user;

  // Determine which org to check permissions for
  const targetOrgId =
    orgId ||
    data?.orgId ||
    user?.activeOrgId ||
    Object.keys(user?.orgIdToUserOrgInfo || {})[0];

  const orgDetails = user?.orgIdToUserOrgInfo?.[targetOrgId] || {};
  const userPermissions = orgDetails?.userPermissions || [];

  // Check if user has all required permissions
  return permissions.every(permission => userPermissions.includes(permission));
}

/**
 * Hook to check if the current user has any of the specified permissions.
 *
 * @param permissions - Array of permission strings to check
 * @param orgId - Optional organization ID to check permissions for. If not provided, uses the current org from route data.
 * @returns boolean - true if the user has ANY of the permissions, false otherwise
 *
 * @example
 * ```tsx
 * const canViewAnalytics = useAnyPermission(['analytics:view', 'analytics:admin']);
 *
 * return (
 *   <div>
 *     {canViewAnalytics && <Link to="/analytics">Analytics</Link>}
 *   </div>
 * );
 * ```
 */
export function useAnyPermission(permissions: string[], orgId?: string): boolean {
  const data = useRouteLoaderData<AppLoaderData>("routes/_app");
  const user = data?.user;

  // Determine which org to check permissions for
  const targetOrgId =
    orgId ||
    data?.orgId ||
    user?.activeOrgId ||
    Object.keys(user?.orgIdToUserOrgInfo || {})[0];

  const orgDetails = user?.orgIdToUserOrgInfo?.[targetOrgId] || {};
  const userPermissions = orgDetails?.userPermissions || [];

  // Check if user has at least one of the required permissions
  return permissions.some(permission => userPermissions.includes(permission));
}

/**
 * Hook to get the user's full permissions array.
 * Useful for debugging or more complex permission logic.
 *
 * @param orgId - Optional organization ID to get permissions for. If not provided, uses the current org from route data.
 * @returns string[] - Array of all user permissions
 *
 * @example
 * ```tsx
 * const permissions = useUserPermissions();
 * console.log('User permissions:', permissions);
 * ```
 */
export function useUserPermissions(orgId?: string): string[] {
  const data = useRouteLoaderData<AppLoaderData>("routes/_app");
  const user = data?.user;

  // Determine which org to check permissions for
  const targetOrgId =
    orgId ||
    data?.orgId ||
    user?.activeOrgId ||
    Object.keys(user?.orgIdToUserOrgInfo || {})[0];

  const orgDetails = user?.orgIdToUserOrgInfo?.[targetOrgId] || {};
  return orgDetails?.userPermissions || [];
}
