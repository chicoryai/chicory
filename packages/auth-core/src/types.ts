/**
 * Core authentication types for Chicory
 * These interfaces are shared between auth-core (local) and auth-propelauth (cloud)
 */

export interface AuthUser {
  userId: string;
  email: string;
  firstName?: string;
  lastName?: string;
  username?: string;
  pictureUrl?: string;
  activeOrgId?: string;
  orgIdToUserOrgInfo?: Record<string, OrgInfo>;
}

export interface OrgInfo {
  orgId: string;
  orgName: string;
  userAssignedRole: string;
  userPermissions: string[];
}

export interface Organization {
  orgId: string;
  name: string;
  metadata?: Record<string, unknown>;
  createdAt: Date;
}

export interface OrgMembership {
  userId: string;
  orgId: string;
  role: 'Owner' | 'Admin' | 'Member';
  permissions: string[];
  joinedAt: Date;
}

export interface ApiKeyValidationResult {
  user?: {
    userId: string;
    email?: string;
  };
  org?: {
    orgId: string;
    orgName?: string;
  };
  metadata?: Record<string, unknown>;
}

export interface CreateApiKeyParams {
  orgId: string;
  userId?: string;
  resourceId?: string;
  resourceType?: 'agent' | 'gateway';
  expiresAtSeconds?: number;
  metadata?: Record<string, unknown>;
}

export interface CreateApiKeyResult {
  apiKeyId: string;
  apiKeyToken: string;
}

export interface ApiKeyInfo {
  apiKeyId: string;
  keyPrefix: string;
  keySuffix?: string;
  orgId?: string;
  userId?: string;
  resourceType?: 'agent' | 'gateway';
  resourceId?: string;
  metadata?: Record<string, unknown>;
  createdAt: Date;
  expiresAt?: Date;
  lastUsedAt?: Date;
}

export interface FetchApiKeysParams {
  userId?: string;
  orgId?: string;
  pageSize?: number;
  pageNumber?: number;
}

export interface FetchApiKeysResult {
  apiKeys: ApiKeyInfo[];
  totalApiKeys?: number;
}

export interface FetchUsersInOrgResult {
  users: Array<{
    userId: string;
    email: string;
    firstName?: string;
    lastName?: string;
    pictureUrl?: string;
    role: string;
    roleInOrg?: string;
  }>;
  totalUsers: number;
}

export interface UpdateUserMetadataParams {
  firstName?: string;
  lastName?: string;
  pictureUrl?: string;
  username?: string;
  properties?: Record<string, unknown>;
}

export interface AuthRoutes {
  loader(request: Request, params: Record<string, string | undefined>): Promise<Response>;
  action(request: Request, params: Record<string, string | undefined>): Promise<Response>;
}

/**
 * Main AuthProvider interface that both local and PropelAuth implementations must satisfy
 */
export interface AuthProvider {
  // Session/User operations
  getUser(request: Request): Promise<AuthUser | null>;
  getUserById(userId: string): Promise<AuthUser | null>;

  // Organization operations
  createOrganization(name: string, userId: string): Promise<Organization>;
  fetchOrg(orgId: string): Promise<Organization | null>;
  addUserToOrg(userId: string, orgId: string, role: string): Promise<void>;
  removeUserFromOrg(userId: string, orgId: string): Promise<void>;
  changeUserRoleInOrg(userId: string, orgId: string, newRole: string): Promise<void>;
  fetchUsersInOrg(orgId: string, pageSize?: number, pageNumber?: number): Promise<FetchUsersInOrgResult>;
  inviteUserToOrg(email: string, orgId: string, role: string): Promise<boolean>;

  // API Key operations
  createApiKey(params: CreateApiKeyParams): Promise<CreateApiKeyResult>;
  validateApiKey(apiKey: string): Promise<ApiKeyValidationResult | null>;
  deleteApiKey(apiKeyId: string): Promise<void>;
  fetchApiKeys(params: FetchApiKeysParams): Promise<FetchApiKeysResult>;

  // User metadata operations
  updateUserMetadata(userId: string, metadata: UpdateUserMetadataParams): Promise<void>;
  fetchUserData(userId: string, includeOrgs?: boolean): Promise<AuthUser | null>;

  // Remix auth routes handler
  routes: AuthRoutes;
}

/**
 * Configuration for local auth provider
 */
export interface LocalAuthConfig {
  mongoUri: string;
  sessionSecret: string;
  cookieName?: string;
  sessionMaxAge?: number; // in seconds, default 7 days
}

/**
 * Configuration for PropelAuth provider
 */
export interface PropelAuthConfig {
  authUrl: string;
  apiKey: string;
  verifierKey: string;
  redirectUri: string;
}

/**
 * Role to permissions mapping for local auth
 */
export const ROLE_PERMISSIONS: Record<string, string[]> = {
  Owner: [
    'org::admin',
    'org::can_invite',
    'org::can_remove_users',
    'org::can_change_roles',
    'projects::create',
    'projects::delete',
    'projects::manage',
    'agents::create',
    'agents::delete',
    'agents::manage',
    'data_sources::create',
    'data_sources::delete',
    'data_sources::manage',
  ],
  Admin: [
    'org::can_invite',
    'org::can_remove_users',
    'projects::create',
    'projects::manage',
    'agents::create',
    'agents::manage',
    'data_sources::create',
    'data_sources::manage',
  ],
  Member: [
    'projects::view',
    'agents::view',
    'agents::execute',
    'data_sources::view',
  ],
};

/**
 * Get permissions for a role
 */
export function getPermissionsForRole(role: string): string[] {
  return ROLE_PERMISSIONS[role] || ROLE_PERMISSIONS.Member;
}
