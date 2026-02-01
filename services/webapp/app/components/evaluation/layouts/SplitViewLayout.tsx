import React, { useState } from 'react';
import { useParams } from '@remix-run/react';
import { useAgentContext } from '~/routes/_app.projects.$projectId.agents.$agentId';
import { Button } from '~/components/Button';
import { Breadcrumbs } from '~/components/Breadcrumbs';
import { 
  PlusIcon, 
  ArrowDownTrayIcon
} from '@heroicons/react/24/outline';

interface SplitViewLayoutProps {
  evaluationList: React.ReactNode;  // Left sidebar content
  detailView: React.ReactNode;      // Right panel content
  metricsBar: React.ReactNode;      // Top metrics dashboard
  onCreateEvaluation: () => void;
}

/**
 * Split-view layout implementing the 30/70 design pattern
 * Provides responsive behavior and proper overflow handling
 */
export function SplitViewLayout({ 
  evaluationList, 
  detailView,
  metricsBar,
  onCreateEvaluation
}: SplitViewLayoutProps) {
  const { agentId, projectId } = useParams();
  const { agent } = useAgentContext();
  
  return (
    <div className="flex flex-col h-screen">
      {/* Fixed Header */}
      <header className="flex-shrink-0 border-gray-200 dark:border-purple-900/20 bg-transparent dark:bg-gray-900/95 backdrop-blur-sm">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <Breadcrumbs items={[
              { label: agent.name, href: `/projects/${projectId}/agents/${agentId}` },
              { label: 'Evaluations', current: true }
            ]} />
            <div className="flex gap-2">
              <Button variant="primary" size="sm" onClick={onCreateEvaluation}>
                <PlusIcon className="w-4 h-4 mr-2" />
                Create Evaluation
              </Button>
            </div>
          </div>
        </div>
      </header>
      
      {/* Metrics Dashboard */}
      <div className="flex-shrink-0 px-6 py-4  border-gray-200 dark:border-purple-900/20 bg-transparent dark:bg-gray-900/80">
        {metricsBar}
      </div>
      
      {/* Split View Content */}
      <div className="flex flex-1 overflow-hidden p-6 gap-6">
        {/* Left Sidebar - 30% desktop */}
        <aside className="relative w-[30%] overflow-hidden rounded-lg border border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20">
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
          <div className="relative z-10 p-4 overflow-y-auto h-full">
            {evaluationList}
          </div>
        </aside>
        
        {/* Right Content - 70% desktop */}
        <main className="flex-1 overflow-y-auto">
          {detailView}
        </main>
      </div>
    </div>
  );
}
