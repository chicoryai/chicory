/**
 * Shared utilities for data source field handling
 */

import type { DataSourceFieldDefinition } from "~/services/chicory.server";

/**
 * Masked password placeholder shown in UI for existing passwords
 */
export const MASKED_PASSWORD_PLACEHOLDER = "••••••••••••";

/**
 * Patterns used to identify sensitive fields that should be masked
 */
const SENSITIVE_FIELD_PATTERNS = ['password', 'key', 'token', 'secret'] as const;

/**
 * Determines if a field contains sensitive data (passwords, API keys, tokens, etc.)
 * that should be masked in the UI and handled carefully.
 *
 * @param field - The field definition to check
 * @returns true if the field is sensitive, false otherwise
 */
export function isSensitiveField(field: { name: string; type?: string }): boolean {
  // Check if field type is explicitly password
  if (field.type === "password") {
    return true;
  }

  // Check if field name contains sensitive patterns
  const nameLower = field.name.toLowerCase();
  return SENSITIVE_FIELD_PATTERNS.some(pattern => nameLower.includes(pattern));
}

/**
 * Checks if a value is the masked password placeholder
 *
 * @param value - The value to check
 * @returns true if the value is the masked placeholder
 */
export function isMaskedValue(value: unknown): boolean {
  return typeof value === 'string' && value === MASKED_PASSWORD_PLACEHOLDER;
}
