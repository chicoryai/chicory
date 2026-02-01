import { Link, useLocation } from "@remix-run/react";
import { useSidebar } from "~/hooks/useSidebar";
import {
  ChatBubbleLeftRightIcon,
  MagnifyingGlassIcon,
  Cog6ToothIcon,
  PuzzlePieceIcon,
  CodeBracketIcon
} from "@heroicons/react/24/outline";

interface Organization {
  orgId: string;
  orgName: string;
  userRole: string;
}

interface Project {
  id: string;
  name: string;
  description?: string;
  organization_id: string;
}

interface ProjectLayoutProps {
  children: React.ReactNode;
  project: Project;
  organization: Organization;
}

/**
 * Layout component for project pages.
 * Provides the project sidebar and content area.
 */
export function ProjectLayout({ 
  children, 
  project, 
  organization 
}: ProjectLayoutProps) {
  const location = useLocation();
  const { isOpen, toggleSidebar } = useSidebar({
    defaultOpen: true,
    closeBreakpoint: 768
  });
  
  // Define navigation links
  const navLinks = [
    {
      to: `/dashboard/org/${organization.orgId}/proj/${project.id}`,
      label: "Overview",
      icon: <MagnifyingGlassIcon className="h-5 w-5" />
    },
    {
      to: `/dashboard/org/${organization.orgId}/proj/${project.id}/exploration`,
      label: "Exploration",
      icon: <MagnifyingGlassIcon className="h-5 w-5" />
    },
    {
      to: `/dashboard/org/${organization.orgId}/proj/${project.id}/chat`,
      label: "Chat",
      icon: <ChatBubbleLeftRightIcon className="h-5 w-5" />
    },
    {
      to: `/dashboard/org/${organization.orgId}/proj/${project.id}/understanding`,
      label: "Understanding",
      icon: <CodeBracketIcon className="h-5 w-5" />
    },
    {
      to: `/dashboard/org/${organization.orgId}/proj/${project.id}/transformation`,
      label: "Transformation",
      icon: <PuzzlePieceIcon className="h-5 w-5" />
    },
    {
      to: `/dashboard/org/${organization.orgId}/proj/${project.id}/integrations`,
      label: "Integrations",
      icon: <Cog6ToothIcon className="h-5 w-5" />
    }
  ];
  
  return (
    <div className="flex h-screen overflow-hidden dark:bg-gray-900">
      {/* Project sidebar */}
      <aside
        className={`${
          isOpen ? 'w-64' : 'w-0 -ml-64'
        } flex flex-col fixed inset-y-0 z-10 bg-white dark:bg-gray-900 shadow-md transition-all duration-300 md:relative md:translate-x-0`}
      >
        {/* Project header */}
        <div className="px-4 py-4 border-b border-gray-200 dark:border-gray-700">
          <Link 
            to={`/dashboard/org/${organization.orgId}`}
            className="flex items-center text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 mb-2"
          >
            <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to {organization.orgName}
          </Link>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white truncate">
            {project.name}
          </h1>
          {project.description && (
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {project.description}
            </p>
          )}
        </div>
        
        {/* Navigation links */}
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-2">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.to;
              return (
                <li key={link.to}>
                  <Link
                    to={link.to}
                    className={`flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                      isActive
                        ? 'bg-gray-200 text-gray-900 dark:bg-gray-700 dark:text-white'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
                    }`}
                  >
                    <span className="mr-3 text-gray-500 dark:text-gray-400">
                      {link.icon}
                    </span>
                    {link.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>
      
      {/* Mobile sidebar toggle */}
      <button
        type="button"
        className="md:hidden fixed top-4 left-4 z-20 p-2 rounded-md bg-white dark:bg-gray-800 shadow-md"
        onClick={toggleSidebar}
      >
        {isOpen ? (
          <svg className="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        )}
      </button>
      
      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="container mx-auto px-4 py-6">
          {children}
        </div>
      </main>
    </div>
  );
}
