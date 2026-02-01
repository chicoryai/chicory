import { MongoClient, Db } from 'mongodb';
import type {
  AuthProvider,
  AuthUser,
  Organization,
  LocalAuthConfig,
  CreateApiKeyParams,
  CreateApiKeyResult,
  ApiKeyValidationResult,
  FetchApiKeysParams,
  FetchApiKeysResult,
  FetchUsersInOrgResult,
  UpdateUserMetadataParams,
  AuthRoutes,
} from './types';
import { UserModel } from './models/user';
import { OrganizationModel } from './models/organization';
import { SessionModel } from './models/session';
import { ApiKeyModel } from './models/api-key';

export class LocalAuthProvider implements AuthProvider {
  private config: LocalAuthConfig;
  private client: MongoClient | null = null;
  private db: Db | null = null;
  private userModel: UserModel | null = null;
  private orgModel: OrganizationModel | null = null;
  private sessionModel: SessionModel | null = null;
  private apiKeyModel: ApiKeyModel | null = null;
  private initialized: boolean = false;

  constructor(config: LocalAuthConfig) {
    this.config = config;
  }

  private async ensureInitialized(): Promise<void> {
    if (this.initialized) return;

    this.client = new MongoClient(this.config.mongoUri);
    await this.client.connect();
    this.db = this.client.db();

    this.userModel = new UserModel(this.db);
    this.orgModel = new OrganizationModel(this.db);
    this.sessionModel = new SessionModel(this.db, this.config.sessionMaxAge);
    this.apiKeyModel = new ApiKeyModel(this.db);

    // Ensure indexes
    await Promise.all([
      this.userModel.ensureIndexes(),
      this.orgModel.ensureIndexes(),
      this.sessionModel.ensureIndexes(),
      this.apiKeyModel.ensureIndexes(),
    ]);

    this.initialized = true;
  }

  private getSessionIdFromRequest(request: Request): string | null {
    const cookieName = this.config.cookieName || '__chicory_session';
    const cookies = request.headers.get('Cookie') || '';
    const match = cookies.match(new RegExp(`${cookieName}=([^;]+)`));
    return match ? match[1] : null;
  }

  async getUser(request: Request): Promise<AuthUser | null> {
    await this.ensureInitialized();

    const sessionId = this.getSessionIdFromRequest(request);
    if (!sessionId) return null;

    const session = await this.sessionModel!.findById(sessionId);
    if (!session) return null;

    const user = await this.userModel!.findById(session.userId);
    if (!user) return null;

    // Get user's org memberships
    const memberships = await this.orgModel!.getUserMemberships(user.userId);

    const orgIdToUserOrgInfo: Record<string, { orgId: string; orgName: string; userAssignedRole: string; userPermissions: string[] }> = {};

    for (const membership of memberships) {
      const org = await this.orgModel!.findById(membership.orgId);
      if (org) {
        orgIdToUserOrgInfo[membership.orgId] = {
          orgId: membership.orgId,
          orgName: org.name,
          userAssignedRole: membership.role,
          userPermissions: membership.permissions,
        };
      }
    }

    const activeOrgId = memberships.length > 0 ? memberships[0].orgId : undefined;

    return {
      userId: user.userId,
      email: user.email,
      firstName: user.firstName,
      lastName: user.lastName,
      username: user.username,
      pictureUrl: user.pictureUrl,
      activeOrgId,
      orgIdToUserOrgInfo,
    };
  }

  async getUserById(userId: string): Promise<AuthUser | null> {
    await this.ensureInitialized();

    const user = await this.userModel!.findById(userId);
    if (!user) return null;

    const memberships = await this.orgModel!.getUserMemberships(userId);
    const orgIdToUserOrgInfo: Record<string, { orgId: string; orgName: string; userAssignedRole: string; userPermissions: string[] }> = {};

    for (const membership of memberships) {
      const org = await this.orgModel!.findById(membership.orgId);
      if (org) {
        orgIdToUserOrgInfo[membership.orgId] = {
          orgId: membership.orgId,
          orgName: org.name,
          userAssignedRole: membership.role,
          userPermissions: membership.permissions,
        };
      }
    }

    return {
      userId: user.userId,
      email: user.email,
      firstName: user.firstName,
      lastName: user.lastName,
      username: user.username,
      pictureUrl: user.pictureUrl,
      activeOrgId: memberships.length > 0 ? memberships[0].orgId : undefined,
      orgIdToUserOrgInfo,
    };
  }

