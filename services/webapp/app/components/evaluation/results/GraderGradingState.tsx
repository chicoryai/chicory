import React from 'react';
import { GraderLoadingHeader } from './GraderLoadingHeader';
import { SkeletonScore, SkeletonBar, SkeletonPulse, SkeletonText } from './skeletons/GraderSkeleton';

interface GraderGradingStateProps {
  criteriaCount?: number;
  showReasoning?: boolean;
}

export const GraderGradingState: React.FC<GraderGradingStateProps> = ({ 
  criteriaCount = 4,
  showReasoning = true 
}) => {
  return (
    <div className="bg-white dark:bg-whitePurple-50/5 backdrop-blur-sm rounded-lg border border-gray-200 dark:border-purple-900/20 overflow-hidden h-full flex flex-col">
      <GraderLoadingHeader />
      
      <div className="p-4 flex-1 overflow-y-auto">
        {/* Overall Score Skeleton */}
        <SkeletonScore />

        {/* Criteria Scores Skeleton */}
        <div className="space-y-2 mb-4">
          <h6 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
            Criteria Breakdown
          </h6>
          <div className="space-y-2 mt-2">
            {Array.from({ length: criteriaCount }).map((_, i) => (
              <SkeletonBar 
                key={i} 
                delay={i * 100}
                progressWidth={60 + (i * 8)} // Varying widths for more realistic look
              />
            ))}
          </div>
        </div>

        {/* Reasoning Skeleton */}
        {showReasoning && (
          <div className="space-y-2">
            <h6 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
              Reasoning
            </h6>
            <SkeletonBar 
              delay={0}
              progressWidth={60}
            />
          </div>
        )}
      </div>
    </div>
  );
};