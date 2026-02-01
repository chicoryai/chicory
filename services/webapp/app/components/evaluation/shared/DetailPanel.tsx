import React from 'react';
import type { Evaluation } from '~/services/chicory.server';
import {
  DocumentTextIcon,
  BeakerIcon,
  ClockIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline';

interface DetailPanelProps {
  evaluation: Evaluation;
  activeTab: string;
  onTabChange: (tab: string) => void;
  children: React.ReactNode;
}

export function DetailPanel({ 
  evaluation, 
  activeTab, 
  onTabChange,
  children 
}: DetailPanelProps) {
  const tabs = [
    { id: 'overview', label: 'Overview', icon: DocumentTextIcon },
    { id: 'test-cases', label: 'Test Cases', icon: BeakerIcon },
    { id: 'runs', label: 'Run History', icon: ClockIcon },
    { id: 'settings', label: 'Settings', icon: Cog6ToothIcon }
  ];
  
  return (
    <div className="relative h-full min-h-[calc(100vh-280px)] overflow-hidden rounded-lg border border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20">
      {/* Light mode gradient */}
      <div 
        className="absolute inset-0 dark:hidden"
        style={{
          background: 'radial-gradient(circle at center, rgba(255, 255, 255, 0.9) 95%, rgba(245, 243, 255, 0.6) 100%)',
        }}
      />
      {/* Dark mode gradient */}
      <div 
        className="absolute inset-0 hidden dark:block"
        style={{
          background: 'radial-gradient(circle at center, rgba(17, 24, 39, 0.9) 95%, rgba(88, 28, 135, 0.2) 100%)',
        }}
      />
      
      {/* Header */}
      <div className="relative z-10 px-6 py-4 border-b border-gray-200/50 dark:border-purple-900/20">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{evaluation.name}</h2>
        {evaluation.description && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{evaluation.description}</p>
        )}
      </div>
      
      {/* Tab Navigation */}
      <div className="relative z-10 border-b border-gray-200/50 dark:border-purple-900/20">
        <nav className="flex space-x-8 px-6" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors
                ${activeTab === tab.id
                  ? 'border-purple-400 text-purple-600 dark:text-purple-400'
                  : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-700'
                }
              `}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>
      
      {/* Tab Content */}
      <div className="relative z-10 p-6 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 400px)' }}>
        {children}
      </div>
    </div>
  );
}