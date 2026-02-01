import React, { useState, useEffect } from "react";
import { json, redirect } from "@remix-run/node";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { useLoaderData, useSubmit, useActionData, useNavigation, useRevalidator } from "@remix-run/react";
import { PlusIcon } from "@heroicons/react/24/outline";
import { auth } from "~/auth/auth.server";
import { fetchOrgDetails, fetchUsersInOrg } from "~/utils/propelauth.server";
import { getProjectsByOrgId, deleteProject, type Project } from "~/services/chicory.server";
import { ProjectsTable } from "~/components/organization";
import { ActionFeedback } from "~/components/ui/ActionFeedback";
import { CreateProjectModal } from "~/components/CreateProjectModal";
import { AddMembersModal } from "~/components/AddMembersModal";
import { useProject } from "~/contexts/project-context";

interface OrgDetails {
  orgId: string;
  name: string;
  createdAt?: number;
  numMembers?: number;
}

interface OrgMember {
  userId: string;
  email: string;
  firstName?: string;
  lastName?: string;
}

export interface ProfileLoaderData {
  orgName: string;
  orgId: string;
  createdAt?: string;
  memberCount?: number;
  projects: Project[];
  members: OrgMember[];
  currentUserId: string;
}

export async function loader({ params, request }: LoaderFunctionArgs) {
  const orgId = params.orgId;
  if (!orgId) {
    throw new Response("Organization ID is required", { status: 400 });
  }

  // Verify user is authenticated and has access to this org
  const user = await auth.getUser(request, {});
  if (!user || !user.orgIdToUserOrgInfo || !user.orgIdToUserOrgInfo[orgId]) {
    throw new Response("Unauthorized", { status: 403 });
  }

  try {
    // Fetch organization details from PropelAuth
    const orgDetails = await fetchOrgDetails(orgId) as OrgDetails;

    if (!orgDetails) {
      throw new Error("Failed to fetch organization details");
    }

    // Get projects for this organization
    const projects = await getProjectsByOrgId(orgId);

    // Fetch organization members
    let members: OrgMember[] = [];
    try {
      const usersResponse = await fetchUsersInOrg(orgId);
      members = usersResponse.users.map((orgUser: any) => ({
        userId: orgUser.userId,
        email: orgUser.email,
        firstName: orgUser.firstName,
        lastName: orgUser.lastName,
      }));
    } catch (error) {
      console.error("Error fetching organization members:", error);
    }

    const data: ProfileLoaderData = {
      orgName: orgDetails.name,
      orgId: orgDetails.orgId,
      createdAt: orgDetails.createdAt ? new Date(orgDetails.createdAt * 1000).toLocaleDateString() : undefined,
      memberCount: orgDetails.numMembers,
      projects,
      members,
      currentUserId: user.userId
    };

    return json(data);
  } catch (error) {
    console.error("Error fetching organization details:", error);

    // Fallback to basic info if API call fails
    // Try to get projects even if org details failed
    let projects: Project[] = [];
    try {
      projects = await getProjectsByOrgId(orgId);
    } catch (projectError) {
      console.error("Error fetching projects:", projectError);
    }

    return json({
      orgName: user.orgIdToUserOrgInfo[orgId].orgName,
      orgId,
      projects,
      members: [],
      currentUserId: user.userId
    } as ProfileLoaderData);
  }
}

export async function action({ request, params }: ActionFunctionArgs) {
  console.log('[Action] Action handler called');
  try {
    const orgId = params.orgId;
    console.log('[Action] orgId:', orgId);
    if (!orgId) {
      console.log('[Action] ERROR: Missing organization ID');
      return json({ error: "Missing organization ID" }, { status: 400 });
    }

    const user = await auth.getUser(request, {});
    console.log('[Action] User authenticated:', !!user);
    if (!user) return redirect("/api/auth/login");

    if (!user.orgIdToUserOrgInfo || !user.orgIdToUserOrgInfo[orgId]) {
      console.log('[Action] ERROR: User not a member of org');
      return json({ error: "Not a member of this organization" }, { status: 403 });
    }

    const formData = await request.formData();
    const intent = formData.get("intent") as string;
    console.log('[Action] Intent:', intent);
    console.log('[Action] FormData entries:', Array.from(formData.entries()));

    if (intent === "delete-project") {
      const projectId = formData.get("projectId") as string;
      console.log('[Action] Delete project - projectId:', projectId);

      if (!projectId) {
        console.log('[Action] ERROR: Project ID is required');
        return json({ error: "Project ID is required" }, { status: 400 });
      }

      try {
        console.log('[Action] Calling deleteProject with:', { projectId, orgId });
        // Delete the project
        const success = await deleteProject(projectId, orgId);
        console.log('[Action] deleteProject result:', success);

        if (success) {
          console.log('[Action] SUCCESS: Project deleted successfully');
          return json({
            success: true,
            message: "Project deleted successfully"
          });
        } else {
          console.log('[Action] ERROR: deleteProject returned false');
          return json({
            error: "Failed to delete project"
          }, { status: 500 });
        }
      } catch (error: any) {
        console.log('[Action] ERROR: Exception during deleteProject:', error);
        return json({
          error: error.message || "Failed to delete project"
        }, { status: 500 });
      }
    }

    console.log('[Action] ERROR: Invalid action intent:', intent);
    return json({ error: "Invalid action" }, { status: 400 });
  } catch (error: any) {
    console.log('[Action] ERROR: Top-level exception:', error);
    return json({ error: error.message || "Action failed" }, { status: 500 });
  }
}

