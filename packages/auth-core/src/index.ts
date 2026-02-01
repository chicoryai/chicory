// Types
export type {
  AuthUser,
  OrgInfo,
  Organization,
  OrgMembership,
  ApiKeyValidationResult,
  CreateApiKeyParams,
  CreateApiKeyResult,
  ApiKeyInfo,
  FetchApiKeysParams,
  FetchApiKeysResult,
  FetchUsersInOrgResult,
  UpdateUserMetadataParams,
  AuthRoutes,
  AuthProvider,
  LocalAuthConfig,
  PropelAuthConfig,
} from './types';

// Constants
export { ROLE_PERMISSIONS, getPermissionsForRole } from './types';

// Local auth provider
export { LocalAuthProvider, createLocalAuthProvider } from './provider';

// Models (for advanced usage)
export { UserModel } from './models/user';
export { OrganizationModel } from './models/organization';
export { SessionModel } from './models/session';
export { ApiKeyModel } from './models/api-key';

// Utilities
export { hashPassword, verifyPassword, generateApiKeyToken, getApiKeyDisplayParts } from './utils/password';
export { generateUserId, generateOrgId, generateSessionId, generateApiKeyId, calculateExpirationDate, isExpired } from './utils/token';
