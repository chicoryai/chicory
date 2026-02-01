import { ReactNode } from "react";

interface Tab {
  id: string;
  name: string;
  icon: ReactNode;
}

interface AgentTabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  children: ReactNode;
}

export default function AgentTabs({ tabs, activeTab, onTabChange, children }: AgentTabsProps) {
  return (
    <div className="dark:bg-gray-900 rounded-lg border border-gray-300 dark:border-gray-700 md:col-span-2 flex flex-col">
      {/* Tabs Header */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex -mb-px" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`${
                activeTab === tab.id
                  ? 'border-purple-500 text-purple-600 dark:text-purple-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              } flex-1 whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center justify-center`}
            >
              {tab.icon && (
                <span className="mr-2 flex h-5 w-5 items-center justify-center">
                  {tab.icon}
                </span>
              )}
              {tab.name}
            </button>
          ))}
        </nav>
      </div>
      
      {/* Tab Content */}
      <div className="flex-1 p-6 overflow-y-auto" style={{ minHeight: '400px' }}>
        {children}
      </div>
    </div>
  );
}