  async createOrganization(name: string, userId: string): Promise<Organization> {
    await this.ensureInitialized();
    const org = await this.orgModel!.create(name, userId);
    return {
      orgId: org.orgId,
      name: org.name,
      metadata: org.metadata,
      createdAt: org.createdAt,
    };
  }

  async fetchOrg(orgId: string): Promise<Organization | null> {
    await this.ensureInitialized();
    const org = await this.orgModel!.findById(orgId);
    if (!org) return null;
    return {
      orgId: org.orgId,
      name: org.name,
      metadata: org.metadata,
      createdAt: org.createdAt,
    };
  }

  async addUserToOrg(userId: string, orgId: string, role: string): Promise<void> {
    await this.ensureInitialized();
    await this.orgModel!.addMember(userId, orgId, role as 'Owner' | 'Admin' | 'Member');
  }

  async removeUserFromOrg(userId: string, orgId: string): Promise<void> {
    await this.ensureInitialized();
    await this.orgModel!.removeMember(userId, orgId);
  }

  async changeUserRoleInOrg(userId: string, orgId: string, newRole: string): Promise<void> {
    await this.ensureInitialized();
    await this.orgModel!.changeRole(userId, orgId, newRole as 'Owner' | 'Admin' | 'Member');
  }

  async fetchUsersInOrg(orgId: string, pageSize?: number, pageNumber?: number): Promise<FetchUsersInOrgResult> {
    await this.ensureInitialized();

    const { members, total } = await this.orgModel!.getOrgMembers(orgId, pageSize, pageNumber);

    const users = await Promise.all(
      members.map(async (membership) => {
        const user = await this.userModel!.findById(membership.userId);
        return {
          userId: membership.userId,
          email: user?.email || '',
          firstName: user?.firstName,
          lastName: user?.lastName,
          pictureUrl: user?.pictureUrl,
          role: membership.role,
          roleInOrg: membership.role,
        };
      })
    );

    return {
      users,
      totalUsers: total,
    };
  }

  async inviteUserToOrg(email: string, orgId: string, role: string): Promise<boolean> {
    await this.ensureInitialized();

    // For local auth, check if user exists and add them directly
    const user = await this.userModel!.findByEmail(email);
    if (user) {
      await this.orgModel!.addMember(user.userId, orgId, role as 'Owner' | 'Admin' | 'Member');
      return true;
    }

    // TODO: For non-existent users, could implement invitation tokens
    // For now, just return false
    console.log(`User ${email} does not exist. Invitation not sent.`);
    return false;
  }

  async createApiKey(params: CreateApiKeyParams): Promise<CreateApiKeyResult> {
    await this.ensureInitialized();
    return this.apiKeyModel!.create(params);
  }

  async validateApiKey(apiKey: string): Promise<ApiKeyValidationResult | null> {
    await this.ensureInitialized();
    return this.apiKeyModel!.validate(apiKey);
  }

  async deleteApiKey(apiKeyId: string): Promise<void> {
    await this.ensureInitialized();
    await this.apiKeyModel!.delete(apiKeyId);
  }

  async fetchApiKeys(params: FetchApiKeysParams): Promise<FetchApiKeysResult> {
    await this.ensureInitialized();

    let apiKeys;
    if (params.userId) {
      apiKeys = await this.apiKeyModel!.findByUser(params.userId, params.pageSize, params.pageNumber);
    } else if (params.orgId) {
      apiKeys = await this.apiKeyModel!.findByOrg(params.orgId, params.pageSize, params.pageNumber);
    } else {
      apiKeys = [];
    }

    return { apiKeys };
  }

  async updateUserMetadata(userId: string, metadata: UpdateUserMetadataParams): Promise<void> {
    await this.ensureInitialized();
    await this.userModel!.updateMetadata(userId, metadata);
  }

