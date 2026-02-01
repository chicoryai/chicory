import React, { useState } from "react";
import { CheckCircleIcon, XCircleIcon, ChevronDownIcon } from "@heroicons/react/24/outline";
import { WrenchIcon } from "@heroicons/react/24/solid";
import { truncateMiddle, formatJson, copyToClipboard } from "~/utils/formatting";

interface ToolExecutionCardProps {
  toolName: string;
  toolId: string;
  input: Record<string, any>;
  output?: string | object;
  isError?: boolean;
  timestamp?: string;
  index?: number;
}

/**
 * Improved ToolExecutionCard component with:
 * - Better visual hierarchy with color coding
 * - Prominent status indicators
 * - Path truncation for better readability
 * - Syntax highlighting for JSON
 * - Copy functionality
 * - Smooth animations
 * - Improved spacing and typography
 */
export const ToolExecutionCard: React.FC<ToolExecutionCardProps> = ({
  toolName,
  toolId,
  input,
  output,
  isError = false,
  timestamp,
  index = 0
}) => {
  const [isInputExpanded, setIsInputExpanded] = useState(false);
  const [isOutputExpanded, setIsOutputExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  // Convert output to string
  const outputText = typeof output === 'string'
    ? output
    : output
      ? formatJson(output)
      : '';

  const handleCopy = async (text: string) => {
    await copyToClipboard(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="animate-slide-in opacity-0"
      style={{
        animationDelay: `${index * 50}ms`,
        animationFillMode: 'forwards'
      }}
    >
      <div className={`group rounded-lg border-l-4 bg-white shadow-sm transition-all hover:shadow-md dark:bg-slate-900/50 ${
        isError
          ? 'border-rose-500 dark:border-rose-400'
          : 'border-emerald-500 dark:border-emerald-400'
      }`}>
        <div className="p-4 space-y-3">
          {/* Header with tool name and status */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              {/* Tool icon */}
              <div className={`flex-shrink-0 rounded-lg p-2 ${
                isError
                  ? 'bg-rose-100 dark:bg-rose-900/30'
                  : 'bg-emerald-100 dark:bg-emerald-900/30'
              }`}>
                <WrenchIcon className={`h-5 w-5 ${
                  isError
                    ? 'text-rose-600 dark:text-rose-400'
                    : 'text-emerald-600 dark:text-emerald-400'
                }`} />
              </div>

              {/* Tool name */}
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                  {toolName}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                  {truncateMiddle(toolId, 20)}
                </p>
              </div>
            </div>

            {/* Status badge - larger and more prominent */}
            <div className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold shadow-sm ${
              isError
                ? 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300'
                : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
            }`}>
              {isError ? (
                <>
                  <XCircleIcon className="h-4 w-4" />
                  <span>Failed</span>
                </>
              ) : (
                <>
                  <CheckCircleIcon className="h-4 w-4" />
                  <span>Success</span>
                </>
              )}
            </div>
          </div>

          {/* Tool execution label */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Tool Execution
            </span>
            <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700" />
            {timestamp && (
              <span className="text-xs text-slate-400 dark:text-slate-500">
                {timestamp}
              </span>
            )}
          </div>

          {/* Input section */}
          <div className="space-y-2">
            <button
              onClick={() => setIsInputExpanded(!isInputExpanded)}
              className="flex items-center gap-2 text-sm font-medium text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100 transition-colors"
            >
              <ChevronDownIcon className={`h-4 w-4 transition-transform ${isInputExpanded ? 'rotate-180' : ''}`} />
              <span>Input Parameters</span>
            </button>

            {isInputExpanded && (
              <div className="rounded-lg border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50">
                <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2 dark:border-slate-700">
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-400">JSON</span>
                  <button
                    onClick={() => handleCopy(formatJson(input))}
                    className="text-xs text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
                  >
                    {copied ? '✓ Copied' : 'Copy'}
                  </button>
                </div>
                <pre className="overflow-x-auto p-3 text-xs font-mono text-slate-700 dark:text-slate-300">
                  {formatJson(input)}
                </pre>
              </div>
            )}
          </div>

          {/* Output section */}
          {outputText && (
            <div className="space-y-2">
              <button
                onClick={() => setIsOutputExpanded(!isOutputExpanded)}
                className="flex items-center gap-2 text-sm font-medium text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100 transition-colors"
              >
                <ChevronDownIcon className={`h-4 w-4 transition-transform ${isOutputExpanded ? 'rotate-180' : ''}`} />
                <span>Output</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">({outputText.length} characters)</span>
              </button>

              {isOutputExpanded && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50">
                  <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2 dark:border-slate-700">
                    <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
                      Full Output
                    </span>
                    <button
                      onClick={() => handleCopy(outputText)}
                      className="text-xs text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
                    >
                      {copied ? '✓ Copied' : 'Copy'}
                    </button>
                  </div>
                  <pre className="overflow-x-auto p-3 text-xs font-mono text-slate-700 dark:text-slate-300 max-h-96">
                    {outputText}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
