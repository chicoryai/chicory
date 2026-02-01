import { useState, useEffect } from "react";
import { Form, useActionData, useLoaderData } from "@remix-run/react";
import { json, redirect } from "@remix-run/node";
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { auth } from "~/auth/auth.server";
import { ClipboardDocumentIcon, EyeIcon, EyeSlashIcon, PlusIcon, TrashIcon, CheckIcon, CodeBracketIcon } from "@heroicons/react/24/outline";

interface ApiKey {
  apiKeyId: string;
  name: string;
  prefix: string;
  suffix: string;
  createdAt: number;
  expiresAtSeconds: number | null;
  lastUsedAt?: number;
  metadata?: Record<string, any>;
}

interface NewApiKey {
  apiKeyId: string;
  apiKeyToken: string;
}

export async function loader({ request }: LoaderFunctionArgs) {
  // Get the authenticated user
  const user = await auth.getUser(request, {});
  
  if (!user) {
    return redirect("/api/auth/login");
  }
  
  try {
    // Fetch the user's API keys using PropelAuth's API
    const apiKeysResponse = await auth.api.fetchCurrentApiKeys({
      userId: user.userId,
      pageSize: 100,
      pageNumber: 0,
    });
    
    // Transform the API keys to match our interface
    const apiKeys = apiKeysResponse.apiKeys.map(key => ({
      apiKeyId: key.apiKeyId,
      name: key.metadata?.name || "Unnamed Key",
      prefix: key.apiKeyId.substring(0, 8),
      suffix: key.apiKeyId.substring(key.apiKeyId.length - 6),
      createdAt: key.createdAt,
      expiresAtSeconds: key.expiresAtSeconds,
      lastUsedAt: key.lastUsedAt,
      metadata: key.metadata,
    }));
    
    return json({ user, apiKeys });
  } catch (error) {
    console.error("Error fetching API keys:", error);
    return json({ user, apiKeys: [], error: "Failed to fetch API keys" });
  }
}

type ActionData = 
  | { success: true; message: string; newKey: { apiKeyId: string; apiKeyToken: string; name: string }; showNewKey: true }
  | { success: true; message: string; deletedKeyId: string }
  | { success: false; error: string };

export async function action({ request }: ActionFunctionArgs) {
  const user = await auth.getUser(request, {});
  
  if (!user) {
    return json({ success: false, error: "Unauthorized" } as ActionData, { status: 401 });
  }
  
  const formData = await request.formData();
  const action = formData.get("_action") as string;
  
  try {
    if (action === "create") {
      const keyName = formData.get("keyName") as string;
      
      if (!keyName) {
        return json({ success: false, error: "Key name is required" } as ActionData, { status: 400 });
      }
      
      // Create an API key using PropelAuth's API
      // Set expiration to 1 year from now (optional)
      const oneYearFromNow = Math.floor(Date.now() / 1000) + 31536000;
      
      const newKey = await auth.api.createApiKey({
        userId: user.userId,
        expiresAtSeconds: oneYearFromNow,
        metadata: {
          name: keyName,
          createdBy: user.email,
        }
      });
      
      return json({ 
        success: true, 
        message: "API key created successfully",
        newKey: {
          ...newKey,
          name: keyName,
        },
        showNewKey: true
      } as ActionData);
    } else if (action === "delete") {
      const keyId = formData.get("keyId") as string;
      
      if (!keyId) {
        return json({ success: false, error: "Key ID is required" } as ActionData, { status: 400 });
      }
      
      // Delete the API key using PropelAuth's API
      await auth.api.deleteApiKey(keyId);
      
      return json({ 
        success: true, 
        message: "API key deleted successfully",
        deletedKeyId: keyId
      } as ActionData);
    }
    
    return json({ success: false, error: "Invalid action" } as ActionData, { status: 400 });
  } catch (error) {
    console.error("Error managing API keys:", error);
    return json({ success: false, error: "Failed to manage API keys" } as ActionData, { status: 500 });
  }
}

