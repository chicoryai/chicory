import { test, expect } from '@playwright/test';
import { AgentsPage } from '../../pages/agents.page';
import { generateAgentName } from '../../utils/test-data';

/**
 * Agent creation tests
 */
test.describe('Agent Creation', () => {
  let projectId: string;

  test.beforeEach(async ({ page }) => {
    // Navigate to app and get project ID
    await page.goto('/');
    await page.waitForURL(/projects/, { timeout: 30000 });

    const url = page.url();
    const match = url.match(/projects\/([^/]+)/);
    projectId = match?.[1] || '';
  });

  test('can create a new agent', async ({ page }) => {
    test.skip(!projectId, 'Project ID not available');

    const agentsPage = new AgentsPage(page);
    await agentsPage.navigate(projectId);

    const agentName = generateAgentName();

    // Create agent
    await agentsPage.createAgent({
      name: agentName,
      description: 'Test agent created by E2E tests',
    });

    // Should redirect to playground
    await expect(page).toHaveURL(/playground/, { timeout: 30000 });
  });

  test('agents page shows list of agents', async ({ page }) => {
    test.skip(!projectId, 'Project ID not available');

    const agentsPage = new AgentsPage(page);
    await agentsPage.navigate(projectId);

    // Page should load
    await page.waitForLoadState('networkidle');

    // Should see create button
    await expect(page.getByRole('button', { name: /create.*agent|new.*agent/i })).toBeVisible({
      timeout: 10000,
    });
  });
});
