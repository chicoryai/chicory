import { clsx } from "clsx";
import { forwardRef } from "react";

type AgentOutputFormatEditorProps = {
  value: string;
  onChange: (value: string) => void;
  textAreaId?: string;
  className?: string;
  placeholder?: string;
  label?: string;
  description?: string;
  rows?: number;
  variant?: 'card' | 'sidebar';
};

export const AgentOutputFormatEditor = forwardRef<HTMLTextAreaElement, AgentOutputFormatEditorProps>(
  function AgentOutputFormatEditor(
    {
      value,
      onChange,
      textAreaId = "output-format",
      className,
      placeholder = "e.g. Provide answers as JSON with keys: title, summary, and recommended_actions",
      label = "Output Format",
      description = "Define the structure, schema, or format for agent responses. Be specific about data types and required fields.",
      rows = 6,
      variant = 'card'
    },
    ref
  ) {
    const containerClasses = clsx(
      'flex flex-col',
      variant === 'sidebar'
        ? 'relative z-10 min-h-0 space-y-4 rounded-2xl bg-white/95 p-1 dark:bg-slate-900'
        : 'rounded-2xl border border-slate-200/80 bg-white p-1 dark:border-slate-800 dark:bg-slate-900'
    );

    const textAreaClasses = variant === 'sidebar'
      ? "w-full resize-none rounded-xl border border-slate-200/80 bg-white px-4 py-3 text-base text-slate-900 focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-200 placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
      : "w-full resize-none rounded-xl border border-slate-200/80 bg-slate-50 px-4 py-3 text-base text-slate-800 focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-200 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";

    return (
      <div className={clsx(containerClasses, className)}>
        <div className="space-y-2">
          <h2 className={clsx(
            "text-sm font-semibold uppercase tracking-[0.2em]",
            variant === 'sidebar' ? "text-slate-500 dark:text-slate-200" : "text-slate-400 dark:text-slate-400"
          )}>
            {label}
          </h2>
          {description && (
            <p className={clsx(
              "mt-2 text-sm",
              variant === 'sidebar' ? "text-slate-500 dark:text-slate-400" : "text-slate-500 dark:text-slate-400"
            )}>
              {description}
            </p>
          )}
        </div>
        <textarea
          id={textAreaId}
          ref={ref}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          rows={rows}
          className={textAreaClasses}
          placeholder={placeholder}
        />
      </div>
    );
  }
);

export default AgentOutputFormatEditor;
