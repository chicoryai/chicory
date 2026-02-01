import React from 'react';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

interface GraderResponse {
  score: number;
  reasoning: string;
  criteria_scores?: {
    helpfulness?: number;
    accuracy?: number;
    completeness?: number;
    tone?: number;
  };
}

interface CriteriaBarProps {
  label: string;
  score: number;
}

function CriteriaBar({ label, score }: CriteriaBarProps) {
  const percentage = Math.round(score * 100);
  const getColor = () => {
    if (score >= 0.8) return 'bg-green-400';
    if (score >= 0.6) return 'bg-yellow-400';
    return 'bg-red-400';
  };

  // Format label: replace underscores with spaces and capitalize each word
  const formatLabel = (str: string) => {
    return str
      .replace(/_/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-xs text-gray-600 dark:text-gray-400 shrink-0">
        {formatLabel(label)}:
      </span>
      <div className="flex items-center gap-2">
        <div className="w-56 h-1.5 bg-gray-200 dark:bg-purple-900/20 rounded-full overflow-hidden">
          <div 
            className={`h-full ${getColor()} transition-all duration-300`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-10 text-right">
          {percentage}%
        </span>
      </div>
    </div>
  );
}

interface GraderSuccessStateProps {
  parsedResponse: GraderResponse;
  showFullReasoning: boolean;
  onToggleReasoning: () => void;
}

export const GraderSuccessState: React.FC<GraderSuccessStateProps> = ({ 
  parsedResponse,
  showFullReasoning,
  onToggleReasoning
}) => {
  const overallPercentage = Math.round(parsedResponse.score * 100);
  const getScoreColor = () => {
    if (parsedResponse.score >= 0.8) return 'text-green-500';
    if (parsedResponse.score >= 0.6) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getScoreBgColor = () => {
    if (parsedResponse.score >= 0.8) return 'bg-green-500/10';
    if (parsedResponse.score >= 0.6) return 'bg-yellow-500/10';
    return 'bg-red-500/10';
  };

  return (
    <div className="bg-white dark:bg-whitePurple-50/5 backdrop-blur-sm rounded-lg border border-gray-200 dark:border-purple-900/20 overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 dark:bg-purple-900/10 border-b border-gray-200 dark:border-purple-900/20">
        <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Grader Evaluation
        </h5>
      </div>

      {/* Content */}
      <div className="p-4 flex-1 overflow-y-auto">
        {/* Overall Score */}
        <div className={`inline-flex items-center justify-center w-20 h-20 rounded-full ${getScoreBgColor()} mb-4`}>
          <span className={`text-2xl font-bold ${getScoreColor()}`}>
            {overallPercentage}%
          </span>
        </div>

        {/* Criteria Scores */}
        {parsedResponse.criteria_scores && Object.keys(parsedResponse.criteria_scores).length > 0 && (
          <div className="space-y-2 mb-4 flex flex-col justify-between">
            <h6 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
              Criteria Breakdown
            </h6>
            {Object.entries(parsedResponse.criteria_scores).map(([key, value]) => (
              value !== undefined && (
                <CriteriaBar key={key} label={key} score={value} />
              )
            ))}
          </div>
        )}

        {/* Reasoning */}
        {parsedResponse.reasoning && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h6 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                Reasoning
              </h6>
              {parsedResponse.reasoning.length > 200 && (
                <button
                  onClick={onToggleReasoning}
                  className="flex items-center gap-1 text-xs text-purple-400 hover:text-purple-300 transition-colors"
                >
                  {showFullReasoning ? (
                    <>
                      Show less <ChevronUpIcon className="w-3 h-3" />
                    </>
                  ) : (
                    <>
                      Show more <ChevronDownIcon className="w-3 h-3" />
                    </>
                  )}
                </button>
              )}
            </div>
            <p className={`text-sm text-gray-700 dark:text-gray-300 leading-relaxed ${
              !showFullReasoning && parsedResponse.reasoning.length > 200 ? 'line-clamp-3' : ''
            }`}>
              {parsedResponse.reasoning}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};