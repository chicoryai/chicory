import { Page, expect } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Agents listing page object
 */
export class AgentsPage extends BasePage {
  // Selectors
  private readonly createAgentButton = () => this.page.getByRole('button', { name: 'Create Agent' });

  private readonly agentCards = () => this.page.locator('[data-testid="agent-card"]').or(
    this.page.locator('[class*="agent-card"]')
  );

  private readonly agentNameInput = () => this.page.getByLabel(/name/i).or(
    this.page.locator('input[name="name"]')
  );

  private readonly agentDescriptionInput = () => this.page.getByLabel(/description/i).or(
    this.page.locator('textarea[name="description"]')
  );

  /**
   * Navigate to agents page for a project
   */
  async navigate(projectId: string) {
    await this.navigateTo(`/projects/${projectId}/agents`);
    await this.waitForPageLoad();
  }

  /**
   * Create a new agent
   */
  async createAgent(options: { name: string; description?: string }) {
    await this.createAgentButton().click();

    // Wait for form/modal
    await this.page.waitForLoadState('networkidle');

    // Fill name
    await this.agentNameInput().fill(options.name);

    // Fill description if provided
    if (options.description) {
      await this.agentDescriptionInput().fill(options.description);
    }

    // Submit
    await this.page.getByRole('button', { name: /create|submit|save/i }).click();

    // Wait for redirect to playground or success
    await this.page.waitForURL(/playground|agents/, { timeout: 30000 });
  }

  /**
   * Click on an agent to open it
   */
  async openAgent(agentName: string) {
    const agentCard = this.page.locator('[data-testid="agent-card"]').filter({ hasText: agentName }).or(
      this.page.locator('[class*="agent-card"]').filter({ hasText: agentName })
    ).or(
      this.page.getByRole('link').filter({ hasText: agentName })
    );

    await agentCard.click();
    await this.page.waitForURL(/agents\/[^/]+/, { timeout: 10000 });
  }

  /**
   * Delete an agent by name
   */
  async deleteAgent(agentName: string) {
    const agentCard = this.page.locator('[data-testid="agent-card"]').filter({ hasText: agentName }).or(
      this.page.locator('[class*="agent-card"]').filter({ hasText: agentName })
    );

    // Find and click delete button
    await agentCard.getByRole('button', { name: /delete/i }).or(
      agentCard.locator('[data-testid="delete-button"]')
    ).click();

    // Confirm deletion
    await this.page.getByRole('button', { name: /confirm|delete/i }).click();

    // Wait for success
    await this.waitForSuccessToast();
  }

  /**
   * Check if an agent exists
   */
  async hasAgent(agentName: string): Promise<boolean> {
    try {
      await expect(this.page.getByText(agentName)).toBeVisible({ timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get the count of agents
   */
  async getAgentCount(): Promise<number> {
    return await this.agentCards().count();
  }
}
