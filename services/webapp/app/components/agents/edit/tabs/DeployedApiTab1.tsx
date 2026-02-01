import { useState, useEffect } from "react";
import { ClipboardDocumentIcon, CodeBracketIcon, ServerIcon, InformationCircleIcon } from "@heroicons/react/24/outline";
import { Form, useSubmit } from "@remix-run/react";

interface DeployedApiTabProps {
  isDeployed: boolean;
  apiEndpoint: string;
  apiKey?: string;
  deploymentStatus?: "idle" | "deploying" | "success" | "error";
  deploymentError?: string;
  onDeploy: () => void;
}

export default function DeployedApiTab({ 
  isDeployed, 
  apiEndpoint, 
  apiKey, 
  deploymentStatus = "idle", 
  deploymentError,
  onDeploy 
}: DeployedApiTabProps) {
  const [localErrorMessage, setLocalErrorMessage] = useState<string>("");
  
  // Update local error message when deployment error changes
  useEffect(() => {
    if (deploymentError) {
      setLocalErrorMessage(deploymentError);
    }
  }, [deploymentError]);
  
  const handleDeployAgent = () => {
    setLocalErrorMessage("");
    onDeploy();
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
    if (!apiKey) return "YOUR_API_KEY";
    return apiKey;
  };

  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'curl' | 'python' | 'nodejs'>('curl');
  const [showAcpInfo, setShowAcpInfo] = useState(false);
  
  return (
    <div>
      {isDeployed ? (
        <div className="space-y-6">
          {/* Pill Tabs for API Examples */}
          <div>
            <div className="flex space-x-2 mb-4 items-center">
              <button
                onClick={() => setActiveTab('curl')}
                className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${activeTab === 'curl' 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'}`}
              >
                cURL
              </button>
              <button
                onClick={() => setActiveTab('python')}
                className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${activeTab === 'python' 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'}`}
              >
                Python
              </button>
              <button
                onClick={() => setActiveTab('nodejs')}
                className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${activeTab === 'nodejs' 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'}`}
              >
                Node.js
              </button>
              
              {/* ACP Info Popover */}
              <div className="relative ml-2">
                {/* Using state instead of CSS hover for better interaction */}
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
            
            <div className="bg-gray-50 dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="flex items-center justify-between bg-gray-100 dark:bg-gray-700 px-4 py-2">
                <div className="flex items-center">
                  <CodeBracketIcon className="h-4 w-4 mr-2 text-gray-500" />
                  <span className="font-medium text-sm">
                    {activeTab === 'curl' ? 'cURL' : activeTab === 'python' ? 'Python' : 'Node.js'}
                  </span>
                </div>
                <button 
                  onClick={() => {
                    // Extract agent ID from the endpoint URL
                    const agentId = apiEndpoint.split('/').pop();
                    const runsEndpoint = `https://app.chicory.ai/api/v1/runs`;
                    const currentTime = new Date().toISOString();
                    
                    let codeSnippet = '';
                    if (activeTab === 'curl') {
                      codeSnippet = `curl -X POST ${runsEndpoint} \
-H "Content-Type: application/json" \
-H "Authorization: Bearer ${getApiKeyDisplay()}" \
-d '{
  "agent_name": "${agentId}",
  "input": [
    {
      "parts": [
        {
          "text": "Your question or input here"
        }
      ],
      "created_at": "${currentTime}"
    }
  ]
}'`;
                    } else if (activeTab === 'python') {
                      codeSnippet = `import requests
from datetime import datetime

url = "${runsEndpoint}"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer ${getApiKeyDisplay()}"
}
payload = {
    "agent_name": "${agentId}",
    "input": [
        {
            "parts": [
                {
                    "text": "Your question or input here"
                }
            ],
            "created_at": "${currentTime}"
        }
    ]
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())`;
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
            text: "Your question or input here"
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
                    navigator.clipboard.writeText(codeSnippet);
                  }}
                  className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  title="Copy to clipboard"
                >
                  <ClipboardDocumentIcon className="h-4 w-4" />
                </button>
              </div>
              <div className="p-4 overflow-x-auto">
                {activeTab === 'curl' && (
                  <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
{`curl -X POST https://app.chicory.ai/api/v1/runs \
-H "Content-Type: application/json" \
-H "Authorization: Bearer ${getApiKeyDisplay()}" \
-d '{
  "agent_name": "${apiEndpoint.split('/').pop()}",
  "input": [
    {
      "parts": [
        {
          "text": "Your question or input here"
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
{`import requests
from datetime import datetime

url = "https://app.chicory.ai/api/v1/runs"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer ${getApiKeyDisplay()}"
}
payload = {
    "agent_name": "${apiEndpoint.split('/').pop()}",
    "input": [
        {
            "parts": [
                {
                    "text": "Your question or input here"
                }
            ],
            "created_at": "${new Date().toISOString()}"
        }
    ]
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())`}
                  </pre>
                )}
                
                {activeTab === 'nodejs' && (
                  <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
{`const fetch = require('node-fetch');

const url = 'https://app.chicory.ai/api/v1/runs';
const options = {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ${getApiKeyDisplay()}'
  },
  body: JSON.stringify({
    agent_name: "${apiEndpoint.split('/').pop()}",
    input: [
      {
        parts: [
          {
            text: "Your question or input here"
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
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className={`bg-gray-100 dark:bg-gray-800 rounded-full p-4 mb-4 relative ${deploymentStatus === "deploying" ? "animate-pulse" : ""}`}>
            <ServerIcon className={`h-10 w-10 ${getDeploymentIconColor()} transition-colors duration-1000`} />
            {deploymentStatus === "deploying" && (
              <div className="absolute inset-0 rounded-full border-4 border-t-yellow-400 border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
            )}
          </div>
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
