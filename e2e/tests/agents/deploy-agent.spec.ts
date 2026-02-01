import { test, expect } from '@playwright/test';
import { AgentsPage } from '../../pages/agents.page';
import { AgentDeployPage } from '../../pages/agent-deploy.page';
import { generateAgentName } from '../../utils/test-data';

/**
 * Agent deployment tests
 */
test.describe('Agent Deployment', () => {
  let projectId: string;
  let agentId: string;
  const agentName = generateAgentName();

  test.beforeAll(async ({ browser }) => {
    // Create an agent for deployment tests
    const page = await browser.newPage();

    await page.goto('/');
    await page.waitForURL(/projects/, { timeout: 30000 });

    const url = page.url();
    const match = url.match(/projects\/([^/]+)/);
    projectId = match?.[1] || '';

    if (projectId) {
      const agentsPage = new AgentsPage(page);
      await agentsPage.navigate(projectId);
      await agentsPage.createAgent({ name: agentName });

      // Get agent ID from URL
      await page.waitForURL(/playground/, { timeout: 30000 });
      const agentMatch = page.url().match(/agents\/([^/]+)/);
      agentId = agentMatch?.[1] || '';
    }

    await page.close();
  });

  test('deploy page is accessible', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available');

    const deployPage = new AgentDeployPage(page);
    await deployPage.navigate(projectId, agentId);

    // Page should load
    await page.waitForLoadState('networkidle');
  });

  test('can enable agent', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available');

    const deployPage = new AgentDeployPage(page);
    await deployPage.navigate(projectId, agentId);

    // Enable agent
    await deployPage.enableAgent();

    // Verify enabled
    const isEnabled = await deployPage.isAgentEnabled();
    expect(isEnabled).toBeTruthy();
  });

  test('can deploy API and get key', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available');

    const deployPage = new AgentDeployPage(page);
    await deployPage.navigate(projectId, agentId);

    // Deploy API
    await deployPage.deployApi();

    // Get API key
    const apiKey = await deployPage.getApiKey();
    expect(apiKey).toBeTruthy();
    expect(apiKey.length).toBeGreaterThan(10);
  });
});
