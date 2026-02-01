import { useState } from "react";
import type { Agent } from "~/services/chicory.server";
import {
  IdentificationIcon,
  DocumentTextIcon,
  ClockIcon,
  CubeIcon,
  SparklesIcon,
  DocumentIcon
} from '@heroicons/react/24/outline';

interface AgentDetailPanelProps {
  agent: Agent;
}

export default function AgentDetailPanel({ agent }: AgentDetailPanelProps) {
  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
            <IdentificationIcon className="h-5 w-5 mr-2 text-blue-500" />
            Agent Information
          </h2>
        </div>
        <div className="px-6 py-4">
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-6">
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">ID</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white font-mono">{agent.id}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Project ID</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white font-mono">{agent.project_id}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Status</dt>
              <dd className="mt-1">
                <StatusBadge status={agent.status || "unknown"} />
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Task Count</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">{agent.task_count}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Created At</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                {new Date(agent.created_at).toLocaleString()}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Last Updated</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                {new Date(agent.updated_at).toLocaleString()}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Output Format</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white font-mono">{agent.output_format}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
            <DocumentTextIcon className="h-5 w-5 mr-2 text-blue-500" />
            Instructions
          </h2>
        </div>
        <div className="px-6 py-4">
          {agent.instructions ? (
            <pre className="whitespace-pre-wrap text-sm text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-900 p-4 rounded-md">
              {agent.instructions}
            </pre>
          ) : (
            <p className="text-gray-500 dark:text-gray-400 italic">No instructions provided</p>
          )}
        </div>
      </div>

      {/* Tasks section would go here in the future */}
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
            <CubeIcon className="h-5 w-5 mr-2 text-blue-500" />
            Recent Tasks
          </h2>
        </div>
        <div className="px-6 py-4">
          <p className="text-gray-500 dark:text-gray-400 italic">No recent tasks</p>
          {/* Task list would go here when implemented */}
        </div>
      </div>
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
    <span className={`${bgColor} ${textColor} text-xs px-2 py-1 rounded-full`}>
      {status}
    </span>
  );
} 