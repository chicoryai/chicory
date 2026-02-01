import React, { useState } from "react";
import { ChevronDownIcon, ChevronRightIcon } from "@heroicons/react/24/outline";

interface ToolExecutionItemProps {
  toolId: string;
  toolName: string;
  input: Record<string, any>;
  result?: any;
  isError?: boolean;
}

/**
 * Component for displaying tool execution (Tool Use + Tool Result fused together)
 * Extracted from AuditTrailItem for reuse in streaming contexts
 */
export const ToolExecutionItem: React.FC<ToolExecutionItemProps> = ({
  toolId,
  toolName,
  input,
  result,
  isError = false
}) => {
  const [inputExpanded, setInputExpanded] = useState(false);
  const [outputExpanded, setOutputExpanded] = useState(false);

  const toggleInput = () => setInputExpanded(prev => !prev);
  const toggleOutput = () => setOutputExpanded(prev => !prev);

  // Convert result to string for display
  let resultText = "";
  if (result !== undefined && result !== null) {
    if (typeof result === "string") {
      resultText = result;
    } else if (Array.isArray(result)) {
      resultText = JSON.stringify(result[0] ?? result, null, 2);
    } else if (typeof result === "object") {
      resultText = JSON.stringify(result, null, 2);
    } else {
      resultText = String(result);
    }
  }

  const shouldShowToggle = resultText.length > 240;
  const displayResult = outputExpanded || !shouldShowToggle
    ? resultText
    : resultText.slice(0, 240) + (resultText.length > 240 ? "…" : "");

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-purple-700 dark:text-purple-200">
          {toolName}
        </span>
        <button
          onClick={toggleInput}
          className="rounded border border-purple-200 px-2 py-0.5 text-xs text-purple-500 hover:border-purple-400 hover:text-purple-600 dark:border-purple-400/50 dark:text-purple-200"
        >
          {inputExpanded ? "Hide input" : "View input"}
        </button>
      </div>

      {/* Status badge and tool ID */}
      {resultText && (
        <div className="flex items-center gap-2 text-xs font-medium">
          <span
            className={`rounded-full px-2 py-0.5 ${
              isError
                ? 'bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:text-rose-200'
                : 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-200'
            }`}
          >
            {isError ? 'Failed' : 'Succeeded'}
          </span>
          <span className="text-gray-500 dark:text-gray-400">
            {toolId.slice(0, 8)}…
          </span>
        </div>
      )}

      {/* Tool input (expandable) */}
      {inputExpanded && (
        <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 shadow-sm shadow-slate-900/5 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-200">
          <pre className="whitespace-pre-wrap">
            {JSON.stringify(input, null, 2)}
          </pre>
        </div>
      )}

      {/* Tool result/output (expandable with truncation) */}
      {resultText && (
        <div className="space-y-1">
          <pre className="whitespace-pre-wrap rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 shadow-sm shadow-slate-900/5 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-200">
            {displayResult}
          </pre>
          {shouldShowToggle && (
            <button
              onClick={toggleOutput}
              className="text-xs font-medium text-purple-600 hover:text-purple-700 dark:text-purple-300"
            >
              {outputExpanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>
      )}
    </div>
  );
};
