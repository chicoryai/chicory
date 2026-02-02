import { initRemixAuth } from '@propelauth/remix';
import { initBaseAuth } from '@propelauth/node';
import type {
  AuthProvider,
  AuthUser,
  Organization,
  PropelAuthConfig,
  CreateApiKeyParams,
  CreateApiKeyResult,
  ApiKeyValidationResult,
  FetchApiKeysParams,
  FetchApiKeysResult,
  FetchUsersInOrgResult,
  UpdateUserMetadataParams,
  AuthRoutes,
} from '@chicory/auth-core';

export class PropelAuthProvider implements AuthProvider {
  private remixAuth: ReturnType<typeof initRemixAuth>;
  private nodeAuth: ReturnType<typeof initBaseAuth>;

  constructor(config: PropelAuthConfig) {
    this.remixAuth = initRemixAuth({
      authUrl: config.authUrl,
      integrationApiKey: config.apiKey,
      verifierKey: config.verifierKey,
      redirectUri: config.redirectUri,
    });

    this.nodeAuth = initBaseAuth({
      authUrl: config.authUrl,
      apiKey: config.apiKey,
    });
  }

  async getUser(request: Request): Promise<AuthUser | null> {
    const user = await this.remixAuth.getUser(request, {});
    if (!user) return null;

    return {
      userId: user.userId,
      email: user.email,
      firstName: user.firstName,
      lastName: user.lastName,
      username: user.username,
      pictureUrl: (user as any).pictureUrl,
      activeOrgId: user.activeOrgId,
      orgIdToUserOrgInfo: user.orgIdToUserOrgInfo as Record<string, {
        orgId: string;
        orgName: string;
        userAssignedRole: string;
        userPermissions: string[];
      }>,
    };
  }

  async getUserById(userId: string): Promise<AuthUser | null> {
    try {
      const userData = await this.nodeAuth.fetchUserMetadataByUserId(userId, true);
      if (!userData) return null;

      return {
        userId: userData.userId,
        email: userData.email,
        firstName: userData.firstName,
        lastName: userData.lastName,
        username: userData.username,
        pictureUrl: userData.pictureUrl,
        activeOrgId: userData.orgIdToOrgInfo ? Object.keys(userData.orgIdToOrgInfo)[0] : undefined,
        orgIdToUserOrgInfo: userData.orgIdToOrgInfo as Record<string, {
          orgId: string;
          orgName: string;
          userAssignedRole: string;
          userPermissions: string[];
        }>,
      };
    } catch (error) {
      console.error('Error fetching user by ID:', error);
      return null;
    }
  }

  async createOrganization(name: string, userId: string): Promise<Organization> {
    const result = await this.nodeAuth.createOrg({ name });

    // Add the creator as Owner
    try {
      await this.nodeAuth.addUserToOrg({
        userId,
        orgId: result.orgId,
        role: 'Owner',
      });
    } catch (error) {
      console.error('Error adding user to organization:', error);
    }

    return {
      orgId: result.orgId,
      name: result.name,
      createdAt: new Date(),
    };
  }

  async fetchOrg(orgId: string): Promise<Organization | null> {
    try {
      const org = await this.nodeAuth.fetchOrg(orgId);
      if (!org) return null;

      return {
        orgId: org.orgId,
        name: org.name,
        metadata: org.metadata,
        createdAt: new Date(),
      };
    } catch (error) {
      console.error('Error fetching org:', error);
      return null;
    }
  }

  async addUserToOrg(userId: string, orgId: string, role: string): Promise<void> {
    await this.nodeAuth.addUserToOrg({ userId, orgId, role });
  }

  async removeUserFromOrg(userId: string, orgId: string): Promise<void> {
    await this.nodeAuth.removeUserFromOrg({ userId, orgId });
  }

  async changeUserRoleInOrg(userId: string, orgId: string, newRole: string): Promise<void> {
    await this.nodeAuth.changeUserRoleInOrg({ userId, orgId, role: newRole });
  }

