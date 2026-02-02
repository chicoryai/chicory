import { redirect } from '@remix-run/node';
import { getProjectsByOrgId } from '~/services/chicory.server';
import type { AuthProvider, AuthUser } from '@chicory/auth-core';

// Singleton for the auth provider
let authProvider: AuthProvider | null = null;
let authInitPromise: Promise<AuthProvider> | null = null;

/**
 * Initialize and return the auth provider based on AUTH_PROVIDER env var.
 * Uses lazy initialization to avoid issues with environment variables at import time.
 */
async function initializeAuth(): Promise<AuthProvider> {
  const provider = process.env.AUTH_PROVIDER || 'local';

  if (provider === 'propelauth') {
    // Dynamic import to avoid loading PropelAuth when not needed
    const { createPropelAuthProvider } = await import('@chicory/auth-propelauth');
    return createPropelAuthProvider({
      authUrl: process.env.REMIX_PUBLIC_AUTH_URL!,
      apiKey: process.env.PROPELAUTH_API_KEY!,
      verifierKey: process.env.PROPELAUTH_VERIFIER_KEY!,
      redirectUri: process.env.PROPELAUTH_REDIRECT_URI!,
    });
  } else {
    // Local auth provider
    const { createLocalAuthProvider } = await import('@chicory/auth-core');
    return createLocalAuthProvider({
      mongoUri: process.env.MONGODB_URI!,
      sessionSecret: process.env.SESSION_SECRET || 'chicory-dev-secret-change-in-production',
    });
  }
}

/**
 * Get the auth provider instance.
 * This is the main entry point for authentication operations.
 */
export async function getAuth(): Promise<AuthProvider> {
  if (authProvider) return authProvider;

  if (!authInitPromise) {
    authInitPromise = initializeAuth().then((provider) => {
      authProvider = provider;
      return provider;
    });
  }

  return authInitPromise;
}

/**
 * Check if using PropelAuth (cloud mode)
 */
export function isCloudAuth(): boolean {
  return process.env.AUTH_PROVIDER === 'propelauth';
}

/**
 * Extended user type with org and project context
 */
export interface UserWithOrgDetails extends AuthUser {
  project?: { id: string; name: string; [key: string]: unknown };
  orgId?: string;
}

/**
 * Get user with organization and project details.
 * This is the main function used by most routes to get authenticated user context.
 */
export async function getUserOrgDetails(request: Request): Promise<UserWithOrgDetails> {
  const auth = await getAuth();
  const user = await auth.getUser(request);

  if (!user) {
    throw redirect('/api/auth/login');
  }

  // Get the active org ID, or the first org ID if active is not set
  let orgId = user.activeOrgId;

  // If no active org, get the first org from orgIdToUserOrgInfo
  if (!orgId && user.orgIdToUserOrgInfo) {
    const orgIds = Object.keys(user.orgIdToUserOrgInfo);
    if (orgIds.length > 0) {
      orgId = orgIds[0];
    }
  }

  // If we have an org ID, fetch its projects
  if (orgId) {
    try {
      const projects = await getProjectsByOrgId(orgId);
      if (projects && projects.length > 0) {
        return {
          ...user,
          project: projects[0],
          orgId,
        };
      }

      return {
        ...user,
        orgId,
      };
    } catch (error) {
      console.error(`Error fetching projects for org ${orgId}:`, error);
    }
  }

  return user;
}

// ============================================================================
// BACKWARD COMPATIBILITY LAYER
// These exports maintain compatibility with existing code that uses the old API.
// New code should use getAuth() and the AuthProvider interface directly.
// ============================================================================

/**
 * @deprecated Use getAuth() instead. This is kept for backward compatibility.
 *
 * Legacy auth object that provides PropelAuth-compatible interface.
 * For PropelAuth mode, this is the actual PropelAuth instance.
 * For local auth mode, this is a compatibility wrapper.
 */
export const auth = {
  /**
   * Get user from request
   */
  async getUser(request: Request, _options?: Record<string, unknown>): Promise<AuthUser | null> {
    const provider = await getAuth();
    return provider.getUser(request);
  },

  /**
   * Handle request - PropelAuth compatibility method
   * For local auth, this is a no-op
   */
  handleRequest(_responseHeaders: Headers, _loadContext: unknown): void {
    // No-op for local auth - PropelAuth uses this for cookie handling
  },

  /**
   * Auth routes handler
   */
  routes: {
    async loader(request: Request, params: Record<string, string | undefined>): Promise<Response> {
      const provider = await getAuth();
      return provider.routes.loader(request, params);
    },
    async action(request: Request, params: Record<string, string | undefined>): Promise<Response> {
      const provider = await getAuth();
      return provider.routes.action(request, params);
    },
  },

  /**
   * PropelAuth API methods (for backward compatibility)
   * Note: These require PropelAuth mode for full functionality
   */
  api: {
    async createApiKey(options: {
      orgId?: string;
      userId?: string;
      expiresAtSeconds?: number;
      metadata?: Record<string, unknown>;
    }): Promise<{ apiKeyId: string; apiKeyToken: string }> {
      const provider = await getAuth();
      return provider.createApiKey({
        orgId: options.orgId || '',
        ...options,
      });
    },

    async deleteApiKey(apiKeyId: string): Promise<void> {
      const provider = await getAuth();
      return provider.deleteApiKey(apiKeyId);
    },

    async fetchCurrentApiKeys(options: {
      orgId?: string;
      userId?: string;
      pageSize?: number;
      pageNumber?: number;
    }): Promise<{ apiKeys: Array<{ apiKeyId: string; [key: string]: unknown }> }> {
      const provider = await getAuth();
      return provider.fetchApiKeys(options);
    },
  },
};
