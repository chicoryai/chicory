import React from "react";

interface OrganizationDetailsProps {
  orgId: string;
  orgName: string;
  userRole: string;
  projectCount: number;
}

/**
 * Displays organization details in a card format
 * Shows organization ID, user role, and project count
 */
export function OrganizationDetails({
  orgId,
  orgName,
  userRole,
  projectCount
}: OrganizationDetailsProps) {
  return (
    <div className="dark:bg-gray-800 shadow rounded-lg overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white">
          Organization Details
        </h2>
      </div>
      <div className="px-6 py-5">
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-6">
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Organization Name
            </dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-white">
              {orgName}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Organization ID
            </dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-white break-all">
              {orgId}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Your Role
            </dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-white">
              {userRole}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Projects
            </dt>
            <dd className="mt-1 text-sm text-gray-900 dark:text-white">
              {projectCount}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
