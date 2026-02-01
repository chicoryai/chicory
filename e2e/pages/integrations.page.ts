import { Page, expect } from '@playwright/test';
import { BasePage } from './base.page';
import path from 'path';

/**
 * Integrations page object for data source management
 */
export class IntegrationsPage extends BasePage {
  // Selectors
  private readonly addDataSourceButton = () => this.page.getByRole('button', { name: /data source/i }).first();

  private readonly dataSourceTable = () => this.page.locator('table').or(
    this.page.locator('[data-testid="connected-data-sources"]')
  );

  private readonly startScanningButton = () => this.page.getByRole('button', { name: /scan/i });

  private readonly trainingStatus = () => this.page.locator('[class*="training"]').or(
    this.page.locator('[data-testid="training-status"]')
  );

  /**
   * Navigate to integrations page for a project
   */
  async navigate(projectId: string) {
    await this.navigateTo(`/projects/${projectId}/integrations`);
    await this.waitForPageLoad();
  }

  /**
   * Click the Add Data Source button
   */
  async clickAddDataSource() {
    await this.addDataSourceButton().click();
  }

  /**
   * Upload a single file (CSV, Excel, or document)
   */
  async uploadFile(filePath: string, fileType: 'csv' | 'excel' | 'document' = 'csv') {
    await this.clickAddDataSource();

    // Wait for the popover to appear
    await this.page.waitForTimeout(500);

    // Map file types to their integration button labels
    // CSV/Excel uploads are typically under "Data" category
    const typeMap: Record<string, string[]> = {
      csv: ['csv', 'data upload'],
      excel: ['excel', 'xlsx', 'spreadsheet'],
      document: ['file upload', 'document']
    };

    // First, click on "Data" category if it's a data file
    if (fileType === 'csv' || fileType === 'excel') {
      const dataTab = this.page.getByRole('button', { name: /^data$/i });
      if (await dataTab.isVisible({ timeout: 2000 }).catch(() => false)) {
        await dataTab.click();
        await this.page.waitForTimeout(300);
      }
    }

    // Try to find and click the appropriate upload button
    let clicked = false;
    for (const label of typeMap[fileType]) {
      const button = this.page.getByRole('button', { name: new RegExp(label, 'i') });
      if (await button.first().isVisible({ timeout: 2000 }).catch(() => false)) {
        await button.first().click();
        clicked = true;
        break;
      }
    }

    if (!clicked) {
      throw new Error(`Could not find upload button for file type: ${fileType}`);
    }

    // Wait for modal to open
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForTimeout(500);

    // Upload file - find the file input
    const fileInput = this.page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(filePath);

    // Wait for file to be processed
    await this.page.waitForTimeout(1000);

    // Submit - look for create/upload button in the modal
    const submitButton = this.page.getByRole('button', { name: /create|upload/i }).last();
    await submitButton.click();

    // Wait for success
    await this.waitForSuccessToast(30000);
  }

  /**
   * Upload a folder
   */
  async uploadFolder(folderPath: string, name: string) {
    await this.clickAddDataSource();

    // Wait for the popover to appear
    await this.page.waitForTimeout(500);

    // Click "Folder Upload" integration card
    await this.page.getByRole('button', { name: /folder upload/i }).click();

    // Wait for folder upload modal
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForTimeout(500);

    // Enter name for the folder data source
    const nameInput = this.page.locator('input#name').or(
      this.page.getByLabel(/name/i)
    );
    await nameInput.fill(name);

    // Set files using the file input
    const folderInput = this.page.locator('input[type="file"]').first();
    await folderInput.setInputFiles(folderPath);

    // Wait for validation
    await this.page.waitForTimeout(1000);

    // Click upload button
    const uploadButton = this.page.getByRole('button', { name: /upload/i }).last();
    await uploadButton.click();

    // Wait for upload to complete (may take time for large folders)
    await expect(this.page.getByText(/upload.*success|folder.*success/i)).toBeVisible({ timeout: 120000 });
  }

  /**
   * Connect BigQuery data source using JSON credential file
   */
  async connectBigQuery(serviceAccountJsonPath: string, datasetId?: string) {
    await this.clickAddDataSource();

    // Wait for the popover to appear
    await this.page.waitForTimeout(500);

    // Select BigQuery - use the button with aria-label "Connect BigQuery"
    await this.page.getByRole('button', { name: /connect bigquery/i }).click();

    // Wait for modal
    await this.page.waitForLoadState('networkidle');

    // Upload service account JSON file
    const jsonInput = this.page.locator('input[accept=".json,application/json"]').or(
      this.page.locator('input[type="file"]')
    );
    await jsonInput.setInputFiles(serviceAccountJsonPath);

    // Wait for credentials to be parsed
    await expect(this.page.getByText(/successfully loaded credentials/i)).toBeVisible({ timeout: 10000 });

    // Optionally set dataset ID
    if (datasetId) {
      await this.page.locator('input#dataset_id').fill(datasetId);
    }

    // Submit
    await this.page.getByRole('button', { name: /create/i }).click();

    // Wait for success
    await this.waitForSuccessToast(30000);
  }

  /**
   * Start scanning/training on all data sources
   */
  async startScanning() {
    await this.startScanningButton().click();

    // Wait for scanning to start
    await expect(this.page.getByText(/running|scanning|processing/i)).toBeVisible({ timeout: 10000 });
  }

  /**
   * Wait for scanning/training to complete
   */
  async waitForScanningComplete(timeout = 300000) {
    // Wait for status to show complete
    await expect(this.page.getByText(/complete|success|finished/i).first()).toBeVisible({ timeout });
  }

  /**
   * Check if a data source exists in the connected sources list
   */
  async hasDataSource(name: string): Promise<boolean> {
    await this.page.waitForLoadState('networkidle');

    // Look for the data source name in a heading element (data source rows use h3)
    const dataSourceHeading = this.page.getByRole('heading', { name: new RegExp(name, 'i') });
    const count = await dataSourceHeading.count();

    if (count > 0) {
      return true;
    }

    // Also check in the general page text
    const pageText = await this.page.textContent('body').catch(() => '');
    return pageText?.toLowerCase().includes(name.toLowerCase()) || false;
  }

  /**
   * Delete a data source by name
   */
  async deleteDataSource(name: string) {
    // Find the row with the data source
    const row = this.page.locator('tr').filter({ hasText: name });

    // Click delete button in the row
    await row.getByRole('button', { name: /delete/i }).or(
      row.locator('[data-testid="delete-button"]')
    ).click();

    // Confirm deletion in modal
    await this.page.getByRole('button', { name: /confirm|delete/i }).click();

    // Wait for success
    await this.waitForSuccessToast();
  }

  /**
   * Get the count of connected data sources
   */
  async getDataSourceCount(): Promise<number> {
    // Wait for page to load
    await this.page.waitForLoadState('networkidle');

    // Try to find the count text like "2 of 2 connected"
    const countText = await this.page.getByText(/(\d+)\s+of\s+(\d+)\s+connected/i).textContent().catch(() => null);
    if (countText) {
      const match = countText.match(/(\d+)\s+of\s+(\d+)\s+connected/i);
      if (match) {
        return parseInt(match[2], 10); // Total count is the second number
      }
    }

    // Fallback: count elements with connected/configured status
    const rows = this.page.getByText(/connected|configured/i);
    return await rows.count();
  }
}