  async fetchUsersInOrg(orgId: string, pageSize: number = 100, pageNumber: number = 0): Promise<FetchUsersInOrgResult> {
    const result = await this.nodeAuth.fetchUsersInOrg({
      orgId,
      pageSize,
      pageNumber,
    });

    return {
      users: result.users.map((user: any) => ({
        userId: user.userId,
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        pictureUrl: user.pictureUrl,
        role: user.roleInOrg || user.role || 'Member',
        roleInOrg: user.roleInOrg,
      })),
      totalUsers: result.totalUsers,
    };
  }

  async inviteUserToOrg(email: string, orgId: string, role: string): Promise<boolean> {
    try {
      await this.nodeAuth.inviteUserToOrg({ email, orgId, role });
      return true;
    } catch (error) {
      console.error('Error inviting user to org:', error);
      return false;
    }
  }

  async createApiKey(params: CreateApiKeyParams): Promise<CreateApiKeyResult> {
    const metadata: Record<string, unknown> = {
      ...params.metadata,
      created_at: new Date().toISOString(),
    };

    if (params.resourceType === 'agent') {
      metadata.agent_id = params.resourceId;
    } else if (params.resourceType === 'gateway') {
      metadata.gateway_id = params.resourceId;
    }

    const result = await this.nodeAuth.createApiKey({
      orgId: params.orgId,
      expiresAtSeconds: params.expiresAtSeconds,
      metadata,
    });

    return {
      apiKeyId: result.apiKeyId,
      apiKeyToken: result.apiKeyToken,
    };
  }

  async validateApiKey(apiKey: string): Promise<ApiKeyValidationResult | null> {
    try {
      const result = await this.nodeAuth.validateApiKey(apiKey);
      return {
        user: result.user ? { userId: result.user.userId, email: result.user.email } : undefined,
        org: result.org ? { orgId: result.org.orgId, orgName: (result.org as any).orgName || (result.org as any).name } : undefined,
        metadata: result.metadata,
      };
    } catch (error) {
      console.error('Error validating API key:', error);
      return null;
    }
  }

  async deleteApiKey(apiKeyId: string): Promise<void> {
    await this.nodeAuth.deleteApiKey(apiKeyId);
  }

  async fetchApiKeys(params: FetchApiKeysParams): Promise<FetchApiKeysResult> {
    // PropelAuth fetches API keys at user level through the Remix auth API
    // This is typically done via auth.api.fetchCurrentApiKeys on the client
    // For server-side, we need to use different approach
    try {
      // Note: PropelAuth's node SDK doesn't have a direct fetchApiKeys method
      // This would typically be done via the Remix auth API
      return { apiKeys: [] };
    } catch (error) {
      console.error('Error fetching API keys:', error);
      return { apiKeys: [] };
    }
  }

  async updateUserMetadata(userId: string, metadata: UpdateUserMetadataParams): Promise<void> {
    await this.nodeAuth.updateUserMetadata(userId, metadata);
  }

  async fetchUserData(userId: string, includeOrgs: boolean = true): Promise<AuthUser | null> {
    try {
      const userData = await this.nodeAuth.fetchUserMetadataByUserId(userId, includeOrgs);
      if (!userData) return null;

      return {
        userId: userData.userId,
        email: userData.email,
        firstName: userData.firstName,
        lastName: userData.lastName,
        username: userData.username,
        pictureUrl: userData.pictureUrl,
      };
    } catch (error) {
      console.error('Error fetching user data:', error);
      return null;
    }
  }

  // Auth routes - delegate to PropelAuth Remix
  routes: AuthRoutes = {
    loader: async (request: Request, params: Record<string, string | undefined>): Promise<Response> => {
      return (this.remixAuth.routes.loader as any)({ request, params });
    },
    action: async (request: Request, params: Record<string, string | undefined>): Promise<Response> => {
      return (this.remixAuth.routes.action as any)({ request, params });
    },
  };

  /**
   * Get the underlying PropelAuth Remix auth instance for advanced usage
   */
  getRemixAuth(): ReturnType<typeof initRemixAuth> {
    return this.remixAuth;
  }

  /**
   * Get the underlying PropelAuth Node auth instance for advanced usage
   */
  getNodeAuth(): ReturnType<typeof initBaseAuth> {
    return this.nodeAuth;
  }
}

/**
 * Factory function to create a PropelAuth provider
 */
export function createPropelAuthProvider(config: PropelAuthConfig): AuthProvider {
  return new PropelAuthProvider(config);
}
