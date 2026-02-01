import { Link } from "@remix-run/react";
import { PlusIcon } from "@heroicons/react/24/outline";

interface Organization {
  orgId: string;
  orgName: string;
  userRole: string;
}

interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

interface OrganizationLayoutProps {
  children: React.ReactNode;
  organization: Organization;
  projects: Project[];
}

/**
 * Layout component for organization pages.
 * Provides the organization header and content area.
 */
export function OrganizationLayout({ 
  children, 
  organization, 
  projects 
}: OrganizationLayoutProps) {
  return (
    <div className="container mx-auto px-4 py-8">
      <header className="mb-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {organization.orgName}
          </h1>
          <Link
            to={`/dashboard/org/${organization.orgId}/new-project`}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-lime-600 hover:bg-lime-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lime-500"
          >
            <PlusIcon className="-ml-1 mr-2 h-5 w-5" aria-hidden="true" />
            New Project
          </Link>
        </div>
        
        {projects.length > 0 && (
          <div className="flex items-center space-x-4 overflow-x-auto pb-2">
            {projects.map((project) => (
              <Link
                key={project.id}
                to={`/dashboard/org/${organization.orgId}/proj/${project.id}`}
                className="px-4 py-2 text-sm font-medium rounded-md bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 whitespace-nowrap"
              >
                {project.name}
              </Link>
            ))}
          </div>
        )}
      </header>
      
      <main>
        {children}
      </main>
    </div>
  );
}
