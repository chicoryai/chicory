import React, { useState } from "react";
import { ChevronDownIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import { GiBrain } from "react-icons/gi";

interface ThinkingBlockProps {
  content: string;
  index?: number;
  autoExpand?: boolean;
}

/**
 * Improved ThinkingBlock component with:
 * - GiBrain icon for better visual identity
 * - Smooth animations on render
 * - Better color scheme (lighter, more subtle)
 * - Collapsible with summary
 * - Improved typography and spacing
 */
export const ThinkingBlock: React.FC<ThinkingBlockProps> = ({
  content,
  index = 0,
  autoExpand = false
}) => {
  const [isExpanded, setIsExpanded] = useState(autoExpand);

  const shouldShowToggle = content.length > 200;
  const summary = content.slice(0, 200) + (content.length > 200 ? "..." : "");

  return (
    <div
      className="group animate-slide-in opacity-0"
      style={{
        animationDelay: `${index * 50}ms`,
        animationFillMode: 'forwards'
      }}
    >
      {/* Clickable header for full block expansion */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full rounded-lg border border-slate-200 bg-white p-4 text-left shadow-sm transition-all hover:shadow-md dark:border-slate-700 dark:bg-slate-900/50 dark:hover:border-slate-600"
      >
        <div className="flex items-start gap-3">
          {/* Brain icon with subtle animation */}
          <div className="flex-shrink-0 rounded-lg bg-slate-100 p-2 dark:bg-slate-800">
            <GiBrain className="h-5 w-5 text-indigo-600 transition-transform group-hover:scale-110 dark:text-indigo-400" />
          </div>

          {/* Content area */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Thinking
              </h3>
              <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700" />
              {shouldShowToggle && (
                <ChevronRightIcon
                  className={`h-4 w-4 text-slate-500 transition-transform dark:text-slate-400 ${
                    isExpanded ? 'rotate-90' : ''
                  }`}
                />
              )}
            </div>

            {/* Preview or full content */}
            {!isExpanded && shouldShowToggle ? (
              <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                {summary}
              </p>
            ) : (
              <div className="space-y-2">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/40">
                  <pre className="whitespace-pre-wrap font-body text-sm leading-relaxed text-slate-700 dark:text-slate-200">
                    {content}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </button>
    </div>
  );
};
