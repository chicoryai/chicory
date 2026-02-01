/**
 * Tabs Component
 * Reusable tab navigation component with glassmorphism styling
 */

import { Fragment } from 'react';
import type { TabsProps } from "~/types/panels";

export function Tabs({ activeTab, onChange, tabs, className = "" }: TabsProps) {
  
  return (
    <div className={`${className} p-2`}>
      <div 
        className="relative rounded-2xl border border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20 overflow-hidden"
        role="tablist"
      >
        {/* Light mode gradient background */}
        <div 
          className="absolute inset-0 dark:hidden"
          style={{
            background: 'radial-gradient(circle at center, rgba(255, 255, 255, 0.9) 95%, rgba(245, 243, 255, 0.6) 100%)',
          }}
        />
        {/* Dark mode gradient background */}
        <div 
          className="absolute inset-0 hidden dark:block"
          style={{
            background: 'radial-gradient(circle at center, rgba(17, 24, 39, 0.9) 95%, rgba(88, 28, 135, 0.2) 100%)',
          }}
        />
        
        <div className="relative flex items-center p-1">
          {tabs.map((tab, index) => (
            <Fragment key={tab.id}>
              <button
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`${tab.id}-panel`}
                disabled={tab.disabled}
                onClick={() => onChange(tab.id)}
                className={`
                  relative flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium
                  rounded-xl transition-all duration-300 ease-out overflow-hidden
                  ${
                    activeTab === tab.id
                      ? "text-purple-600 dark:text-purple-400 border border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20"
                      : "text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-white/10 dark:hover:bg-white/5 border border-transparent"
                  }
                  ${tab.disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
                `}
              >
                {/* Active tab gradient backgrounds */}
                {activeTab === tab.id && (
                  <>
                    {/* Light mode gradient */}
                    <div 
                      className="absolute inset-0 dark:hidden pointer-events-none"
                      style={{
                        background: 'radial-gradient(circle at center, rgba(255, 255, 255, 0.9) 95%, rgba(245, 243, 255, 0.6) 100%)',
                      }}
                    />
                    {/* Dark mode gradient */}
                    <div 
                      className="absolute inset-0 hidden dark:block pointer-events-none"
                      style={{
                        background: 'radial-gradient(circle at center, rgba(17, 24, 39, 0.9) 95%, rgba(88, 28, 135, 0.2) 100%)',
                      }}
                    />
                  </>
                )}
                
                {tab.icon && <span className="flex-shrink-0 relative z-10">{tab.icon}</span>}
                <span className="relative z-10">{tab.label}</span>
                {tab.badge !== undefined && (
                  <span
                    className={`
                      ml-1 inline-flex items-center justify-center px-2 py-0.5 
                      text-xs font-medium rounded-full relative z-10
                      ${
                        activeTab === tab.id
                          ? "bg-purple-500/20 text-purple-700 dark:bg-purple-400/20 dark:text-purple-300 backdrop-blur-sm"
                          : "bg-gray-200/40 text-gray-600 dark:bg-gray-700/40 dark:text-gray-300 backdrop-blur-sm"
                      }
                    `}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
              {/* Add divider between tabs (not after the last one) */}
              {index < tabs.length - 1 && (
                <div className="w-px h-6 bg-gradient-to-b from-transparent via-gray-300/30 to-transparent dark:via-gray-600/30" />
              )}
            </Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}