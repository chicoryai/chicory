import React from 'react';
import { BaseComponentProps } from '~/types/integrations';

interface IntegrationsLayoutProps extends BaseComponentProps {
  leftColumn: React.ReactNode;
  rightColumn: React.ReactNode;
  title?: string;
  description?: string;
}

/**
 * Main layout component for integrations page
 * Provides a responsive two-column layout with 70/30 split
 */
export default function IntegrationsLayout({
  leftColumn,
  rightColumn,
  title = "Integrations",
  description = "Connect your data sources and manage training",
  className = ""
}: IntegrationsLayoutProps) {
  return (
    <div className={`min-h-screen ${className}`}>
      {/* Header */}
      <div className="">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
                {title}
              </h1>
              {description && (
                <p className="mt-3 text-base text-gray-600 dark:text-gray-400 leading-relaxed">
                  {description}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-10 gap-10">
          {/* Left Column - 70% */}
          <div className="lg:col-span-7">
            {leftColumn}
          </div>
          
          {/* Right Column - 30% */}
          <div className="lg:col-span-3">
            {rightColumn}
          </div>
        </div>
      </div>
    </div>
  );
} 