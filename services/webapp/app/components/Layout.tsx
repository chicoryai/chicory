import { Link, useLocation, Form, useNavigate } from "@remix-run/react";
import { ThemeToggle } from "./ThemeToggle";
import { Button } from "./Button";
import { useState, useEffect, useRef } from "react";
import { ChevronDownIcon, ChevronUpIcon, PlusIcon } from "@heroicons/react/24/outline";

interface SidebarLinkProps {
  to: string;
  label: string;
  isActive: boolean;
}

interface User {
  email?: string;
  firstName?: string;
  lastName?: string;
}

interface Organization {
  orgId: string;
  orgName: string;
  userRole: string;
}

interface DashboardLayoutProps {
  children: React.ReactNode;
  user: User;
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

function UserPopover({ user }: { user: User }) {
  const [isOpen, setIsOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  
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
  
  return (
    <div className="relative" ref={popoverRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center w-full px-4 py-3 text-left text-sm hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors duration-150"
      >
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-800 dark:text-white truncate">{displayName}</p>
        </div>
        <ChevronUpIcon className={`h-4 w-4 text-gray-500 dark:text-gray-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      
      {isOpen && (
        <div className="absolute bottom-full left-0 right-0 mb-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="font-medium text-gray-900 dark:text-white">{displayName}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">{user.email}</div>
          </div>
          
          <div className="py-2">
            <Link 
              to="/dashboard/settings" 
              className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              onClick={() => setIsOpen(false)}
            >
              Your profile
            </Link>
            <Link 
              to="/dashboard/settings/preferences" 
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

export function DashboardLayout({ children, user, currentOrg, orgs = [] }: DashboardLayoutProps) {
  const location = useLocation();
  const isNewRoute = location.pathname === "/dashboard/new";
  
  // Projects links
  const projectLinks = [
    {
      to: currentOrg ? `/dashboard/org/${currentOrg.orgId}` : "/dashboard",
      label: "Dashboard",
      isActive: location.pathname === (currentOrg ? `/dashboard/org/${currentOrg.orgId}` : "/dashboard") || 
                (location.pathname.startsWith('/dashboard/org/') && location.pathname.split('/').length === 4),
    },
  ];
  
  // Management links
  const managementLinks = currentOrg ? [
    {
      to: `/dashboard/org/${currentOrg.orgId}/integrations`,
      label: "Integrations",
      isActive: location.pathname === `/dashboard/org/${currentOrg.orgId}/integrations`,
    },
  ] : [];
  
  // Check if current route is an organization route
  const isOrgRoute = location.pathname.startsWith('/dashboard/org/');
  const currentOrgId = isOrgRoute ? location.pathname.split('/')[3] : currentOrg?.orgId;

  // If we're on the new route, we're creating an organization
  // Use a layout without sidebar for better focus on the setup process
  if (isNewRoute) {
    return (
      <div className="flex flex-col h-screen bg-gray-100 dark:bg-gray-900">
        {/* Top Navigation Bar */}
        <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              {/* Logo */}
              <div className="flex items-center">
                <Link to="/dashboard" className="flex items-center">
                  <span className="text-xl font-semibold text-gray-800 dark:text-white">Chicory AI</span>
                </Link>
              </div>
              
              {/* Right side controls */}
              <div className="flex items-center space-x-4">
                <ThemeToggle />
                <div className="text-sm text-gray-600 dark:text-gray-300">{user?.email}</div>
                <Form method="post" action="/api/auth/logout">
                  <Button 
                    type="submit"
                    variant="tertiary" 
                    size="sm"
                  >
                    Log out
                  </Button>
                </Form>
              </div>
            </div>
          </div>
        </header>
        
        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="flex h-screen dark:bg-gray-900 overflow-hidden">
      {/* Sidebar */}
      <aside className="bg-white dark:bg-gray-900 text-gray-800 dark:text-white w-48 flex flex-col h-full border-r border-gray-200 dark:border-gray-800">
        <div className="flex-1 flex flex-col h-full">
          {/* Logo and Name */}
          <div className="flex items-center px-4 py-5">
            <div className="flex-shrink-0 mr-3">
              <img 
                src="/icon_32x32.png" 
                alt="Chicory AI" 
                width="24" 
                height="24" 
                className="w-6 h-6"
              />
            </div>
            <div className="text-xl font-semibold text-gray-800 dark:text-white">Chicory AI</div>
          </div>
          
          {/* Organization Selector */}
          <OrganizationSelector orgs={orgs} currentOrg={currentOrg} />
          
          {/* Navigation */}
          <nav className="flex-1 pt-2 overflow-y-auto">
            {/* Projects section */}
            <div className="mb-6 pb-4">
              {projectLinks.map((link, index) => (
                <SidebarLink
                  key={`project-${index}`}
                  to={link.to}
                  label={link.label}
                  isActive={link.isActive}
                />
              ))}
            </div>
            
            {/* Management section - only show if we have a current org */}
          </nav>
          
          {/* User Info & Popover - Pinned to bottom */}
          <div className="mt-auto border-t border-gray-200 dark:border-gray-800">
            <UserPopover user={user} />
          </div>
        </div>
      </aside>
      
      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        <div className="flex-1 p-8 overflow-auto">{children}</div>
      </main>
    </div>
  );
}
