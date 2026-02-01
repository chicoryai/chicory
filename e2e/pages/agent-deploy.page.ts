import { Page, expect } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Agent Deploy page object for deployment and API key management
 */
export class AgentDeployPage extends BasePage {
  // Selectors
  private readonly deployApiButton = () => this.page.getByRole('button', { name: /deploy.*api|generate.*key/i });

  private readonly apiKeyDisplay = () => this.page.locator('code').or(
    this.page.locator('[data-testid="api-key"]')
  ).or(
    this.page.locator('[class*="api-key"]')
  );

  private readonly showApiKeyButton = () => this.page.getByRole('button', { name: /show/i });

  private readonly copyApiKeyButton = () => this.page.getByRole('button', { name: /copy/i });

  private readonly regenerateButton = () => this.page.getByRole('button', { name: /regenerate/i });

  private readonly enableAgentButton = () => this.page.getByRole('button', { name: /enable.*agent/i });

  private readonly disableAgentButton = () => this.page.getByRole('button', { name: /disable.*agent/i });

  private readonly deploymentStatus = () => this.page.locator('[class*="deployment"]').or(
    this.page.locator('[data-testid="deployment-status"]')
  );

  /**
   * Navigate to deploy page for an agent
   */
  async navigate(projectId: string, agentId: string) {
    await this.navigateTo(`/projects/${projectId}/agents/${agentId}/deploy`);
    await this.waitForPageLoad();
  }

  /**
   * Deploy API access for the agent
   */
  async deployApi() {
    // Check if already deployed
    const isDeployed = await this.isDeployed();
    if (isDeployed) {
      console.log('Agent already has API deployed');
      return;
    }

    await this.deployApiButton().click();

    // Wait for API key to be generated
    await expect(this.apiKeyDisplay()).toBeVisible({ timeout: 30000 });
  }

  /**
   * Get the API key
   */
  async getApiKey(): Promise<string> {
    // Show the API key if it's hidden
    try {
      if (await this.showApiKeyButton().isVisible({ timeout: 2000 })) {
        await this.showApiKeyButton().click();
        await this.page.waitForTimeout(500);
      }
    } catch {
      // Show button may not exist
    }

    // Get the API key text
    const keyElement = this.apiKeyDisplay().first();
    await expect(keyElement).toBeVisible();

    const keyText = await keyElement.textContent();
    return keyText?.trim() || '';
  }

  /**
   * Check if API is deployed
   */
  async isDeployed(): Promise<boolean> {
    try {
      await this.apiKeyDisplay().waitFor({ state: 'visible', timeout: 3000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Enable the agent
   */
  async enableAgent() {
    // Check if already enabled
    const isEnabled = await this.isAgentEnabled();
    if (isEnabled) {
      console.log('Agent already enabled');
      return;
    }

    await this.enableAgentButton().click();

    // Wait for status change
    await expect(this.page.getByText(/enabled/i)).toBeVisible({ timeout: 10000 });
  }

  /**
   * Disable the agent
   */
  async disableAgent() {
    // Check if already disabled
    const isEnabled = await this.isAgentEnabled();
    if (!isEnabled) {
      console.log('Agent already disabled');
      return;
    }

    await this.disableAgentButton().click();

    // Wait for status change
    await expect(this.page.getByText(/disabled/i)).toBeVisible({ timeout: 10000 });
  }

  /**
   * Check if agent is enabled
   */
  async isAgentEnabled(): Promise<boolean> {
    try {
      // Look for enabled indicator
      await this.page.getByText(/enabled/i).waitFor({ state: 'visible', timeout: 3000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Regenerate API key
   */
  async regenerateApiKey(): Promise<string> {
    await this.regenerateButton().click();

    // Confirm regeneration if dialog appears
    try {
      await this.page.getByRole('button', { name: /confirm/i }).click({ timeout: 3000 });
    } catch {
      // No confirmation dialog
    }

    // Wait for new key
    await this.page.waitForTimeout(1000);

    return await this.getApiKey();
  }

  /**
   * Copy API key to clipboard
   */
  async copyApiKey() {
    await this.copyApiKeyButton().click();

    // Wait for copy confirmation
    await this.waitForToast(/copied/i, { timeout: 5000 });
  }

  /**
   * Get the API endpoint URL
   */
  async getApiEndpoint(): Promise<string | null> {
    const endpointElement = this.page.locator('[data-testid="api-endpoint"]').or(
      this.page.locator('[class*="endpoint"]')
    ).or(
      this.page.getByText(/api.*endpoint/i).locator('+ *')
    );

    try {
      const text = await endpointElement.textContent({ timeout: 5000 });
      return text?.trim() || null;
    } catch {
      return null;
    }
  }
}
