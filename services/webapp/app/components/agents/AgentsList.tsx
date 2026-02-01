import { useState } from "react";
import { Form, Link, useNavigate, useSubmit } from "@remix-run/react";
import type { Agent } from "~/services/chicory.server";
import AgentCreateModal from "./AgentCreateModal";
import EmptyState from "./EmptyState";
import { 
  SparklesIcon, 
  PlusIcon,
  ClockIcon,
  PlayIcon,
  StopIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';

interface AgentsListProps {
  agents: Agent[];
  projectId: string;
  onDeleteAgent?: (agentId: string, event: React.MouseEvent) => void;
}

export default function AgentsList({ agents, projectId, onDeleteAgent }: AgentsListProps) {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const submit = useSubmit();
  const navigate = useNavigate();

  const handleStartAgent = (agentId: string) => {
    const formData = new FormData();
    formData.append("intent", "start");
    formData.append("projectId", projectId);
    formData.append("agentId", agentId);
    submit(formData, { method: "post" });
  };

  const handleStopAgent = (agentId: string) => {
    const formData = new FormData();
    formData.append("intent", "stop");
    formData.append("projectId", projectId);
    formData.append("agentId", agentId);
    submit(formData, { method: "post" });
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <SparklesIcon className="h-5 w-5 mr-2 text-blue-500" />
            Agents
          </h2>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors flex items-center"
          >
            <PlusIcon className="h-4 w-4 mr-1" />
            New Agent
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {agents.length === 0 ? (
          <div className="p-8">
            <EmptyState 
              title="No agents found"
              description="Create your first agent to get started with AI assistance"
              actionText="Create your first agent"
              onAction={() => setShowCreateModal(true)}
            />
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {agents.map((agent) => (
              <div 
                key={agent.id} 
                className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer"
                onClick={() => navigate(`/projects/${projectId}/agents/${agent.id}`)}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white flex items-center">
                      <SparklesIcon className="h-4 w-4 mr-1.5 text-blue-500" />
                      {agent.name}
                    </h3>
                    {agent.description && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                        {agent.description}
                      </p>
                    )}
                  </div>
                  <div className="flex space-x-2">
                    {agent.status === "running" ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStopAgent(agent.id);
                        }}
                        className="p-1.5 bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-300 rounded"
                        title="Stop agent"
                      >
                        <StopIcon className="h-4 w-4" />
                      </button>
                    ) : (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStartAgent(agent.id);
                        }}
                        className="p-1.5 bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-300 rounded"
                        title="Start agent"
                      >
                        <PlayIcon className="h-4 w-4" />
                      </button>
                    )}
                    
                    {onDeleteAgent && (
                      <button
                        onClick={(e) => onDeleteAgent(agent.id, e)}
                        className="p-1.5 bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-300 rounded"
                        title="Delete agent"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
                <div className="mt-2 flex items-center text-xs text-gray-500 dark:text-gray-400">
                  <span className="flex items-center">
                    <ClockIcon className="h-4 w-4 mr-1" />
                    {new Date(agent.created_at).toLocaleDateString()}
                  </span>
                  <span className="mx-2">•</span>
                  <span className="flex items-center">
                    <DocumentTextIcon className="h-4 w-4 mr-1" />
                    {agent.task_count} tasks
                  </span>
                  <span className="mx-2">•</span>
                  <StatusBadge status={agent.status} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showCreateModal && (
        <AgentCreateModal 
          projectId={projectId}
          onClose={() => setShowCreateModal(false)}
        />
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  let bgColor = "bg-gray-100 dark:bg-gray-700";
  let textColor = "text-gray-800 dark:text-gray-200";

  if (status === "running") {
    bgColor = "bg-green-100 dark:bg-green-900";
    textColor = "text-green-800 dark:text-green-200";
  } else if (status === "error") {
    bgColor = "bg-red-100 dark:bg-red-900";
    textColor = "text-red-800 dark:text-red-200";
  } else if (status === "stopped") {
    bgColor = "bg-yellow-100 dark:bg-yellow-900";
    textColor = "text-yellow-800 dark:text-yellow-200";
  }

  return (
    <span className={`${bgColor} ${textColor} text-xs px-2 py-0.5 rounded-full`}>
      {status}
    </span>
  );
} 
