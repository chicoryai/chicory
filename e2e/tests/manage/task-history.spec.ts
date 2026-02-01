import { test, expect } from '@playwright/test';
import { AgentsPage } from '../../pages/agents.page';
import { AgentPlaygroundPage } from '../../pages/agent-playground.page';
import { AgentManagePage } from '../../pages/agent-manage.page';
import { generateAgentName, SAMPLE_TASKS } from '../../utils/test-data';

/**
 * Task history (Manage page) tests
 */
test.describe('Task History', () => {
  let projectId: string;
  let agentId: string;
  const agentName = generateAgentName();

  test.beforeAll(async ({ browser }) => {
    // Create an agent and run a task for history tests
    const page = await browser.newPage();

    await page.goto('/');
    await page.waitForURL(/projects/, { timeout: 30000 });

    const url = page.url();
    const match = url.match(/projects\/([^/]+)/);
    projectId = match?.[1] || '';

    if (projectId) {
      // Create agent
      const agentsPage = new AgentsPage(page);
      await agentsPage.navigate(projectId);
      await agentsPage.createAgent({ name: agentName });

      // Get agent ID
      await page.waitForURL(/playground/, { timeout: 30000 });
      const agentMatch = page.url().match(/agents\/([^/]+)/);
      agentId = agentMatch?.[1] || '';

      // Run a task to create history
      if (agentId) {
        const playgroundPage = new AgentPlaygroundPage(page);
        await playgroundPage.submitTask(SAMPLE_TASKS.simple);
        await playgroundPage.waitForStreamingComplete(60000);
      }
    }

    await page.close();
  });

  test('manage page is accessible', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available');

    const managePage = new AgentManagePage(page);
    await managePage.navigate(projectId, agentId);

    // Page should load
    await page.waitForLoadState('networkidle');
  });

  test('can see task history', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available');

    const managePage = new AgentManagePage(page);
    await managePage.navigate(projectId, agentId);

    // Should have at least one task
    const hasTasks = await managePage.hasTasks();
    expect(hasTasks).toBeTruthy();
  });

  test('task history shows correct count', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available');

    const managePage = new AgentManagePage(page);
    await managePage.navigate(projectId, agentId);

    // Should have at least 1 task
    const count = await managePage.getTaskCount();
    expect(count).toBeGreaterThanOrEqual(1);
  });
});
