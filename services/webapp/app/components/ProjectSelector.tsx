import { useState, useRef, useEffect, useMemo } from 'react';
import { Link, useNavigate, useLocation, useParams } from '@remix-run/react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';

import { useProject } from '~/contexts/project-context';
import type { Project } from '~/services/chicory.server';

interface ProjectSelectorProps {
  organizationId: string;
  isOpen: boolean;
  userId?: string;
  className?: string;
}

export function ProjectSelector({
  organizationId,
  isOpen: sidebarIsOpen,
  userId,
  className = ""
}: ProjectSelectorProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const hasHandledNoProjects = useRef(false);

  const { activeProject, projects, setActiveProject } = useProject();
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();

  // Filter projects to only show ones where the user is a member
  const userProjects = useMemo(
    () => userId
      ? projects.filter(project => project.members?.includes(userId))
      : projects,
    [userId, projects]
  );

  // Automatically update activeProject if it's not in the user's accessible projects
  useEffect(() => {
    if (userId && userProjects.length > 0 && activeProject) {
      // Check if current activeProject is still accessible
      const isActiveProjectAccessible = userProjects.some(p => p.id === activeProject.id);

      if (!isActiveProjectAccessible) {
        // Active project is not accessible anymore, switch to first available project
        console.log(`Active project "${activeProject.name}" is not accessible, switching to "${userProjects[0].name}"`);
        setActiveProject(userProjects[0]);
      }
    }
  }, [userId, userProjects, activeProject, setActiveProject]);

  // Reset the flag when user gets projects again
  useEffect(() => {
    if (userProjects.length > 0) {
      hasHandledNoProjects.current = false;
    }
  }, [userProjects.length]);

  // If user has no projects, clear active project and redirect to workzone
  useEffect(() => {
    if (userId && userProjects.length === 0 && activeProject && !hasHandledNoProjects.current) {
      hasHandledNoProjects.current = true;
      setActiveProject(null);
      // Only redirect if currently on a project page
      if (location.pathname.startsWith('/projects/')) {
        navigate('/workzone');
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, userProjects.length, activeProject?.id, location.pathname]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Handle project selection - only allow if user has access to projects
  const currentProjectId = userProjects.length > 0
    ? (params.projectId ?? activeProject?.id ?? userProjects[0]?.id ?? null)
    : null;

  const selectProject = (project: Project) => {
    setActiveProject(project);
    setIsDropdownOpen(false);

    const nextPath = `/projects/${project.id}/agents${location.search}${location.hash}`;
    navigate(nextPath);
  };
  
  return (
    <>
      <div className={`${className}`}>
        <div className="px-4 py-3">
          {sidebarIsOpen ? (
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => userProjects.length > 0 && setIsDropdownOpen(!isDropdownOpen)}
                disabled={userProjects.length === 0}
                className={`flex items-center justify-between w-full px-2 py-1.5 text-left text-xs bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 transition-colors duration-150 rounded-md ${
                  userProjects.length > 0
                    ? 'hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer'
                    : 'opacity-60 cursor-not-allowed'
                }`}
              >
                <div className="flex-1 min-w-0">
                  <p className="font-normal truncate text-gray-900 dark:text-white">
                    {userProjects.length === 0
                      ? "No Projects Available"
                      : (activeProject?.name || "Select Project")}
                  </p>
                </div>
                {userProjects.length > 0 && (
                  <ChevronDownIcon
                    className={`h-4 w-4 text-gray-400 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`}
                  />
                )}
              </button>
                
                {isDropdownOpen && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg z-50 max-h-60 overflow-y-auto">
                    {userProjects.length > 0 ? (
                      <div className="py-1">
                        {userProjects.map((project) => (
                          <button
                            key={project.id}
                            onClick={() => selectProject(project)}
                            className={`block w-full text-left px-3 py-1.5 text-xs ${
                              project.id === activeProject?.id
                                ? 'bg-indigo-50 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300'
                                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                            }`}
                          >
                            <div className="font-normal truncate">{project.name}</div>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="py-3 px-4">
                        <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
                          You're not a member of any projects
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          Contact your organization admin to be added to a project, or use{' '}
                          <Link
                            to="/workzone"
                            className="text-indigo-600 dark:text-indigo-400 hover:underline"
                            onClick={() => setIsDropdownOpen(false)}
                          >
                            Workzone
                          </Link>
                        </p>
                      </div>
                    )}
                  </div>
                )}
            </div>
          ) : null}
        </div>
      </div>
    </>
  );
}
