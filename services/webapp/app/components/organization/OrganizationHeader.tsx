import React from "react";
import { UserGroupIcon, CheckCircleIcon } from "@heroicons/react/24/solid";

interface OrganizationHeaderProps {
  orgName: string;
  isActive: boolean;
}

/**
 * Header component for the organization dashboard
 * Displays the organization name and active status
 */
export function OrganizationHeader({
  orgName,
  isActive
}: OrganizationHeaderProps) {
  return (
    <div className="flex items-center mb-6">
      <UserGroupIcon className="h-8 w-8 text-purple-500 mr-3" />
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
        {orgName}
      </h1>
      {isActive && (
        <span className="ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
          <CheckCircleIcon className="h-4 w-4 mr-1" />
          Active
        </span>
      )}
    </div>
  );
}
