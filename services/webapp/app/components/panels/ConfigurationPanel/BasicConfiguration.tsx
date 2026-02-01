/**
 * BasicConfiguration Component
 * Form fields for basic agent configuration
 */

import { useCallback } from "react";
import { motion } from "framer-motion";

interface BasicConfigurationProps {
  name: string;
  description: string;
  outputFormat: string;
  onNameChange: (name: string) => void;
  onDescriptionChange: (description: string) => void;
  onOutputFormatChange: (format: string) => void;
}

export function BasicConfiguration({
  name,
  description,
  outputFormat,
  onNameChange,
  onDescriptionChange,
  onOutputFormatChange,
}: BasicConfigurationProps) {
  const handleNameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onNameChange(e.target.value);
    },
    [onNameChange]
  );

  const handleDescriptionChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      onDescriptionChange(e.target.value);
    },
    [onDescriptionChange]
  );


  return (
    <div className="space-y-4">
      {/* Agent Name */}
      <div>
        <label
          htmlFor="agent-name"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          Agent Name
        </label>
        <input
          id="agent-name"
          type="text"
          value={name}
          onChange={handleNameChange}
          placeholder="Enter agent name"
          className="
            w-full px-3 py-2 
            border border-gray-300 dark:border-gray-600 
            rounded-lg
            bg-white dark:bg-gray-700
            text-gray-900 dark:text-white
            placeholder-gray-400 dark:placeholder-gray-500
            focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
            transition-all duration-200
          "
        />
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          A descriptive name for your agent
        </p>
      </div>

      {/* Description */}
      <div>
        <label
          htmlFor="agent-description"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          Description
        </label>
        <textarea
          id="agent-description"
          value={description}
          onChange={handleDescriptionChange}
          placeholder="Describe what your agent does"
          rows={3}
          className="
            w-full px-3 py-2 
            border border-gray-300 dark:border-gray-600 
            rounded-lg
            bg-white dark:bg-gray-700
            text-gray-900 dark:text-white
            placeholder-gray-400 dark:placeholder-gray-500
            focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
            transition-all duration-200
            resize-none
          "
        />
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Brief description of your agent's purpose and capabilities
        </p>
      </div>

      {/* Output Format */}
      <div>
        <label
          htmlFor="output-format"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          Output Format
        </label>
        <textarea
          id="output-format"
          value={outputFormat || ''}
          onChange={(e) => onOutputFormatChange(e.target.value)}
          placeholder="Specify the output format for agent responses (e.g., JSON, Markdown, Plain Text)"
          rows={4}
          className="
            w-full px-3 py-2 
            border border-gray-300 dark:border-gray-600 
            rounded-lg
            bg-white dark:bg-gray-700
            text-gray-900 dark:text-white
            placeholder-gray-400 dark:placeholder-gray-500
            focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent
            transition-all duration-200
            resize-none
          "
        />
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Define how the agent should format its responses
        </p>
      </div>
    </div>
  );
}