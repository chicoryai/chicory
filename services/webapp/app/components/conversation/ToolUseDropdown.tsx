/**
 * ToolUseDropdown Component
 * Collapsible section showing tool execution with status indicators
 */

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronRightIcon,
  WrenchScrewdriverIcon,
  CheckIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { collapsibleVariants, contentBlockVariants, easeInVariants } from "~/components/animations/transitions";

interface ToolUseDropdownProps {
  id: string;
  name: string;
  input: Record<string, unknown>;
  output: string | null;
  isError: boolean;
  isExecuting?: boolean; // Explicitly passed when streaming; defaults to false for persisted messages
  defaultExpanded?: boolean;
  isStreaming?: boolean;
  activeDescription?: string; // Human-readable description shown while tool is executing
}

export function ToolUseDropdown({
  name,
  input,
  output,
  isError,
  isExecuting = false, // Default to complete (not executing) for persisted messages
  defaultExpanded = false,
  isStreaming = false,
  activeDescription,
}: ToolUseDropdownProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const handleToggle = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  // Use activeDescription when available, otherwise fall back to input.description or name
  const description = activeDescription
    ? activeDescription
    : typeof input.description === "string"
      ? input.description
      : name;

  return (
    <motion.div
      variants={isStreaming ? contentBlockVariants : easeInVariants}
      initial="hidden"
      animate="visible"
      className="my-2"
    >
      {/* Header button */}
      <button
        onClick={handleToggle}
        className={`flex items-center gap-3 w-full text-left text-sm py-2.5 px-3 rounded-t-lg bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors focus:outline-none ${
          !isExpanded ? "rounded-b-lg border-b-1 border-gray-300 dark:border-gray-700" : ""
        }`}
        aria-expanded={isExpanded}
      >
        <motion.div
          animate={{ rotate: isExpanded ? 90 : 0 }}
          transition={{ duration: 0.2 }}
          className="flex-shrink-0"
        >
          <ChevronRightIcon className="h-4 w-4 text-gray-500" />
        </motion.div>

        <WrenchScrewdriverIcon className="h-4 w-4 text-purple-500 flex-shrink-0" />
        <span className="text-gray-600 dark:text-gray-300 truncate flex-1">
          {description}
        </span>

        {/* Status indicator */}
        <div className="flex-shrink-0 ml-2">
          {isExecuting ? (
            <svg
              className="h-4 w-4 animate-spin text-purple-500"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          ) : isError ? (
            <XMarkIcon className="h-4 w-4 text-rose-500" />
          ) : (
            <CheckIcon className="h-4 w-4 text-emerald-500" />
          )}
        </div>
      </button>

      {/* Expandable content */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            variants={collapsibleVariants}
            initial="collapsed"
            animate="expanded"
            exit="collapsed"
            className="overflow-hidden"
          >
            <div className="">
              {/* Input section */}
              <div className="rounded-b-md border-t-0 border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                <div className="px-2 py-1 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Input
                  </span>
                </div>
                <pre className="p-2 text-xs font-mono text-gray-700 dark:text-gray-300 overflow-x-auto max-h-40">
                  {JSON.stringify(input, null, 2)}
                </pre>
              </div>

              {/* Output section (only show when available) */}
              {output !== null && (
                <div
                  className={`rounded-md border ${
                    isError
                      ? "border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-900/20"
                      : "border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50"
                  }`}
                >
                  <div
                    className={`px-2 py-1 border-b ${
                      isError
                        ? "border-rose-200 dark:border-rose-800"
                        : "border-gray-200 dark:border-gray-700"
                    }`}
                  >
                    <span
                      className={`text-[10px] font-medium uppercase tracking-wider ${
                        isError
                          ? "text-rose-600 dark:text-rose-400"
                          : "text-gray-500 dark:text-gray-400"
                      }`}
                    >
                      Output {isError && "(Error)"}
                    </span>
                  </div>
                  <pre
                    className={`p-2 text-xs font-mono overflow-x-auto max-h-60 ${
                      isError
                        ? "text-rose-700 dark:text-rose-300"
                        : "text-gray-700 dark:text-gray-300"
                    }`}
                  >
                    {typeof output === "string"
                      ? output
                      : JSON.stringify(output, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
