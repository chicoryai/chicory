import React from 'react';

interface EmptyStateProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="relative h-full min-h-[calc(100vh-280px)] flex items-center justify-center overflow-hidden rounded-lg border border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20">
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
      <div className="relative z-10 text-center max-w-sm">
        <div className="mx-auto w-16 h-16 rounded-full bg-purple-100 dark:bg-purple-900/20 flex items-center justify-center mb-4">
          <Icon className="w-8 h-8 text-purple-600 dark:text-purple-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">{title}</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">{description}</p>
        {action && <div>{action}</div>}
      </div>
    </div>
  );
}