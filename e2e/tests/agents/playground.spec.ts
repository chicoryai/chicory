import { test, expect } from '@playwright/test';
import { AgentsPage } from '../../pages/agents.page';
import { AgentPlaygroundPage } from '../../pages/agent-playground.page';
import { generateAgentName, SAMPLE_TASKS, SAMPLE_INSTRUCTIONS } from '../../utils/test-data';

/**
 * Agent playground tests
 */
test.describe('Agent Playground', () => {
  let projectId: string;
  let agentId: string;
  const agentName = generateAgentName();

  test.beforeAll(async ({ browser }) => {
    // Create an agent for playground tests
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

  test('playground is accessible', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available');

    const playgroundPage = new AgentPlaygroundPage(page);
    await playgroundPage.navigate(projectId, agentId);

    // Verify playground is ready
    const isReady = await playgroundPage.isReady();
    expect(isReady).toBeTruthy();
  });

  test('can submit a task and get response', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available');

    const playgroundPage = new AgentPlaygroundPage(page);
    await playgroundPage.navigate(projectId, agentId);

    // Submit a task
    await playgroundPage.submitTask(SAMPLE_TASKS.simple);

    // Wait for response
    await playgroundPage.waitForStreamingComplete(60000);

    // Verify response
    const response = await playgroundPage.getLatestResponse();
    expect(response).toBeTruthy();
    expect(response!.length).toBeGreaterThan(0);
  });

  test('can configure agent instructions', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available');

    const playgroundPage = new AgentPlaygroundPage(page);
    await playgroundPage.navigateToConfigure(projectId, agentId);

    // Set instructions
    await playgroundPage.setInstructions(SAMPLE_INSTRUCTIONS.basic);

    // Save
    await playgroundPage.saveConfiguration();
  });
});
