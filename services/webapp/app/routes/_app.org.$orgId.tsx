import React, { useState, useEffect } from "react";
import { json, redirect } from "@remix-run/node";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { useLoaderData, useSubmit, useActionData, useNavigation, Outlet, useLocation, useNavigate } from "@remix-run/react";
import { auth } from "~/auth/auth.server";
import { getProjectsByOrgId, type Project } from "~/services/chicory.server";
import { inviteUserToOrg, fetchUsersInOrg, fetchOrgDetails } from "~/utils/propelauth.server";
import {
  OrganizationHeader,
  OrganizationDetails,
  ProjectsList,
  OrganizationSettings
} from "~/components/organization";
import { ActionFeedback } from "~/components/ui/ActionFeedback";

interface Organization {
  orgId: string;
  orgName: string;
  userRole: string;
}

interface User {
  userId: string;
  email?: string;
  firstName?: string;
  lastName?: string;
  activeOrgId?: string;
  orgIdToUserOrgInfo?: Record<string, {
    orgId: string;
    orgName: string;
    userRole: string;
    userAssignedRole?: string;
  }>;
}

interface LoaderData {
  user: User;
  organization: Organization;
  projects: Project[];
  members: Array<{
    userId: string;
    email: string;
    firstName?: string;
    lastName?: string;
    role: string;
  }>;
  isActive: boolean;
}

export async function loader({ request, params }: LoaderFunctionArgs) {
  try {
    const orgId = params.orgId;
    if (!orgId) {
      return redirect("/projects");
    }
    
    // Get the user and verify they're authenticated
    const user = await auth.getUser(request, {});

    if (!user) {
      return redirect("/api/auth/login");
    }

    // RBAC: Check if user has permission to view organization page
    // Permissions are managed in PropelAuth dashboard
    // Get permissions from org-specific data
    const orgPermissions = user.orgIdToUserOrgInfo?.[orgId]?.userPermissions || [];
    if (!orgPermissions.includes('canManageOrg')) {
      throw new Response("You don't have permission to view organization settings", { status: 403 });
    }

    // Check if user is a member of this organization
    if (!user.orgIdToUserOrgInfo || !user.orgIdToUserOrgInfo[orgId]) {
      return redirect("/projects");
    }
    
    // Get organization details from user info
    const orgInfo = user.orgIdToUserOrgInfo[orgId] as any;
    const organization = {
      orgId,
      orgName: orgInfo.orgName,
      userRole: orgInfo.userAssignedRole || orgInfo.userRole || 'Member'
    };
    
    // Get projects for this organization
    const projects = await getProjectsByOrgId(orgId);
    
    // Fetch organization members using PropelAuth API
    let members: Array<{
      userId: string;
      email: string;
      firstName?: string;
      lastName?: string;
      role: string;
    }> = [];
    try {
      const usersResponse = await fetchUsersInOrg(orgId);
      members = usersResponse.users.map((orgUser: any) => ({
        userId: orgUser.userId as string,
        email: orgUser.email as string,
        firstName: orgUser.firstName as string | undefined,
        lastName: orgUser.lastName as string | undefined,
        role: (orgUser.orgIdToOrgInfo?.[orgId]?.userAssignedRole || orgUser.orgIdToOrgInfo?.[orgId]?.userRole || 'Member') as string
      }));
    } catch (error) {
      console.error("Error fetching organization members:", error);
      // Fallback to just the current user if we can't fetch members
      members = [
        {
          userId: user.userId as string,
          email: (user.email || "") as string,
          firstName: user.firstName as string | undefined,
          lastName: user.lastName as string | undefined,
          role: ((user.orgIdToUserOrgInfo[orgId] as any).userAssignedRole || (user.orgIdToUserOrgInfo[orgId] as any).userRole || 'Member') as string
        }
      ];
    }
    
    // Check if this is the active organization
    const isActive = user.activeOrgId === orgId;
    
    return json({ 
      user,
      organization,
      projects,
      members,
      isActive
    });
    
  } catch (error) {
    console.error("Error loading organization:", error);
    return redirect("/projects");
  }
}

