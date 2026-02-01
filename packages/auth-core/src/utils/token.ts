import { v4 as uuidv4 } from 'uuid';

/**
 * Generate a unique user ID
 */
export function generateUserId(): string {
  return uuidv4();
}

/**
 * Generate a unique organization ID
 */
export function generateOrgId(): string {
  return uuidv4();
}

/**
 * Generate a unique session ID
 */
export function generateSessionId(): string {
  return uuidv4();
}

/**
 * Generate a unique API key ID
 */
export function generateApiKeyId(): string {
  return uuidv4();
}

/**
 * Calculate expiration date from seconds
 */
export function calculateExpirationDate(expiresInSeconds?: number): Date | undefined {
  if (!expiresInSeconds) return undefined;
  return new Date(Date.now() + expiresInSeconds * 1000);
}

/**
 * Check if a date has expired
 */
export function isExpired(expiresAt?: Date): boolean {
  if (!expiresAt) return false;
  return new Date() > expiresAt;
}
