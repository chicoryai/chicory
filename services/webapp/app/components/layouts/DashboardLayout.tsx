import { Link, useLocation, useNavigate } from "@remix-run/react";
import { ThemeToggle } from "../ThemeToggle";
import { Button } from "../Button";
import { useState, useEffect, useRef } from "react";
import { ChevronDownIcon, ChevronUpIcon, PlusIcon } from "@heroicons/react/24/outline";
import { useSidebar } from "~/hooks/useSidebar";
import { UserMenu } from "../UserMenu";

interface SidebarLinkProps {
  to: string;
  label: string;
  isActive: boolean;
}

export interface DashboardUser {
  email?: string;
  firstName?: string;
  lastName?: string;
  userPermissions?: string[];
}

interface Organization {
  orgId: string;
  orgName: string;
  userRole: string;
}

interface DashboardLayoutProps {
  children: React.ReactNode;
  user: DashboardUser;
  currentOrg?: Organization | null;
  orgs?: Organization[];
}

function SidebarLink({ to, label, isActive }: SidebarLinkProps) {
  return (
    <Link
      to={to}
      className={`block px-4 py-2.5 text-xs ${
        isActive
          ? "bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-white"
          : "text-gray-600 hover:bg-gray-200 hover:text-gray-800 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
      }`}
    >
      {label}
    </Link>
  );
}

function OrganizationSelector({ orgs, currentOrg }: { orgs: Organization[], currentOrg?: Organization | null }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  
  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);
  
  const handleOrgSelect = (orgId: string) => {
    navigate(`/dashboard/org/${orgId}`);
    setIsOpen(false);
  };
  
  return (
    <div className="px-4 py-3" ref={dropdownRef}>
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm text-gray-500 dark:text-gray-400">
          ORGANIZATIONS
        </span>
        <Link 
          to="/dashboard/new" 
          className="p-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          title="Create new organization"
        >
          <PlusIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
        </Link>
      </div>
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center justify-between w-full px-3 py-2 text-left bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-md transition-colors"
        >
          <span className="text-sm font-medium text-gray-800 dark:text-white truncate">
            {currentOrg ? currentOrg.orgName : 'Select Organization'}
          </span>
          <ChevronDownIcon className={`h-4 w-4 text-gray-500 dark:text-gray-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
        </button>
        
        {isOpen && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10 max-h-64 overflow-y-auto">
            {orgs.map((org) => (
              <button
                key={org.orgId}
                onClick={() => handleOrgSelect(org.orgId)}
                className={`block w-full text-left px-3 py-2 text-sm ${
                  currentOrg?.orgId === org.orgId
                    ? "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-white"
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                }`}
              >
                {org.orgName}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Main layout component for dashboard pages.
 * Provides the sidebar, header, and main content area.
 */
export function DashboardLayout({ children, user, currentOrg, orgs = [] }: DashboardLayoutProps) {
  const location = useLocation();
  const { isOpen, toggleSidebar } = useSidebar({
    defaultOpen: true,
    closeBreakpoint: 768,
    openBreakpoint: 1024
  });
  
  // Projects links
  const projectLinks = [
    {
      to: currentOrg ? `/dashboard/org/${currentOrg.orgId}` : "/dashboard",
      label: "Projects"
    },
    {
      to: "/dashboard/organizations",
      label: "Organizations"
    }
  ];
  
  // Settings links
  const settingsLinks = [
    {
      to: "/dashboard/settings",
      label: "Account Settings"
    }
  ];
  
  return (
    <div className="flex h-screen overflow-hidden bg-white dark:bg-gray-900">
      {/* Sidebar */}
      <aside 
        className={`${
          isOpen ? 'w-64' : 'w-0 -ml-64'
        } flex flex-col fixed inset-y-0 z-10 bg-white dark:bg-gray-800 shadow-md transition-all duration-300 md:relative md:translate-x-0`}
      >
        {/* Logo */}
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <Link to="/dashboard" className="flex items-center">
            <span className="text-xl font-bold text-lime-500">Chicory</span>
            <span className="ml-1 text-xl font-bold text-gray-900 dark:text-white">AI</span>
          </Link>
        </div>
        
        {/* Organization selector */}
        {orgs.length > 0 && (
          <OrganizationSelector orgs={orgs} currentOrg={currentOrg} />
        )}
        
        {/* Navigation links */}
        <nav className="flex-1 overflow-y-auto">
          <div className="px-3 py-2">
            <div className="mb-2 px-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
              Workspace
            </div>
            {projectLinks.map((link) => (
              <SidebarLink
                key={link.to}
                to={link.to}
                label={link.label}
                isActive={location.pathname === link.to}
              />
            ))}
          </div>
          
          <div className="px-3 py-2">
            <div className="mb-2 px-4 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
              Settings
            </div>
            {settingsLinks.map((link) => (
              <SidebarLink
                key={link.to}
                to={link.to}
                label={link.label}
                isActive={location.pathname === link.to}
              />
            ))}
          </div>
        </nav>
        
        {/* User menu */}
        <UserMenu user={user} />
      </aside>
      
      {/* Mobile sidebar toggle */}
      <button
        type="button"
        className="md:hidden fixed top-4 left-4 z-20 p-2 rounded-md bg-white dark:bg-gray-800 shadow-md"
        onClick={toggleSidebar}
      >
        {isOpen ? (
          <svg className="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        )}
      </button>
      
      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
