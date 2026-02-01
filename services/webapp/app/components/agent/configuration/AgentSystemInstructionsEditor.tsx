import { clsx } from "clsx";
import type { ReactNode } from "react";

const MAX_CHARS = 20000;

type AgentSystemInstructionsEditorProps = {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  placeholder?: string;
  label?: string;
  description?: string;
  editorKey?: string | number;
  variant?: 'card' | 'sidebar';
  actions?: ReactNode;
};

export function AgentSystemInstructionsEditor({
  value,
  onChange,
  className,
  placeholder = "Include specific instructions, examples, and constraints in agent prompt. The more guidance you provide, the better the agent will perform.",
  label = "Agent Prompt",
  description = "Provide the agent with detailed guidance.",
  editorKey,
  variant = 'card',
  actions,
}: AgentSystemInstructionsEditorProps) {
  const charCount = value.length;
  const isOverLimit = charCount > MAX_CHARS;
  const isNearLimit = charCount > MAX_CHARS * 0.9; // 90% of limit

  const containerClasses = clsx(
    "flex min-h-0 flex-col",
    variant === 'sidebar'
      ? "gap-4 rounded-2xl bg-white/95 dark:bg-slate-900 p-1"
      : "h-full rounded-2xl border border-slate-200/80 bg-white p-1 dark:border-slate-800 dark:bg-slate-900",
    className
  );

  return (
    <div className={containerClasses}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h2 className={clsx(
            "text-sm font-semibold uppercase tracking-[0.2em]",
            variant === 'sidebar' ? "text-slate-500 dark:text-slate-200" : "text-slate-400"
          )}>
            {label}
          </h2>
          {description && (
            <p
              className={clsx(
                "mt-2 text-sm",
                variant === 'sidebar'
                  ? "text-slate-500 dark:text-slate-300"
                  : "text-slate-500 dark:text-slate-400"
              )}
            >
              {description}
            </p>
          )}
        </div>
        {actions ? (
          <div className="flex shrink-0 items-center gap-2 self-start">
            {actions}
          </div>
        ) : null}
      </div>
      <div
        className={clsx(
          variant === 'sidebar'
            ? "mt-3 flex-1 min-h-0"
            : "mt-4 flex-1 min-h-0"
        )}
      >
        <textarea
          key={editorKey}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          rows={variant === 'sidebar' ? 12 : 10}
          className={clsx(
            "guidance-scroll w-full rounded-2xl border border-slate-200 bg-white text-base text-slate-900 transition duration-150 placeholder:text-slate-400 focus:outline-none hover:border-slate-300 focus:border-purple-500 focus:ring-1 focus:ring-purple-300/70 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100 dark:hover:border-slate-700 dark:focus:border-purple-400 dark:focus:ring-purple-400/40",
            variant === 'sidebar'
              ? "h-full min-h-[320px] resize-none px-6 py-6 pr-8 shadow-sm"
              : "min-h-[240px] resize-y px-4 py-4 shadow-sm",
            isOverLimit && "border-red-500 focus:border-red-500 focus:ring-red-300/70 dark:border-red-500 dark:focus:border-red-400 dark:focus:ring-red-400/40"
          )}
        />
        <div className="mt-2 flex items-center justify-between px-2 text-xs">
          <span className={clsx(
            "font-medium",
            isOverLimit
              ? "text-red-600 dark:text-red-400"
              : isNearLimit
                ? "text-yellow-600 dark:text-yellow-400"
                : "text-slate-500 dark:text-slate-400"
          )}>
            {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters
          </span>
          {isOverLimit && (
            <span className="font-semibold text-red-600 dark:text-red-400">
              {(charCount - MAX_CHARS).toLocaleString()} over limit
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default AgentSystemInstructionsEditor;
