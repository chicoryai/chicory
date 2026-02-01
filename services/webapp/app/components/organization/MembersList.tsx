import React, { useState, useMemo } from "react";
import { PlusIcon, UsersIcon, MagnifyingGlassIcon } from "@heroicons/react/24/outline";

interface Member {
  userId: string;
  email: string;
  firstName?: string;
  lastName?: string;
  role: string;
}

interface MembersListProps {
  members: Member[];
  onInviteMember?: () => void;
}

/**
 * Displays a list of organization members with their roles
 * Includes search functionality and a button to invite new members
 */
export function MembersList({ members, onInviteMember }: MembersListProps) {
  const [searchQuery, setSearchQuery] = useState("");

  // Filter members based on search query
  const filteredMembers = useMemo(() => {
    if (!searchQuery.trim()) return members;

    const query = searchQuery.toLowerCase();
    return members.filter((member) => {
      const fullName = `${member.firstName || ''} ${member.lastName || ''}`.toLowerCase();
      const email = member.email.toLowerCase();
      return fullName.includes(query) || email.includes(query);
    });
  }, [members, searchQuery]);

  return (
    <div className="dark:bg-gray-800 shadow rounded-lg overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
          <UsersIcon className="h-5 w-5 text-gray-500 dark:text-gray-400 mr-2" />
          Members
        </h2>
      </div>
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="relative">
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
      </div>
      <div className="px-6 py-5 max-h-96 overflow-y-auto">
        {filteredMembers.length === 0 ? (
          <p className="text-center text-sm text-gray-500 dark:text-gray-400 py-4">
            {searchQuery ? "Member not found" : "No members"}
          </p>
        ) : (
          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {filteredMembers.map((member) => (
              <li key={member.userId} className="py-4 flex items-center">
                <div className="flex-shrink-0">
                  <div className="h-10 w-10 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center text-purple-800 dark:text-purple-200 font-medium">
                    {member.firstName
                      ? member.firstName.charAt(0)
                      : member.email.charAt(0).toUpperCase()}
                  </div>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {member.firstName && member.lastName
                      ? `${member.firstName} ${member.lastName}`
                      : member.email}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {member.role}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="px-6 py-3 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600">
        <button
          onClick={onInviteMember}
          className="w-full inline-flex justify-center items-center px-4 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-white dark:text-gray-300 bg-purple-500 dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          Invite Member
        </button>
      </div>
    </div>
  );
}
