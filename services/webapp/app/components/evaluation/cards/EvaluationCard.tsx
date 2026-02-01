import React from 'react';
import type { Evaluation } from '~/services/chicory.server';
import { StatusBadge, type EvaluationStatus } from '~/components/evaluation/StatusBadge';
import { PlayIcon, TrashIcon } from '@heroicons/react/24/outline';

interface EvaluationCardProps {
  evaluation: Evaluation;
  selected: boolean;
  lastRun?: {
    score: number;
    status: string;
    date: string;
  };
  activeRun?: {
    id: string;
    status: string;
    completed: number;
    total: number;
  };
  onSelect: (id: string) => void;
  onRun: (id: string) => void;
  onDelete: (id: string) => void;
}

export function EvaluationCard({ 
  evaluation, 
  selected, 
  lastRun,
  activeRun,
  onSelect, 
  onRun,
  onDelete 
}: EvaluationCardProps) {
  const isRunning = activeRun?.status === 'running';
  const progress = activeRun && activeRun.total > 0 
    ? (activeRun.completed / activeRun.total) * 100 
    : 0;
  return (
    <div 
      className={`
        relative overflow-hidden rounded-lg p-2 border transition-all cursor-pointer
        ${selected 
          ? 'border-purple-400 shadow-lg shadow-purple-400/20' 
          : 'border-whitePurple-100/50 dark:border-whitePurple-200/30 shadow-md shadow-whitePurple-50/50 dark:shadow-purple-900/20 hover:border-purple-300 dark:hover:border-purple-400/50'
        }
      `}
      onClick={() => onSelect(evaluation.id)}
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
      {/* Glowing border effect when selected */}
      {selected && (
        <div className="absolute inset-0 rounded-lg bg-gradient-to-r from-purple-400/10 to-lime-400/5 dark:from-purple-400/20 dark:to-lime-400/10" />
      )}
      
      <div className="relative z-10 flex items-center justify-between">
        {/* Left Content - Name, Status, Date */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-gray-900 dark:text-gray-100 text-sm truncate" title={evaluation.name}>
                {evaluation.name}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {new Date(evaluation.created_at).toLocaleDateString()}
              </span>
              {isRunning && (
                <span className="text-xs text-purple-600 dark:text-purple-400 font-medium animate-pulse">
                  {activeRun.total} tests
                </span>
              )}
            </div>
          </div>
        </div>
        
        {/* Right Content - Actions */}
        <div className="flex items-center gap-2">
          {/* Actions */}
          <div className="flex items-center gap-1">
            <button
              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={(e) => {
                e.stopPropagation();
                if (!isRunning) {
                  onRun(evaluation.id);
                }
              }}
              disabled={isRunning}
              title={isRunning ? "Evaluation is running" : "Run evaluation"}
            >
              <PlayIcon className={`w-4 h-4 ${isRunning ? 'text-gray-400 dark:text-gray-600' : 'text-purple-600 dark:text-purple-400'}`} />
            </button>
            <button
              className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors group"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(evaluation.id);
              }}
              title="Delete evaluation"
            >
              <TrashIcon className="w-4 h-4 text-gray-500 dark:text-gray-400 group-hover:text-red-600 dark:group-hover:text-red-400 transition-colors" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}