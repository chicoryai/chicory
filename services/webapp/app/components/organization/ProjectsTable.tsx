import React, { useState, useEffect } from "react";
import { TrashIcon, UserPlusIcon } from "@heroicons/react/24/outline";
import type { Project } from "~/services/chicory.server";
import { ConfirmationModal } from "~/components/ConfirmationModal";

interface ProjectsTableProps {
  projects: Project[];
  onDeleteProject: (projectId: string) => void;
  onManageMembers?: (projectId: string, projectName: string, currentMembers: string[]) => void;
  isDeleting?: boolean;
}

/**
 * Displays projects in a table format with delete functionality
 */
export function ProjectsTable({
  projects,
  onDeleteProject,
  onManageMembers,
  isDeleting = false
}: ProjectsTableProps) {
  const [deletingProjectId, setDeletingProjectId] = useState<string | null>(null);
  const [confirmDeleteProject, setConfirmDeleteProject] = useState<{ id: string; name: string } | null>(null);

  // Reset deletingProjectId if the project no longer exists in the list
  useEffect(() => {
    if (deletingProjectId && !projects.find(p => p.id === deletingProjectId)) {
      setDeletingProjectId(null);
    }
  }, [projects, deletingProjectId]);

  const handleDeleteClick = (projectId: string, projectName: string) => {
    setConfirmDeleteProject({ id: projectId, name: projectName });
  };

  const handleConfirmDelete = () => {
    if (confirmDeleteProject) {
      setDeletingProjectId(confirmDeleteProject.id);
      onDeleteProject(confirmDeleteProject.id);
      setConfirmDeleteProject(null);
    }
  };

  return (
    <div className="dark:bg-gray-800 shadow rounded-lg overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white">
          Projects
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="w-1/4 px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Members
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {projects.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                  No projects found
                </td>
              </tr>
            ) : (
              projects.map((project) => (
                <tr key={project.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900 dark:text-white whitespace-normal break-words">
                      {project.name}
                    </div>
                    {project.description && (
                      <div className="text-sm text-gray-500 dark:text-gray-400 whitespace-normal break-words">
                        {project.description}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white font-mono break-all">
                      {project.id}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-white">
                      {project.members?.length || 0} {project.members?.length === 1 ? 'member' : 'members'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      {onManageMembers && (
                        <button
                          onClick={() => onManageMembers(project.id, project.name, project.members || [])}
                          className="inline-flex items-center px-3 py-1 border border-transparent text-sm leading-4 font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:text-indigo-400 dark:bg-indigo-900/20 dark:hover:bg-indigo-900/30 transition-colors"
                        >
                          <UserPlusIcon className="h-4 w-4 mr-1" />
                          Members
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteClick(project.id, project.name)}
                        disabled={isDeleting || deletingProjectId === project.id}
                        className="inline-flex items-center px-3 py-1 border border-transparent text-sm leading-4 font-medium rounded-md text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed dark:text-red-400 dark:bg-red-900/20 dark:hover:bg-red-900/30"
                      >
                        {deletingProjectId === project.id ? (
                          <>
                            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-red-700 dark:text-red-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Deleting...
                          </>
                        ) : (
                          <>
                            <TrashIcon className="h-4 w-4 mr-1" />
                            Delete
                          </>
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <ConfirmationModal
        isOpen={!!confirmDeleteProject}
        onClose={() => setConfirmDeleteProject(null)}
        onConfirm={handleConfirmDelete}
        title="Delete Project"
        message={`Are you sure you want to delete the project "${confirmDeleteProject?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
      />
    </div>
  );
}
