import React from "react";
import { Link } from "@remix-run/react";
import { PlusIcon } from "@heroicons/react/24/outline";
import type { Project } from "~/services/chicory.server";

interface ProjectsListProps {
  projects: Project[];
  onNewProject?: () => void;
}

/**
 * Displays a list of projects for an organization
 * Includes a button to create a new project
 */
export function ProjectsList({ projects, onNewProject }: ProjectsListProps) {
  return (
    <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white">
          Projects
        </h2>
        <button 
          onClick={onNewProject}
          className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-purple-700 bg-purple-100 hover:bg-purple-200 dark:text-purple-200 dark:bg-purple-900 dark:hover:bg-purple-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
        >
          <PlusIcon className="h-4 w-4 mr-1" />
          New Project
        </button>
      </div>
      <div className="px-6 py-5">
        {projects.length > 0 ? (
          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {projects.map((project) => (
              <li key={project.id} className="py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                      {project.name}
                    </h3>
                    {project.description && (
                      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                        {project.description}
                      </p>
                    )}
                  </div>
                  <Link
                    to={`/proj/${project.id}`}
                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                  >
                    View
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No projects found for this organization.
          </p>
        )}
      </div>
    </div>
  );
}
