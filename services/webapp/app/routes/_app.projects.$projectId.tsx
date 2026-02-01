import { json, redirect } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import { Link, Outlet, useLoaderData } from "@remix-run/react";
import { useEffect } from "react";

import { getUserOrgDetails } from "~/auth/auth.server";
import { getProjectsByOrgId, getProjectById, type Project } from "~/services/chicory.server";
import { useProject } from "~/contexts/project-context";

interface LoaderData {
  project: Project;
  projects: Project[];
  orgId: string;
  isMember: boolean;
}

export async function loader({ request, params }: LoaderFunctionArgs) {
  const projectId = params.projectId;

  if (!projectId) {
    throw new Response("Project ID is required", { status: 400 });
  }

  // Get authenticated user and org details (getUserOrgDetails calls auth.getUser internally)
  const userDetails = await getUserOrgDetails(request);
  if (userDetails instanceof Response) {
    return userDetails;
  }

  // Extract userId from userDetails (which includes the user object)
  const userId = userDetails.userId;
  if (!userId) {
    return redirect("/api/auth/login");
  }

  const orgId = "orgId" in userDetails ? (userDetails as any).orgId : undefined;
  if (!orgId) {
    return redirect("/new");
  }

  const projects = await getProjectsByOrgId(orgId);
  const projectFromList = projects.find(project => project.id === projectId);

  // Ensure the requested project exists and belongs to the org
  const project = projectFromList ?? (await getProjectById(projectId));

  if (!project || project.organization_id !== orgId) {
    throw new Response("Project not found", { status: 404 });
  }

  // Check if user is a member of this project
  // project.members is typed as string[] (non-optional), so no optional chaining needed
  const isMember = project.members.includes(userId);

  return json<LoaderData>({ project, projects, orgId, isMember });
}

function NotProjectMember({ projectName }: { projectName: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-white via-purple-50/20 to-lime-50/20 dark:from-gray-900 dark:via-purple-950/20 dark:to-lime-950/10">
      <div className="text-center max-w-md px-6">
        <div className="mb-6">
          <div className="mx-auto w-16 h-16 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-purple-600 dark:text-purple-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-3 font-['Outfit']">
          Not a Project Member
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6 font-['Plus_Jakarta_Sans']">
          You don't have access to <span className="font-semibold">{projectName}</span>.
          Please contact the project owner to request access.
        </p>
        <Link
          to="/workzone"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-purple-600 text-white font-medium hover:bg-purple-700 transition-colors"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 7l5 5m0 0l-5 5m5-5H6"
            />
          </svg>
          Go to Workzone
        </Link>
      </div>
    </div>
  );
}

export default function ProjectLayout() {
  const { project, projects, isMember } = useLoaderData<typeof loader>();
  const { setActiveProject, setProjects } = useProject();

  useEffect(() => {
    setProjects(projects);
    setActiveProject(project);
  }, [project, projects, setActiveProject, setProjects]);

  if (!isMember) {
    return <NotProjectMember projectName={project.name} />;
  }

  return <Outlet context={{ project }} />;
}
