/**
 * DeploymentSection Component
 * API endpoint and deployment configuration
 */

import { useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { 
  ClipboardDocumentIcon, 
  EyeIcon, 
  EyeSlashIcon,
  CodeBracketIcon,
  ServerIcon,
  InformationCircleIcon,
  ArrowPathIcon,
  PowerIcon
} from "@heroicons/react/24/outline";
import { Form, useSubmit } from "@remix-run/react";

// API endpoints configuration - dynamically determine base URL
const getApiBaseUrl = () => {
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/api/v1`;
  }
  return "https://app.chicory.ai/api/v1";
};

interface DeploymentSectionProps {
  agentId: string;
  projectId: string;
  apiKey?: string;
  isDeployed?: boolean;
  deploymentStatus?: "idle" | "deploying" | "success" | "error";
  deploymentError?: string;
  onDeploy?: () => void;
  agentStatus?: string;
  isUpdatingStatus?: boolean;
}

export function DeploymentSection({ 
  agentId, 
  projectId, 
  apiKey, 
  isDeployed = false,
  deploymentStatus = "idle",
  deploymentError,
  onDeploy,
  agentStatus = "disabled",
  isUpdatingStatus = false
}: DeploymentSectionProps) {
  const [showApiKey, setShowApiKey] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [localErrorMessage, setLocalErrorMessage] = useState<string>("");
  const [activeTab, setActiveTab] = useState<'curl' | 'python' | 'nodejs'>('curl');
  const [activeEndpoint, setActiveEndpoint] = useState<'create' | 'get'>('create');
  const [showAcpInfo, setShowAcpInfo] = useState(false);
  const submit = useSubmit();

  // Generate API endpoint dynamically
  const apiBaseUrl = getApiBaseUrl();
  const apiEndpoint = typeof window !== 'undefined'
    ? `${window.location.origin}/v1/agents/${agentId}`
    : `https://app.chicory.ai/v1/agents/${agentId}`;
  
  // Update local error message when deployment error changes
  useEffect(() => {
    if (deploymentError) {
      setLocalErrorMessage(deploymentError);
    }
  }, [deploymentError]);

  // Handle deploy agent
  const handleDeployAgent = () => {
    setLocalErrorMessage("");
    if (onDeploy) {
      onDeploy();
    }
  };
  
  // Handle toggle status
  const handleToggleStatus = () => {
    const newState = agentStatus === 'enabled' ? 'disabled' : 'enabled';
    
    const formData = new FormData();
    formData.append('intent', 'updateStatus');
    formData.append('state', newState);
    
    submit(formData, { method: 'post' });
  };
  
  // Helper function to get deployment icon color based on status
  const getDeploymentIconColor = () => {
    switch (deploymentStatus) {
      case "deploying":
        return "text-yellow-400";
      case "success":
        return "text-green-500";
      case "error":
        return "text-red-500";
      default:
        return "text-gray-400";
    }
  };

  // Helper function to get API key display value
  const getApiKeyDisplay = () => {
    // If we have an API key, always display it regardless of deployment status
    if (apiKey) return apiKey;
    
    // If we're deploying but don't have an API key yet, show a loading message
    if (deploymentStatus === "deploying") {
      return "Generating API key...";
    }
    
    // Default fallback
    return "YOUR_API_KEY";
  };

  // Copy to clipboard
  const copyToClipboard = useCallback((text: string, type: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(type);
      setTimeout(() => setCopied(null), 2000);
    });
  }, []);
  
  // Function to generate and copy code snippet based on active tab and endpoint
  const handleCopyCodeSnippet = () => {
    // Extract agent ID from the endpoint URL
    const currentTime = new Date().toISOString();
    const runsEndpoint = `${apiBaseUrl}/runs`;
    
    let codeSnippet = '';
    
    if (activeEndpoint === 'create') {
      if (activeTab === 'curl') {
        codeSnippet = `curl -X POST ${runsEndpoint} \\
-H "Content-Type: application/json" \\
-H "Authorization: Bearer ${getApiKeyDisplay()}" \\
-d '{
  "agent_name": "${agentId}",
  "input": [
    {
      "parts": [
        {
          "content_type": "text/plain",
          "content": "Your question or input here"
        }
      ],
      "created_at": "${currentTime}"
    }
  ]
}'`;
      } else if (activeTab === 'python') {
        codeSnippet = `import asyncio
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart

async def run_async():
    async with Client(base_url="${apiBaseUrl}", auth=("Bearer ${getApiKeyDisplay()}") as client:
        run = await client.run_async(
            agent="${agentId}",
            input=[Message(parts=[MessagePart(content="Hello")])]
        )
        print("Run ID:", run.run_id)
        
        # Later, retrieve results
        result = await client.get_run(run.run_id)
        print(result)

if __name__ == "__main__":
    asyncio.run(run_async())`;
      } else {
        codeSnippet = `const fetch = require('node-fetch');

const url = '${runsEndpoint}';
const options = {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ${getApiKeyDisplay()}'
  },
  body: JSON.stringify({
    agent_name: "${agentId}",
    input: [
      {
        parts: [
          {
            content_type: "text/plain",
            content: "Your question or input here"
          }
        ],
        created_at: "${currentTime}"
      }
    ]
  })
};

fetch(url, options)
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));`;
      }
    } else { // 'get' endpoint
      const runIdPlaceholder = 'YOUR_RUN_ID';
      
      if (activeTab === 'curl') {
        codeSnippet = `curl -X GET ${runsEndpoint}/${runIdPlaceholder} \\
-H "Authorization: Bearer ${getApiKeyDisplay()}"`;
      } else if (activeTab === 'python') {
        codeSnippet = `import asyncio
from acp_sdk.client import Client

async def run_sync():
    async with Client(base_url="${apiBaseUrl}", auth=("Bearer ${getApiKeyDisplay()}") as client:
        run = await client.run_sync(
            agent="${agentId}",
            input=[Message(parts=[MessagePart(content="Hello")])]
        )
        print(run.output)

if __name__ == "__main__":
    asyncio.run(run_sync())`;
      } else {
        codeSnippet = `const fetch = require('node-fetch');

const url = '${runsEndpoint}/${runIdPlaceholder}';
const options = {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ${getApiKeyDisplay()}'
  }
};

fetch(url, options)
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));`;
      }
    }
    
    copyToClipboard(codeSnippet, 'code');
  };

  return (
    <div>
      {isDeployed ? (
        <div className="space-y-6">
          {/* Language Tabs */}
          <div>
            <div className="flex space-x-2 mb-4 items-center">
              <button
                onClick={() => setActiveTab('curl')}
                className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${
                  activeTab === 'curl' 
                    ? 'bg-purple-600 text-white' 
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                cURL
              </button>
              <button
                onClick={() => setActiveTab('python')}
                className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${
                  activeTab === 'python' 
                    ? 'bg-purple-600 text-white' 
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                Python
              </button>
              <button
                onClick={() => setActiveTab('nodejs')}
                className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${
                  activeTab === 'nodejs' 
                    ? 'bg-purple-600 text-white' 
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                }`}
              >
                Node.js
              </button>
              
              {/* ACP Info Popover */}
              <div className="relative ml-2">
                <button 
                  onClick={() => setShowAcpInfo(prev => !prev)}
                  className="flex items-center text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  aria-label="Agent Communication Protocol Info"
                >
                  <InformationCircleIcon className="h-5 w-5" />
                </button>
                {showAcpInfo && (
                  <div 
                    className="absolute right-0 w-72 p-3 mt-2 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-700 z-50"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <h4 className="text-sm font-medium text-gray-900 dark:text-white">Agent Communication Protocol</h4>
                      <button 
                        onClick={() => setShowAcpInfo(false)} 
                        className="text-gray-400 hover:text-gray-500"
                        aria-label="Close info"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                      These examples follow the Agent Communication Protocol (ACP), a standardized way for applications to communicate with AI agents.
                    </p>
                    <a 
                      href="https://agentcommunicationprotocol.dev/introduction/welcome" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-xs text-purple-600 dark:text-purple-400 hover:underline inline-block"
                    >
                      Learn more about ACP →
                    </a>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-whiteLime-50 dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="flex items-center justify-between bg-gray-100 dark:bg-gray-700 px-4 py-2">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center">
                    <CodeBracketIcon className="h-4 w-4 mr-2 text-gray-500" />
                    <span className="font-medium text-sm">
                      {activeTab === 'curl' ? 'cURL' : activeTab === 'python' ? 'Python' : 'Node.js'}
                    </span>
                  </div>
                </div>
                <div className="flex items-center space-x-4">
                  <div className="flex space-x-2 items-center">
                    <button
                      onClick={() => setActiveEndpoint('create')}
                      className={`px-2 py-1 text-xs font-medium rounded-md ${
                        activeEndpoint === 'create' 
                          ? 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300' 
                          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                      }`}
                    >
                      Create Run
                    </button>
                    <button
                      onClick={() => setActiveEndpoint('get')}
                      className={`px-2 py-1 text-xs font-medium rounded-md ${
                        activeEndpoint === 'get' 
                          ? 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300' 
                          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                      }`}
                    >
                      Get Run
                    </button>
                  </div>
                  <button 
                    onClick={handleCopyCodeSnippet}
                    className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                    title="Copy to clipboard"
                  >
                    {copied === 'code' ? (
                      <span className="text-green-500 text-xs">Copied!</span>
                    ) : (
                      <ClipboardDocumentIcon className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              <div className="p-4 overflow-x-auto">
                {activeEndpoint === 'create' ? (
                  <>
                    {activeTab === 'curl' && (
                      <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
{`curl -X POST ${apiBaseUrl}/runs \\
-H "Content-Type: application/json" \\
-H "Authorization: Bearer ${getApiKeyDisplay()}" \\
-d '{
  "agent_name": "${agentId}",
  "input": [
    {
      "parts": [
        {
          "content_type": "text/plain",
          "content": "Your question or input here"
        }
      ],
      "created_at": "${new Date().toISOString()}"
    }
  ]
}'`}
                      </pre>
                    )}
                    
                    {activeTab === 'python' && (
                      <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
{`import asyncio
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart

async def run_async():
    async with Client(base_url="${apiBaseUrl}", auth=("Bearer ${getApiKeyDisplay()}") as client:
        run = await client.run_async(
            agent="${agentId}",
            input=[Message(parts=[MessagePart(content="Hello")])]
        )
        print("Run ID:", run.run_id)
        
        # Later, retrieve results
        result = await client.get_run(run.run_id)
        print(result)

if __name__ == "__main__":
    asyncio.run(run_async())`}
                      </pre>
                    )}
                    
                    {activeTab === 'nodejs' && (
                      <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
{`const fetch = require('node-fetch');

const url = '${apiBaseUrl}/runs';
const options = {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ${getApiKeyDisplay()}'
  },
  body: JSON.stringify({
    agent_name: "${agentId}",
    input: [
      {
        parts: [
          {
            content_type: "text/plain",
            content: "Your question or input here"
          }
        ],
        created_at: "${new Date().toISOString()}"
      }
    ]
  })
};

fetch(url, options)
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));`}
                      </pre>
                    )}
                  </>
                ) : (
                  <>
                    {activeTab === 'curl' && (
                      <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
{`curl -X GET ${apiBaseUrl}/runs/YOUR_RUN_ID \\
-H "Authorization: Bearer ${getApiKeyDisplay()}"`}
                      </pre>
                    )}
                    
                    {activeTab === 'python' && (
                      <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
{`import asyncio
from acp_sdk.client import Client

async def run_sync():
    async with Client(base_url="${apiBaseUrl}", auth=("Bearer ${getApiKeyDisplay()}") as client:
        run = await client.run_sync(
            agent="${agentId}",
            input=[Message(parts=[MessagePart(content="Hello")])]
        )
        print(run.output)

if __name__ == "__main__":
    asyncio.run(run_sync())`}
                      </pre>
                    )}
                    
                    {activeTab === 'nodejs' && (
                      <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
{`const fetch = require('node-fetch');

const url = '${apiBaseUrl}/runs/YOUR_RUN_ID';
const options = {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer ${getApiKeyDisplay()}'
  }
};

fetch(url, options)
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));`}
                      </pre>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          {deploymentStatus === "deploying" ? (
            <div className="relative w-64 h-64 flex items-center justify-center mb-6">
              {/* Central Server Node */}
              <div className="absolute z-10 animate-pulse">
                <div className="bg-purple-100 dark:bg-purple-900 rounded-full p-3 shadow-lg">
                  <ServerIcon className="h-12 w-12 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
              
              {/* Surrounding Network Nodes */}
              {[...Array(6)].map((_, i) => {
                const delay = `${i * 0.2}s`;
                const angle = (i * 60) * (Math.PI / 180);
                const x = Math.cos(angle) * 80;
                const y = Math.sin(angle) * 80;
                
                return (
                  <div 
                    key={`node-${i}`}
                    className="absolute w-8 h-8 rounded-full bg-lime-100 dark:bg-lime-900 flex items-center justify-center"
                    style={{
                      transform: `translate(${x}px, ${y}px) scale(0)`,
                      animation: `node-appear 0.6s ${delay} forwards`,
                      boxShadow: '0 0 10px rgba(0, 0, 0, 0.1)'
                    }}
                  >
                    <div className="w-4 h-4 rounded-full bg-lime-500 dark:bg-lime-400"></div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex items-center justify-center mb-6">
              <div className={`bg-whiteLime-50 dark:bg-gray-800 rounded-full p-4 relative`}>
                <ServerIcon className={`h-10 w-10 ${getDeploymentIconColor()} transition-colors duration-1000`} />
              </div>
            </div>
          )}
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            {deploymentStatus === "deploying" ? "Deploying Agent..." : 
             deploymentStatus === "success" ? "Deployment Successful!" : 
             deploymentStatus === "error" ? "Deployment Failed" : 
             "Agent Not Deployed"}
          </h3>
          <p className="text-gray-500 dark:text-gray-400 max-w-md mb-6">
            {deploymentStatus === "deploying" ? "Setting up API access for your agent..." :
             deploymentStatus === "success" ? "Your agent is being deployed. This page will refresh shortly." :
             deploymentStatus === "error" ? localErrorMessage || "An error occurred during deployment. Please try again." :
             "This agent is not currently deployed for API access. Enable the agent and set up API access to get started."}
          </p>
          {deploymentStatus !== "deploying" && deploymentStatus !== "success" && (
            <button
              onClick={handleDeployAgent}
              type="button"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Deploy Agent
            </button>
          )}
          {deploymentStatus === "error" && (
            <p className="text-red-500 text-sm mt-2">{localErrorMessage}</p>
          )}
        </div>
      )}
    </div>
  );
}