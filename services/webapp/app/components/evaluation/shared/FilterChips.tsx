import React from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface FilterChipsProps {
  filters: string[];
  onChange: (filters: string[]) => void;
}

const availableFilters = [
  { id: 'active', label: 'Active', color: 'green' },
  { id: 'completed', label: 'Completed', color: 'blue' },
  { id: 'failed', label: 'Failed', color: 'red' },
  { id: 'recent', label: 'Recent', color: 'purple' }
];

export function FilterChips({ filters, onChange }: FilterChipsProps) {
  const toggleFilter = (filterId: string) => {
    if (filters.includes(filterId)) {
      onChange(filters.filter(f => f !== filterId));
    } else {
      onChange([...filters, filterId]);
    }
  };
  
  return (
    <div className="flex flex-wrap gap-2">
      {availableFilters.map(filter => {
        const isActive = filters.includes(filter.id);
        return (
          <button
            key={filter.id}
            onClick={() => toggleFilter(filter.id)}
            className={`
              px-3 py-1 rounded-full text-sm font-medium transition-all
              ${isActive
                ? 'bg-purple-100 dark:bg-purple-400/20 text-purple-700 dark:text-purple-300 border border-purple-300 dark:border-purple-400/30'
                : 'bg-gray-100 dark:bg-whitePurple-50/5 text-gray-700 dark:text-gray-400 border border-gray-300 dark:border-purple-900/20 hover:border-purple-300 dark:hover:border-purple-400/30'
              }
            `}
          >
            {filter.label}
            {isActive && (
              <XMarkIcon className="inline-block w-3 h-3 ml-1" />
            )}
          </button>
        );
      })}
    </div>
  );
}