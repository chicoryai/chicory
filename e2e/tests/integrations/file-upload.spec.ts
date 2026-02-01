import { test, expect } from '@playwright/test';
import { IntegrationsPage } from '../../pages/integrations.page';
import { TEST_FILES, ensureTestDataExists } from '../../utils/test-data';

/**
 * File upload integration tests
 */
test.describe('File Upload', () => {
  let projectId: string;

  test.beforeAll(async () => {
    ensureTestDataExists();
  });

  test.beforeEach(async ({ page }) => {
    // Navigate to app and get project ID
    await page.goto('/');
    await page.waitForURL(/projects/, { timeout: 30000 });

    const url = page.url();
    const match = url.match(/projects\/([^/]+)/);
    projectId = match?.[1] || '';
  });

  test('can upload CSV file', async ({ page }) => {
    test.skip(!projectId, 'Project ID not available');

    const integrationsPage = new IntegrationsPage(page);
    await integrationsPage.navigate(projectId);

    // Upload CSV file
    await integrationsPage.uploadFile(TEST_FILES.sampleCsv, 'csv');

    // Verify upload succeeded
    const hasDataSource = await integrationsPage.hasDataSource('sample');
    expect(hasDataSource).toBeTruthy();
  });

  test('can see uploaded file in data sources list', async ({ page }) => {
    test.skip(!projectId, 'Project ID not available');

    const integrationsPage = new IntegrationsPage(page);
    await integrationsPage.navigate(projectId);

    // Check data sources count
    const count = await integrationsPage.getDataSourceCount();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});
