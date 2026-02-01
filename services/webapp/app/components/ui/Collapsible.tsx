/**
 * Collapsible Section Component
 * Reusable collapsible container with animations
 */

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRightIcon } from "@heroicons/react/24/outline";
import type { CollapsibleSectionProps } from "~/types/panels";
import { collapsibleVariants } from "~/components/animations/transitions";

export function CollapsibleSection({
  title,
  defaultOpen = false,
  children,
  icon,
  badge,
  className = "",
  onToggle,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const handleToggle = useCallback(() => {
    const newState = !isOpen;
    setIsOpen(newState);
    onToggle?.(newState);
  }, [isOpen, onToggle]);

  return (
    <div
      className={`
        relative rounded-lg border border-whitePurple-100/70 dark:border-whitePurple-200/30 
        shadow-md shadow-whitePurple-100/50 dark:shadow-purple-900/20
        ${className}
      `}
    >
      {/* Light mode gradient */}
      <div 
        className="absolute inset-0 dark:hidden pointer-events-none rounded-lg"
        style={{
          background: 'radial-gradient(circle at center, rgba(255, 255, 255, 0.9) 95%, rgba(245, 243, 255, 0.6) 100%)',
        }}
      />
      {/* Dark mode gradient */}
      <div 
        className="absolute inset-0 hidden dark:block pointer-events-none rounded-lg"
        style={{
          background: 'radial-gradient(circle at center, rgba(17, 24, 39, 0.9) 95%, rgba(88, 28, 135, 0.2) 100%)',
        }}
      />
      
      {/* Header */}
      <button
        onClick={handleToggle}
        className="
          relative z-10 w-full px-4 py-3 
          flex items-center justify-between
          hover:bg-white/20 dark:hover:bg-gray-700/20
          transition-colors duration-200 rounded-t-lg
          focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-inset
        "
        aria-expanded={isOpen}
        aria-controls={`${title}-content`}
      >
        <div className="flex items-center gap-3">
          {/* Chevron icon with rotation */}
          <motion.div
            animate={{ rotate: isOpen ? 90 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronRightIcon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          </motion.div>

          {/* Custom icon */}
          {icon && (
            <span className="text-gray-500 dark:text-gray-400">
              {icon}
            </span>
          )}

          {/* Title */}
          <h3 className="text-sm font-medium text-gray-900 dark:text-white">
            {title}
          </h3>

          {/* Badge */}
          {badge !== undefined && (
            <span className="
              inline-flex items-center justify-center
              px-2 py-0.5 text-xs font-medium rounded-full
              bg-purple-100 text-purple-800 
              dark:bg-purple-900 dark:text-purple-200
            ">
              {badge}
            </span>
          )}
        </div>
      </button>

      {/* Content */}
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            id={`${title}-content`}
            variants={collapsibleVariants}
            initial="collapsed"
            animate="expanded"
            exit="collapsed"
            className="relative z-10 overflow-hidden"
          >
            <div className="px-4 pb-4 pt-2">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}