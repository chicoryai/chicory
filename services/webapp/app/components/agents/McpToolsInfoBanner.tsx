/**
 * MCP Tools Info Banner Component
 * Educates users about building agents using the MCP Tools approach
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CommandLineIcon,
  ChevronDownIcon,
  SparklesIcon,
  ArrowTopRightOnSquareIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";

interface McpToolsInfoBannerProps {
  className?: string;
  defaultExpanded?: boolean;
  onDismiss?: () => void;
}

const MCP_DOCS_URL = "https://docs.chicory.ai/getting-started/getting-started/building-your-first-agent/1-agent-creation#getting-started-with-mcp-tools";

export function McpToolsInfoBanner({
  className = "",
  defaultExpanded = false,
  onDismiss,
}: McpToolsInfoBannerProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [isDismissed, setIsDismissed] = useState(false);

  if (isDismissed) {
    return null;
  }

  const handleDismiss = () => {
    setIsDismissed(true);
    onDismiss?.();
  };

  return (
    <div
      className={`
        relative overflow-hidden rounded-xl
        border border-gray-200 dark:border-gray-700
        bg-white dark:bg-gray-800
        shadow-sm
        ${className}
      `}
    >

      {/* Header - Always visible */}
      <div className="relative z-10">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between gap-3 text-left hover:bg-purple-50/50 dark:hover:bg-purple-900/20 transition-colors duration-200 rounded-t-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-inset"
          aria-expanded={isExpanded}
        >
          <div className="flex items-center gap-3">
            <div className="flex-shrink-0 p-1.5 rounded-lg bg-purple-100 dark:bg-purple-900/50">
              <CommandLineIcon className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                Build Agents with MCP Tools
                <SparklesIcon className="w-4 h-4 text-purple-500" />
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Use natural language in Claude Desktop, VS Code, or any MCP-compatible IDE
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <motion.div
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronDownIcon className="w-5 h-5 text-gray-400 dark:text-gray-500" />
            </motion.div>
            {onDismiss && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDismiss();
                }}
                className="p-1 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                aria-label="Dismiss"
              >
                <XMarkIcon className="w-4 h-4 text-gray-400" />
              </button>
            )}
          </div>
        </button>

        {/* Expandable Content */}
        <AnimatePresence initial={false}>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="px-4 pb-4 pt-1 space-y-4">
                {/* Overview */}
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Chicory provides MCP tools for agent management. Connect your preferred LLM interface and build agents conversationally.
                </p>

                {/* Available Tools */}
                <div className="space-y-2">
                  <h4 className="text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                    Available MCP Tools
                  </h4>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { name: "projects", desc: "Access organization context" },
                      { name: "agents", desc: "Agent lifecycle management" },
                      { name: "tasks", desc: "Task execution & results" },
                      { name: "evaluation", desc: "Testing & validation" },
                    ].map((tool) => (
                      <div
                        key={tool.name}
                        className="flex items-start gap-2 p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50"
                      >
                        <code className="text-xs font-mono text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/30 px-1.5 py-0.5 rounded">
                          {tool.name}
                        </code>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {tool.desc}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Getting Started Steps */}
                <div className="space-y-2.5">
                  <h4 className="text-xs font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                    Getting Started
                  </h4>
                  <ol className="space-y-2">
                    {[
                      {
                        step: "1",
                        title: "Connect MCP Tools",
                        description:
                          "Install Chicory MCP server and configure with your API token",
                      },
                      {
                        step: "2",
                        title: "Verify Context",
                        description:
                          "Use chicory_get_context to access your organization's data sources",
                      },
                      {
                        step: "3",
                        title: "Create Your Agent",
                        description:
                          'Describe what you want: "Create an agent that helps users query our data warehouse"',
                      },
                      {
                        step: "4",
                        title: "Test & Deploy",
                        description:
                          "Use chicory_execute_agent to test, then deploy to production",
                      },
                    ].map((item) => (
                      <li key={item.step} className="flex gap-3">
                        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400 text-xs font-semibold flex items-center justify-center">
                          {item.step}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                            {item.title}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {item.description}
                          </p>
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>

                {/* Benefits */}
                <div className="flex flex-wrap gap-2">
                  {[
                    "Natural Language",
                    "Rapid Iteration",
                    "Full Platform Access",
                    "Local Validation",
                  ].map((benefit) => (
                    <span
                      key={benefit}
                      className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-purple-100/70 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300"
                    >
                      {benefit}
                    </span>
                  ))}
                </div>

                {/* CTA */}
                <div className="pt-2 border-t border-purple-100 dark:border-purple-800/50">
                  <a
                    href={MCP_DOCS_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-sm font-medium text-purple-600 hover:text-purple-700 dark:text-purple-400 dark:hover:text-purple-300 transition-colors group"
                  >
                    View full documentation
                    <ArrowTopRightOnSquareIcon className="w-4 h-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </a>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default McpToolsInfoBanner;
