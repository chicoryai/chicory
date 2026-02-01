import { useState, useEffect } from "react";
import { ClipboardDocumentIcon, CodeBracketIcon, ServerIcon, InformationCircleIcon, ArrowPathIcon, PowerIcon } from "@heroicons/react/24/outline";
import { Form, useSubmit } from "@remix-run/react";
import GatewaySelector from "~/components/agents/GatewaySelector";
import type { MCPGateway } from "~/services/chicory.server";

// API endpoints configuration
const API_BASE_URL = "https://app.chicory.ai/api/v1";

interface DeployedApiTabProps {
  isDeployed: boolean;
  apiEndpoint: string;
  apiKey?: string;
  deploymentStatus?: "idle" | "deploying" | "success" | "error";
  deploymentError?: string;
  onDeploy: (deploymentType: 'api' | 'mcp-tool', gatewayId?: string) => void;
  agentStatus?: string;
  isUpdatingStatus?: boolean;
  projectId?: string;
  gateways?: MCPGateway[];
}

export default function DeployedApiTab({ 
  isDeployed, 
  apiEndpoint, 
  apiKey, 
  deploymentStatus = "idle", 
  deploymentError,
  onDeploy,
  agentStatus = "disabled",
  isUpdatingStatus = false,
  projectId = "",
  gateways = []
}: DeployedApiTabProps) {
  const [localErrorMessage, setLocalErrorMessage] = useState<string>("");
  const [deploymentType, setDeploymentType] = useState<'api' | 'mcp-tool'>('api');
  const [selectedGatewayId, setSelectedGatewayId] = useState<string>("");
  const submit = useSubmit();
  
  // Update local error message when deployment error changes
  useEffect(() => {
    if (deploymentError) {
      setLocalErrorMessage(deploymentError);
    }
  }, [deploymentError]);
  
  const handleDeployAgent = () => {
    setLocalErrorMessage("");
    if (deploymentType === 'mcp-tool' && !selectedGatewayId) {
      setLocalErrorMessage("Please select a gateway to deploy to");
      return;
    }
    onDeploy(deploymentType, selectedGatewayId);
  };
  
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

  const [copied, setCopied] = useState(false);
  const [activeEndpoint, setActiveEndpoint] = useState<'create' | 'get'>('create');
  const [showAcpInfo, setShowAcpInfo] = useState(false);
  
  // Function to generate and copy code snippet for cURL only
  const handleCopyCodeSnippet = () => {
    // Extract agent ID from the endpoint URL
    const agentId = apiEndpoint.split('/').pop() || '';
    const runsEndpoint = `${API_BASE_URL}/projects/${projectId}/runs`;
    const currentTime = new Date().toISOString();

    let codeSnippet = '';

    if (activeEndpoint === 'create') {
      codeSnippet = `curl -X POST ${runsEndpoint} \
-H "Content-Type: application/json" \
-H "Authorization: Bearer ${getApiKeyDisplay()}" \
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
    } else { // 'get' endpoint
      const runIdPlaceholder = 'YOUR_RUN_ID';
      codeSnippet = `curl -X GET ${runsEndpoint}/${runIdPlaceholder} \
-H "Authorization: Bearer ${getApiKeyDisplay()}"`;
    }

    navigator.clipboard.writeText(codeSnippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <div>
      {isDeployed ? (
        <div className="space-y-6">
          {/* Removed Endpoint Toggle from here */}
          
          {/* Code Snippet Section */}
          <div>
            <div className="flex space-x-2 mb-4 items-center">
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
            
            <div className="bg-whiteLime-50 dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="flex items-center justify-between bg-gray-100 dark:bg-gray-700 px-4 py-2">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center">
                    <CodeBracketIcon className="h-4 w-4 mr-2 text-gray-500" />
                    <span className="font-medium text-sm">cURL</span>
                  </div>
                </div>
                <div className="flex items-center space-x-4">
                  <div className="flex space-x-2 items-center">
                      <button
                        onClick={() => setActiveEndpoint('create')}
                        className={`px-2 py-1 text-xs font-medium rounded-md ${activeEndpoint === 'create' 
                          ? 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300' 
                          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}
                      >
                        Create Run
                      </button>
                      <button
                        onClick={() => setActiveEndpoint('get')}
                        className={`px-2 py-1 text-xs font-medium rounded-md ${activeEndpoint === 'get' 
                          ? 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300' 
                          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}`}
                      >
                        Get Run
                      </button>
                    </div>
                  <button 
                    onClick={handleCopyCodeSnippet}
                    className="p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                    title="Copy to clipboard"
                  >
                    {copied ? (
                      <span className="text-green-500 text-xs">Copied!</span>
                    ) : (
                      <ClipboardDocumentIcon className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
              <div className="p-4 overflow-x-auto">
                {activeEndpoint === 'create' ? (
                  <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
{`curl -X POST https://app.chicory.ai/api/v1/projects/${projectId}/runs \
-H "Content-Type: application/json" \
-H "Authorization: Bearer ${getApiKeyDisplay()}" \
-d '{
  "agent_name": "${apiEndpoint.split('/').pop()}",
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
                ) : (
                  <pre className="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
{`curl -X GET https://app.chicory.ai/api/v1/projects/${projectId}/runs/YOUR_RUN_ID \
-H "Authorization: Bearer ${getApiKeyDisplay()}"`}
                  </pre>
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
              <div className="absolute z-10 animate-agent-pulse">
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
            {deploymentStatus === "deploying" ? "Setting up access for your agent..." :
             deploymentStatus === "success" ? "Your agent is being deployed. This page will refresh shortly." :
             deploymentStatus === "error" ? localErrorMessage || "An error occurred during deployment. Please try again." :
             "Choose how you want to deploy this agent."}
          </p>
          
          {/* Deployment Type Selection */}
          {deploymentStatus !== "deploying" && deploymentStatus !== "success" && !isDeployed && (
            <div className="mb-6 max-w-md">
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Deployment Type
                  </label>
                  <div className="space-y-2">
                    <label className="flex items-center p-3 border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                      <input
                        type="radio"
                        name="deploymentType"
                        value="api"
                        checked={deploymentType === 'api'}
                        onChange={(e) => setDeploymentType('api')}
                        className="mr-3 text-purple-600 focus:ring-purple-500"
                      />
                      <div>
                        <div className="font-medium text-gray-900 dark:text-white">Deploy as API</div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          Generate an API key for direct API access
                        </div>
                      </div>
                    </label>
                    <label className="flex items-center p-3 border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                      <input
                        type="radio"
                        name="deploymentType"
                        value="mcp-tool"
                        checked={deploymentType === 'mcp-tool'}
                        onChange={(e) => setDeploymentType('mcp-tool')}
                        className="mr-3 text-purple-600 focus:ring-purple-500"
                      />
                      <div>
                        <div className="font-medium text-gray-900 dark:text-white">Deploy as MCP Tool</div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          Add this agent as a tool to an MCP gateway
                        </div>
                      </div>
                    </label>
                  </div>
                </div>
                
                {/* Gateway Selector for MCP Tool deployment */}
                {deploymentType === 'mcp-tool' && (
                  <div className="mt-4">
                    <GatewaySelector
                      projectId={projectId}
                      selectedGatewayId={selectedGatewayId}
                      onSelectGateway={setSelectedGatewayId}
                      gateways={gateways}
                      disabled={deploymentStatus === "deploying"}
                    />
                  </div>
                )}
              </div>
            </div>
          )}
          
          {deploymentStatus !== "deploying" && deploymentStatus !== "success" && (
            <button
              onClick={handleDeployAgent}
              type="button"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={deploymentType === 'mcp-tool' && !selectedGatewayId}
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
