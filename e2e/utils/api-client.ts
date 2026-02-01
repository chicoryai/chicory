import { APIRequestContext, request } from '@playwright/test';

/**
 * API client for interacting with deployed Chicory agents
 */
export class ChicoryApiClient {
  private baseUrl: string;
  private apiKey: string;
  private context: APIRequestContext | null = null;

  constructor(baseUrl: string, apiKey: string) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  /**
   * Initialize the API context
   */
  async init() {
    this.context = await request.newContext({
      baseURL: this.baseUrl,
      extraHTTPHeaders: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Create a new run (execute the agent)
   */
  async createRun(projectId: string, agentId: string, input: string): Promise<{
    id: string;
    status: string;
    [key: string]: any;
  }> {
    if (!this.context) await this.init();

    const response = await this.context!.post(`/projects/${projectId}/agents/${agentId}/tasks`, {
      data: {
        content: input,
        role: 'user',
      },
    });

    if (!response.ok()) {
      const errorBody = await response.text();
      throw new Error(`API request failed: ${response.status()} - ${errorBody}`);
    }

    return response.json();
  }

  /**
   * Get run/task status
   */
  async getRun(projectId: string, agentId: string, taskId: string): Promise<{
    id: string;
    status: string;
    content?: string;
    [key: string]: any;
  }> {
    if (!this.context) await this.init();

    const response = await this.context!.get(
      `/projects/${projectId}/agents/${agentId}/tasks/${taskId}`
    );

    if (!response.ok()) {
      const errorBody = await response.text();
      throw new Error(`API request failed: ${response.status()} - ${errorBody}`);
    }

    return response.json();
  }

  /**
   * Wait for a run to complete
   */
  async waitForRunComplete(
    projectId: string,
    agentId: string,
    taskId: string,
    timeout = 60000
  ): Promise<{
    id: string;
    status: string;
    content?: string;
    [key: string]: any;
  }> {
    const startTime = Date.now();
    const pollInterval = 1000;

    while (Date.now() - startTime < timeout) {
      const run = await this.getRun(projectId, agentId, taskId);

      if (run.status === 'completed' || run.status === 'COMPLETED') {
        return run;
      }

      if (run.status === 'failed' || run.status === 'FAILED' || run.status === 'error') {
        throw new Error(`Run failed with status: ${run.status}`);
      }

      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    throw new Error(`Run ${taskId} did not complete within ${timeout}ms`);
  }

  /**
   * Execute agent and wait for result (convenience method)
   */
  async executeAndWait(
    projectId: string,
    agentId: string,
    input: string,
    timeout = 60000
  ): Promise<{
    taskId: string;
    status: string;
    response?: string;
  }> {
    // Create the run
    const createResult = await this.createRun(projectId, agentId, input);

    // Wait for completion
    const result = await this.waitForRunComplete(
      projectId,
      agentId,
      createResult.id,
      timeout
    );

    return {
      taskId: createResult.id,
      status: result.status,
      response: result.content,
    };
  }

  /**
   * List recent tasks for an agent
   */
  async listTasks(
    projectId: string,
    agentId: string,
    limit = 10
  ): Promise<Array<{
    id: string;
    status: string;
    content?: string;
    [key: string]: any;
  }>> {
    if (!this.context) await this.init();

    const response = await this.context!.get(
      `/projects/${projectId}/agents/${agentId}/tasks?limit=${limit}`
    );

    if (!response.ok()) {
      const errorBody = await response.text();
      throw new Error(`API request failed: ${response.status()} - ${errorBody}`);
    }

    return response.json();
  }

  /**
   * Clean up the API context
   */
  async dispose() {
    if (this.context) {
      await this.context.dispose();
      this.context = null;
    }
  }
}
