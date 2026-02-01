/**
 * APIDeploymentCard Component
 * Manages API deployment for the agent
 */

import { useState, useCallback } from "react";
import { 
  ServerIcon, 
  ClipboardDocumentIcon,
  EyeIcon,
  EyeSlashIcon,
  CodeBracketIcon,
  InformationCircleIcon
} from "@heroicons/react/24/outline";

interface APIDeploymentCardProps {
  agentId: string;
  projectId: string;
  isDeployed: boolean;
  apiKey?: string;
  onDeploy: () => Promise<void>;
  onUndeploy: () => Promise<void>;
}

export function APIDeploymentCard({
  agentId,
  projectId,
  isDeployed,
  apiKey,
  onDeploy,
  onUndeploy,
}: APIDeploymentCardProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'curl' | 'python' | 'nodejs'>('curl');
  const [showAcpInfo, setShowAcpInfo] = useState(false);

  const API_BASE_URL = "https://app.chicory.ai/api/v1";

  const handleDeploy = useCallback(async () => {
    setIsLoading(true);
    try {
      await onDeploy();
    } finally {
      setIsLoading(false);
    }
  }, [onDeploy]);

  const handleUndeploy = useCallback(async () => {
    setIsLoading(true);
    try {
      await onUndeploy();
    } finally {
      setIsLoading(false);
    }
  }, [onUndeploy]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const getCodeExample = () => {
    const apiKeyDisplay = apiKey || "YOUR_API_KEY";
    
    if (activeTab === 'curl') {
      return `curl -X POST ${API_BASE_URL}/runs \\
-H "Content-Type: application/json" \\
-H "Authorization: Bearer ${apiKeyDisplay}" \\
-d '{
  "agent_name": "${agentId}",
  "input": [{
    "parts": [{
      "content_type": "text/plain",
      "content": "Your question here"
    }],
    "created_at": "${new Date().toISOString()}"
  }]
}'`;
    } else if (activeTab === 'python') {
      return `import asyncio
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart

async def run_async():
    async with Client(
        base_url="${API_BASE_URL}",
        auth=("Bearer", "${apiKeyDisplay}")
    ) as client:
        run = await client.run_async(
            agent="${agentId}",
            input=[Message(parts=[MessagePart(content="Hello")])]
        )
        print("Run ID:", run.run_id)

asyncio.run(run_async())`;
    } else {
      return `const fetch = require('node-fetch');

const url = '${API_BASE_URL}/runs';
const options = {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ${apiKeyDisplay}'
  },
  body: JSON.stringify({
    agent_name: "${agentId}",
    input: [{
      parts: [{
        content_type: "text/plain",
        content: "Your question here"
      }],
      created_at: "${new Date().toISOString()}"
    }]
  })
};

fetch(url, options)
  .then(res => res.json())
  .then(data => console.log(data));`;
    }
  };

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Card Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ServerIcon className="w-5 h-5 text-purple-600" />
            <h3 className="font-medium text-gray-900 dark:text-white">API Deployment</h3>
            {isDeployed && (
              <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded-full">
                Active
              </span>
            )}
          </div>
          
          {/* Action Button */}
          {isDeployed ? (
            <button
              onClick={handleUndeploy}
              disabled={isLoading}
              className="px-3 py-1.5 text-sm font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 disabled:opacity-50"
            >
              {isLoading ? "Processing..." : "Revoke Access"}
            </button>
          ) : (
            <button
              onClick={handleDeploy}
              disabled={isLoading}
              className="px-3 py-1.5 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md disabled:opacity-50 flex items-center"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Deploying...
                </>
              ) : (
                "Deploy"
              )}
            </button>
          )}
        </div>
      </div>

      {/* Card Content */}
      <div className="p-4">
        {isLoading && !isDeployed ? (
          // Deployment Animation
          <div className="flex flex-col items-center justify-center py-8">
            <div className="relative w-32 h-32 mb-4">
              {/* Central API Node */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900 rounded-full flex items-center justify-center animate-pulse">
                  <ServerIcon className="w-8 h-8 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
              
              {/* Orbiting Dots */}
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="absolute w-3 h-3 bg-purple-500 rounded-full"
                  style={{
                    top: '50%',
                    left: '50%',
                    transform: `rotate(${i * 90}deg) translateX(40px) translateY(-50%)`,
                    animation: `orbit 2s linear infinite`,
                    animationDelay: `${i * 0.25}s`
                  }}
                />
              ))}
            </div>
            <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">Setting up API endpoint...</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Generating secure access credentials</p>
            
            <style jsx>{`
              @keyframes orbit {
                from {
                  transform: rotate(0deg) translateX(40px) translateY(-50%);
                }
                to {
                  transform: rotate(360deg) translateX(40px) translateY(-50%);
                }
              }
            `}</style>
          </div>
        ) : isDeployed ? (
          <div className="space-y-4">
            {/* API Key Display */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                API Key
              </label>
              <div className="flex items-center space-x-2">
                <div className="flex-1 font-mono text-sm bg-gray-50 dark:bg-gray-800 px-3 py-2 rounded-md border border-gray-200 dark:border-gray-700">
                  {showApiKey ? apiKey : "••••••••••••••••••••••••"}
                </div>
                <button
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  title={showApiKey ? "Hide API key" : "Show API key"}
                >
                  {showApiKey ? <EyeSlashIcon className="w-4 h-4" /> : <EyeIcon className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => copyToClipboard(apiKey || "")}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  title="Copy API key"
                >
                  {copied ? (
                    <span className="text-green-500 text-xs">Copied!</span>
                  ) : (
                    <ClipboardDocumentIcon className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Code Examples */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Quick Start
                </label>
                <div className="flex items-center space-x-1">
                  {/* Language Tabs */}
                  {(['curl', 'python', 'nodejs'] as const).map((lang) => (
                    <button
                      key={lang}
                      onClick={() => setActiveTab(lang)}
                      className={`px-2 py-1 text-xs font-medium rounded-md transition-colors ${
                        activeTab === lang
                          ? 'bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300'
                          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                      }`}
                    >
                      {lang === 'nodejs' ? 'Node.js' : lang.charAt(0).toUpperCase() + lang.slice(1)}
                    </button>
                  ))}
                  
                  {/* ACP Info */}
                  <div className="relative ml-2">
                    <button
                      onClick={() => setShowAcpInfo(!showAcpInfo)}
                      className="text-gray-400 hover:text-gray-500"
                    >
                      <InformationCircleIcon className="w-4 h-4" />
                    </button>
                    {showAcpInfo && (
                      <div className="absolute right-0 top-6 w-64 p-3 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-700 z-50">
                        <h4 className="text-xs font-medium text-gray-900 dark:text-white mb-1">
                          Agent Communication Protocol
                        </h4>
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                          Standardized API for AI agent communication.
                        </p>
                        <a
                          href="https://agentcommunicationprotocol.dev"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-purple-600 dark:text-purple-400 hover:underline"
                        >
                          Learn more →
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="relative">
                <pre className="text-xs bg-gray-50 dark:bg-gray-800 p-3 rounded-md border border-gray-200 dark:border-gray-700 overflow-x-auto">
                  <code className="text-gray-800 dark:text-gray-200">{getCodeExample()}</code>
                </pre>
                <button
                  onClick={() => copyToClipboard(getCodeExample())}
                  className="absolute top-2 right-2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <ClipboardDocumentIcon className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Deploy this agent as an API to integrate it with external applications using REST endpoints.
          </p>
        )}
      </div>
    </div>
  );
}