  async fetchUserData(userId: string, _includeOrgs?: boolean): Promise<AuthUser | null> {
    return this.getUserById(userId);
  }

  // Auth routes for login/signup/logout
  routes: AuthRoutes = {
    loader: async (request: Request, params: Record<string, string | undefined>): Promise<Response> => {
      const url = new URL(request.url);
      const path = params['*'] || url.pathname.replace('/api/auth/', '');

      if (path === 'login') {
        // Return login page or check if already logged in
        const user = await this.getUser(request);
        if (user) {
          return new Response(null, {
            status: 302,
            headers: { Location: '/' },
          });
        }
        return new Response(JSON.stringify({ action: 'login' }), {
          headers: { 'Content-Type': 'application/json' },
        });
      }

      if (path === 'logout') {
        const sessionId = this.getSessionIdFromRequest(request);
        if (sessionId) {
          await this.ensureInitialized();
          await this.sessionModel!.delete(sessionId);
        }
        const cookieName = this.config.cookieName || '__chicory_session';
        return new Response(null, {
          status: 302,
          headers: {
            Location: '/api/auth/login',
            'Set-Cookie': `${cookieName}=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; SameSite=Lax`,
          },
        });
      }

      return new Response('Not found', { status: 404 });
    },

    action: async (request: Request, params: Record<string, string | undefined>): Promise<Response> => {
      const url = new URL(request.url);
      const path = params['*'] || url.pathname.replace('/api/auth/', '');
      await this.ensureInitialized();

      if (path === 'login') {
        const formData = await request.formData();
        const email = formData.get('email') as string;
        const password = formData.get('password') as string;

        if (!email || !password) {
          return new Response(JSON.stringify({ error: 'Email and password required' }), {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          });
        }

        const user = await this.userModel!.verifyCredentials(email, password);
        if (!user) {
          return new Response(JSON.stringify({ error: 'Invalid credentials' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' },
          });
        }

        const session = await this.sessionModel!.create(user.userId, {
          userAgent: request.headers.get('User-Agent') || undefined,
        });

        const cookieName = this.config.cookieName || '__chicory_session';
        const maxAge = this.config.sessionMaxAge || 7 * 24 * 60 * 60;

        return new Response(null, {
          status: 302,
          headers: {
            Location: '/',
            'Set-Cookie': `${cookieName}=${session.sessionId}; Path=/; Max-Age=${maxAge}; HttpOnly; SameSite=Lax`,
          },
        });
      }

      if (path === 'signup') {
        const formData = await request.formData();
        const email = formData.get('email') as string;
        const password = formData.get('password') as string;
        const firstName = formData.get('firstName') as string | undefined;
        const lastName = formData.get('lastName') as string | undefined;

        if (!email || !password) {
          return new Response(JSON.stringify({ error: 'Email and password required' }), {
            status: 400,
            headers: { 'Content-Type': 'application/json' },
          });
        }

        // Check if user already exists
        const existingUser = await this.userModel!.findByEmail(email);
        if (existingUser) {
          return new Response(JSON.stringify({ error: 'User already exists' }), {
            status: 409,
            headers: { 'Content-Type': 'application/json' },
          });
        }

        // Create user
        const user = await this.userModel!.create({ email, password, firstName, lastName });

        // Create default organization for user
        await this.orgModel!.create(`${email}'s Organization`, user.userId);

        // Create session
        const session = await this.sessionModel!.create(user.userId, {
          userAgent: request.headers.get('User-Agent') || undefined,
        });

        const cookieName = this.config.cookieName || '__chicory_session';
        const maxAge = this.config.sessionMaxAge || 7 * 24 * 60 * 60;

        return new Response(null, {
          status: 302,
          headers: {
            Location: '/',
            'Set-Cookie': `${cookieName}=${session.sessionId}; Path=/; Max-Age=${maxAge}; HttpOnly; SameSite=Lax`,
          },
        });
      }

      return new Response('Not found', { status: 404 });
    },
  };
}

/**
 * Factory function to create a local auth provider
 */
export function createLocalAuthProvider(config: LocalAuthConfig): AuthProvider {
  return new LocalAuthProvider(config);
}
