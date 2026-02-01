import { Page, expect } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Agent Playground page object for testing agents
 */
export class AgentPlaygroundPage extends BasePage {
  // Selectors
  private readonly taskInput = () => this.page.locator('textarea').first().or(
    this.page.getByRole('textbox')
  ).or(
    this.page.locator('[data-testid="task-input"]')
  );

  private readonly submitButton = () => this.page.getByRole('button', { name: /submit|send/i }).or(
    this.page.locator('[data-testid="submit-button"]')
  );

  private readonly stopButton = () => this.page.getByRole('button', { name: /stop/i });

  private readonly streamingIndicator = () => this.page.locator('[data-streaming="true"]').or(
    this.page.locator('[class*="streaming"]')
  ).or(
    this.page.locator('[class*="loading"]')
  );

  private readonly assistantMessages = () => this.page.locator('[class*="assistant"]').or(
    this.page.locator('[data-role="assistant"]')
  ).or(
    this.page.locator('[data-testid="assistant-message"]')
  );

  private readonly userMessages = () => this.page.locator('[class*="user"]').or(
    this.page.locator('[data-role="user"]')
  ).or(
    this.page.locator('[data-testid="user-message"]')
  );

  /**
   * Navigate to playground for an agent
   */
  async navigate(projectId: string, agentId: string) {
    await this.navigateTo(`/projects/${projectId}/agents/${agentId}/playground`);
    await this.waitForPageLoad();
  }

  /**
   * Navigate to configure page
   */
  async navigateToConfigure(projectId: string, agentId: string) {
    await this.navigateTo(`/projects/${projectId}/agents/${agentId}/playground/configure`);
    await this.waitForPageLoad();
  }

  /**
   * Submit a task/question to the agent
   */
  async submitTask(task: string) {
    // Clear any existing text
    await this.taskInput().clear();

    // Type the task
    await this.taskInput().fill(task);

    // Click submit
    await this.submitButton().click();
  }

  /**
   * Wait for streaming response to complete
   */
  async waitForStreamingComplete(timeout = 60000) {
    // First, wait a moment for streaming to potentially start
    await this.page.waitForTimeout(500);

    // Wait for streaming indicator to disappear (if it exists)
    try {
      await expect(this.streamingIndicator()).toBeHidden({ timeout });
    } catch {
      // Streaming may have already completed or indicator not found
    }

    // Also wait for stop button to disappear (alternative indicator)
    try {
      await expect(this.stopButton()).toBeHidden({ timeout: 5000 });
    } catch {
      // Stop button may not exist
    }
  }

  /**
   * Wait for a new response to appear
   */
  async waitForResponse(timeout = 60000) {
    const initialCount = await this.assistantMessages().count();

    // Wait for a new message to appear
    await expect(async () => {
      const currentCount = await this.assistantMessages().count();
      expect(currentCount).toBeGreaterThan(initialCount);
    }).toPass({ timeout });
  }

  /**
   * Get the latest assistant response text
   */
  async getLatestResponse(): Promise<string | null> {
    const messages = await this.assistantMessages().all();
    if (messages.length === 0) return null;

    const lastMessage = messages[messages.length - 1];
    return await lastMessage.textContent();
  }

  /**
   * Get all assistant responses
   */
  async getAllResponses(): Promise<string[]> {
    const messages = await this.assistantMessages().all();
    const responses: string[] = [];

    for (const message of messages) {
      const text = await message.textContent();
      if (text) responses.push(text);
    }

    return responses;
  }

  /**
   * Check if the playground is ready to accept input
   */
  async isReady(): Promise<boolean> {
    try {
      await this.taskInput().waitFor({ state: 'visible', timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Stop a running response
   */
  async stopResponse() {
    if (await this.stopButton().isVisible()) {
      await this.stopButton().click();
    }
  }

  /**
   * Configure agent instructions
   */
  async setInstructions(instructions: string) {
    // Find instructions editor
    const instructionsEditor = this.page.locator('textarea[name*="instructions"]').or(
      this.page.locator('[data-testid="instructions-editor"]')
    ).or(
      this.page.getByLabel(/instructions/i)
    );

    await instructionsEditor.clear();
    await instructionsEditor.fill(instructions);
  }

  /**
   * Configure agent output format
   */
  async setOutputFormat(format: string) {
    const outputFormatEditor = this.page.locator('textarea[name*="output"]').or(
      this.page.locator('[data-testid="output-format-editor"]')
    ).or(
      this.page.getByLabel(/output.*format/i)
    );

    await outputFormatEditor.clear();
    await outputFormatEditor.fill(format);
  }

  /**
   * Save agent configuration
   */
  async saveConfiguration() {
    await this.page.getByRole('button', { name: /save/i }).click();

    // Wait for save confirmation
    await expect(this.page.getByText(/saved/i)).toBeVisible({ timeout: 10000 });
  }
}
