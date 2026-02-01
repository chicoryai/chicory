import { Page, expect } from '@playwright/test';
import { BasePage } from './base.page';

/**
 * Agent Manage page object for viewing task history
 */
export class AgentManagePage extends BasePage {
  // Selectors
  private readonly taskTable = () => this.page.locator('table').or(
    this.page.locator('[data-testid="task-table"]')
  );

  private readonly taskRows = () => this.page.locator('table tbody tr').or(
    this.page.locator('[data-testid="task-row"]')
  );

  private readonly paginationNext = () => this.page.getByRole('button', { name: /next/i });

  private readonly paginationPrev = () => this.page.getByRole('button', { name: /prev|previous/i });

  /**
   * Navigate to manage page for an agent
   */
  async navigate(projectId: string, agentId: string) {
    await this.navigateTo(`/projects/${projectId}/agents/${agentId}/manage`);
    await this.waitForPageLoad();
  }

  /**
   * Get the count of tasks in the table
   */
  async getTaskCount(): Promise<number> {
    return await this.taskRows().count();
  }

  /**
   * Check if any tasks exist
   */
  async hasTasks(): Promise<boolean> {
    try {
      await this.taskTable().waitFor({ state: 'visible', timeout: 5000 });
      const count = await this.getTaskCount();
      return count > 0;
    } catch {
      return false;
    }
  }

  /**
   * Get task details by index (0-based)
   */
  async getTaskDetails(index: number): Promise<{
    query?: string;
    response?: string;
    timestamp?: string;
    status?: string;
  }> {
    const row = this.taskRows().nth(index);

    // Extract various fields from the row
    const details: {
      query?: string;
      response?: string;
      timestamp?: string;
      status?: string;
    } = {};

    // Try to get query/input
    const queryCell = row.locator('td').first();
    details.query = await queryCell.textContent() || undefined;

    // Try to get response
    const responseCell = row.locator('td').nth(1);
    details.response = await responseCell.textContent() || undefined;

    return details;
  }

  /**
   * Click on a task to view details
   */
  async viewTaskDetails(index: number) {
    const row = this.taskRows().nth(index);
    await row.click();

    // Wait for details panel/modal to open
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Check if a specific query exists in the task history
   */
  async hasTaskWithQuery(query: string): Promise<boolean> {
    try {
      await expect(this.taskTable()).toContainText(query, { timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Go to next page of tasks
   */
  async nextPage() {
    if (await this.paginationNext().isEnabled()) {
      await this.paginationNext().click();
      await this.waitForPageLoad();
    }
  }

  /**
   * Go to previous page of tasks
   */
  async prevPage() {
    if (await this.paginationPrev().isEnabled()) {
      await this.paginationPrev().click();
      await this.waitForPageLoad();
    }
  }

  /**
   * Filter tasks by source (API, Playground, etc.)
   */
  async filterBySource(source: 'api' | 'playground' | 'mcp' | 'all') {
    const filterButton = this.page.getByRole('button', { name: /filter|source/i });

    if (await filterButton.isVisible()) {
      await filterButton.click();

      // Select the source option
      await this.page.getByRole('option', { name: new RegExp(source, 'i') }).or(
        this.page.getByText(new RegExp(source, 'i'))
      ).click();

      await this.waitForPageLoad();
    }
  }

  /**
   * Wait for new task to appear
   */
  async waitForNewTask(timeout = 30000) {
    const initialCount = await this.getTaskCount();

    await expect(async () => {
      const currentCount = await this.getTaskCount();
      expect(currentCount).toBeGreaterThan(initialCount);
    }).toPass({ timeout });
  }
}