export default function OrganizationProfile() {
  const data = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();
  const submit = useSubmit();
  const revalidator = useRevalidator();
  const { projects: contextProjects, setProjects } = useProject();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [manageMembersProject, setManageMembersProject] = useState<{
    id: string;
    name: string;
    currentMembers: string[];
  } | null>(null);

  // Explicitly type the data to avoid TypeScript errors
  const { orgName, orgId, createdAt, memberCount, projects: loaderProjects, members, currentUserId } = data as ProfileLoaderData;

  const isSubmitting = navigation.state === "submitting";

  // Sync loader projects with context when loader data changes
  useEffect(() => {
    setProjects(loaderProjects);
  }, [loaderProjects, setProjects]);

  // Use context projects for display (keeps UI in sync with both creates and deletes)
  const projects = contextProjects;

  const handleManageMembers = (projectId: string, projectName: string, currentMembers: string[]) => {
    setManageMembersProject({
      id: projectId,
      name: projectName,
      currentMembers
    });
  };

  const handleMembersUpdated = (updatedMembers: string[]) => {
    if (!manageMembersProject) return;

    // Update the project in the context
    setProjects(prevProjects =>
      prevProjects.map(p =>
        p.id === manageMembersProject.id
          ? { ...p, members: updatedMembers }
          : p
      )
    );

    // Revalidate all route loaders to fetch fresh project data from the server
    // This ensures the global projects list (from _app.tsx) reflects the updated memberships
    revalidator.revalidate();
  };

  return (
    <div className="p-6">
      {actionData && 'success' in actionData && actionData.success && (
        <ActionFeedback 
          type="success" 
          message={actionData.message as string} 
        />
      )}
      
      {actionData && 'error' in actionData && actionData.error && (
        <ActionFeedback 
          type="error" 
          message={actionData.error as string} 
        />
      )}
      
          
          {memberCount !== undefined && (
            <div>
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total Members
              </h3>
              <p className="mt-1 text-base text-gray-900 dark:text-white">
                {memberCount}
              </p>
            </div>
          )}
        
        {createdAt && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Created On
            </h3>
            <p className="mt-1 text-base text-gray-900 dark:text-white">
              {createdAt}
            </p>
          </div>
        )}

        {/* Projects Section */}
        <div className="mt-8 -mx-6">
          <div className="flex items-center justify-between mb-4 px-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Projects</h2>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors duration-150"
            >
              <PlusIcon className="h-4 w-4" />
              Create New Project
            </button>
          </div>

          <ProjectsTable
            projects={projects}
            onDeleteProject={(projectId) => {
              submit(
                {
                  intent: "delete-project",
                  projectId: projectId
                },
                { method: "post" }
              );
            }}
            onManageMembers={handleManageMembers}
            isDeleting={isSubmitting}
          />
        </div>

        <CreateProjectModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          organizationId={orgId}
          redirectOnCreate={false}
          availableMembers={members}
          currentUserId={currentUserId}
        />

        <AddMembersModal
          isOpen={!!manageMembersProject}
          onClose={() => setManageMembersProject(null)}
          projectId={manageMembersProject?.id || ''}
          projectName={manageMembersProject?.name || ''}
          currentMembers={manageMembersProject?.currentMembers || []}
          availableMembers={members}
          onSuccess={handleMembersUpdated}
        />
    </div>
  );
}
