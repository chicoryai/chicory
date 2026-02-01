/**
 * ThinkingDropdown Component
 * Collapsible section showing assistant's thinking process
 */

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRightIcon, LightBulbIcon } from "@heroicons/react/24/outline";
import { collapsibleVariants, contentBlockVariants, easeInVariants } from "~/components/animations/transitions";

interface ThinkingDropdownProps {
  thinking: string;
  signature?: string;
  defaultExpanded?: boolean;
  isStreaming?: boolean;
}

export function ThinkingDropdown({
  thinking,
  defaultExpanded = false,
  isStreaming = false,
}: ThinkingDropdownProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const handleToggle = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  return (
    <motion.div
      variants={isStreaming ? contentBlockVariants : easeInVariants}
      initial="hidden"
      animate="visible"
      className="mb-2"
    >
      {/* Header button */}
      <button
        onClick={handleToggle}
        className="flex items-center gap-3 text-sm text-violet-600 dark:text-violet-400 hover:text-violet-700 dark:hover:text-violet-300 transition-colors py-2.5 px-3 rounded-lg bg-violet-50 dark:bg-violet-900/20"
        aria-expanded={isExpanded}
      >
        <motion.div
          animate={{ rotate: isExpanded ? 90 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronRightIcon className="h-4 w-4" />
        </motion.div>
        <LightBulbIcon className="h-4 w-4" />
        <span className="font-medium">Thinking</span>
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
            <div className="mt-3 pl-5 text-sm text-gray-600 dark:text-gray-400 border-l-2 border-violet-200 dark:border-violet-800">
              <pre className="whitespace-pre-wrap font-sans leading-relaxed">
                {thinking}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