export default function ApiKeysSettings() {
  const { user, apiKeys } = useLoaderData<typeof loader>();
  const actionData = useActionData<ActionData>();
  const [isCreating, setIsCreating] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [visibleKeyId, setVisibleKeyId] = useState<string | null>(null);
  const [newKey, setNewKey] = useState<string | null>(null);

  // Update newKey when actionData changes (after form submission)
  useEffect(() => {
    if (actionData?.success && 'newKey' in actionData && actionData.showNewKey) {
      setNewKey(actionData.newKey.apiKeyToken);
      setIsCreating(false); // Close the create form
      setKeyName(""); // Reset the form
    }
  }, [actionData]);
  
  // Filter out deleted keys
  const filteredKeys = apiKeys.filter(
    key => !(actionData?.success && 'deletedKeyId' in actionData && key.apiKeyId === actionData.deletedKeyId)
  );
  
  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    // You could add a toast notification here
  };
  
  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };
  
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">API Keys</h2>
        <button
          type="button"
          onClick={() => setIsCreating(!isCreating)}
          className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-purple-500 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          Create API Key
        </button>
      </div>
      
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        API keys allow you to authenticate requests to the Chicory API. Keep your API keys secure and never share them publicly.
      </p>
      
      {actionData?.success && !('showNewKey' in actionData) && (
        <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-md">
          {actionData.message}
        </div>
      )}
      
      {actionData?.success === false && actionData.error && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-md">
          {actionData.error}
        </div>
      )}
      
      {isCreating && (
        <div className="mb-6 bg-gray-50 dark:bg-gray-700/30 rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Create New API Key</h3>
          
          <Form method="post" className="space-y-4">
            <input type="hidden" name="_action" value="create" />
            
            <div>
              <label htmlFor="keyName" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Key Name
              </label>
              <input
                type="text"
                id="keyName"
                name="keyName"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                placeholder="e.g., Development, Production, etc."
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-800 dark:text-white sm:text-sm"
                required
              />
            </div>
            
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white dark:bg-gray-800 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-sm font-medium text-white bg-purple-500 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Create
              </button>
            </div>
          </Form>
        </div>
      )}
      
      {newKey && (
        <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-md font-medium text-green-800 dark:text-green-300">API Key Created Successfully</h3>
            <button
              type="button"
              onClick={() => setNewKey(null)}
              className="text-green-700 dark:text-green-400 hover:text-green-600 dark:hover:text-green-300"
            >
              &times;
            </button>
          </div>
          <p className="text-sm text-green-700 dark:text-green-400 mb-3">
            This is the only time your API key will be displayed. Please copy it now and store it securely.
          </p>
          <div className="flex items-center space-x-2">
            <code className="flex-1 p-2 bg-white dark:bg-gray-800 border border-green-300 dark:border-green-700 rounded text-sm font-mono overflow-x-auto">
              {newKey}
            </code>
            <button
              type="button"
              onClick={() => handleCopyKey(newKey)}
              className="p-2 text-green-700 dark:text-green-400 hover:text-green-600 dark:hover:text-green-300"
              title="Copy to clipboard"
            >
              <ClipboardDocumentIcon className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}
      
      <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200 dark:divide-gray-700">
          {filteredKeys.length > 0 ? (
            filteredKeys.map((apiKey) => (
              <li key={apiKey.apiKeyId} className="px-4 py-4 sm:px-6">
                <div className="flex items-center justify-between">
                  <div className="flex flex-col">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white">{apiKey.name}</h4>
                    <div className="mt-1 flex items-center">
                      <code className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                        {apiKey.prefix}•••••••••••••{apiKey.suffix}
                      </code>
                    </div>
                  </div>
                  <Form method="post">
                    <input type="hidden" name="_action" value="delete" />
                    <input type="hidden" name="keyId" value={apiKey.apiKeyId} />
                    <button
                      type="submit"
                      className="ml-2 text-red-600 hover:text-red-500 dark:text-red-500 dark:hover:text-red-400"
                      title="Delete API key"
                    >
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  </Form>
                </div>
                <div className="mt-2 sm:flex sm:justify-between">
                  <div className="sm:flex">
                    <p className="flex items-center text-xs text-gray-500 dark:text-gray-400">
                      Created: {formatDate(apiKey.createdAt)}
                    </p>
                    {apiKey.lastUsedAt && (
                      <p className="mt-1 flex items-center text-xs text-gray-500 dark:text-gray-400 sm:mt-0 sm:ml-6">
                        Last used: {formatDate(apiKey.lastUsedAt)}
                      </p>
                    )}
                    {apiKey.expiresAtSeconds && (
                      <p className="mt-1 flex items-center text-xs text-gray-500 dark:text-gray-400 sm:mt-0 sm:ml-6">
                        Expires: {formatDate(apiKey.expiresAtSeconds)}
                      </p>
                    )}
                  </div>
                </div>
              </li>
            ))
          ) : (
            <li className="px-4 py-6 sm:px-6 text-center text-gray-500 dark:text-gray-400">
              No API keys found. Create one to get started.
            </li>
          )}
        </ul>
      </div>
      
      {/* MCP Configuration Section */}
      <div className="mt-8 space-y-6">
        <div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">MCP Configuration</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Use your API key to connect Chicory's MCP server to your IDE. Configure once to access all your projects.
          </p>
        </div>

        {/* Available Tools */}
        <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md p-6">
          <h4 className="text-md font-medium text-gray-900 dark:text-white mb-3">Available MCP Tools</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              // Project & Agent Management
              { name: 'chicory_list_projects', description: 'List all accessible projects' },
              { name: 'chicory_get_context', description: 'Get project context and MCP tools' },
              { name: 'chicory_create_agent', description: 'Create new agents with custom prompts' },
              { name: 'chicory_list_agents', description: 'List all agents in a project' },
              { name: 'chicory_get_agent', description: 'Get detailed agent information' },
              { name: 'chicory_update_agent', description: 'Update agent configuration' },
              { name: 'chicory_deploy_agent', description: 'Deploy (enable) an agent' },
              { name: 'chicory_execute_agent', description: 'Execute an agent with a task' },
              { name: 'chicory_list_agent_tasks', description: 'List all tasks executed by an agent' },
              { name: 'chicory_get_agent_task', description: 'Get task details with execution trail' },
              // Evaluations
              { name: 'chicory_create_evaluation', description: 'Create evaluation with test cases' },
              { name: 'chicory_list_evaluations', description: 'List all evaluations for an agent' },
              { name: 'chicory_get_evaluation', description: 'Get evaluation details and test cases' },
              { name: 'chicory_execute_evaluation', description: 'Run an evaluation on an agent' },
              { name: 'chicory_get_evaluation_result', description: 'Get evaluation run results and scores' },
              { name: 'chicory_list_evaluation_runs', description: 'List all runs for an evaluation' },
              { name: 'chicory_add_evaluation_test_cases', description: 'Add test cases to an evaluation' },
              { name: 'chicory_delete_evaluation', description: 'Delete an evaluation' },
              // Data Sources / Integrations
              { name: 'chicory_list_data_source_types', description: 'List available integration types' },
              { name: 'chicory_list_data_sources', description: 'List connected data sources in a project' },
              { name: 'chicory_get_data_source', description: 'Get data source details' },
              { name: 'chicory_create_data_source', description: 'Create a new data source/integration' },
              { name: 'chicory_update_data_source', description: 'Update data source configuration' },
              { name: 'chicory_delete_data_source', description: 'Delete a data source' },
              { name: 'chicory_validate_credentials', description: 'Validate data source credentials' },
              { name: 'chicory_test_connection', description: 'Test connection to a data source' },
              // Folder/File Management
              { name: 'chicory_list_folder_files', description: 'List files in a folder upload' },
              { name: 'chicory_get_folder_file', description: 'Get file details and download URL' },
              { name: 'chicory_delete_folder_file', description: 'Delete a file from folder upload' }
            ].map((tool) => (
              <div 
                key={tool.name}
                className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <CodeBracketIcon className="h-5 w-5 text-purple-600 dark:text-purple-400 flex-shrink-0 mt-0.5" />
                <div>
                  <code className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {tool.name}
                  </code>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {tool.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* IDE Configurations */}
        <MCPConfigCard
          title="Claude Code CLI"
          configPath="~/Library/Application Support/Claude/claude_desktop_config.json"
          config={{
            mcpServers: {
              "chicory": {
                type: "http",
                url: "https://app.chicory.ai/mcp/platform",
                headers: {
                  "Authorization": "Bearer YOUR_API_KEY_HERE"
                },
                timeout: 300000
              }
            }
          }}
        />

        <MCPConfigCard
          title="Claude Desktop"
          configPath="~/Library/Application Support/Claude/claude_desktop_config.json"
          config={{
            mcpServers: {
              "chicory": {
                command: "npx",
                args: [
                  "-y",
                  "mcp-remote",
                  "https://app.chicory.ai/mcp/platform",
                  "--header",
                  "Authorization: Bearer YOUR_API_KEY_HERE"
                ]
              }
            }
          }}
        />

        <MCPConfigCard
          title="Cursor"
          configPath="~/.cursor/mcp_settings.json"
          config={{
            mcpServers: {
              "chicory": {
                url: "https://app.chicory.ai/mcp/platform",
                headers: {
                  "Authorization": "Bearer YOUR_API_KEY_HERE"
                }
              }
            }
          }}
        />

        <MCPConfigCard
          title="Windsurf"
          configPath="~/.codeium/windsurf/mcp_config.json"
          config={{
            mcpServers: {
              "chicory": {
                command: "npx",
                args: ["-y", "@modelcontextprotocol/server-http", "https://app.chicory.ai/mcp/platform"],
                env: {
                  AUTHORIZATION: "Bearer YOUR_API_KEY_HERE"
                }
              }
            }
          }}
        />

        {/* Setup Instructions */}
        <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md p-6">
          <h4 className="text-md font-medium text-gray-900 dark:text-white mb-4">Setup Instructions</h4>
          <ol className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-400 rounded-full flex items-center justify-center text-xs font-semibold">
                1
              </span>
              <span>Create an API key above and copy it</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-400 rounded-full flex items-center justify-center text-xs font-semibold">
                2
              </span>
              <span>Copy the configuration for your IDE using the copy button</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-400 rounded-full flex items-center justify-center text-xs font-semibold">
                3
              </span>
              <span>Replace YOUR_API_KEY_HERE with your actual API key</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-400 rounded-full flex items-center justify-center text-xs font-semibold">
                4
              </span>
              <span>Open your IDE's configuration file (path shown in each card)</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-400 rounded-full flex items-center justify-center text-xs font-semibold">
                5
              </span>
              <span>Add the configuration to the file (merge with existing config if needed)</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex-shrink-0 w-6 h-6 bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-400 rounded-full flex items-center justify-center text-xs font-semibold">
                6
              </span>
              <span>Restart your IDE for changes to take effect</span>
            </li>
          </ol>
        </div>
      </div>
    </div>
  );
}

function MCPConfigCard({ title, configPath, config }: { title: string; configPath: string; config: object }) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(JSON.stringify(config, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-white dark:bg-gray-800 shadow overflow-hidden sm:rounded-md p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h4 className="text-md font-medium text-gray-900 dark:text-white">{title}</h4>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Configuration file: <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded">{configPath}</code>
          </p>
        </div>
      </div>
      <div className="relative">
        <pre className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 overflow-x-auto text-sm border border-gray-200 dark:border-gray-700">
          <code className="text-gray-800 dark:text-gray-200">
            {JSON.stringify(config, null, 2)}
          </code>
        </pre>
        <button
          onClick={copyToClipboard}
          className="absolute top-2 right-2 p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          title="Copy to clipboard"
        >
          {copied ? (
            <CheckIcon className="h-4 w-4 text-green-600" />
          ) : (
            <ClipboardDocumentIcon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
          )}
        </button>
      </div>
    </div>
  );
}
