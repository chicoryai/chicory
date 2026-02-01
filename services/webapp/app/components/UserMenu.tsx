import React, { useState, useRef, useEffect } from "react";
import { Link, Form } from "@remix-run/react";
import { ChevronUpIcon, UserCircleIcon, ArrowLeftOnRectangleIcon } from "@heroicons/react/24/outline";
import { ThemeToggle } from "~/components/ThemeToggle";
import { DashboardUser } from "~/components/layouts/DashboardLayout";
import { usePermission } from "~/hooks/usePermissions";

interface UserMenuProps {
  user: DashboardUser & {
    activeOrgId?: string;
    orgIdToUserOrgInfo?: Record<string, any>;
  };
  className?: string;
  compact?: boolean;
  onClose?: () => void;
  showCloseButton?: boolean;
}

export function UserMenu({ user, className = "", compact = false, onClose, showCloseButton = false }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Check if user has permission to view organization page
  const canViewOrg = usePermission('canManageOrg');

  // Close popover when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Display user's name if available, otherwise email
  const displayName = user.firstName && user.lastName
    ? `${user.firstName} ${user.lastName}`
    : user.email;

  // First letter of the first name or email for compact avatar
  const userInitial = user.firstName
    ? user.firstName.charAt(0)
    : user.email
      ? user.email.charAt(0).toUpperCase()
      : 'U';

  // Get the active org ID or the first org ID if active is not set
  const orgId = user.activeOrgId || (user.orgIdToUserOrgInfo ? Object.keys(user.orgIdToUserOrgInfo)[0] : undefined);
  
  if (compact) {
    return (
      <div className={`relative z-40 ${className}`} ref={popoverRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors duration-150"
          title={displayName}
        >
          {userInitial}
        </button>
        
        {isOpen && (
          <div className="absolute bottom-full left-0 mb-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10 w-48">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="font-medium text-gray-900 dark:text-white">{displayName}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">{user.email}</div>
            </div>
            
            <div className="py-2">
              <Link
                to="/settings/profile"
                className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                onClick={() => setIsOpen(false)}
              >
                Your profile
              </Link>
              {/* Only show Organization link if user has org:view permission */}
              {orgId && canViewOrg && (
                <Link
                  to={`/org/${orgId}`}
                  className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                  onClick={() => setIsOpen(false)}
                >
                  Organization
                </Link>
              )}
              <Link
                to="/settings/preferences"
                className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                onClick={() => setIsOpen(false)}
              >
                Notification settings
              </Link>
              <div className="px-4 py-2 flex items-center justify-between">
                <span className="text-sm text-gray-700 dark:text-gray-300">Theme</span>
                <ThemeToggle />
              </div>
              <Form method="post" action="/api/auth/logout">
                <button 
                  type="submit"
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  Sign out
                </button>
              </Form>
            </div>
          </div>
        )}
      </div>
    );
  }
  
  return (
    <div className={`relative z-40 ${className}`} ref={popoverRef}>
      <div className="flex items-center w-full">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center flex-1 px-4 py-3 text-left text-sm hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors duration-150"
        >
          <ChevronUpIcon className={`h-4 w-4 text-gray-500 dark:text-gray-400 transition-transform duration-200 mr-3 ${isOpen ? 'rotate-180' : ''}`} />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-800 dark:text-white truncate">{displayName}</p>
          </div>
        </button>
        {showCloseButton && onClose && (
          <button
            type="button"
            onClick={onClose}
            className="mr-3 text-purple-500 transition hover:text-purple-600 dark:text-gray-300 dark:hover:text-purple-200"
            title="Collapse sidebar"
          >
            <ArrowLeftOnRectangleIcon className="h-5 w-5" />
          </button>
        )}
      </div>
      
      {isOpen && (
        <div className="absolute bottom-full left-0 right-0 mb-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="font-medium text-gray-900 dark:text-white">{displayName}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">{user.email}</div>
          </div>
          
          <div className="py-2">
            <Link
              to="/settings/profile"
              className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              onClick={() => setIsOpen(false)}
            >
              Your profile
            </Link>
            {/* Only show Organization link if user has org:view permission */}
            {orgId && canViewOrg && (
              <Link
                to={`/org/${orgId}`}
                className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                onClick={() => setIsOpen(false)}
              >
                Organization
              </Link>
            )}
            <div className="px-4 py-2 flex items-center justify-between">
              <span className="text-sm text-gray-700 dark:text-gray-300">Theme</span>
              <ThemeToggle />
            </div>
            <Form method="post" action="/api/auth/logout">
              <button 
                type="submit"
                className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                Sign out
              </button>
            </Form>
          </div>
        </div>
      )}
    </div>
  );
}
