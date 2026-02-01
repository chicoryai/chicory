import React from 'react';
import { ArrowUpIcon, ArrowDownIcon, MinusIcon } from '@heroicons/react/24/outline';

interface MetricData {
  label: string;
  value: number | string;
  trend?: 'up' | 'down' | 'stable';
  icon: React.ComponentType<{ className?: string }>;
  color: 'purple' | 'lime' | 'green' | 'amber';
}

interface MetricsBarProps {
  metrics: MetricData[];
}

function TrendIndicator({ direction }: { direction: 'up' | 'down' | 'stable' }) {
  if (direction === 'up') {
    return (
      <div className="flex items-center text-green-400 text-xs">
        <ArrowUpIcon className="w-3 h-3 mr-1" />
        <span>+12%</span>
      </div>
    );
  }
  if (direction === 'down') {
    return (
      <div className="flex items-center text-red-400 text-xs">
        <ArrowDownIcon className="w-3 h-3 mr-1" />
        <span>-5%</span>
      </div>
    );
  }
  return (
    <div className="flex items-center text-gray-400 text-xs">
      <MinusIcon className="w-3 h-3 mr-1" />
      <span>0%</span>
    </div>
  );
}

export function MetricsBar({ metrics }: MetricsBarProps) {
  const getColorClasses = (color: string) => {
    switch (color) {
      case 'purple':
        return 'text-purple-400';
      case 'lime':
        return 'text-lime-400';
      case 'green':
        return 'text-green-400';
      case 'amber':
        return 'text-amber-400';
      default:
        return 'text-gray-400';
    }
  };
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric, index) => (
        <div 
          key={metric.label}
          className="relative overflow-hidden rounded-lg p-4 border border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20"
        >
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
          <div className="relative z-10 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">{metric.label}</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">
                {metric.value}
              </p>
              {metric.trend && (
                <div className="mt-2">
                  <TrendIndicator direction={metric.trend} />
                </div>
              )}
            </div>
            <div className={getColorClasses(metric.color)}>
              <metric.icon className="w-8 h-8" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}