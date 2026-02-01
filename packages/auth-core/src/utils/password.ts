import bcrypt from 'bcrypt';

const SALT_ROUNDS = 12;

/**
 * Hash a password using bcrypt
 */
export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, SALT_ROUNDS);
}

/**
 * Verify a password against a hash
 */
export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}

/**
 * Generate a random API key token
 */
export function generateApiKeyToken(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  const length = 48;
  let result = 'chi_'; // Prefix for Chicory API keys
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 * Get prefix and suffix from an API key for display purposes
 */
export function getApiKeyDisplayParts(apiKey: string): { prefix: string; suffix: string } {
  return {
    prefix: apiKey.substring(0, 8),
    suffix: apiKey.substring(apiKey.length - 6),
  };
}
