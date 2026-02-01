import React, { useState } from "react";
import { json, redirect } from "@remix-run/node";
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { useLoaderData, useSubmit, useActionData, useNavigation } from "@remix-run/react";
import { auth } from "~/auth/auth.server";
import { fetchUsersInOrg, changeUserRoleInOrg, removeUserFromOrg, inviteUserToOrg } from "~/utils/propelauth.server";
import { UserIcon, TrashIcon, EyeIcon, ShieldCheckIcon, PlusIcon, MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import { ActionFeedback } from "~/components/ui/ActionFeedback";
import { usePermission } from "~/hooks/usePermissions";

interface PropelAuthUser {
  userId: string;
  roleInOrg: string;
  additionalRolesInOrg?: string[];
  email: string;
  emailConfirmed: boolean;
  hasPassword: boolean;
  firstName?: string;
  lastName?: string;
  pictureUrl?: string;
  properties?: Record<string, any>;
  metadata?: any;
  locked: boolean;
  enabled: boolean;
  mfaEnabled: boolean;
  canCreateOrgs: boolean;
  createdAt: number;
  lastActiveAt: number;
  updatePasswordRequired: boolean;
}

interface Member {
  userId: string;
  email: string;
  emailConfirmed: boolean;
  firstName?: string;
  lastName?: string;
  role: string;
  additionalRoles?: string[];
  lastActiveAt?: string;
  pictureUrl?: string;
  mfaEnabled: boolean;
  enabled: boolean;
  locked: boolean;
  hasPassword: boolean;
}

export interface MembersLoaderData {
  members: Member[];
  currentUserRole: string;
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
    // Fetch organization members from PropelAuth
    const usersResponse = await fetchUsersInOrg(orgId);

    const members = usersResponse.users.map((propelUser: PropelAuthUser) => ({
      userId: propelUser.userId,
      email: propelUser.email,
      emailConfirmed: propelUser.emailConfirmed,
      firstName: propelUser.firstName,
      lastName: propelUser.lastName,
      role: propelUser.roleInOrg,
      additionalRoles: propelUser.additionalRolesInOrg,
      lastActiveAt: propelUser.lastActiveAt ? new Date(propelUser.lastActiveAt * 1000).toLocaleDateString() : undefined,
      pictureUrl: propelUser.pictureUrl,
      mfaEnabled: propelUser.mfaEnabled,
      enabled: propelUser.enabled,
      locked: propelUser.locked,
      hasPassword: propelUser.hasPassword
    }));

    const data: MembersLoaderData = {
      members,
      currentUserRole: user.orgIdToUserOrgInfo[orgId].userAssignedRole || 'Member'
    };

    return json(data);
  } catch (error) {
    console.error("Error fetching organization members:", error);

    // Fallback to just the current user if API call fails
    return json({
      members: [{
        userId: user.userId,
        email: user.email || "",
        emailConfirmed: true,
        firstName: user.firstName,
        lastName: user.lastName,
        role: user.orgIdToUserOrgInfo[orgId].userAssignedRole || 'Member',
        mfaEnabled: false,
        enabled: true,
        locked: false,
        hasPassword: true
      }],
      currentUserRole: user.orgIdToUserOrgInfo[orgId].userAssignedRole || 'Member'
    } as MembersLoaderData);
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

    // Check if user has admin privileges
    const currentUserRole = user.orgIdToUserOrgInfo[orgId].userAssignedRole || 'Member';
    const isAdmin = currentUserRole === 'Owner' || currentUserRole === 'Admin';

    if (!isAdmin) {
      return json({ error: "Insufficient permissions" }, { status: 403 });
    }

    const formData = await request.formData();
    const intent = formData.get("intent") as string;

    if (intent === "change-role") {
      const userId = formData.get("userId") as string;
      const newRole = formData.get("newRole") as string;

      if (!userId || !newRole) {
        return json({ error: "User ID and role are required" }, { status: 400 });
      }

      try {
        await changeUserRoleInOrg(userId, orgId, newRole);
        return json({
          success: true,
          message: `Role updated to ${newRole} successfully`
        });
      } catch (error: any) {
        return json({
          error: error.message || "Failed to update role"
        }, { status: 500 });
      }
    }

    if (intent === "remove-member") {
      const userId = formData.get("userId") as string;

      if (!userId) {
        return json({ error: "User ID is required" }, { status: 400 });
      }

      // Prevent user from removing themselves
      if (userId === user.userId) {
        return json({ error: "Cannot remove yourself from the organization" }, { status: 400 });
      }

      try {
        await removeUserFromOrg(userId, orgId);
        return json({
          success: true,
          message: "Member removed successfully"
        });
      } catch (error: any) {
        return json({
          error: error.message || "Failed to remove member"
        }, { status: 500 });
      }
    }

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

export default function OrganizationMembers() {
  const data = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();
  const submit = useSubmit();

  // Explicitly type the data to avoid TypeScript errors
  const { members, currentUserRole } = data as MembersLoaderData;

  const isAdmin = currentUserRole === 'Owner' || currentUserRole === 'Admin';
  const isSubmitting = navigation.state === "submitting";

  // RBAC Permission checks
  const canInvite = usePermission('propelauth::can_invite');
  const canChangeRoles = usePermission('propelauth::can_change_roles');
  const canRemoveUsers = usePermission('propelauth::can_remove_users');
  const canViewOtherMembers = usePermission('propelauth::can_view_other_members');

  // State for role change modal
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [newRole, setNewRole] = useState("");

  // State for user details modal
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [detailsMember, setDetailsMember] = useState<Member | null>(null);

  // State for invite member modal
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("Member");

  // State for member search
  const [searchQuery, setSearchQuery] = useState("");

  // Filter members based on search query
  const filteredMembers = React.useMemo(() => {
    if (!searchQuery.trim()) return members;

    const query = searchQuery.toLowerCase();
    return members.filter((member) => {
      const fullName = `${member.firstName || ''} ${member.lastName || ''}`.toLowerCase();
      const email = member.email.toLowerCase();
      return fullName.includes(query) || email.includes(query);
    });
  }, [members, searchQuery]);

  const handleRoleChange = (member: Member) => {
    setSelectedMember(member);
    setNewRole(member.role);
    setShowRoleModal(true);
  };

  const handleViewDetails = (member: Member) => {
    setDetailsMember(member);
    setShowDetailsModal(true);
  };

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

  const handleRoleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedMember && newRole) {
      submit(
        {
          intent: "change-role",
          userId: selectedMember.userId,
          newRole: newRole
        },
        { method: "post" }
      );
      setShowRoleModal(false);
      setSelectedMember(null);
    }
  };

  const handleRemoveMember = (member: Member) => {
    const confirmMessage = `Are you sure you want to remove ${member.firstName && member.lastName ? `${member.firstName} ${member.lastName}` : member.email} from this organization?`;
    if (window.confirm(confirmMessage)) {
      submit(
        {
          intent: "remove-member",
          userId: member.userId
        },
        { method: "post" }
      );
    }
  };

  return (
    <div className="mt-6">
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

      <div className="dark:bg-gray-800 shadow rounded-lg overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Members & Permissions
          </h2>
        </div>

        {/* Search Bar and Invite Button */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search members..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg font-ui text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-400 focus:border-transparent"
            />
          </div>
          {/* Only show Invite button if user has permission */}
          {canInvite && (
            <button
              onClick={() => setShowInviteModal(true)}
              className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              Invite Member
            </button>
          )}
        </div>

        <div className="overflow-hidden">
        <table className="min-w-full divide-y divide-gray-300 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th scope="col" className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 dark:text-white sm:pl-6">
                User
              </th>
              <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">
                Role
              </th>
              <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">
                MFA
              </th>
              <th scope="col" className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">
                Last Active
              </th>
              <th scope="col" className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-900">
            {filteredMembers.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  {searchQuery ? "No members found matching your search" : "No members found"}
                </td>
              </tr>
            ) : (
              filteredMembers.map((member) => (
              <tr key={member.userId}>
                <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm sm:pl-6">
                  <div className="flex items-center">
                    <div className="h-10 w-10 flex-shrink-0">
                      {member.pictureUrl ? (
                        <img className="h-10 w-10 rounded-full" src={member.pictureUrl} alt="" />
                      ) : (
                        <div className="h-10 w-10 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                          <UserIcon className="h-6 w-6 text-purple-600 dark:text-purple-300" />
                        </div>
                      )}
                    </div>
                    <div className="ml-4">
                      <div className="font-medium text-gray-900 dark:text-white">
                        {member.firstName && member.lastName
                          ? `${member.firstName} ${member.lastName}`
                          : member.email}
                      </div>
                      <div className="text-gray-500 dark:text-gray-400">{member.email}</div>
                    </div>
                  </div>
                </td>
                <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${member.role === 'Owner'
                      ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
                      : member.role === 'Admin'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                        : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                    }`}>
                    {member.role}
                  </span>
                </td>
                <td className="whitespace-nowrap px-3 py-4 text-sm">
                  {member.mfaEnabled ? (
                    <span className="inline-flex items-center text-green-600 dark:text-green-400">
                      <ShieldCheckIcon className="h-5 w-5 mr-1" />
                      Enabled
                    </span>
                  ) : (
                    <span className="text-gray-400 dark:text-gray-500">Disabled</span>
                  )}
                </td>
                <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                  {member.lastActiveAt || 'Never'}
                </td>
                <td className="relative py-4 pl-3 pr-4 text-sm font-medium sm:pr-6">
                  <div className="flex flex-col gap-2 items-start">
                    {/* Only show View User Details if user has permission */}
                    {canViewOtherMembers && (
                      <button
                        type="button"
                        onClick={() => handleViewDetails(member)}
                        className="inline-flex items-center gap-2 px-2.5 py-1 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                        title="View User Details"
                      >
                        <EyeIcon className="h-4 w-4" />
                        View User Details
                      </button>
                    )}
                    {/* Only show Change Role button if user has permission */}
                    {canChangeRoles && (
                      <button
                        type="button"
                        onClick={() => handleRoleChange(member)}
                        disabled={isSubmitting}
                        className="inline-flex items-center gap-2 px-2.5 py-1 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Change Role"
                      >
                        <UserIcon className="h-4 w-4" />
                        Change Role
                      </button>
                    )}
                    {/* Only show Remove button if user has permission */}
                    {canRemoveUsers && (
                      <button
                        type="button"
                        onClick={() => handleRemoveMember(member)}
                        disabled={isSubmitting}
                        className="inline-flex items-center gap-2 px-2.5 py-1 border border-red-300 dark:border-red-700 rounded-md text-red-700 dark:text-red-400 bg-white dark:bg-gray-800 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Remove from Org"
                      >
                        <TrashIcon className="h-4 w-4" />
                        Remove from Org
                      </button>
                    )}
                  </div>
                </td>
              </tr>
              ))
            )}
          </tbody>
        </table>
        </div>
      </div>

      {/* Role Change Modal */}
      {showRoleModal && selectedMember && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">Change Member Role</h3>
            </div>
            <form onSubmit={handleRoleSubmit}>
              <div className="px-6 py-4">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  Change role for {selectedMember.firstName && selectedMember.lastName
                    ? `${selectedMember.firstName} ${selectedMember.lastName}`
                    : selectedMember.email}
                </p>
                <div>
                  <label htmlFor="role" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Role
                  </label>
                  <select
                    id="role"
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    className="w-full px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg font-ui text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-400 focus:border-transparent"
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
                  onClick={() => {
                    setShowRoleModal(false);
                    setSelectedMember(null);
                  }}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                >
                  Update Role
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* User Details Modal */}
      {showDetailsModal && detailsMember && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">Member Details</h3>
            </div>
            <div className="px-6 py-6">
              {/* User Profile Section */}
              <div className="flex items-center mb-6">
                <div className="h-16 w-16 flex-shrink-0">
                  {detailsMember.pictureUrl ? (
                    <img className="h-16 w-16 rounded-full" src={detailsMember.pictureUrl} alt="" />
                  ) : (
                    <div className="h-16 w-16 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                      <UserIcon className="h-10 w-10 text-purple-600 dark:text-purple-300" />
                    </div>
                  )}
                </div>
                <div className="ml-4">
                  <h4 className="text-xl font-semibold text-gray-900 dark:text-white">
                    {detailsMember.firstName && detailsMember.lastName
                      ? `${detailsMember.firstName} ${detailsMember.lastName}`
                      : detailsMember.email}
                  </h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{detailsMember.email}</p>
                </div>
              </div>

              {/* Details Grid */}
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 rounded-lg">
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Role</dt>
                  <dd className="mt-1">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${detailsMember.role === 'Owner'
                        ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
                        : detailsMember.role === 'Admin'
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                          : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                      }`}>
                      {detailsMember.role}
                    </span>
                  </dd>
                </div>

                <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 rounded-lg">
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">MFA Status</dt>
                  <dd className="mt-1 text-sm font-medium">
                    {detailsMember.mfaEnabled ? (
                      <span className="inline-flex items-center text-green-600 dark:text-green-400">
                        <ShieldCheckIcon className="h-4 w-4 mr-1" />
                        Enabled
                      </span>
                    ) : (
                      <span className="text-gray-500 dark:text-gray-400">Disabled</span>
                    )}
                  </dd>
                </div>

                <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 rounded-lg">
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Email Confirmed</dt>
                  <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-white">
                    {detailsMember.emailConfirmed ? 'Yes' : 'No'}
                  </dd>
                </div>

                <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 rounded-lg">
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Has Password</dt>
                  <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-white">
                    {detailsMember.hasPassword ? 'Yes' : 'No'}
                  </dd>
                </div>

                <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 rounded-lg">
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Account Status</dt>
                  <dd className="mt-1">
                    {detailsMember.enabled ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                        Disabled
                      </span>
                    )}
                  </dd>
                </div>

                <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 rounded-lg">
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Locked</dt>
                  <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-white">
                    {detailsMember.locked ? 'Yes' : 'No'}
                  </dd>
                </div>

                <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 rounded-lg sm:col-span-2">
                  <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Last Active</dt>
                  <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-white">
                    {detailsMember.lastActiveAt || 'Never'}
                  </dd>
                </div>

                {detailsMember.additionalRoles && detailsMember.additionalRoles.length > 0 && (
                  <div className="bg-gray-50 dark:bg-gray-700 px-4 py-3 rounded-lg sm:col-span-2">
                    <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Additional Roles</dt>
                    <dd className="mt-2 flex flex-wrap gap-2">
                      {detailsMember.additionalRoles.map((role, index) => (
                        <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                          {role}
                        </span>
                      ))}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
            <div className="px-6 py-3 bg-gray-50 dark:bg-gray-700 flex justify-end">
              <button
                type="button"
                onClick={() => {
                  setShowDetailsModal(false);
                  setDetailsMember(null);
                }}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

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
                  <label htmlFor="invite-role" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Role
                  </label>
                  <select
                    id="invite-role"
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
