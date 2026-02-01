import React from "react";
import { CheckCircleIcon, ClockIcon } from "@heroicons/react/24/outline";
import { MarkdownRenderer } from "~/components/MarkdownRenderer";
import { ThinkingBlock } from "./ThinkingBlock";
import { ToolExecutionCard } from "./ToolExecutionCard";
import { formatTimestamp } from "~/utils/formatting";

interface AgentMessageCardProps {
  agentName?: string;
  status?: 'running' | 'completed' | 'failed';
  timestamp?: string;
  thinking?: string[];
  text?: string;
  tools?: Array<{
    toolName: string;
    toolId: string;
    input: Record<string, any>;
    output?: string | object;
    isError?: boolean;
  }>;
  index?: number;
}

/**
 * Improved AgentMessageCard component with:
 * - Clean visual hierarchy
 * - Status indicators
 * - Timeline view
 * - Organized content sections
 * - Smooth animations
 */
export const AgentMessageCard: React.FC<AgentMessageCardProps> = ({
  agentName = "Agent",
  status = 'completed',
  timestamp,
  thinking = [],
  text,
  tools = [],
  index = 0
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'completed':
        return {
          icon: CheckCircleIcon,
          color: 'text-emerald-600 dark:text-emerald-400',
          bgColor: 'bg-emerald-50 dark:bg-emerald-900/20',
          borderColor: 'border-emerald-200 dark:border-emerald-800',
          label: 'Completed'
        };
      case 'running':
        return {
          icon: ClockIcon,
          color: 'text-blue-600 dark:text-blue-400',
          bgColor: 'bg-blue-50 dark:bg-blue-900/20',
          borderColor: 'border-blue-200 dark:border-blue-800',
          label: 'Running'
        };
      case 'failed':
        return {
          icon: CheckCircleIcon,
          color: 'text-rose-600 dark:text-rose-400',
          bgColor: 'bg-rose-50 dark:bg-rose-900/20',
          borderColor: 'border-rose-200 dark:border-rose-800',
          label: 'Failed'
        };
    }
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;

  return (
    <div
      className="animate-slide-in opacity-0"
      style={{
        animationDelay: `${index * 100}ms`,
        animationFillMode: 'forwards'
      }}
    >
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900/50">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
          <div className="flex items-center gap-3">
            {/* Agent avatar/icon */}
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 text-white font-bold text-sm shadow-lg">
              {agentName.charAt(0).toUpperCase()}
            </div>

            {/* Agent name */}
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-slate-100">
                {agentName}
              </h2>
              {timestamp && (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {formatTimestamp(timestamp)}
                </p>
              )}
            </div>
          </div>

          {/* Status badge */}
          <div className={`flex items-center gap-2 rounded-full border px-3 py-1.5 ${statusConfig.borderColor} ${statusConfig.bgColor}`}>
            <StatusIcon className={`h-4 w-4 ${statusConfig.color}`} />
            <span className={`text-sm font-medium ${statusConfig.color}`}>
              {statusConfig.label}
            </span>
          </div>
        </div>

        {/* Content */}
        <div className="space-y-4 p-6">
          {/* Thinking blocks */}
          {thinking.length > 0 && (
            <div className="space-y-3">
              {thinking.map((thinkContent, idx) => (
                <ThinkingBlock
                  key={`thinking-${idx}`}
                  content={thinkContent}
                  index={idx}
                />
              ))}
            </div>
          )}

          {/* Text content */}
          {text && (
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <MarkdownRenderer
                content={text}
                variant="task"
                className="text-slate-700 dark:text-slate-300"
              />
            </div>
          )}

          {/* Tool executions */}
          {tools.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Tool Executions
                </h3>
                <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700" />
                <span className="text-xs text-slate-400">
                  {tools.length} {tools.length === 1 ? 'tool' : 'tools'}
                </span>
              </div>

              <div className="space-y-3">
                {tools.map((tool, idx) => (
                  <ToolExecutionCard
                    key={`tool-${idx}`}
                    toolName={tool.toolName}
                    toolId={tool.toolId}
                    input={tool.input}
                    output={tool.output}
                    isError={tool.isError}
                    index={idx}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
