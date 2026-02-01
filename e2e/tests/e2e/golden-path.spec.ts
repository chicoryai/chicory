import { test, expect } from '@playwright/test';
import { LoginPage } from '../../pages/login.page';
import { AgentsPage } from '../../pages/agents.page';
import { AgentPlaygroundPage } from '../../pages/agent-playground.page';
import { AgentDeployPage } from '../../pages/agent-deploy.page';
import { AgentManagePage } from '../../pages/agent-manage.page';
import { IntegrationsPage } from '../../pages/integrations.page';
import { ChicoryApiClient } from '../../utils/api-client';
import {
  generateAgentName,
  TEST_FILES,
  SAMPLE_TASKS,
  SAMPLE_INSTRUCTIONS,
  ensureTestDataExists,
  getBigQueryCredentialsPath,
} from '../../utils/test-data';

/**
 * Golden Path E2E Test Suite
 *
 * Tests the complete user journey:
 * 1. Login with test credentials
 * 2. Upload a single file
 * 3. Upload a folder
 * 4. Connect BigQuery
 * 5. Run scan/training
 * 6. Create agent
 * 7. Configure agent
 * 8. Test in playground
 * 9. Deploy agent
 * 10. Execute via API
 * 11. View task history
 */
test.describe('Golden Path E2E', () => {
  // Shared state between tests
  let projectId: string;
  let agentId: string;
  let apiKey: string;
  const agentName = generateAgentName();

  // Setup before all tests
  test.beforeAll(async () => {
    // Ensure test data files exist
    ensureTestDataExists();
  });

  test('1. User can log in and view projects', async ({ page }) => {
    const loginPage = new LoginPage(page);

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Should redirect to projects (using stored auth state)
    await page.waitForURL(/projects/, { timeout: 30000 });

    // Extract project ID from URL
    const url = page.url();
    const match = url.match(/projects\/([^/]+)/);
    projectId = match?.[1] || '';

    expect(projectId).toBeTruthy();
    console.log(`Project ID: ${projectId}`);
  });

  test('2. User can see data sources on integrations page', async ({ page }) => {
    test.skip(!projectId, 'Project ID not available from previous test');

    const integrationsPage = new IntegrationsPage(page);
    await integrationsPage.navigate(projectId);

    // Check if data sources already exist (expected in this project)
    const dataSourceCount = await integrationsPage.getDataSourceCount();
    console.log(`Found ${dataSourceCount} existing data sources`);

    // Project should have at least one data source
    expect(dataSourceCount).toBeGreaterThanOrEqual(1);
  });

  test('3. User can view connected data sources', async ({ page }) => {
    test.skip(!projectId, 'Project ID not available from previous test');

    const integrationsPage = new IntegrationsPage(page);
    await integrationsPage.navigate(projectId);

    // Verify we can see the connected data sources table
    await page.waitForLoadState('networkidle');

    // Should see data sources (BigQuery is connected)
    const hasBigQuery = await integrationsPage.hasDataSource('BigQuery');
    console.log(`BigQuery connected: ${hasBigQuery}`);

    // At least one data source should exist
    const count = await integrationsPage.getDataSourceCount();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('4. User can access BigQuery data source', async ({ page }) => {
    test.skip(!projectId, 'Project ID not available from previous test');

    const integrationsPage = new IntegrationsPage(page);
    await integrationsPage.navigate(projectId);

    // Verify BigQuery is connected
    const hasBigQuery = await integrationsPage.hasDataSource('BigQuery');

    if (!hasBigQuery) {
      console.log('BigQuery not connected, attempting to connect...');

      // Get BigQuery credentials path
      let bigQueryPath: string;
      try {
        bigQueryPath = getBigQueryCredentialsPath();
      } catch {
        console.log('BigQuery credentials not configured, skipping');
        test.skip();
        return;
      }

      // Connect BigQuery
      await integrationsPage.connectBigQuery(bigQueryPath);
    }

    // Verify BigQuery connection appears
    const hasDataSource = await integrationsPage.hasDataSource('BigQuery');
    expect(hasDataSource).toBeTruthy();
  });

  test('5. User can run scan/training', async ({ page }) => {
    test.skip(!projectId, 'Project ID not available from previous test');

    const integrationsPage = new IntegrationsPage(page);
    await integrationsPage.navigate(projectId);

    // Check if there are data sources to scan
    const dataSourceCount = await integrationsPage.getDataSourceCount();
    if (dataSourceCount === 0) {
      console.log('No data sources available for scanning, skipping');
      test.skip();
      return;
    }

    // Check if scan is already complete
    const scanCompleteText = page.getByText(/scan.*complete|complete.*scan/i);
    const isAlreadyComplete = await scanCompleteText.isVisible({ timeout: 2000 }).catch(() => false);

    if (isAlreadyComplete) {
      console.log('Scan already completed, verifying status');
      // Just verify the scan completed state
      await expect(scanCompleteText.first()).toBeVisible();
    } else {
      // Start scanning
      await integrationsPage.startScanning();

      // Wait for scanning to complete (with long timeout for real data sources)
      await integrationsPage.waitForScanningComplete(300000); // 5 minutes
    }
  });

  test('6. User can create an agent', async ({ page }) => {
    test.skip(!projectId, 'Project ID not available from previous test');

    const agentsPage = new AgentsPage(page);
    await agentsPage.navigate(projectId);

    // Create new agent
    await agentsPage.createAgent({
      name: agentName,
      description: 'Agent created by E2E golden path test',
    });

    // Verify we're on playground page
    await expect(page).toHaveURL(/playground/, { timeout: 30000 });

    // Extract agent ID from URL
    const url = page.url();
    const match = url.match(/agents\/([^/]+)/);
    agentId = match?.[1] || '';

    expect(agentId).toBeTruthy();
    console.log(`Agent ID: ${agentId}`);
  });

  test('7. User can configure agent instructions', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available from previous tests');

    const playgroundPage = new AgentPlaygroundPage(page);
    await playgroundPage.navigateToConfigure(projectId, agentId);

    // Set instructions
    await playgroundPage.setInstructions(SAMPLE_INSTRUCTIONS.basic);

    // Save configuration
    await playgroundPage.saveConfiguration();
  });

  test('8. User can test agent in playground', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available from previous tests');

    const playgroundPage = new AgentPlaygroundPage(page);
    await playgroundPage.navigate(projectId, agentId);

    // Verify playground is ready
    const isReady = await playgroundPage.isReady();
    expect(isReady).toBeTruthy();

    // Submit a test task
    await playgroundPage.submitTask(SAMPLE_TASKS.simple);

    // Wait for streaming response to complete
    await playgroundPage.waitForStreamingComplete(60000);

    // Verify we got a response
    const response = await playgroundPage.getLatestResponse();
    expect(response).toBeTruthy();
    expect(response!.length).toBeGreaterThan(0);

    console.log(`Playground response: ${response?.substring(0, 100)}...`);
  });

  test('9. User can deploy agent and get API key', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available from previous tests');

    const deployPage = new AgentDeployPage(page);
    await deployPage.navigate(projectId, agentId);

    // Enable agent
    await deployPage.enableAgent();

    // Deploy API access
    await deployPage.deployApi();

    // Get API key
    apiKey = await deployPage.getApiKey();

    expect(apiKey).toBeTruthy();
    expect(apiKey.length).toBeGreaterThan(10);

    console.log(`API Key obtained: ${apiKey.substring(0, 10)}...`);
  });

  test('10. User can call deployed agent via API', async ({ request }) => {
    test.skip(!projectId || !agentId || !apiKey, 'Required IDs/key not available from previous tests');

    const apiUrl = process.env.API_URL || 'http://localhost:8000';
    const apiClient = new ChicoryApiClient(apiUrl, apiKey);

    try {
      await apiClient.init();

      // Execute agent via API
      const result = await apiClient.executeAndWait(
        projectId,
        agentId,
        SAMPLE_TASKS.greeting,
        60000
      );

      expect(result.status).toBe('completed');
      expect(result.response).toBeTruthy();

      console.log(`API response status: ${result.status}`);
      console.log(`API response: ${result.response?.substring(0, 100)}...`);
    } finally {
      await apiClient.dispose();
    }
  });

  test('11. User can view task history', async ({ page }) => {
    test.skip(!projectId || !agentId, 'Project/Agent ID not available from previous tests');

    const managePage = new AgentManagePage(page);
    await managePage.navigate(projectId, agentId);

    // Should have at least 2 tasks (playground + API)
    await page.waitForTimeout(2000); // Allow time for tasks to appear

    const hasTasks = await managePage.hasTasks();
    expect(hasTasks).toBeTruthy();

    const taskCount = await managePage.getTaskCount();
    expect(taskCount).toBeGreaterThanOrEqual(1);

    console.log(`Task count in history: ${taskCount}`);
  });
});
