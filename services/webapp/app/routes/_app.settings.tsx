import { Outlet, Link, useLocation } from "@remix-run/react";
import { json } from "@remix-run/node";
import type { LoaderFunctionArgs, MetaFunction } from "@remix-run/node";
import { auth } from "~/auth/auth.server";
import { Cog6ToothIcon, KeyIcon, UserCircleIcon } from "@heroicons/react/24/outline";

export const meta: MetaFunction = () => {
  return [
    { title: "Settings - Chicory AI" },
    { name: "description", content: "Manage your Chicory AI account settings" },
  ];
};

export async function loader({ request }: LoaderFunctionArgs) {
  // Get the authenticated user
  const user = await auth.getUser(request, {});
  
  if (!user) {
    return json({ error: "Unauthorized" }, { status: 401 });
  }
  
  return json({ user });
}

interface SettingsTab {
  id: string;
  name: string;
  href: string;
  icon: React.ForwardRefExoticComponent<React.SVGProps<SVGSVGElement>>;
}

export default function Settings() {
  const location = useLocation();
  const currentPath = location.pathname;
  
  // Define the settings tabs
  const tabs: SettingsTab[] = [
    {
      id: "profile",
      name: "Profile",
      href: "/settings/profile",
      icon: UserCircleIcon,
    },
    {
      id: "app",
      name: "App Settings",
      href: "/settings/app",
      icon: Cog6ToothIcon,
    },
    {
      id: "apikeys",
      name: "API Keys",
      href: "/settings/apikeys",
      icon: KeyIcon,
    },
  ];
  
  // Determine which tab is active
  const getActiveTab = () => {
    if (currentPath === "/settings") return "profile";
    return tabs.find(tab => currentPath.includes(tab.id))?.id || "profile";
  };
  
  const activeTab = getActiveTab();
  
  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <h1 className="text-3xl font-bold mb-2">Settings</h1>
      <p className="text-gray-600 dark:text-gray-400 mb-8">
        Manage your account settings, application preferences, and API keys
      </p>
      
      <div className="flex flex-col md:flex-row gap-8">
        {/* Settings Navigation */}
        <div className="w-full md:w-48 shrink-0">
          <nav className="space-y-1 dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <Link
                  key={tab.id}
                  to={tab.href}
                  className={`flex items-center px-4 py-3 text-sm font-medium ${
                    isActive
                      ? "bg-indigo-50 dark:bg-indigo-900/20 border-l-4 border-indigo-500 text-indigo-700 dark:text-indigo-300"
                      : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  }`}
                >
                  <tab.icon
                    className={`mr-3 h-5 w-5 ${
                      isActive ? "text-indigo-500" : "text-gray-400 dark:text-gray-500"
                    }`}
                    aria-hidden="true"
                  />
                  <span>{tab.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>
        
        {/* Settings Content */}
        <div className="flex-1 bg-whitePurple-50 dark:bg-gray-800 rounded-lg shadow p-6">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
