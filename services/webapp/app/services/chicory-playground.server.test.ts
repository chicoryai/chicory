// Tests for Playground API service functions
// Note: This test file is structured to be compatible with Jest/Vitest
// To run these tests, you'll need to install a test framework:
// npm install --save-dev vitest @vitest/ui
// Then add to package.json scripts: "test": "vitest"

import {
  createPlayground,
  listPlaygrounds,
  getPlayground,
  updatePlayground,
  deletePlayground,
  createPlaygroundInvocation,
  listPlaygroundInvocations,
  getPlaygroundInvocation
} from './chicory-playground.server';

import type {
  PlaygroundCreate,
  PlaygroundUpdate,
  PlaygroundResponse,
  InvocationCreate,
  InvocationResponse
} from '../types/playground';

// Mock fetch globally
const mockFetch = jest.fn() || vi.fn();
global.fetch = mockFetch as any;

// Helper to create mock response
const mockResponse = (data: any, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  statusText: status === 200 ? 'OK' : 'Error',
  json: async () => data,
  text: async () => JSON.stringify(data)
});

describe('Playground Service', () => {
  const projectId = 'test-project-123';
  const agentId = 'test-agent-456';
  const playgroundId = 'test-playground-789';

  beforeEach(() => {
    mockFetch.mockClear();
    // Reset console methods
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('createPlayground', () => {
    it('should create a playground successfully', async () => {
      const playgroundData: PlaygroundCreate = {
        name: 'Test Playground',
        description: 'A test playground',
        settings: { temperature: 0.7 }
      };

      const mockPlayground: PlaygroundResponse = {
        id: playgroundId,
        agent_id: agentId,
        project_id: projectId,
        name: 'Test Playground',
        description: 'A test playground',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        settings: { temperature: 0.7 }
      };

      mockFetch.mockResolvedValueOnce(mockResponse(mockPlayground));

      const result = await createPlayground(projectId, agentId, playgroundData);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/projects/${projectId}/agents/${agentId}/playgrounds`),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(playgroundData)
        })
      );
      expect(result).toEqual(mockPlayground);
    });

    it('should handle creation errors', async () => {
      const playgroundData: PlaygroundCreate = {
        name: 'Test Playground'
      };

      mockFetch.mockResolvedValueOnce(
        mockResponse({ detail: 'Invalid data' }, 400)
      );

      await expect(
        createPlayground(projectId, agentId, playgroundData)
      ).rejects.toThrow('Failed to create playground');
    });
  });

  describe('listPlaygrounds', () => {
    it('should list playgrounds with default pagination', async () => {
      const mockList = {
        playgrounds: [
          {
            id: '1',
            agent_id: agentId,
            project_id: projectId,
            name: 'Playground 1',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z'
          },
          {
            id: '2',
            agent_id: agentId,
            project_id: projectId,
            name: 'Playground 2',
            created_at: '2024-01-02T00:00:00Z',
            updated_at: '2024-01-02T00:00:00Z'
          }
        ],
        total: 2,
        has_more: false
      };

      mockFetch.mockResolvedValueOnce(mockResponse(mockList));

      const result = await listPlaygrounds(projectId, agentId);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/projects/${projectId}/agents/${agentId}/playgrounds?limit=10&skip=0`)
      );
      expect(result.playgrounds).toHaveLength(2);
      expect(result.has_more).toBe(false);
    });

    it('should handle pagination parameters', async () => {
      const mockList = {
        playgrounds: [],
        has_more: true
      };

      mockFetch.mockResolvedValueOnce(mockResponse(mockList));

      await listPlaygrounds(projectId, agentId, 20, 10);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('limit=20&skip=10')
      );
    });

    it('should return empty list on error', async () => {
      mockFetch.mockResolvedValueOnce(mockResponse({}, 500));

      const result = await listPlaygrounds(projectId, agentId);

      expect(result.playgrounds).toEqual([]);
      expect(result.has_more).toBe(false);
    });
  });

  describe('getPlayground', () => {
    it('should get a single playground', async () => {
      const mockPlayground: PlaygroundResponse = {
        id: playgroundId,
        agent_id: agentId,
        project_id: projectId,
        name: 'Test Playground',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      };

      mockFetch.mockResolvedValueOnce(mockResponse(mockPlayground));

      const result = await getPlayground(projectId, agentId, playgroundId);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/projects/${projectId}/agents/${agentId}/playgrounds/${playgroundId}`)
      );
      expect(result).toEqual(mockPlayground);
    });

    it('should return null for 404', async () => {
      mockFetch.mockResolvedValueOnce(mockResponse({}, 404));

      const result = await getPlayground(projectId, agentId, playgroundId);

      expect(result).toBeNull();
    });
  });

  describe('updatePlayground', () => {
    it('should update a playground', async () => {
      const updates: PlaygroundUpdate = {
        name: 'Updated Playground',
        settings: { temperature: 0.9 }
      };

      const mockUpdated: PlaygroundResponse = {
        id: playgroundId,
        agent_id: agentId,
        project_id: projectId,
        name: 'Updated Playground',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z',
        settings: { temperature: 0.9 }
      };

      mockFetch.mockResolvedValueOnce(mockResponse(mockUpdated));

      const result = await updatePlayground(projectId, agentId, playgroundId, updates);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/projects/${projectId}/agents/${agentId}/playgrounds/${playgroundId}`),
        expect.objectContaining({
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updates)
        })
      );
      expect(result).toEqual(mockUpdated);
    });
  });

  describe('deletePlayground', () => {
    it('should delete a playground successfully', async () => {
      mockFetch.mockResolvedValueOnce(mockResponse({}, 204));

      const result = await deletePlayground(projectId, agentId, playgroundId);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/projects/${projectId}/agents/${agentId}/playgrounds/${playgroundId}`),
        expect.objectContaining({
          method: 'DELETE'
        })
      );
      expect(result).toBe(true);
    });

    it('should return true for 404 (already deleted)', async () => {
      mockFetch.mockResolvedValueOnce(mockResponse({}, 404));

      const result = await deletePlayground(projectId, agentId, playgroundId);

      expect(result).toBe(true);
    });

    it('should throw error for other failures', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ detail: 'Forbidden' }, 403)
      );

      await expect(
        deletePlayground(projectId, agentId, playgroundId)
      ).rejects.toThrow('Failed to delete playground');
    });
  });

  describe('createPlaygroundInvocation', () => {
    const invocationId = 'test-invocation-123';

    it('should create an invocation successfully', async () => {
      const invocationData: InvocationCreate = {
        input: 'Test input prompt',
        metadata: { user: 'test-user' }
      };

      const mockInvocation: InvocationResponse = {
        id: invocationId,
        playground_id: playgroundId,
        agent_id: agentId,
        project_id: projectId,
        input: 'Test input prompt',
        output: 'Generated response',
        status: 'completed',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:01Z',
        duration_ms: 1000,
        token_usage: {
          input_tokens: 10,
          output_tokens: 20,
          total_tokens: 30
        },
        cost_usd: 0.001
      };

      mockFetch.mockResolvedValueOnce(mockResponse(mockInvocation, 201));

      const result = await createPlaygroundInvocation(
        projectId,
        agentId,
        playgroundId,
        invocationData
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(
          `/projects/${projectId}/agents/${agentId}/playgrounds/${playgroundId}/invocations`
        ),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(invocationData)
        })
      );
      expect(result).toEqual(mockInvocation);
    });
  });

  describe('listPlaygroundInvocations', () => {
    it('should list invocations with default parameters', async () => {
      const mockList = {
        invocations: [
          {
            id: '1',
            playground_id: playgroundId,
            agent_id: agentId,
            project_id: projectId,
            input: 'Input 1',
            status: 'completed',
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:01Z'
          },
          {
            id: '2',
            playground_id: playgroundId,
            agent_id: agentId,
            project_id: projectId,
            input: 'Input 2',
            status: 'failed',
            error: 'Timeout',
            created_at: '2024-01-02T00:00:00Z',
            updated_at: '2024-01-02T00:00:01Z'
          }
        ],
        total: 2,
        has_more: false
      };

      mockFetch.mockResolvedValueOnce(mockResponse(mockList));

      const result = await listPlaygroundInvocations(projectId, agentId, playgroundId);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(
          `/projects/${projectId}/agents/${agentId}/playgrounds/${playgroundId}/invocations?limit=10&skip=0&sort_order=desc`
        )
      );
      expect(result.invocations).toHaveLength(2);
      expect(result.has_more).toBe(false);
    });

    it('should handle custom pagination and sort order', async () => {
      const mockList = {
        invocations: [],
        has_more: false
      };

      mockFetch.mockResolvedValueOnce(mockResponse(mockList));

      await listPlaygroundInvocations(projectId, agentId, playgroundId, 25, 50, 'asc');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('limit=25&skip=50&sort_order=asc')
      );
    });
  });

  describe('getPlaygroundInvocation', () => {
    const invocationId = 'test-invocation-123';

    it('should get a single invocation', async () => {
      const mockInvocation: InvocationResponse = {
        id: invocationId,
        playground_id: playgroundId,
        agent_id: agentId,
        project_id: projectId,
        input: 'Test input',
        output: 'Test output',
        status: 'completed',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:01Z'
      };

      mockFetch.mockResolvedValueOnce(mockResponse(mockInvocation));

      const result = await getPlaygroundInvocation(
        projectId,
        agentId,
        playgroundId,
        invocationId
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(
          `/projects/${projectId}/agents/${agentId}/playgrounds/${playgroundId}/invocations/${invocationId}`
        )
      );
      expect(result).toEqual(mockInvocation);
    });

    it('should return null for 404', async () => {
      mockFetch.mockResolvedValueOnce(mockResponse({}, 404));

      const result = await getPlaygroundInvocation(
        projectId,
        agentId,
        playgroundId,
        invocationId
      );

      expect(result).toBeNull();
    });
  });
});

// Test environment setup instructions
describe('Test Setup Instructions', () => {
  it.skip('To set up testing for this project', () => {
    console.log(`
    To enable testing for this project, follow these steps:

    1. Install test dependencies:
       npm install --save-dev vitest @vitest/ui happy-dom

    2. Add test script to package.json:
       "scripts": {
         ...
         "test": "vitest",
         "test:ui": "vitest --ui",
         "test:coverage": "vitest --coverage"
       }

    3. Create vitest.config.ts in project root:
       import { defineConfig } from 'vitest/config';

       export default defineConfig({
         test: {
           environment: 'happy-dom',
           globals: true,
           setupFiles: ['./test/setup.ts']
         }
       });

    4. Create test/setup.ts for global test setup:
       // Add any global test setup here
       process.env.CHICORY_API_URL = 'http://test-api.example.com';

    5. Run tests:
       npm test
    `);
  });
});