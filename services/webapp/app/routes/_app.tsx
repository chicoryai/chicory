import { Outlet, redirect, useLoaderData, useLocation } from "@remix-run/react";
import { ThemeProvider } from "~/contexts/theme-context";
import { ProjectProvider } from "~/contexts/project-context";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { getTheme } from "~/utils/theme.server";
import { auth, getUserOrgDetails } from "~/auth/auth.server";
import { useSidebar } from "~/hooks/useSidebar";
import { usePageVisibility } from "~/hooks/usePageVisibility";
import { Sidebar } from "~/components/layouts/Sidebar";
import { getProjectsByOrgId, createProject } from "~/services/chicory.server";
import { InlineNetworkError } from "~/components/NetworkError";

export async function loader({ request }: LoaderFunctionArgs) {
  try {
    // Try to get the authenticated user
    const user = await auth.getUser(request, {});

    // Get the theme
    const theme = await getTheme(request);

    // If user is not authenticated, redirect to login
    if (!user) {
      return redirect("/api/auth/login");
    } else {
      if (!user.orgIdToUserOrgInfo || Object.keys(user.orgIdToUserOrgInfo).length === 0) {
        // User has no organizations, redirect to create one
        return redirect("/api/auth/login"); // Adjust this as needed
      }

      // Get the first organization ID (we'll use this to check for projects)
      const orgId = Object.keys(user.orgIdToUserOrgInfo)[0];

      // Get all projects for this organization with improved error handling
      let projects: Awaited<ReturnType<typeof getProjectsByOrgId>> = [];
      try {
        projects = await getProjectsByOrgId(orgId);
      } catch (error) {
        console.error("Failed to fetch projects:", error);
        // Return partial data instead of throwing - let the UI handle the error gracefully
        // The retry logic in fetchWithRetry will have already attempted to recover
        return json({
          theme,
          user,
          projects: [],
          activeProject: null,
          orgId,
          error: "Failed to load projects. Please refresh the page or check your connection."
        });
      }

      // If no projects exist, create a default project
      if (!projects || projects.length === 0) {
        console.log(`No projects found for organization ${orgId}. Creating a default project.`);
        try {
          const defaultProject = await createProject({
            name: "Default Project",
            organization_id: orgId,
            description: "Automatically created default project",
            members: [user.userId] // Add current user as first member
          });
          projects = [defaultProject];
          console.log("Default project created successfully");
        } catch (error) {
          console.error("Error creating default project:", error);
          projects = [];
        }
      }

      // Get user org details to access project ID
      const url = new URL(request.url);
      const match = url.pathname.match(/\/projects\/([^/]+)/);
      const requestedProjectId = match ? decodeURIComponent(match[1]) : null;

      const userOrgDetails = await getUserOrgDetails(request);
      const orgScopedProjects = projects;

      let activeProject = (requestedProjectId && orgScopedProjects.find(project => project.id === requestedProjectId)) || null;

      if (!activeProject && userOrgDetails && typeof userOrgDetails === 'object' && 'project' in userOrgDetails) {
        const userProject = (userOrgDetails as any).project;
        if (userProject && orgScopedProjects.some(project => project.id === userProject.id)) {
          activeProject = userProject;
        }
      }

      if (!activeProject && orgScopedProjects.length > 0) {
        activeProject = orgScopedProjects[0];
      }

      // Return user data, theme, and projects
      return json({ theme, user, projects, activeProject, orgId });
    }
  } catch (error) {
    // If there's an authentication error (like invalid/expired token), redirect to login
    console.error("Authentication error:", error);

    // Check if it's specifically an auth error vs network error
    if (error instanceof Error &&
      (error.message.includes('authentication') ||
        error.message.includes('unauthorized') ||
        error.message.includes('token'))) {
      return redirect("/api/auth/login");
    }

    // For other errors (network, etc.), throw to be handled by ErrorBoundary
    throw error;
  }
}

export async function action({ request }: ActionFunctionArgs) {
  const user = await auth.getUser(request, {});
  if (!user) {
    return redirect("/api/auth/login");
  }

  const formData = await request.formData();
  const actionType = formData.get("action");

  if (actionType === "create-project") {
    const name = formData.get("name") as string;
    const description = formData.get("description") as string;
    const organizationId = formData.get("organizationId") as string;

    if (!name || !organizationId) {
      return json({ error: "Name and organization ID are required" }, { status: 400 });
    }

    try {
      const project = await createProject({
        name,
        organization_id: organizationId,
        description: description || undefined,
        members: [user.userId] // Add current user as first member
      });
      return json({ success: true, project });
    } catch (error) {
      console.error("Error creating project:", error);
      return json({ error: "Failed to create project" }, { status: 500 });
    }
  }

  return json({ error: "Invalid action" }, { status: 400 });
}

/**
 * Main app layout that includes the sidebar and wraps all authenticated routes
 */
export default function AppLayout() {
  const data = useLoaderData<typeof loader>();
  const theme = data?.theme || null;
  const user = data?.user;
  const projects = data?.projects || [];
  const activeProject = data?.activeProject || null;
  const orgId = data?.orgId;
  const error = (data as any)?.error;
  const location = useLocation();
  const projectMatch = location.pathname.match(/\/projects\/([^/]+)/);
  const requestedProjectId = projectMatch ? decodeURIComponent(projectMatch[1]) : null;
  const providerInitialProject = requestedProjectId
    ? projects.find(project => project.id === requestedProjectId) || activeProject
    : activeProject;
  const { isOpen, toggleSidebar } = useSidebar({
    defaultOpen: false,
    closeBreakpoint: 768,
    openBreakpoint: Number.POSITIVE_INFINITY
  });

  // Revalidate data when tab becomes visible after being idle
  usePageVisibility({
    revalidateOnVisible: true,
    minIdleTime: 60000 // Revalidate if idle for more than 1 minute
  });

  return (
    <ThemeProvider specifiedTheme={theme}>
      <ProjectProvider
        initialProjects={projects}
        initialProject={providerInitialProject}
        authoritativeProjectId={requestedProjectId}
      >
        <div className="flex h-screen overflow-hidden bg-transparent dark:bg-gray-900">
          {/* Sidebar Component */}
          <Sidebar
            isOpen={isOpen}
            user={user}
            toggleSidebar={toggleSidebar}
            organizationId={orgId}
          />

          {/* Main content */}
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            {/* Show error banner if projects failed to load */}
            {error && (
              <div className="flex-shrink-0 p-4">
                <InlineNetworkError message={error} />
              </div>
            )}

            {/* Main content area */}
            <main className="flex-1 min-h-0 overflow-auto">
              <Outlet />
            </main>
          </div>
        </div>
      </ProjectProvider>
    </ThemeProvider>
  );
}