export async function action({ request, params }: ActionFunctionArgs) {
  try {
    const orgId = params.orgId;
    if (!orgId) return json({ error: "Missing organization ID" }, { status: 400 });

    const user = await auth.getUser(request, {});
    if (!user) return redirect("/api/auth/login");

    if (!user.orgIdToUserOrgInfo || !user.orgIdToUserOrgInfo[orgId]) {
      return json({ error: "Not a member of this organization" }, { status: 403 });
    }

    const formData = await request.formData();
    const intent = formData.get("intent") as string;

    if (intent === "invite-member") {
      const email = formData.get("email") as string;
      const role = formData.get("role") as string;

      if (!email) {
        return json({ error: "Email is required" }, { status: 400 });
      }

      if (!role) {
        return json({ error: "Role is required" }, { status: 400 });
      }

      try {
        // Use PropelAuth's API to invite a user to the organization
        await inviteUserToOrg(email, orgId, role);

        return json({
          success: true,
          message: `Invitation sent to ${email}`
        });
      } catch (error: any) {
        return json({
          error: error.message || "Failed to send invitation"
        }, { status: 500 });
      }
    }

    return json({ error: "Invalid action" }, { status: 400 });
  } catch (error: any) {
    return json({ error: error.message || "Action failed" }, { status: 500 });
  }
}

export default function OrganizationDashboard() {
  const { 
    user, 
    organization, 
    projects, 
    members, 
    isActive 
  } = useLoaderData<typeof loader>();
  
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();
  const submit = useSubmit();
  const location = useLocation();
  const navigate = useNavigate();
  
  const isSubmitting = navigation.state === "submitting";
  
  // Determine which settings tab is active based on the URL
  const currentPath = location.pathname;
  const activeSettingId = currentPath.endsWith('/profile') ? 'profile' : 
                          currentPath.endsWith('/members') ? 'members' : 
                          currentPath.endsWith('/billing') ? 'billing' : 'profile';
  
  // Navigate to profile by default if we're at the root org path
  useEffect(() => {
    if (currentPath.endsWith(`/org/${organization.orgId}`)) {
      navigate(`profile`, { replace: true });
    }
  }, [currentPath, organization.orgId, navigate]);
  
  // State for the invite member modal
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("Member");

  // Handle member invitation
  const handleInviteMember = (e: React.FormEvent) => {
    e.preventDefault();
    
    submit(
      { 
        intent: "invite-member",
        email: inviteEmail,
        role: inviteRole
      },
      { method: "post" }
    );
    
    // Close the modal after submission
    setShowInviteModal(false);
    setInviteEmail("");
    setInviteRole("Member");
  };

  // Settings links for the organization
  const settingsLinks = [
    { id: "profile", label: "Organization Profile", href: `profile`, isActive: activeSettingId === 'profile' },
    { id: "members", label: "Members & Permissions", href: `members`, isActive: activeSettingId === 'members' },
    // { id: "billing", label: "Billing & Plans", href: `billing`, isActive: activeSettingId === 'billing' }
  ];
  
  return (
    <div className="min-h-screen dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <OrganizationHeader
          orgName={organization.orgName}
          isActive={isActive}
        />

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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Organization Info and Settings */}
          <div className="lg:col-span-2">
            <OrganizationDetails
              orgId={organization.orgId}
              orgName={organization.orgName}
              userRole={organization.userRole}
              projectCount={projects.length}
            />
          </div>

          {/* Settings Only */}
          <div>
            <OrganizationSettings
              links={settingsLinks}
              onSettingClick={(id) => {
                // Navigate to the setting route
                navigate(settingsLinks.find(link => link.id === id)?.href || 'profile');
              }}
            />
          </div>
        </div>

        {/* Outlet for Settings Views - Full Width */}
        <div className="mt-6">
          <Outlet />
        </div>
      </div>
      
      {/* Invite Member Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">Invite Team Member</h3>
            </div>
            <form onSubmit={handleInviteMember}>
              <div className="px-6 py-4">
                <div className="mb-4">
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    id="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 dark:bg-gray-700 dark:text-white"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="role" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Role
                  </label>
                  <select
                    id="role"
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="Owner">Owner</option>
                    <option value="Admin">Admin</option>
                    <option value="Member">Member</option>
                  </select>
                </div>
              </div>
              <div className="px-6 py-3 bg-gray-50 dark:bg-gray-700 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                >
                  Send Invitation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
