import type { Project } from "~/services/chicory.server";
import { Link } from "@remix-run/react";
import { SparklesIcon } from '@heroicons/react/24/outline';

interface AgentLayoutProps {
  project: Project;
  children: React.ReactNode;
}

export default function AgentLayout({ project, children }: AgentLayoutProps) {
  return (
    <div className="h-full flex flex-col">
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 py-4 px-6">
        <div className="flex justify-between items-center">
          <div>
            <Link 
              to={`/projects/${project.id}`}
              className="text-blue-600 dark:text-blue-400 hover:underline text-sm flex items-center"
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to project
            </Link>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mt-1 flex items-center">
              <SparklesIcon className="h-6 w-6 mr-2 text-blue-500" />
              {project.name} - Agents
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-sm">{project.description}</p>
          </div>
        </div>
      </div>
      
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  );
} 