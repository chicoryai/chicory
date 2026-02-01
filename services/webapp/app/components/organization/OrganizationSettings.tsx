import React from "react";
import { Cog6ToothIcon } from "@heroicons/react/24/solid";

interface SettingsLink {
  id: string;
  label: string;
  href: string;
  isActive?: boolean;
}

interface OrganizationSettingsProps {
  links: SettingsLink[];
  onSettingClick?: (id: string) => void;
}

/**
 * Displays organization settings navigation
 * Provides links to different settings pages
 */
export function OrganizationSettings({ links, onSettingClick }: OrganizationSettingsProps) {
  return (
    <div className="dark:bg-gray-800 shadow rounded-lg overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white flex items-center">
          <Cog6ToothIcon className="h-5 w-5 text-gray-500 dark:text-gray-400 mr-2" />
          Settings
        </h2>
      </div>
      <div className="px-6 py-5">
        <nav className="space-y-1">
          {links.map((link) => (
            <a 
              key={link.id}
              href={link.href}
              onClick={(e) => {
                if (onSettingClick) {
                  e.preventDefault();
                  onSettingClick(link.id);
                }
              }}
              className={`group flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                link.isActive 
                  ? "text-gray-900 dark:text-white bg-gray-50 dark:bg-gray-700" 
                  : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </div>
  );
}
