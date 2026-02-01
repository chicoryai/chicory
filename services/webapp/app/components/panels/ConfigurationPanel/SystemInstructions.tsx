/**
 * SystemInstructions Component
 * Textarea for system prompt configuration
 */

import { useCallback, useEffect, useState } from "react";

interface SystemInstructionsProps {
  value: string;
  onChange: (value: string) => void;
}

export function SystemInstructions({ value, onChange }: SystemInstructionsProps) {
  const [charCount, setCharCount] = useState(value.length);

  useEffect(() => {
    setCharCount(value.length);
  }, [value]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value;
      setCharCount(newValue.length);
      onChange(newValue);
    },
    [onChange]
  );

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-1">
        <label
          htmlFor="system-instructions"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          System Prompt
        </label>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {charCount} characters
        </span>
      </div>
      
      <textarea
        id="system-instructions"
        value={value}
        onChange={handleChange}
        placeholder="You are a helpful AI assistant..."
        rows={8}
        className="
          w-full px-3 py-2 
          border border-gray-300 dark:border-gray-600 
          rounded-lg
          bg-white dark:bg-gray-700
          text-gray-900 dark:text-white
          placeholder-gray-400 dark:placeholder-gray-500
          focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
          transition-all duration-200
          font-mono text-sm
        "
      />
      
      <p className="text-xs text-gray-500 dark:text-gray-400">
        Define the agent's behavior, personality, and capabilities. This prompt is sent with every request.
      </p>
    </div>
  );
}
